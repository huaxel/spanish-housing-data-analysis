#!/usr/bin/env bash
# Repeatable browser checks for the Evidence dashboard.
# Waits deterministically for chart hydration, asserts canvas counts and key
# content per page, and fails on page errors. Requires the global
# playwright-cli (headless by default). Complements scripts/smoke_dashboard.sh.
# Usage: bash scripts/smoke_browser.sh [BASE_URL]
set -euo pipefail

BASE="${1:-http://127.0.0.1:3000}"
SESSION="housing-browser-smoke"

if ! command -v playwright-cli >/dev/null; then
	echo "SKIP browser checks: playwright-cli not installed"
	exit 0
fi

check_page() { # check_page <path> <min canvases> <snippet> [snippet...]
	local path="$1" min_canvases="$2"; shift 2
	local snippets_json
	snippets_json="$(printf '%s\n' "$@" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read().splitlines()))')"
	local result
	result="$(playwright-cli -s="$SESSION" run-code "async (page) => {
		const errs = [];
		page.on('pageerror', (e) => errs.push(String(e && e.message || e)));
		await page.goto('$BASE$path', { waitUntil: 'domcontentloaded' });
		await page.waitForFunction(
			(n) => document.querySelectorAll('canvas').length >= n, $min_canvases, { timeout: 30000 });
		const text = await page.evaluate(() => document.body.innerText);
		const canvases = await page.evaluate(() => document.querySelectorAll('canvas').length);
		const missing = $snippets_json.filter((s) => !text.includes(s));
		return { canvases, missing, errs };
	}" 2>/dev/null | sed -n '/^### Result/,/^### Ran/p' | sed '1d;$d')"
	python3 - "$path" "$result" <<'PY'
import json, sys
path, result = sys.argv[1], json.loads(sys.argv[2])
problems = []
if result["errs"]:
    problems.append(f"page errors: {result['errs']}")
if result["missing"]:
    problems.append(f"missing content: {result['missing']}")
if problems:
    print(f"FAIL browser {path} (canvases={result['canvases']}): " + "; ".join(problems))
    sys.exit(1)
print(f"OK   browser {path} (canvases={result['canvases']})")
PY
}

trap 'playwright-cli -s="$SESSION" close >/dev/null 2>&1 || true' EXIT

playwright-cli -s="$SESSION" open "$BASE/" >/dev/null 2>&1

fail=0
check_page "/"           8 "Precios, stock" "Datos y cobertura" || fail=1
check_page "/ccaa/"      7 "Comunidades autónomas" "Madrid, Comunidad de" || fail=1
check_page "/comparar/"  7 "Resumen del periodo" "38 records" || fail=1
check_page "/municipios/" 5 "la capital se despega" "Santa Coloma de Gramenet" || fail=1
exit $fail
