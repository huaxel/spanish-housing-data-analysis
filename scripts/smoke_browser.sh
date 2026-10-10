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
			(n) => document.querySelectorAll('canvas').length >= n && (document.querySelector('h1')?.innerText.length ?? 0) > 0,
			$min_canvases, { timeout: 30000 });
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

check_map() { # check_map <path>: Leaflet container + municipal polygons, no page errors
	local path="$1"
	local result
	result="$(playwright-cli -s="$SESSION" run-code "async (page) => {
		const errs = [];
		page.on('pageerror', (e) => errs.push(String(e && e.message || e)));
		await page.goto('$BASE$path', { waitUntil: 'domcontentloaded' });
		await page.waitForFunction(
			() => document.querySelectorAll('.leaflet-container').length >= 1,
			null, { timeout: 30000 });
		await page.waitForTimeout(5000);
		return {
			leaflet: await page.evaluate(() => document.querySelectorAll('.leaflet-container').length),
			paths: await page.evaluate(() => document.querySelectorAll('.leaflet-container svg path').length),
			errs
		};
	}" 2>/dev/null | sed -n '/^### Result/,/^### Ran/p' | sed '1d;$d')"
	python3 - "$path" "$result" <<'PY'
import json, sys
path, result = sys.argv[1], json.loads(sys.argv[2])
problems = []
if result["errs"]:
    problems.append(f"page errors: {result['errs']}")
if result["leaflet"] < 1:
    problems.append("no leaflet container")
if result["paths"] < 3000:
    problems.append(f"too few polygons: {result['paths']}")
if problems:
    print(f"FAIL map {path}: " + "; ".join(problems))
    sys.exit(1)
print(f"OK   map {path} (polygons={result['paths']})")
PY
}

trap 'playwright-cli -s="$SESSION" close >/dev/null 2>&1 || true' EXIT

# Open with retry: playwright-cli can race the session bootstrap; a cold
# open occasionally fails and poisons every later $result with empty JSON.
for _ in 1 2 3; do
	if playwright-cli -s="$SESSION" open "$BASE/" >/dev/null 2>&1; then
		break
	fi
	sleep 2
done

fail=0
check_page "/"           8 "Precios, stock" "Datos y cobertura" || fail=1
check_page "/ccaa/"      7 "Comunidades autónomas" "Madrid, Comunidad de" || fail=1
# NOTE: dev renders query-inspector chrome ('N records ...') that static
# builds omit — assert shipped content only, valid against both.
check_page "/comparar/"  7 "Resumen del periodo" "comunitat valenciana" || fail=1
check_page "/municipios/" 5 "la capital se despega" "Santa Coloma de Gramenet" || fail=1
check_page "/renta/"      2 "Renta municipal" "SERPAVI" || fail=1
check_page "/renta-ingresos/" 2 "Cuánta renta municipal se va en firmar un contrato" "tasa de sobrecarga" "SERPAVI" || fail=1
check_page "/vacancia/"   1 "Vivienda vacía" "consumo eléctrico" || fail=1
check_page "/acceso/" 0 "Stock no es acceso" "Por quintil de ingresos" "Hacinamiento por quintil de ingresos" "Módulo ECV 2025" || fail=1
check_page "/compra/" 1 "efectivo inicial y cuota" "Supuestos editables" || fail=1
check_page "/incertidumbre/" 0 "No detectar no es demostrar ausencia" "Tamaño y precisión" || fail=1
check_page "/stock/" 8 "Qué vivienda existe y dónde" "distribución ponderada" "Capitales andaluzas" "Provincia de Sevilla" || fail=1
check_map "/vacancia/" || fail=1
exit $fail
