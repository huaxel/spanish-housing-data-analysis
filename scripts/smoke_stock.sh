#!/usr/bin/env bash
# Runtime contract for the physical-stock pilot. No production-data edits.
# Usage: bash scripts/smoke_stock.sh [BASE_URL]
set -euo pipefail
BASE="${1:-http://127.0.0.1:3000}"
SESSION="housing-stock-smoke"
if ! command -v playwright-cli >/dev/null; then
  echo "Browser validation unavailable: playwright-cli is required"
  exit 2
fi
trap 'playwright-cli -s="$SESSION" close >/dev/null 2>&1 || true' EXIT
expected="$(uv run python - <<'PY'
import json
import duckdb
from spanish_housing.data_paths import PROCESSED
with duckdb.connect(str(PROCESSED / 'stock.duckdb'), read_only=True) as con:
    rows = con.execute('select match_status,count(*),sum(dwelling_properties) '
                       'from buildings group by match_status order by match_status').fetchall()
    map_count = con.execute('select count(*) from barrios where area_km2 is not null').fetchone()[0]
from pathlib import Path
report = json.loads(Path('artifacts/stock_rent_descriptive.json').read_text())
print(json.dumps({'coverage': rows, 'map_count': map_count,
                  'reader_summary': report['results']['lectura_stock_renta'],
                  'weighted_dates': report['results']['stock_fechas_sensibilidad'],
                  'omission_summary': report['results']['resumen_omision_stock_ingreso'],
                  'omissions': report['results']['omision_distrito_stock_ingreso'],
                  'income': report['results']['sensibilidad_stock_ingreso'],
                  'associations': report['results']['asociaciones_stock_renta']}))
