#!/usr/bin/env bash
# Browser contract for /perfil/, using read-only real-source query expectations.
# Usage: bash scripts/smoke_profile.sh [BASE_URL]
set -euo pipefail
cd "$(dirname "$0")/.."
BASE="${1:-http://127.0.0.1:3000}"
SESSION="housing-profile-smoke"
command -v playwright-cli >/dev/null || { echo 'playwright-cli required'; exit 2; }
trap 'playwright-cli -s="$SESSION" close >/dev/null 2>&1 || true' EXIT
uv run python scripts/export_profile_income.py --check
expected="$(uv run python - <<'PY'
import json
import re
from pathlib import Path

import duckdb

con = duckdb.connect()
con.execute("attach 'data/processed/marts.duckdb' as marts (read_only)")
con.execute("attach 'data/processed/housing_access.duckdb' as access (read_only)")
con.execute("attach 'data/processed/profile_income.duckdb' as profile_income (read_only)")
con.execute('create schema housing')
con.execute('use marts')
for source in ('perfil_catalogo', 'perfil_censo', 'perfil_alquiler', 'vacancy_municipal', 'perfil_provincias'):
    sql = Path(f'evidence/sources/housing/{source}.sql').read_text()
    con.execute(f'create table memory.housing.{source} as {sql}')
con.execute('use memory')
queries = dict(re.findall(r'```sql (\w+)\n(.*?)\n```', Path('evidence/pages/perfil.md').read_text(), re.S))

def query(name, code):
    sql = queries[name].replace('${inputs.municipio_perfil.value}', code)
    for dep in ('municipios_perfil', 'identidad_perfil', 'cortes_perfil'):
        placeholder = '${' + dep + '}'
        if placeholder in sql:
            sql = sql.replace(placeholder, '(' + query(dep, code) + ')')
    return sql

census_only = con.execute("""
    select codigo from housing.perfil_catalogo
    where municipio = 'Municipio sin nombre en SERPAVI'
    order by codigo limit 1
""").fetchone()
suppressed = con.execute('''
    select codigo from housing.perfil_censo
    where secciones_suprimidas > 0 order by codigo limit 1
''').fetchone()
adrh_only = con.execute("""
    select codigo from profile_income.municipal
    where anyo = (select max(anyo) from profile_income.municipal)
      and renta_neta_hogar is not null
      and codigo not in (select codigo from housing.perfil_catalogo)
    order by codigo limit 1
""").fetchone()
hidden_income = con.execute("""
    select m.codigo from profile_income.municipal m
    where m.anyo = (select max(anyo) from profile_income.municipal)
      and m.renta_neta_hogar is null
      and exists (select 1 from profile_income.municipal h
                  where h.codigo=m.codigo and h.renta_neta_hogar is not null)
    order by m.codigo limit 1
""").fetchone()
if not all((census_only, suppressed, adrh_only, hidden_income)):
    raise SystemExit('Profile browser fixtures require rentless, suppressed and ADRH-only cases')
cases = []
for code in dict.fromkeys(('28079', '01001', census_only[0], suppressed[0],
                           adrh_only[0], hidden_income[0])):
    label = con.execute('select etiqueta from (' + query('municipios_perfil', code) +
                        ') where codigo=?', [code]).fetchone()[0]
    cases.append({
        'code': code, 'label': label,
        'identity': con.execute(query('identidad_perfil', code)).fetchone(),
        'indicators': con.execute(query('indicadores_perfil', code)).fetchall(),
        'rent': con.execute(query('historia_alquiler_perfil', code)).fetchall(),
        'income': con.execute(query('historia_ingresos_perfil', code)).fetchall(),
        'proxy': con.execute(query('historia_proxy_perfil', code)).fetchall(),
    })
print(json.dumps(cases))
PY
)"
playwright-cli -s="$SESSION" open about:blank >/dev/null
output="$(playwright-cli -s="$SESSION" run-code "async (page) => {
 const cases=$expected, errors=[];
 page.on('pageerror', e=>errors.push(String(e)));
 page.on('console', m=>{if(m.type()==='error')errors.push(m.text());});
 await page.goto('$BASE/perfil/',{waitUntil:'domcontentloaded'});
 await page.waitForFunction(()=>document.querySelectorAll('canvas').length>=3,null,{timeout:60000});
 const read=async()=>page.locator('article table').evaluateAll(tables=>tables.filter(t=>t.getBoundingClientRect().height>0).map(t=>
   [...t.querySelectorAll('tr')].map(r=>[...r.querySelectorAll('td')].map(c=>c.innerText.trim())).filter(r=>r.length)));
 const wanted=[];
 for(const row of cases){
   const button=page.locator('button[role=combobox]').filter({hasText:'Busca tu municipio'});
   if(!(await button.innerText()).includes(row.code)){
     await button.click();
     await page.locator('input[role=combobox]').last().fill(row.code);
     await page.getByRole('option',{name:row.label,exact:true}).click();
   }
   await page.waitForFunction((r)=>{
     const tables=[...document.querySelectorAll('article table')].filter(t=>t.getBoundingClientRect().height>0);
     const cells=tables[0]?[...tables[0].querySelectorAll('td')].map(c=>c.innerText.trim()):[];
     return cells[0]===r.identity[1]&&cells[1]===r.identity[2]&&cells[2]===r.code&&cells[3]===r.identity[3];
   },row,{timeout:20000});
   const matches=(actual)=>{
     if(actual.length!==5||actual[1].length!==7||actual[2].length!==row.rent.length||actual[3].length!==row.income.length||actual[4].length!==row.proxy.length)return false;
     const num=(s,n,tolerance=0.0051)=>n===null?!/[0-9]/.test(s):s.trim()!==''&&Math.abs(Number(s.replaceAll(',',''))-n)<tolerance;
     for(const r of row.indicators){
       const a=actual[1].find(a=>a[0]===r[1]);
       if(!a||!num(a[1],r[2])||!num(a[2],r[3])||a[3]!==r[4]||a[4]!==r[7]||a[5]!==r[5]||a[6]!==r[6])return false;
     }
     for(const [index,expected] of [[2,row.rent],[3,row.income],[4,row.proxy]])
       if(expected.some((r,i)=>r.some((n,j)=>!num(actual[index][i][j],n,index===4&&(j===1||j===2)?0.501:0.0051))))return false;
     return true;
   };
   let actual;
   // Identity and dependent queries settle independently; poll the actual cells.
   for(let attempt=0;attempt<100;attempt++){
     actual=await read();
     if(matches(actual))break;
     await page.waitForTimeout(200);
   }
   if(!matches(actual))throw Error(JSON.stringify({code:row.code,actual,expected:row}));
   wanted.push(row.code);
 }
 await page.setViewportSize({width:390,height:844});
 const width=await page.evaluate(()=>({viewport:innerWidth,page:document.documentElement.scrollWidth}));
 if(width.page>width.viewport)throw Error('Mobile page overflows: '+JSON.stringify(width));
 if(errors.length)throw Error(errors.join('; '));
 return {status:'PASS profile browser',codes:wanted,mobile:width};
}")"
printf '%s\n' "$output"
grep -q 'PASS profile browser' <<<"$output"
! grep -q '^### Error' <<<"$output"
