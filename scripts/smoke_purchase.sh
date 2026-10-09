#!/usr/bin/env bash
# Actual browser contract for /compra/: compilation alone missed a missing
# query bundle and an incorrect Slider input.value interpolation.
# Usage: bash scripts/smoke_purchase.sh [BASE_URL]
set -euo pipefail

BASE="${1:-http://127.0.0.1:3000}"
SESSION="housing-purchase-smoke"
if ! command -v playwright-cli >/dev/null; then
	echo "Browser validation unavailable: playwright-cli is required"
	exit 2
fi
trap 'playwright-cli -s="$SESSION" close >/dev/null 2>&1 || true' EXIT

playwright-cli -s="$SESSION" open "$BASE/compra/" >/dev/null
output="$(playwright-cli -s="$SESSION" run-code "async (page) => {
  const errors = [];
  page.on('pageerror', e => errors.push(String(e)));
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  await page.goto('$BASE/compra/', { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => document.querySelectorAll('canvas').length >= 1,
    null, { timeout: 45000 });
  const numbers = page.locator('input[type=number]');
  if (await numbers.count() !== 6) throw Error('Numeric control contract changed');
  const cash = page.locator('table').filter({ hasText: 'Precio (€)' }).last();
  const payments = page.locator('table').filter({ hasText: 'Escenario hipotético' }).last();
  const cells = async table => table.locator('tr').filter({ has: page.locator('td') }).first().locator('td').allInnerTexts();
  const clean = values => values.map(v => Number(v.replaceAll(',', '').trim()));
  const initialCash = clean(await cells(cash));
  const initialPayment = (await cells(payments))[2];
  if (initialCash[4] !== 75000 || initialCash[6] !== 25000 || initialPayment !== '843.21')
    throw Error('Default scenario is not hydrated correctly: ' + JSON.stringify({ initialCash, initialPayment }));
  await numbers.nth(0).fill('300000');
  await page.waitForFunction(() => [...document.querySelectorAll('table')]
    .some(t => t.innerText.includes('1,011.85')), null, { timeout: 15000 });
  const changedCash = clean(await cells(cash));
  const changedPayment = (await cells(payments))[2];
  if (changedCash[4] !== 90000 || changedCash[6] !== 40000 || changedPayment !== '1,011.85')
    throw Error('Price input did not recalculate cash and debt service');
  await numbers.nth(1).fill('0');
  await page.waitForFunction(() => [...document.querySelectorAll('table')]
    .filter(t => t.innerText.includes('Escenario hipotético'))
    .some(t => { const rows = [...t.querySelectorAll('tr')].filter(r => r.querySelector('td'));
      return rows.length === 3 && rows.every(r => r.querySelectorAll('td')[2]?.innerText.trim() === '0.00'); }),
    null, { timeout: 15000 });
  const noLoanCash = clean(await cells(cash));
  if (noLoanCash[1] !== 0 || noLoanCash[4] !== 330000) throw Error('No-loan cash is wrong');
  return { errors, initialCash, initialPayment, changedCash, changedPayment, noLoanCash };
}" 2>&1)"
result="$(printf '%s\n' "$output" | sed -n '/^### Result/,/^### Ran/p' | sed '1d;$d')"
if [ -z "$result" ]; then
	printf '%s\n' "$output"
	exit 1
fi

python3 - "$result" <<'PY'
import json
import sys

if not sys.argv[1].strip():
    raise SystemExit("FAIL purchase browser: no result; page hydration or assertions failed")
result = json.loads(sys.argv[1])
if result["errors"]:
    raise SystemExit(f"FAIL purchase browser: {result['errors']}")
print("OK purchase browser: defaults hydrate; price and no-loan controls recalculate")
PY