PY
)"
# Start blank: navigating twice can abort the first map fetch and log a false error.
playwright-cli -s="$SESSION" open about:blank >/dev/null
output="$(playwright-cli -s="$SESSION" run-code "async (page) => {
  const errors = [];
  let geometryLoaded = false;
  page.on('pageerror', e => errors.push(String(e)));
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('response', r => {
    if (r.url().includes('/geo/sevilla_barrios.geojson')) geometryLoaded = r.status() === 200;
  });
  await page.goto('$BASE/stock/', { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => [...document.querySelectorAll('table')]
    .filter(t => t.innerText.includes('Asignación espacial'))
    .some(t => [...t.querySelectorAll('tr')].filter(r => r.querySelector('td')).length > 1),
    null, { timeout: 45000 });
  const table = page.locator('table').filter({ hasText: 'Asignación espacial' }).last();
  const cells = await table.locator('tr').evaluateAll(rows => rows.map(row =>
    [...row.querySelectorAll('td')].map(cell => cell.innerText)));
  const coverage = cells.filter(row => row.length >= 4).map(row =>
    [row[0].trim(), Number(row[1].replace(/[^0-9]/g, '')), Number(row[3].replace(/[^0-9]/g, ''))]);
  coverage.sort((a, b) => a[0].localeCompare(b[0]));
  const expected = $expected;
  if (JSON.stringify(coverage) !== JSON.stringify(expected.coverage))
    throw Error('Coverage differs from the pinned sidecar: ' + JSON.stringify(coverage));
  await page.locator('.leaflet-overlay-pane path').first().waitFor({ timeout: 30000 });
  await page.waitForTimeout(3000);
  if (!geometryLoaded) throw Error('Barrio geometry did not load successfully');
  const text = await page.locator('body').innerText();
  for (const phrase of ['Superficie construida: separar parcelas pequeñas y grandes conjuntos', 'Mediana año mínimo por registro',
      'Cambio neto de hogares', 'Sin año mínimo válido', 'invalid_topology']) {
    if (!text.includes(phrase)) throw Error('Missing hydrated stock panel: ' + phrase);
  }
  await page.waitForFunction(() => [...document.querySelectorAll('table')]
    .filter(t => t.innerText.includes('Correlación de rangos centrados por distrito'))
    .some(t => [...t.querySelectorAll('tr')].filter(r => r.querySelector('td')).length === $(uv run python -c "import json;print(len(json.load(open('artifacts/stock_rent_descriptive.json'))['results']['asociaciones_stock_renta']))")),
    null, { timeout: 15000 });
  const associations = page.locator('table').filter({ hasText: 'Correlación de rangos centrados por distrito' }).last();
  const associationCells = await associations.locator('tr').evaluateAll(rows => rows.map(row =>
    [...row.querySelectorAll('td')].map(cell => cell.innerText)).filter(row => row.length === 7));
  for (const wanted of expected.associations) {
    const row = associationCells.find(row => row[0].trim() === wanted.variable);
    if (!row || Number(row[1]) !== wanted.n) throw Error('Association sample size differs');
    for (const [index, key] of [[4, 'pearson'], [5, 'spearman'], [6, 'rangos_centrados_distrito']]) {
      const value = Number(row[index].trim().replace('−', '-').replace(',', '.'));
      if (!Number.isFinite(value) || Math.abs(value - wanted[key]) > 0.00051)
        throw Error('Association differs from verified report: ' + key);
    }
  }
  await page.waitForFunction(() => [...document.querySelectorAll('table')]
    .filter(t => t.innerText.includes('Rangos ajustados por distrito e ingreso'))
    .some(t => [...t.querySelectorAll('tr')].filter(r => r.querySelector('td')).length === $(uv run python -c "import json;print(len(json.load(open('artifacts/stock_rent_descriptive.json'))['results']['sensibilidad_stock_ingreso']))")),
    null, { timeout: 15000 });
  const incomeTable = page.locator('table').filter({ hasText: 'Rangos ajustados por distrito e ingreso' }).last();
  const incomeCells = await incomeTable.locator('tr').evaluateAll(rows => rows.map(row =>
    [...row.querySelectorAll('td')].map(cell => cell.innerText)).filter(row => row.length === 8));
  for (const wanted of expected.income) {
    const row = incomeCells.find(row => row[0].trim() === wanted.variable && Number(row[1]) === wanted.anyo_ingreso);
    if (!row || Number(row[2]) !== wanted.n || Number(row[3]) !== wanted.distritos)
      throw Error('Income sensitivity sample differs');
    for (const [index, key] of [[4, 'spearman_misma_muestra'], [5, 'distrito_misma_muestra'], [6, 'distrito_ingreso']]) {
      const value = Number(row[index].trim().replace('−', '-').replace(',', '.'));
      if (!Number.isFinite(value) || Math.abs(value - wanted[key]) > 0.00051)
        throw Error('Income sensitivity differs from verified report: ' + key);
    }
    if (row[7].trim() !== wanted.estado) throw Error('Income sensitivity status differs');
  }
  await page.waitForFunction(() => [...document.querySelectorAll('table')]
    .filter(t => t.innerText.includes('Mínimo al omitir un distrito'))
    .some(t => [...t.querySelectorAll('tr')].filter(r => r.querySelector('td')).length === $(uv run python -c "import json;print(len(json.load(open('artifacts/stock_rent_descriptive.json'))['results']['resumen_omision_stock_ingreso']))")),
    null, { timeout: 15000 });
  const omissionSummary = page.locator('table').filter({ hasText: 'Mínimo al omitir un distrito' }).last();
  const summaryCells = await omissionSummary.locator('tr').evaluateAll(rows => rows.map(row =>
    [...row.querySelectorAll('td')].map(cell => cell.innerText)).filter(row => row.length === 9));
  for (const wanted of expected.omission_summary) {
    const row = summaryCells.find(row => row[0].trim() === wanted.variable && Number(row[1]) === wanted.anyo_ingreso);
    if (!row) throw Error('Missing omission summary');
    for (const [index, key] of [[2, 'omisiones'], [3, 'omisiones_validas'], [4, 'omisiones_nulas'], [5, 'n_minimo'], [6, 'n_maximo']])
      if (Number(row[index]) !== wanted[key]) throw Error('Omission summary count differs: ' + key);
    for (const [index, key] of [[7, 'asociacion_minima'], [8, 'asociacion_maxima']]) {
      const value = Number(row[index].trim().replace('−', '-').replace(',', '.'));
      if (!Number.isFinite(value) || Math.abs(value - wanted[key]) > 0.00051)
        throw Error('Omission summary coefficient differs: ' + key);
    }
  }
  const omissionDetail = page.locator('table').filter({ hasText: 'Asociación reajustada tras omisión' }).last();
  await omissionDetail.locator('td').first().waitFor({ timeout: 15000 });
  const detailCells = await omissionDetail.locator('tr').evaluateAll(rows => rows.map(row =>
    [...row.querySelectorAll('td')].map(cell => cell.innerText)).filter(row => row.length === 7));
  if (detailCells.length !== 12) throw Error('Omission detail page is empty or incomplete');
  for (const row of detailCells) {
    const wanted = expected.omissions.find(r => r.variable === row[0].trim() && r.anyo_ingreso === Number(row[1]) && r.distrito_omitido === row[2].trim());
    const value = Number(row[5].trim().replace('−', '-').replace(',', '.'));
    if (!wanted || Number(row[3]) !== wanted.n || Number(row[4]) !== wanted.distritos
        || Math.abs(value - wanted.distrito_ingreso) > 0.00051 || !Number.isFinite(value)
        || row[6].trim() !== wanted.estado) throw Error('Omission detail differs');
  }
  const weightTable = page.locator('table').filter({ hasText: 'Mediana mínima BU, peso por inmuebles' }).last();
  await weightTable.locator('td').first().waitFor({ timeout: 15000 });
  const weightCells = await weightTable.locator('tr').evaluateAll(rows => rows.map(row =>
    [...row.querySelectorAll('td')].map(cell => cell.innerText)).filter(row => row.length === 8));
  if (weightCells.length !== 12) throw Error('Weighting coverage table is empty or incomplete');
  for (const row of weightCells) {
    const wanted = expected.weighted_dates.find(r => r.barrio === row[0].trim());
    if (!wanted) throw Error('Unknown weighting barrio');
    for (const [index, key] of [[1, 'mediana_anyo_minimo'], [2, 'mediana_anyo_minimo_ponderada'],
        [3, 'registros_con_fecha'], [4, 'inmuebles_vivienda'], [5, 'pesos_con_fecha'], [6, 'pesos_sin_fecha']]) {
      const cell = row[index].trim();
      if (wanted[key] === null) {
        if (/[0-9]/.test(cell)) throw Error('Null weight/date became a number');
      } else if (Number(cell.replace(/[^0-9-]/g, '')) !== wanted[key])
        throw Error('Weighting coverage differs: ' + key);
    }
  }
  const readerTable = page.locator('table').filter({ hasText: 'Proxy físico, no oferta disponible' }).last();
  await readerTable.locator('td').first().waitFor({ timeout: 15000 });
  const readerCells = await readerTable.locator('tr').evaluateAll(rows => rows.map(row =>
    [...row.querySelectorAll('td')].map(cell => cell.innerText)).filter(row => row.length === 8));
  if (readerCells.length !== expected.reader_summary.length) throw Error('Reader summary cardinality differs');
  for (const wanted of expected.reader_summary) {
    const row = readerCells.find(row => row[0].trim() === wanted.variable);
    if (!row || row[7].trim() !== wanted.lectura) throw Error('Reader summary coverage status differs');
    for (const [index, key] of [[1, 'n_sin_ajuste'], [3, 'n_ingreso_2019'], [5, 'n_ingreso_2020']])
      if (Number(row[index]) !== wanted[key]) throw Error('Reader summary sample differs: ' + key);
    for (const [index, key] of [[2, 'rho_sin_ajuste'], [4, 'rho_ingreso_2019'], [6, 'rho_ingreso_2020']]) {
      const value = Number(row[index].trim().replace('−', '-').replace(',', '.'));
      if (!Number.isFinite(value) || Math.abs(value - wanted[key]) > 0.00051)
        throw Error('Reader summary coefficient differs: ' + key);
    }
  }
  if (await page.locator('canvas').count() < 5) throw Error('Stock/rent scatterplots did not render');
  const polygons = page.locator('.leaflet-overlay-pane path');
  if (await polygons.count() !== expected.map_count) throw Error('Valid geometry map count differs from sidecar');
  const colors = await polygons.evaluateAll(paths => [...new Set(paths.map(p => p.getAttribute('fill')))]);
  if (colors.length < 2) throw Error('Density values did not color the barrio polygons');
  await page.locator('.leaflet-container').screenshot({ path: '/tmp/housing-stock-map.png' });
  await page.screenshot({ path: '/tmp/housing-stock-browser.png', fullPage: true });
  return { errors, coverage, mapPolygons: await polygons.count(), colors, geometryLoaded };
}" 2>&1)"
result="$(printf '%s\n' "$output" | sed -n '/^### Result/,/^### Ran/p' | sed '1d;$d')"
if [ -z "$result" ]; then
  printf '%s\n' "$output"
  exit 1
fi
python3 - "$result" <<'PY'
import json
import sys
result = json.loads(sys.argv[1])
if result['errors']:
    raise SystemExit(f"FAIL stock browser: {result['errors']}")
print('OK stock browser: pinned coverage hydrates; barrio map and stock panels load')
PY
