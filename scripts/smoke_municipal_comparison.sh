#!/usr/bin/env bash
# Same-year municipal comparison: controls, support, snapshots and actual downloads.
# Usage: bash scripts/smoke_municipal_comparison.sh [BASE_URL]
set -euo pipefail
cd "$(dirname "$0")/.."
BASE="${1:-http://127.0.0.1:3000}"
SESSION="housing-municipal-comparison-smoke"
command -v playwright-cli >/dev/null || { echo 'playwright-cli required'; exit 2; }
trap 'playwright-cli -s="$SESSION" close >/dev/null 2>&1 || true' EXIT
export MUNICIPAL_COMPARISON_SMOKE_DIR
MUNICIPAL_COMPARISON_SMOKE_DIR=$(mktemp -d /tmp/housing-municipal-comparison.XXXXXX)
expected="$(uv run python - <<'PY'
import json,os,re
from pathlib import Path
import duckdb

con=duckdb.connect()
for name,file in [('marts','marts'),('access','housing_access'),('profile_income','profile_income')]:
    con.execute(f"attach 'data/processed/{file}.duckdb' as {name} (read_only)")
con.execute('create schema housing');con.execute('use marts')
for source in ('perfil_catalogo','perfil_provincias','perfil_alquiler','perfil_censo','vacancy_municipal'):
    con.execute(f'create table memory.housing.{source} as '+Path(f'evidence/sources/housing/{source}.sql').read_text())
con.execute('use memory')
text=Path('evidence/pages/comparar-municipios.md').read_text()
queries=dict(re.findall(r'```sql (\w+)\n(.*?)\n```',text,re.S))
def render(name,inputs):
    sql=re.sub(r'\$\{inputs\.(\w+)\.value\}',lambda m:inputs[m[1]],queries[name])
    return re.sub(r'\$\{(\w+)\}',lambda m:'('+render(m[1],inputs)+')',sql)

def execute(name,inputs):
    return con.execute(render(name,inputs)).fetchall()

cases=[]
for a,b,metric,first,last in [
    ('28079','08019','alquiler',2015,2023),
    ('28079','08019','alquiler',2023,2015),
    ('28079','01011','alquiler',2015,2023),
    ('28079','01011','ingresos',2015,2023),
    ('28079','02036','ingresos',2023,2023),
    ('28079','01001','proxy',2023,2023),
    ('28079','28079','alquiler',2015,2023),
    ('48916','28079','ingresos',2023,2023),
]:
    inputs=dict(municipio_a=a,municipio_b=b,metrica_municipal=metric,
                desde_municipal=str(first),hasta_municipal=str(last))
    names=execute('municipios_comparables',inputs)
    labels={r[0]:r[-1] for r in names}
    metric_row=execute('medida_aplicada',inputs)[0]
    series=execute('serie_comun',inputs)
    cases.append({
      'inputs':inputs, 'aLabel':labels[a], 'bLabel':labels[b], 'metricLabel':metric_row[1],
      'tables':[
        [[r[0],r[2],r[3],r[1],r[4]] for r in execute('seleccion_comparable',inputs)],
        [metric_row[1:]], execute('cobertura_comparable',inputs),
        [[r[0],r[1],r[2],r[4],r[5]] for r in execute('calendario_comparable',inputs)],
        [[r[1],r[3],r[2],r[4],r[6],r[5],r[7]] for r in execute('contexto_comparable',inputs)],
      ],
      'download':[dict(zip(('metrica','unidad','anyo','lado','codigo','municipio','serie','valor'),
                          (r[5],r[6],r[0],r[1],r[2],r[3],r[4],r[7]),strict=True)) for r in series],
    })
