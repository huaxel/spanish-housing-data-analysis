#!/usr/bin/env bash
# Repeatable health check for the Evidence dashboard (local + Tailscale).
# Dev mode serves a client-rendered shell, so HTTP checks assert liveness
# only; page content is asserted against the prerendered static build.
# Usage: bash scripts/smoke_dashboard.sh [TAILNET_IP=...]
set -euo pipefail

if [ -z "${TAILNET_IP:-}" ]; then
	TAILNET_IP="$(tailscale ip -4 2>/dev/null | head -1 || true)"
fi
if [ -z "$TAILNET_IP" ]; then
	echo "FAIL tailnet: no address (is tailscaled running? or set TAILNET_IP=...)"
	exit 1
fi
LOCAL="http://127.0.0.1:3000"
fail=0

alive() { # alive <label> <url>
	local label="$1" url="$2" code
	code="$(curl --max-time 15 -s -o /dev/null -w '%{http_code}' "$url" || true)"
	if [ "$code" != "200" ]; then
		echo "FAIL $label: HTTP $code ($url)"; fail=1
	else
		echo "OK   $label ($url)"
	fi
}

content() { # content <label> <file> <snippet>
	if [ ! -f "$1" ]; then
		echo "FAIL $2: missing $1 (run: make evidence-build)"; fail=1; return
	fi
	if ! grep -q "$3" "$1"; then
		echo "FAIL $2: '$3' not in $1 (stale build? run: make evidence-build)"; fail=1
	else
		echo "OK   $2"
	fi
}

alive "dev nacional"      "$LOCAL/"
alive "dev comunidades"   "$LOCAL/ccaa/"
alive "dev comparar"      "$LOCAL/comparar/"
alive "dev municipios"    "$LOCAL/municipios/"
alive "dev renta"         "$LOCAL/renta/"
alive "dev vacancia"      "$LOCAL/vacancia/"
alive "tailnet comparar"  "http://$TAILNET_IP:3000/comparar/"

content evidence/build/index.html          "build nacional"     "Precios, stock"
content evidence/build/ccaa/index.html     "build comunidades"  "Comunidades aut"
content evidence/build/comparar/index.html "build comparar"     "Resumen del periodo"
content evidence/build/municipios/index.html "build municipios" "la capital se despega"
content evidence/build/renta/index.html    "build renta"        "Renta municipal"
content evidence/build/vacancia/index.html "build vacancia"     "Vivienda vacía"

if ! tailscale serve status 2>/dev/null | grep -q 'tcp://.*:3000'; then
	echo "FAIL tailscale: no TCP :3000 proxy configured"; fail=1
else
	echo "OK   tailscale TCP :3000 proxy configured"
fi

if [ ! -f evidence/.evidence/template/static/data/manifest.json ]; then
	echo "FAIL sources: no extracted source manifest (run: cd evidence && npm run sources)"; fail=1
else
	echo "OK   sources manifest present"
fi

exit $fail
