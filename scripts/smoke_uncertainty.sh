#!/usr/bin/env bash
# Runtime contract: approximate normal ranges, not invented bootstrap intervals.
# Usage: bash scripts/smoke_uncertainty.sh [BASE_URL]
set -euo pipefail

BASE="${1:-http://127.0.0.1:3000}"
SESSION="housing-uncertainty-smoke"
if ! command -v playwright-cli >/dev/null; then
	echo "Browser validation unavailable: playwright-cli is required"
	exit 2
fi
trap 'playwright-cli -s="$SESSION" close >/dev/null 2>&1 || true' EXIT

playwright-cli -s="$SESSION" open "$BASE/incertidumbre/" >/dev/null
output="$(playwright-cli -s="$SESSION" run-code "async (page) => {
  const errors = [];
  page.on('pageerror', e => errors.push(String(e)));
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  await page.goto('$BASE/incertidumbre/', { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => [...document.querySelectorAll('table')]
    .filter(t => t.innerText.includes('¿Rango normal dentro de la banda?'))
    .some(t => [...t.querySelectorAll('tr')].filter(r => r.querySelector('td')).length === 4),
    null, { timeout: 45000 });
  const models = page.locator('table').filter({ hasText: 'Wild-p: H₀ coeficiente = 0' }).last();
  const band = page.locator('table').filter({ hasText: '¿Rango normal dentro de la banda?' }).last();
  const rows = async table => table.locator('tr').filter({ has: page.locator('td') }).allInnerTexts();
  const beforeModels = await rows(models);
  const beforeBand = await rows(band);
  if (beforeModels.length !== 4 || beforeBand.filter(r => r.includes('Sí:')).length !== 2
      || beforeBand.filter(r => r.includes('No:')).length !== 2)
    throw Error('Default normal-range containment is not hydrated correctly');
  await page.getByRole('slider').press('End');
  await page.waitForFunction(() => [...document.querySelectorAll('table')]
    .filter(t => t.innerText.includes('¿Rango normal dentro de la banda?'))
    .some(t => { const rows = [...t.querySelectorAll('tr')].filter(r => r.querySelector('td'));
      return rows.length === 4 && rows.every(r => r.innerText.includes('Sí:')); }),
    null, { timeout: 15000 });
  const afterBand = await rows(band);
  const afterModels = await rows(models);
  if (JSON.stringify(beforeModels) !== JSON.stringify(afterModels))
    throw Error('Changing the band changed source coefficients or tests');
  if (afterBand.length !== 4 || afterBand.some(r => !r.includes('Sí:')))
    throw Error('Wider magnitude band did not recalculate all specifications');
  // Prespecified candidate inversion: default sale model shows all 41 points.
  const candidates = page.locator('table').filter({ hasText: 'Wild-p de H₀: coeficiente = c' }).last();
  const summary = page.locator('table').filter({ hasText: 'Menor c no rechazado (pp)' }).last();
  await candidates.locator('td').first().waitFor({ timeout: 45000 });
  await summary.locator('td').first().waitFor({ timeout: 45000 });
  const candidateRows = async table => table.locator('tr').filter({ has: page.locator('td') }).allInnerTexts();
  const beforeCandidates = await candidateRows(candidates);
  const beforeSummary = await candidateRows(summary);
  if (beforeCandidates.length !== 41) throw Error('Inversion candidate grid is not 41 tested points');
  if (beforeSummary.length !== 4) throw Error('Inversion summary missing one of the four models');
  if (!beforeCandidates.some(r => r.includes('No rechazada')))
    throw Error('Default model shows no accepted candidate');
  // Switch to the rent-only model and confirm the grid re-renders with new p.
  const beforeText = await candidates.innerText();
  const modelo = page.locator('button[role=combobox]').filter({ hasText: 'Modelo' });
  await modelo.click();
  await page.locator('input[role=combobox]').last().fill('Alquiler · Solo turismo');
  await page.getByRole('option', { name: 'Alquiler · Solo turismo', exact: true }).click();
  await page.waitForFunction((prev) => {
    const t = [...document.querySelectorAll('table')]
      .filter(x => x.innerText.includes('Wild-p de H₀: coeficiente = c')).at(-1);
    return t && t.innerText !== prev;
  }, beforeText, { timeout: 15000 });
  const rentCandidates = await candidateRows(candidates);
  if (JSON.stringify(rentCandidates) === JSON.stringify(beforeCandidates))
    throw Error('Switching inversion model did not change the tested-point p-values');
  const text = await page.locator('body').innerText();
  for (const phrase of ['41 candidatos', 'no es una prueba de equivalencia',
      'reproduce exactamente el wild_p_zero', 'nulo, no cero', 'puntos probados'])
    if (!text.includes(phrase)) throw Error('Missing inversion caveat: ' + phrase);
  return { errors, modelRows: beforeModels.length, beforeBand, afterBand,
    candidateRows: beforeCandidates.length, summaryRows: beforeSummary.length };
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
if result["errors"]:
    raise SystemExit(f"FAIL uncertainty browser: {result['errors']}")
if result["candidateRows"] != 41 or result["summaryRows"] != 4:
    raise SystemExit(f"FAIL uncertainty browser: inversion grid/summary rows {result}")
print("OK uncertainty browser: all models hydrate; band updates without changing estimates;")
print("OK inversion grid: 41 tested points per model, model switch changes p, caveats present")
PY
