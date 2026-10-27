#!/usr/bin/env bash
# Real-browser contract for /deficit/: selector changes, dates, coverage, nulls.
# Usage: bash scripts/smoke_deficit.sh [BASE_URL]
set -euo pipefail
cd "$(dirname "$0")/.."
BASE="${1:-http://127.0.0.1:3000}"
SESSION="housing-deficit-smoke"
command -v playwright-cli >/dev/null || { echo 'playwright-cli required'; exit 2; }
trap 'playwright-cli -s="$SESSION" close >/dev/null 2>&1 || true' EXIT
uv run python scripts/export_deficit.py --check
expected="$(uv run python - <<'PY'
import json
import re
from pathlib import Path

import duckdb

con = duckdb.connect()
con.execute("attach 'data/processed/deficit.duckdb' as deficit (read_only)")
queries = dict(re.findall(r'```sql (\w+)\n(.*?)\n```', Path('evidence/pages/deficit.md').read_text(), re.S))

def query(name, code, window):
    sql = queries[name].replace('${inputs.territorio_deficit.value}', code)
    sql = sql.replace('${inputs.ventana_deficit.value}', window)
    if '${seleccion_deficit}' in sql:
        sql = sql.replace('${seleccion_deficit}', '(' + query('seleccion_deficit', code, window) + ')')
    return sql

cases = []
for window, code in [('2021-2024', 'NACIONAL'), ('2021-2025', 'NACIONAL'),
                     ('2021-2024', '28'), ('2021-2025', '35'),
                     ('2021-2024', '42'), ('2021-2025', '51+52')]:
    cursor = con.execute(query('seleccion_deficit', code, window))
    row = dict(zip([d[0] for d in cursor.description], cursor.fetchone(), strict=True))
    values = [
        [[row[k] for k in ('provincia', 'flow_start', 'flow_end', 'household_start_year',
                           'household_end_year', 'stock_start_year', 'stock_end_year')]],
        con.execute(query('cantidades_deficit', code, window)).fetchall(),
        con.execute(query('cobertura_deficit', code, window)).fetchall(),
        [[row[k] for k in ('gap_stock', 'gap_completions', 'gap_completions_upper')]],
        con.execute(query('ventanas_comparadas_deficit', code, window)).fetchall(),
        [r[1:] for r in con.execute(query('provincias_deficit', code, window)).fetchall()[:10]],
    ]
    cases.append({'window': window, 'windowLabel': window.replace('-', '–') + ' (años completos)',
                  'code': code, 'label': row['provincia'], 'tables': values})
print(json.dumps(cases))
PY
)"
playwright-cli -s="$SESSION" open about:blank >/dev/null
output="$(playwright-cli -s="$SESSION" run-code "async (page) => {
 const cases=$expected, errors=[];
 page.on('pageerror',e=>errors.push(String(e)));
 page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
 await page.goto('$BASE/deficit/',{waitUntil:'domcontentloaded'});
 await page.waitForFunction(()=>document.querySelectorAll('canvas').length>=2,null,{timeout:60000});
 const choose=async(title,label)=>{
   const button=page.locator('button[role=combobox]').filter({hasText:title});
   if((await button.innerText()).includes(label))return;
   await button.click();
   await page.locator('input[role=combobox]').last().fill(label);
   await page.getByRole('option',{name:label,exact:true}).click();
 };
 const read=async()=>page.locator('article table').evaluateAll(ts=>ts.filter(t=>t.getBoundingClientRect().height>0).map(t=>
   [...t.querySelectorAll('tr')].map(r=>[...r.querySelectorAll('td')].map(c=>c.innerText.trim())).filter(r=>r.length)));
 const same=(a,b)=>a.length===b.length&&b.every((rows,i)=>a[i].length===rows.length&&rows.every((r,j)=>
   a[i][j].length===r.length&&r.every((v,k)=>v===null?!/[0-9]/.test(a[i][j][k]):
     typeof v==='number'?a[i][j][k]!==''&&Number(a[i][j][k].replaceAll(',',''))===v:a[i][j][k]===v)));
 const checked=[];
 for(const row of cases){
   await choose('Años de actividad',row.windowLabel);
   await choose('España o provincia',row.label);
   let actual;
   for(let attempt=0;attempt<100;attempt++){
     actual=await read();
     if(same(actual,row.tables))break;
     await page.waitForTimeout(200);
   }
   if(!same(actual,row.tables))throw Error(JSON.stringify({window:row.window,code:row.code,actual,expected:row.tables}));
   checked.push(row.window+'/'+row.code);
 }
 const text=await page.locator('body').innerText();
 for(const phrase of ['Ninguna de las dos restas cuenta viviendas disponibles ni hogares sin casa',
   'Una celda ausente no es cero','cota superior del saldo','no tasas anuales ni una previsión'])
   if(!text.includes(phrase))throw Error('Missing caveat: '+phrase);
 await page.setViewportSize({width:390,height:844});
 const width=await page.evaluate(()=>({viewport:innerWidth,page:document.documentElement.scrollWidth}));
 if(width.page>width.viewport)throw Error('Mobile overflow: '+JSON.stringify(width));
 if(errors.length)throw Error(errors.join('; '));
 return {status:'PASS deficit browser',checked,mobile:width};
}")"
printf '%s\n' "$output"
grep -q 'PASS deficit browser' <<<"$output"
! grep -q '^### Error' <<<"$output"