Path(os.environ['MUNICIPAL_COMPARISON_SMOKE_DIR'],'expected.json').write_text(json.dumps(cases,ensure_ascii=False,allow_nan=False))
for case in cases: case.pop('download')
print(json.dumps(cases,ensure_ascii=False,allow_nan=False))
PY
)"
playwright-cli -s="$SESSION" open about:blank >/dev/null
output="$(playwright-cli -s="$SESSION" run-code "async(page)=>{
 const cases=$expected, errors=[];
 page.on('pageerror',e=>errors.push(String(e)));
 await page.goto('$BASE/comparar-municipios/',{waitUntil:'domcontentloaded'});
 await page.waitForFunction(()=>document.querySelectorAll('canvas').length>=1,null,{timeout:60000});
 const choose=async(title,label)=>{
   const button=page.locator('button[role=combobox]').filter({hasText:title});
   if((await button.innerText()).includes(label))return;
   await button.click();await page.locator('input[role=combobox]').last().fill(label);
   await page.getByRole('option',{name:label,exact:true}).click();
 };
 const read=async()=>page.locator('article table').evaluateAll(ts=>ts.filter(t=>t.getBoundingClientRect().height>0).map(t=>
   [...t.querySelectorAll('tr')].map(r=>[...r.querySelectorAll('td')].map(c=>c.innerText.trim())).filter(r=>r.length)));
 const same=(a,b)=>a.length===b.length&&b.every((rows,i)=>a[i].length===rows.length&&rows.every((r,j)=>
   a[i][j].length===r.length&&r.every((v,k)=>v===null?!/[0-9]/.test(a[i][j][k]):
     typeof v==='number'?a[i][j][k]!==''&&Math.abs(Number(a[i][j][k].replaceAll(',',''))-v)<0.0051:a[i][j][k]===v)));
 let checked=0;
 for(const row of cases){
   if(checked===4)await page.setViewportSize({width:390,height:844});
   await choose('Municipio A (',row.aLabel);
   await choose('Municipio B (',row.bLabel);
   await choose('Medida (',row.metricLabel);
   await choose('Desde (',row.inputs.desde_municipal);
   await choose('Hasta (',row.inputs.hasta_municipal);
   let actual;
   for(let attempt=0;attempt<100;attempt++){
     actual=await read();if(same(actual,row.tables))break;await page.waitForTimeout(200);
   }
   if(!same(actual,row.tables))throw Error(JSON.stringify({inputs:row.inputs,actual,expected:row.tables}));
   const panel=page.locator('[data-evidence-chart=comparar-municipios-serie]');
   if(!await panel.evaluate(e=>e.open)){await panel.locator('summary').focus();await page.keyboard.press('Enter');}
   const button=panel.getByRole('button',{name:'Descargar JSON del gráfico',exact:true});
   for(let attempt=0;attempt<100;attempt++){
     const sql=await panel.locator('pre').innerText();
     if(await button.isEnabled()&&Object.values(row.inputs).every(v=>sql.includes(\"'\"+v+\"'\")))break;
     await page.waitForTimeout(200);
   }
   for(const format of ['json','csv']){
     const waiting=page.waitForEvent('download');
     await panel.getByRole('button',{name:'Descargar '+format.toUpperCase()+' del gráfico',exact:true}).click();
     await (await waiting).saveAs('$MUNICIPAL_COMPARISON_SMOKE_DIR/'+checked+'.'+format);
     await page.waitForTimeout(500);
   }
   checked++;
 }
 const width=await page.evaluate(()=>({viewport:innerWidth,page:document.documentElement.scrollWidth}));
 if(width.page>width.viewport)throw Error('Mobile overflow: '+JSON.stringify(width));
 if(errors.length)throw Error(errors.join('; '));
 return {status:'PASS municipal comparison controls',cases:checked,mobile:width};
}")"
printf '%s\n' "$output"
grep -q 'PASS municipal comparison controls' <<<"$output"
! grep -q '^### Error' <<<"$output"
uv run python - <<'PY'
import csv,json,math,os
from pathlib import Path
root=Path(os.environ['MUNICIPAL_COMPARISON_SMOKE_DIR'])
cases=json.loads((root/'expected.json').read_text())
for i,case in enumerate(cases):
    actual=json.loads((root/f'{i}.json').read_text())
    expected=case['download']
    assert len(actual)==len(expected)
    for a,b in zip(actual,expected,strict=True):
        assert list(a)==list(b)
        for key,value in b.items():
            if isinstance(value,(int,float)):
                assert isinstance(a[key],(int,float)) and not isinstance(a[key],bool)
                assert math.isclose(a[key],value,rel_tol=1e-12,abs_tol=1e-12)
            else: assert a[key]==value
    with (root/f'{i}.csv').open(encoding='utf-8-sig',newline='') as f:
        csv_rows=list(csv.reader(f))
    assert csv_rows[0]==list(expected[0]) and len(csv_rows)==len(expected)+1
    for cells,row in zip(csv_rows[1:],expected,strict=True):
        for cell,value in zip(cells,row.values(),strict=True):
            if value is None: assert cell==''
            elif isinstance(value,(int,float)): assert math.isclose(float(cell),value,rel_tol=1e-12,abs_tol=1e-12)
            else: assert cell==value
print(f'PASS common-support downloads: {len(cases)} scenarios, CSV/JSON preserve exact years/codes/units/null masks')
PY
