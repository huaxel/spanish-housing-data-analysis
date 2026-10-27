#!/usr/bin/env bash
# Query-linked evidence panels: content, current SQL, CSV/JSON and selector updates.
# Usage: bash scripts/smoke_provenance.sh [BASE_URL]
set -euo pipefail
cd "$(dirname "$0")/.."
BASE="${1:-http://127.0.0.1:3000}"
SESSION="housing-provenance-smoke"
command -v playwright-cli >/dev/null || { echo 'playwright-cli required'; exit 2; }
trap 'playwright-cli -s="$SESSION" close >/dev/null 2>&1 || true' EXIT
uv run python scripts/export_chart_provenance.py --check
export PROVENANCE_SMOKE_DIR
PROVENANCE_SMOKE_DIR=$(mktemp -d /tmp/housing-provenance-downloads.XXXXXX)
uv run python - <<'PY'
import json, os, re, sys
from pathlib import Path
import duckdb
sys.path.insert(0, 'scripts')
from export_chart_provenance import declarations

con=duckdb.connect()
for name,file in [('marts','marts'),('access','housing_access'),('profile_income','profile_income'),('deficit','deficit')]:
    con.execute(f"attach 'data/processed/{file}.duckdb' as {name} (read_only)")
con.execute('create schema housing');con.execute('use marts')
for name in ('mart_ccaa_anual','aeat_viviendas_uso','vacancy_municipal','perfil_catalogo','perfil_censo','perfil_alquiler','perfil_provincias'):
    con.execute(f'create table memory.housing.{name} as '+Path(f'evidence/sources/housing/{name}.sql').read_text())
con.execute('use memory')
cases=[]
for route, scenarios in [
    ('reportaje',[('default',{})]),
    ('perfil',[(code,{'municipio_perfil':code}) for code in ('28079','01011','02036','48916')]),
    ('deficit',[('national',{'territorio_deficit':'NACIONAL','ventana_deficit':'2021-2024'}),
                ('canary',{'territorio_deficit':'35','ventana_deficit':'2021-2025'}),
                ('negative',{'territorio_deficit':'42','ventana_deficit':'2021-2024'})]),
]:
    text=Path(f'evidence/pages/{route}.md').read_text()
    queries=dict(re.findall(r'```sql (\w+)\n(.*?)\n```',text,re.S))
    def render(name, inputs):
        sql=queries[name]
        sql=re.sub(r'\$\{inputs\.(\w+)\.value\}',lambda m: inputs[m[1]],sql)
        return re.sub(r'\$\{(\w+)\}',lambda m:'('+render(m[1],inputs)+')',sql)
    for identifier, inputs in scenarios:
        panels=[]
        for panel in declarations({f'evidence/pages/{route}.md':text}):
            cursor=con.execute(render(panel['query'],inputs))
            names=[d[0] for d in cursor.description]
            rows=[dict(zip(names,row,strict=True)) for row in cursor.fetchall()]
            panel['rows']=[{k:row[k] for k in panel['columns']} for row in rows]
            panels.append(panel)
        case={'route':route,'id':identifier,'inputs':inputs,'panels':panels}
        if route=='perfil':
            case['label']=con.execute('select etiqueta from ('+render('municipios_perfil',inputs)+') where codigo=?',[inputs['municipio_perfil']]).fetchone()[0]
        if route=='deficit':
            case['label']=con.execute('select provincia from deficit.comparisons where cpro=? limit 1',[inputs['territorio_deficit']]).fetchone()[0]
            case['windowLabel']=inputs['ventana_deficit'].replace('-','–')+' (años completos)'
        cases.append(case)
Path(os.environ['PROVENANCE_SMOKE_DIR'],'expected.json').write_text(json.dumps(cases,ensure_ascii=False,allow_nan=False))
PY
configuration="$(uv run python - <<'PYCONFIG'
import json,os
from pathlib import Path
cases=json.loads(Path(os.environ['PROVENANCE_SMOKE_DIR'],'expected.json').read_text())
for case in cases:
    for panel in case['panels']:
        panel.pop('rows')
