"""Interactive localhost dashboard (Evidence stays upstream-blocked).

Reads marts.duckdb, writes artifacts/preview/index.html: self-contained page
(no CDN, no build step) with a CCAA selector driving SVG charts from embedded
JSON. Serve: python3 -m http.server -d artifacts/preview 8091 --bind 0.0.0.0
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import duckdb  # noqa: E402
from spanish_housing.data_paths import PROCESSED, ROOT  # noqa: E402

con = duckdb.connect(str(PROCESSED / "marts.duckdb"), read_only=True)

COLS = ["ccaa", "anyo", "viv_por_1000_hab", "viv_por_hogar", "eur_m2_libre",
        "ipv_general", "afford_90m2_years", "hip_viv_num", "share_20_34",
        "share_1persona", "hogares", "poblacion", "share_nueva", "trx_total",
        "viv_turisticas", "share_turistica_no_princ", "pop_source"]
rows = [dict(zip(COLS, r, strict=True)) for r in con.execute(
    f"SELECT {', '.join(COLS)} FROM mart_ccaa_anual ORDER BY ccaa, anyo").fetchall()]
data = {}
for r in rows:
    data.setdefault(r["ccaa"], []).append({k: v for k, v in r.items() if k != "ccaa"})

table25 = con.execute(
    "SELECT ccaa, eur_m2_libre, afford_90m2_years, viv_por_hogar, viv_por_1000_hab,"
    " hip_viv_num, share_turistica_no_princ FROM mart_ccaa_anual"
    " WHERE anyo = 2025 AND ccaa != 'Nacional' ORDER BY eur_m2_libre DESC").fetchall()
aff24 = {r[0]: r[1] for r in con.execute(
    "SELECT ccaa, afford_90m2_years FROM mart_ccaa_anual WHERE anyo = 2024").fetchall()}


def pct(t) -> str:
    return f"{t * 100:.1f}%" if t else "—"


table = "".join(
    f"<tr><td>{c}</td><td>{e:,.0f}</td><td>{aff24.get(c) or '—'}</td>"
    f"<td>{h or '—'}</td><td>{v:,.0f}</td><td>{n:,.0f}</td><td>{pct(t)}</td></tr>"
    for c, e, _a, h, v, n, t in table25)

options = "".join(f"<option>{c}</option>" for c in sorted(data))

html = """<!doctype html><html lang="es"><head><meta charset="utf-8">
<title>Vivienda en España — panel</title>
<style>body{font-family:sans-serif;max-width:720px;margin:auto;padding:16px}
table{border-collapse:collapse;width:100%}td,th{border:1px solid #ddd;padding:4px 8px;font-size:13px;text-align:right}
td:first-child,th:first-child{text-align:left}.note{color:#666;font-size:13px}
select{font-size:15px;padding:4px 8px;margin:8px 0}svg{max-width:100%}</style>
</head><body>
<h1>Vivienda en España: precios, stock y población</h1>
<p class="note">Panel interactivo sobre los marts (<code>make gates</code> en verde).
El visor Evidence sigue bloqueado upstream — esta página lo sustituye.</p>
<label>Territorio: <select id="terr">""" + options + """</select></label>
<div id="charts"></div>
<h3>CCAA 2025 (asequibilidad 2024)</h3>
<table><tr><th>CCAA</th><th>€/m²</th><th>años renta</th><th>viv/hogar</th>
<th>viv/1000</th><th>hipotecas</th><th>% tur/no-princ</th></tr>""" + table + """</table>
<p class="note">Métodos y límites en <code>docs/methods.md</code>. Celdas vacías pre-2021/2022/2025 según ventana de cada fuente.</p>
<script>
const DATA = """ + json.dumps(data) + """;
function line(el, title, years, left, right, ll, rl) {
  const W = 660, H = 250, P = 46;
  const L = left.filter(v => v != null), R = right.filter(v => v != null);
  let lo = Math.min(...L), hi = Math.max(...L), rlo = Math.min(...R), rhi = Math.max(...R);
  if (lo === hi) hi = lo + 1; if (rlo === rhi) rhi = rlo + 1;
  const X = i => P + i / (years.length - 1) * (W - 2 * P);
  const Y = (v, a, b) => H - P - (v - a) / (b - a) * (H - 2 * P);
  function path(vals, a, b) {
    let d = "", pen = false;
    vals.forEach((v, i) => {
      if (v == null) { pen = false; return; }
      d += (pen ? " L" : "M") + X(i).toFixed(0) + "," + Y(v, a, b).toFixed(0);
      pen = true;
    });
    return d;
  }
  const last = (vals, a, b) => {
    for (let i = vals.length - 1; i >= 0; i--)
      if (vals[i] != null) return [X(i), Y(vals[i], a, b)];
  };
  const [lx, ly] = last(left, lo, hi), [rx, ry] = last(right, rlo, rhi);
  let grid = "";
  [P, H / 2, H - P].forEach(y => {
    grid += `<line x1="${P}" y1="${y}" x2="${W - P}" y2="${y}" stroke="#eee"/>`;
  });
  el.innerHTML = `<h3>${title}</h3><svg width="${W}" height="${H}">${grid}`
    + `<path d="${path(left, lo, hi)}" stroke="#1f77b4" stroke-width="2" fill="none"/>`
    + `<circle cx="${lx}" cy="${ly}" r="3" fill="#1f77b4"/>`
    + `<path d="${path(right, rlo, rhi)}" stroke="#d62728" stroke-width="2" fill="none" stroke-dasharray="5,3"/>`
    + `<circle cx="${rx}" cy="${ry}" r="3" fill="#d62728"/>`
    + `<text x="${P}" y="${H - 8}" font-size="10" fill="#666">${years[0]} … ${years[years.length - 1]}</text>`
    + `<text x="${W - P}" y="16" font-size="11" fill="#1f77b4" text-anchor="end">— ${ll} (${lo}–${hi})</text>`
    + `<text x="${W - P}" y="30" font-size="11" fill="#d62728" text-anchor="end">- - ${rl} (${rlo}–${rhi})</text></svg>`;
}
function render(terr) {
  const rows = DATA[terr];
  const years = rows.map(r => r.anyo);
  const col = k => rows.map(r => r[k]);
  const el = document.getElementById("charts");
  el.innerHTML = "";
  const panels = [
    ["Precio: IPV vs €/m² libre", col("ipv_general"), col("eur_m2_libre"), "IPV base 2025", "€/m²"],
    ["Stock: viv/1000 hab vs viv/hogar", col("viv_por_1000_hab"), col("viv_por_hogar"), "viv/1000", "viv/hogar"],
    ["Asequibilidad (años renta 90m²) vs hipotecas", col("afford_90m2_years"), col("hip_viv_num"), "años", "hipotecas"],
    ["Jóvenes 20–34 (%) vs 1-persona (%)", col("share_20_34").map(v => v == null ? null : +(v * 100).toFixed(2)), col("share_1persona").map(v => v == null ? null : +(v * 100).toFixed(2)), "% 20–34", "% 1-pers"],
  ];
  panels.forEach(([t, l, r, ll, rl]) => {
    const d = document.createElement("div");
    el.appendChild(d);
    line(d, terr + " — " + t, years, l, r, ll, rl);
  });
}
const sel = document.getElementById("terr");
sel.value = "Nacional";
sel.addEventListener("change", () => render(sel.value));
render("Nacional");
</script></body></html>"""

outdir = ROOT / "artifacts" / "preview"
outdir.mkdir(parents=True, exist_ok=True)
(outdir / "index.html").write_text(html, encoding="utf-8")
print(f"dashboard: {outdir / 'index.html'} ({len(html) // 1024} KiB, "
      f"{len(data)} territorios)")
