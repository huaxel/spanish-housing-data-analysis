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
  return { errors, modelRows: beforeModels.length, beforeBand, afterBand };
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
print("OK uncertainty browser: all models hydrate; band updates without changing estimates")
PY