print(json.dumps(cases,ensure_ascii=False))
PYCONFIG
)"
playwright-cli -s="$SESSION" open about:blank >/dev/null
output="$(playwright-cli -s="$SESSION" run-code "async(page)=>{
 const dir='$PROVENANCE_SMOKE_DIR';
 const cases=$configuration;
 const errors=[];page.on('pageerror',e=>errors.push(String(e)));
 const choose=async(title,label)=>{
   const button=page.locator('button[role=combobox]').filter({hasText:title});
   if((await button.innerText()).includes(label))return;
   await button.click();await page.locator('input[role=combobox]').last().fill(label);
   await page.getByRole('option',{name:label,exact:true}).click();
 };
 let previous='',downloads=0;
 for(const item of cases){
   if(item.route==='perfil'&&item.id==='02036')await page.setViewportSize({width:390,height:844});
   if(previous!==item.route){
     await page.goto('$BASE/'+item.route+'/',{waitUntil:'domcontentloaded'});
     await page.waitForFunction(n=>document.querySelectorAll('canvas').length>=n,{reportaje:8,perfil:3,deficit:2}[item.route],{timeout:60000});
     previous=item.route;
   }
   await page.locator('details.evidence-panel').first().waitFor();
   if(item.route==='perfil')await choose('Busca tu municipio',item.label);
   if(item.route==='deficit'){
     await choose('Años de actividad',item.windowLabel);
     await choose('España o provincia',item.label);
   }
   for(const expected of item.panels){
     const panel=page.locator('[data-evidence-chart='+expected.chart+']');
     if(!await panel.evaluate(e=>e.open)){await panel.locator('summary').focus();await page.keyboard.press('Enter');}
     for(let attempt=0;attempt<100;attempt++){
       const sql=await panel.locator('pre').innerText();
       const ready=await panel.getByRole('button',{name:'Descargar JSON del gráfico',exact:true}).isEnabled();
       if(ready&&Object.values(item.inputs).every(v=>sql.includes(\"'\"+v+\"'\")))break;
       await page.waitForTimeout(200);
     }
     const sql=await panel.locator('pre').innerText();
     if(sql.includes('$'+'{')||!Object.values(item.inputs).every(v=>sql.includes(\"'\"+v+\"'\")))throw Error('Unresolved or stale SQL: '+expected.chart);
     for(const file of expected.files)if(!(await panel.innerText()).includes(file))throw Error('Missing source: '+file);
     for(const format of ['json','csv']){
       const waiting=page.waitForEvent('download');
       await panel.getByRole('button',{name:'Descargar '+format.toUpperCase()+' del gráfico',exact:true}).click();
       let download;
       try {download=await waiting;}catch(error){throw Error(expected.chart+'/'+item.id+'/'+format+': '+String(error));}
       await download.saveAs(dir+'/'+expected.chart+'-'+item.id+'.'+format);
       // Chromium rate-limits rapid downloads; emulate distinct human actions.
       await page.waitForTimeout(500);
     }
     downloads++;
   }
 }
 await page.setViewportSize({width:390,height:844});
 const mobile=await page.evaluate(()=>({viewport:innerWidth,page:document.documentElement.scrollWidth}));
 if(mobile.page>mobile.viewport)throw Error('Expanded evidence panel overflows mobile');
 if(errors.length)throw Error(errors.join('; '));
 return {status:'Evidence panels downloaded',datasets:downloads,mobile};
}")"
printf '%s\n' "$output"
grep -q 'Evidence panels downloaded' <<<"$output"
! grep -q '^### Error' <<<"$output"
uv run python - <<'PY'
import csv,json,math,os
from pathlib import Path
root=Path(os.environ['PROVENANCE_SMOKE_DIR'])
cases=json.loads((root/'expected.json').read_text())
count=0
for case in cases:
    for panel in case['panels']:
        with (root/f"{panel['chart']}-{case['id']}.csv").open(encoding='utf-8-sig',newline='') as f:
            rows=list(csv.reader(f))
        actual_json=json.loads((root/f"{panel['chart']}-{case['id']}.json").read_text())
        identity=[k for k in panel['columns'] if k in {'anyo','ccaa','codigo','group_code','uso','serie','concepto','definicion'}]
        assert identity
        key=lambda row:tuple(row[k] for k in identity)
        expected_by_key={key(r):r for r in panel['rows']}
        actual_by_key={key(r):r for r in actual_json}
        assert len(actual_by_key)==len(actual_json)==len(expected_by_key)==len(panel['rows'])
        assert actual_by_key.keys()==expected_by_key.keys()
        for identity_key,actual in actual_by_key.items():
            expected=expected_by_key[identity_key]
            assert list(actual)==panel['columns']
            for column in panel['columns']:
                value=expected[column]
                if isinstance(value,(int,float)):
                    assert not isinstance(actual[column],bool) and isinstance(actual[column],(int,float))
                    assert math.isclose(actual[column],value,rel_tol=1e-12,abs_tol=1e-12)
                else: assert actual[column]==value
        assert rows[0]==panel['columns']
        assert len(rows)==len(actual_json)+1
        for actual,expected in zip(rows[1:],actual_json,strict=True):
            for text,key in zip(actual,panel['columns'],strict=True):
                value=expected[key]
                if value is None: assert text==''
                elif isinstance(value,(int,float)): assert math.isclose(float(text),value,rel_tol=1e-12,abs_tol=1e-12)
                else: assert text==str(value)
        count+=1
print(f'PASS chart provenance: {count} query-matched JSON datasets and independent CSV round-trips; headers/types/nulls/precision preserved')
PY
