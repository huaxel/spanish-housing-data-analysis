#!/usr/bin/env bash
# Read-only runtime check of the separate reference-year profile.
set -euo pipefail
BASE="${1:-http://127.0.0.1:3000}"
SESSION="housing-municipal2021-smoke"
command -v playwright-cli >/dev/null || { echo 'playwright-cli required'; exit 2; }
trap 'playwright-cli -s="$SESSION" close >/dev/null 2>&1 || true' EXIT
uv run python scripts/build_sevilla_2021.py --check
expected="$(uv run python - <<'PY'
import duckdb,json,re
from pathlib import Path
from spanish_housing.data_paths import PROCESSED
with duckdb.connect(str(PROCESSED/'sevilla_2021.duckdb'),read_only=True) as c:
 rows=c.execute('select * from perfiles order by codigo').fetchall()
 aggregates=c.execute('select * from agregados_excluidos order by fuente,codigo,medida').fetchall()
 tenure=c.execute('select * from tenencia_contexto order by codigo').fetchall()
 q=re.search(r'```sql seleccion_alineada\n(.*?)\n```',Path('evidence/pages/stock-2021.md').read_text(),re.S).group(1)
 selection=c.execute(q.replace('alignment.perfiles','perfiles')).fetchall()
print(json.dumps({'rows':rows,'aggregates':aggregates,'selection':selection,'tenure':tenure,
 'coverage':[len(rows),sum(r[2] is not None for r in rows),sum(r[3] is not None for r in rows),
             sum(r[5] is not None for r in rows),sum(r[-1] for r in rows),
             sum(r[6]=='duplicate' or r[7]=='duplicate' for r in rows),
             sum(r[6]=='label_mismatch' or r[7]=='label_mismatch' for r in rows)]}))
PY
)"
playwright-cli -s="$SESSION" open about:blank >/dev/null
output="$(playwright-cli -s="$SESSION" run-code "async (page) => {
  const errors = [];
  page.on('pageerror', e => errors.push(String(e)));
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  const expected = $expected;
  await page.goto('$BASE/stock-2021/', {waitUntil:'domcontentloaded'});
  const coverage = page.locator('table').filter({hasText:'Con los tres datos'}).last();
  await coverage.locator('td').first().waitFor({timeout:45000});
  const cells = async table => table.locator('tr').evaluateAll(rows => rows.map(r =>
    [...r.querySelectorAll('td')].map(c => c.innerText.trim())).filter(r => r.length));
  const count = s => Number(s.replace(/[^0-9-]/g,''));
  const actual = (await cells(coverage))[0].map(count);
  if (JSON.stringify(actual) !== JSON.stringify(expected.coverage)) throw Error('Coverage mismatch');
  const check = (cell, value, price=false) => {
    if (value === null) { if (/[0-9]/.test(cell)) throw Error('Missing value became numeric'); return; }
    const n = price ? Number(cell.replace(',', '.')) : count(cell);
    if (!Number.isFinite(n) || Math.abs(n-value) > (price ? 0.0051 : 0)) throw Error('Numeric mismatch');
  };
  const capital = page.locator('table').filter({hasText:'Hogares censales, enero 2021'}).last();
  await capital.locator('td').first().waitFor({timeout:15000});
  const capitalCells = (await cells(capital))[0];
  const wanted = expected.rows.find(r => r[0] === '41091');
  if (capitalCells[0] !== wanted[0] || capitalCells[1] !== wanted[1]) throw Error('Capital identity mismatch');
  for (const i of [2,3,4,5]) check(capitalCells[i],wanted[i],i===5);
  const profiles = page.locator('table').filter({hasText:'Estado de la unión de alquiler'}).last();
  await profiles.locator('td').first().waitFor({timeout:15000});
  const profileCells = await cells(profiles);
  if (profileCells.length !== Math.min(12,expected.rows.length)) throw Error('Profile page cardinality mismatch');
  for (const row of profileCells) {
    const r = expected.rows.find(r => r[0] === row[0]);
    if (!r || row[1] !== r[1]) throw Error('Municipal identity mismatch');
    for (const i of [2,3,4,5]) check(row[i],r[i],i===5);
    if (row[6] !== r[6] || row[7] !== r[7]) throw Error('Source status mismatch');
  }
  const aggregates = page.locator('table').filter({hasText:'Valor publicado sin repartir'}).last();
  await aggregates.locator('td').first().waitFor({timeout:15000});
  if (JSON.stringify(await cells(aggregates)) !== JSON.stringify(expected.aggregates)) throw Error('Excluded aggregate mismatch');
  const selection = page.locator('table').filter({hasText:'Estado del denominador de hogares'}).last();
  await selection.locator('td').first().waitFor({timeout:15000});
  const selectionCells = await cells(selection);
  if (selectionCells.length !== expected.selection.length) throw Error('Selection cardinality mismatch');
  for (const row of selectionCells) {
    const wanted = expected.selection.find(r => r[0] === row[0]);
    if (!wanted || row[7] !== wanted[7]) throw Error('Selection identity/status mismatch');
    for (const i of [1,3,4,6]) check(row[i],wanted[i]);
    for (const i of [2,5]) {
      if (wanted[i] === null) { check(row[i],null); continue; }
      const n = Number(row[i].replace('%','').trim().replace(',', '.'))/100;
      if (!Number.isFinite(n) || Math.abs(n-wanted[i])>0.00051) throw Error('Selection share mismatch');
    }
  }
  const tenure = page.locator('table').filter({hasText:'Completitud de celdas publicadas'}).last();
  await tenure.locator('td').first().waitFor({timeout:15000});
  const tenureCells = await cells(tenure);
  if (tenureCells.length !== expected.tenure.length) throw Error('Tenure publication scope mismatch');
  for (const row of tenureCells) {
    const r = expected.tenure.find(r => r[0] === row[0]);
    if (!r || row[1] !== r[1] || row[6] !== r[6]) throw Error('Tenure identity/status mismatch');
    for (const i of [2,3,4,5]) check(row[i],r[i]);
  }
  const text = await page.locator('body').innerText();
  for (const phrase of ['1 de enero de 2021','ejercicio fiscal 2021','2020','no es oferta disponible',
      'establecimientos colectivos','no un déficit/excedente','no mide cobertura de contratos','no hogares ni contratos','no están cubiertas por esta tabla',
      'no son dos comprobaciones independientes']) if (!text.includes(phrase)) throw Error('Missing limitation: '+phrase);
  if (errors.length) throw Error(errors.join('; '));
  return 'PASS municipal2021: coverage, capital, profiles, nulls, selection shares, tenure context, aggregates and limitations';
}")"
printf '%s\n' "$output"
grep -q 'PASS municipal2021' <<<"$output"
! grep -q '^### Error' <<<"$output"
