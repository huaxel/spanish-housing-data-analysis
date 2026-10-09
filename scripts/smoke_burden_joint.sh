#!/usr/bin/env bash
set -euo pipefail
BASE="${1:-http://127.0.0.1:3000}"
SESSION="housing-joint-burden-smoke"
command -v playwright-cli >/dev/null || { echo 'playwright-cli required'; exit 2; }
trap 'playwright-cli -s="$SESSION" close >/dev/null 2>&1 || true' EXIT
uv run python scripts/verify_housing_overburden.py
expected="$(uv run python - <<'PY'
import duckdb,json
from spanish_housing.data_paths import PROCESSED
with duckdb.connect(str(PROCESSED/'housing_access.duckdb'),read_only=True) as c:
 year=c.execute('select max(survey_year) from overburden where rate_pct is not null').fetchone()[0]
 joint=c.execute('select age_label,poverty_label,survey_year,rate_pct,status from overburden_age_poverty '
                 'where survey_year=? order by age_code,poverty_code',[year]).fetchall()
 marginals={group:c.execute('select group_label,survey_year,rate_pct,status from overburden '
                           'where survey_year=? and breakdown=? order by group_code',[year,group]).fetchall()
            for group in ['age','income','tenure']}
print(json.dumps({'joint':joint,'marginals':marginals}))
PY
)"
playwright-cli -s="$SESSION" open about:blank >/dev/null
output="$(playwright-cli -s="$SESSION" run-code "async (page) => {
  const expected = $expected, errors=[];
  page.on('pageerror', e => errors.push(String(e)));
  page.on('console', m => { if (m.type()==='error') errors.push(m.text()); });
  await page.goto('$BASE/acceso/',{waitUntil:'domcontentloaded'});
  const flag = x => /^[-–—]$/.test(x.trim()) ? '' : x.trim();
  const checkRate = (cell,wanted) => {
    if (wanted === null) { if (/[0-9]/.test(cell)) throw Error('Missing rate became numeric'); return; }
    const value=Number(cell.trim().replace(',', '.'));
    if (!Number.isFinite(value) || Math.abs(value-wanted)>0.051) throw Error('Displayed rate differs');
  };
  const read = async heading => {
    const table=page.locator('table').filter({hasText:heading}).last();
    await table.locator('td').first().waitFor({timeout:45000});
    return table.locator('tr').evaluateAll(rows => rows.map(row =>
      [...row.querySelectorAll('td')].map(c=>c.innerText.trim())).filter(r=>r.length));
  };
  const joint=await read('Calidad del cruce');
  if (joint.length!==expected.joint.length) throw Error('Joint cell count differs');
  for (const row of joint) {
    const wanted=expected.joint.find(r=>r[0]===row[0] && r[1]===row[1]);
    if (!wanted || Number(row[2].replace(/[^0-9]/g,''))!==wanted[2] || flag(row[4])!==wanted[4])
      throw Error('Joint coordinates/year/status differ');
    checkRate(row[3],wanted[3]);
  }
  for (const [group,heading] of [['age','Edad (etiqueta Eurostat)'],['income','Quintil (etiqueta Eurostat)'],
      ['tenure','Tenencia (etiqueta Eurostat)']]) {
    const rows=await read(heading), wanted=expected.marginals[group];
    if (rows.length!==wanted.length) throw Error('Marginal cell count differs');
    for (const row of rows) {
      const r=wanted.find(r=>r[0]===row[0]);
      if (!r || Number(row[1].replace(/[^0-9]/g,''))!==r[1] || flag(row[3])!==r[3]) throw Error('Marginal coordinate/year/status differs');
      checkRate(row[2],r[2]);
    }
  }
  const text=await page.locator('body').innerText();
  for (const phrase of ['celdas conjuntas publicadas directamente','personas de cada combinación',
      'No identifica jóvenes inquilinos de bajos ingresos','No es el primer quintil',
      'sexo total','no toda la población']) if (!text.includes(phrase)) throw Error('Missing caveat: '+phrase);
  if (errors.length) throw Error(errors.join('; '));
  return 'PASS joint burden: published coordinates/rates/year/nulls/flags and original marginals';
}")"
printf '%s\n' "$output"
grep -q 'PASS joint burden' <<<"$output"
! grep -q '^### Error' <<<"$output"
