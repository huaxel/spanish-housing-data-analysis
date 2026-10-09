#!/usr/bin/env bash
set -euo pipefail
BASE="${1:-http://127.0.0.1:3000}"
SESSION="housing-ecv-joint-smoke"
command -v playwright-cli >/dev/null || { echo 'playwright-cli required'; exit 2; }
trap 'playwright-cli -s="$SESSION" close >/dev/null 2>&1 || true' EXIT
uv run python scripts/build_ecv_joint.py --check
expected="$(uv run python - <<'PY'
import duckdb,json
from spanish_housing.data_paths import PROCESSED
with duckdb.connect(str(PROCESSED/'ecv_joint_burden.duckdb'),read_only=True) as c:
 cursor=c.execute("select * from joint_burden order by age_code,poverty_code,tenure_code")
 names=[x[0] for x in cursor.description]
 print(json.dumps([dict(zip(names,r,strict=True)) for r in cursor.fetchall()]))
PY
)"
playwright-cli -s="$SESSION" open about:blank >/dev/null
output="$(playwright-cli -s="$SESSION" run-code "async (page) => {
 const expected=$expected, errors=[];
 page.on('pageerror',e=>errors.push(String(e)));
 page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
 await page.goto('$BASE/acceso/',{waitUntil:'domcontentloaded'});
 const headings=['Personas sobrecargadas dentro del grupo','Personas de la muestra: grupo',
                 'Personas de hogares con renta total marcada como imputada'];
 for(const h of headings) await page.locator('table').filter({hasText:h}).last().locator('td').first().waitFor({timeout:45000});
 const matrix=page.locator('table').filter({hasText:'Carga en alquiler de mercado (%)'}).last();
 await matrix.locator('td').first().waitFor({timeout:45000});
 const matrixRows=await matrix.locator('tr').evaluateAll(rows=>rows.map(r=>
   [...r.querySelectorAll('td')].map(c=>c.innerText.trim())).filter(r=>r.length));
 const matrixExpected=expected.filter(r=>r.tenure_code==='RENT_MKT'&&r.age_code!=='TOTAL'&&r.poverty_code!=='TOTAL');
 if(matrixRows.length!==10||matrixExpected.length!==10)throw Error('Incomplete market-rent grid');
 const seen=new Set();
 for(const a of matrixRows){
   const r=matrixExpected.find(r=>r.age_label===a[0]&&r.poverty_label===a[1]);
   if(!r||seen.has(r.age_code+':'+r.poverty_code))throw Error('Matrix coordinates differ or duplicate');
   seen.add(r.age_code+':'+r.poverty_code);
   const count=s=>Number(s.replace(/[^0-9]/g,'')),num=s=>Number(s.replace(',', '.'));
   const state=r.status==='available'?'Estimación descriptiva disponible':
     r.status==='empty'?'Sin personas en la muestra de esta combinación':
     r.status==='no_valid_cost'?'Sin costes válidos':'Tasa no mostrada: muestra o cobertura insuficiente';
   if(count(a[2])!==r.survey_year||count(a[3])!==r.income_year||
      (r.rate_pct===null?/[0-9]/.test(a[4]):!Number.isFinite(num(a[4]))||Math.abs(num(a[4])-r.rate_pct)>=0.051)||
      count(a[5])!==r.sample_valid_persons||count(a[6])!==r.sample_valid_households||
      (r.weighted_missing_cost_loss_pct===null?/[0-9]/.test(a[7]):!Number.isFinite(num(a[7]))||Math.abs(num(a[7])-r.weighted_missing_cost_loss_pct)>=0.0051)||
      a[8]!==state||(r.suppression_reasons?a[9]!==r.suppression_reasons:/[a-z0-9]/i.test(a[9])))
     throw Error('Market-rent matrix rate/null/coverage/status differs');
 }
 const select=async(title,label)=>{
   const button=page.locator('button[role=combobox]').filter({hasText:title});
   if((await button.innerText()).includes(label))return;
   await button.click();
   // Evidence virtualises its menu: search reaches options below the first five.
   await page.locator('input[role=combobox]').last().fill(label);
   await page.getByRole('option',{name:label,exact:true}).click();
 };
 for(const row of expected){
   await select('Edad de la persona (fin del año de ingresos)',row.age_label);
   await select('Situación respecto al umbral nacional',row.poverty_label);
   await select('Régimen del hogar',row.tenure_label);
   const wanted={row,headings};
   try { await page.waitForFunction(({row:r,headings})=>{
     const cells=heading=>{
       const tables=[...document.querySelectorAll('table')].filter(t=>t.innerText.includes(heading));
       const t=tables.at(-1);
       return t?[...t.querySelectorAll('td')].map(x=>x.innerText.trim()):[];
     };
     const [a,b,c]=headings.map(cells);
     if(a.length!==5||b.length!==6||c.length!==2)return false;
     const count=s=>Number(s.replace(/[^0-9]/g,''));
     const rate=s=>Number(s.replace(',', '.'));
     const blank=s=>!/[0-9]/.test(s);
     const state=r.status==='available'?'Estimación descriptiva disponible':
       r.status==='empty'?'Sin personas en la muestra de esta combinación':
       r.status==='no_valid_cost'?'Sin costes válidos':
       r.status==='marginal_not_published'?'Tasa no publicada: total solapado':
       'Tasa no mostrada: muestra o cobertura insuficiente';
     return count(a[0])===r.survey_year&&count(a[1])===r.income_year&&a[3]===state&&
       (r.rate_pct===null?blank(a[2]):Math.abs(rate(a[2])-r.rate_pct)<0.051)&&
       (r.suppression_reasons?a[4]===r.suppression_reasons:blank(a[4]))&&
       count(b[0])===r.sample_target_persons&&count(b[1])===r.sample_valid_persons&&
       count(b[2])===r.sample_valid_households&&
       Math.abs(count(b[3])-r.weighted_target_persons)<=0.501&&
       Math.abs(count(b[4])-r.weighted_valid_persons)<=0.501&&
       (r.weighted_missing_cost_loss_pct===null?blank(b[5]):
         Math.abs(rate(b[5])-r.weighted_missing_cost_loss_pct)<0.0051)&&
       count(c[0])===r.known_imputed_income_target_persons&&
       count(c[1])===r.known_imputed_allowance_target_persons;
   },wanted,{timeout:15000}); } catch(e) {
     const actual=await Promise.all(headings.map(h=>page.locator('table').filter({hasText:h}).last().locator('td').allTextContents()));
     throw Error(JSON.stringify({coordinates:[row.age_code,row.poverty_code,row.tenure_code],wanted:row,actual,cause:String(e)}));
   }
 }
 const text=await page.locator('body').innerText();
 for(const phrase of ['Estimación descriptiva propia','no por quintiles','jóvenes co-residentes',
     'menos de 50 personas válidas','menos de 30 hogares distintos válidos','más del 5%',
     'no es cero','No hay intervalos de diseño','no demuestra que cada joven pague el alquiler',
     'No es un efecto de la edad', 'componente mecánico'])
   if(!text.includes(phrase))throw Error('Missing caveat: '+phrase);
 if(errors.length)throw Error(errors.join('; '));
 return 'PASS ECV joint: 90 selector combinations and 10-cell market-rent comparison, rates/nulls/statuses, coverage, imputation and caveats';
}")"
printf '%s\n' "$output"
grep -q 'PASS ECV joint: 90 selector' <<<"$output"
! grep -q '^### Error' <<<"$output"
