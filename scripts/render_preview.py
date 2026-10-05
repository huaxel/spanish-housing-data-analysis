"""Render a static localhost preview of the explorer pages (Evidence is blocked).

Reads marts.duckdb, writes artifacts/preview/index.html with inline SVG.
Serve: uv run python scripts/render_preview.py && python -m http.server -d artifacts/preview 8088
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import duckdb  # noqa: E402

from spanish_housing.data_paths import PROCESSED, ROOT  # noqa: E402

con = duckdb.connect(str(PROCESSED / "marts.duckdb"), read_only=True)
W, H, PAD = 640, 260, 44


def svg_dual(title: str, xs: list, left: list, right: list, llabel: str, rlabel: str) -> str:
    def scale(vs: list, lo: float, hi: float) -> list:
        return [
            H - PAD - (v - lo) / (hi - lo) * (H - 2 * PAD) if v is not None else None for v in vs
        ]

    lx, rx = [v for v in left if v is not None], [v for v in right if v is not None]
    llo, lhi, rlo, rhi = min(lx), max(lx), min(rx), max(rx)
    if llo == lhi:
        lhi = llo + 1
    if rlo == rhi:
        rhi = rlo + 1
    n = len(xs)
    X = [PAD + i / (n - 1) * (W - 2 * PAD) for i in range(n)]

    def path(ys: list, lo: float, hi: float, vals: list) -> str:
        pts = [(X[i], ys[i]) for i, v in enumerate(vals) if v is not None]
        return "M" + " L".join(f"{x:.0f},{y:.0f}" for x, y in pts)

    ly, ry = scale(left, llo, lhi), scale(right, rlo, rhi)
    lx_last = next((X[i], ly[i]) for i in range(n - 1, -1, -1) if left[i] is not None)
    rx_last = next((X[i], ry[i]) for i in range(n - 1, -1, -1) if right[i] is not None)
    grid = "".join(
        f'<line x1="{PAD}" y1="{y}" x2="{W - PAD}" y2="{y}" stroke="#eee"/>'
        f'<text x="4" y="{y + 4}" font-size="10" fill="#666">{llo + (lhi - llo) * (H - PAD - y) / (H - 2 * PAD):.0f}</text>'
        for y in (PAD, H // 2, H - PAD)
    )
    return (
        f"<h3>{title}</h3><svg width='{W}' height='{H}' font-family='sans-serif'>"
        f"{grid}<path d='{path(ly, llo, lhi, left)}' stroke='#1f77b4' stroke-width='2' fill='none'/>"
        f"<circle cx='{lx_last[0]:.0f}' cy='{lx_last[1]:.0f}' r='3' fill='#1f77b4'/>"
        f"<path d='{path(ry, rlo, rhi, right)}' stroke='#d62728' stroke-width='2' "
        f"fill='none' stroke-dasharray='5,3'/>"
        f"<circle cx='{rx_last[0]:.0f}' cy='{rx_last[1]:.0f}' r='3' fill='#d62728'/>"
        f"<text x='{PAD}' y='{H - 8}' font-size='10' fill='#666'>{xs[0]} … {xs[-1]}</text>"
        f"<text x='{W - PAD}' y='16' font-size='11' fill='#1f77b4' text-anchor='end'>— {llabel}</text>"
        f"<text x='{W - PAD}' y='30' font-size='11' fill='#d62728' text-anchor='end'>- - {rlabel}</text>"
        "</svg>"
    )


def col(sql: str, params: list | None = None) -> list:
    return [r[0] for r in con.execute(sql, params or []).fetchall()]


nat = "SELECT anyo, ipv_general, eur_m2_libre, viv_por_1000_hab, viv_por_hogar, afford_90m2_years, hip_viv_num, share_20_34 FROM mart_ccaa_anual WHERE ccaa='Nacional' ORDER BY anyo"
rows = con.execute(nat).fetchall()
years = [r[0] for r in rows]
ipv = [r[1] for r in rows]
eur = [r[2] for r in rows]
v1000 = [r[3] for r in rows]
vhogar = [r[4] for r in rows]
afford = [r[5] for r in rows]
hip = [r[6] for r in rows]
yshare = [round(r[7] * 100, 2) if r[7] else None for r in rows]

ccaa25 = con.execute(
    "SELECT ccaa, eur_m2_libre, afford_90m2_years, viv_por_hogar, viv_por_1000_hab,"
    " hip_viv_num, share_turistica_no_princ FROM mart_ccaa_anual"
    " WHERE anyo=2025 AND ccaa!='Nacional' ORDER BY eur_m2_libre DESC"
).fetchall()
ccaa24 = {
    r[0]: r[1]
    for r in con.execute(
        "SELECT ccaa, afford_90m2_years FROM mart_ccaa_anual WHERE anyo=2024"
    ).fetchall()
}


def pct(t: float | None) -> str:
    return f"{t * 100:.1f}%" if t else "—"


table = "".join(
    f"<tr><td>{c}</td><td>{e:,.0f}</td><td>{ccaa24.get(c) or '—'}</td>"
    f"<td>{h or '—'}</td><td>{v:,.0f}</td><td>{n:,.0f}</td><td>{pct(t)}</td></tr>"
    for c, e, _a, h, v, n, t in ccaa25
)

html = f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<title>Vivienda en España — vista previa</title>
<style>body{{font-family:sans-serif;max-width:700px;margin:auto;padding:16px}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ddd;padding:4px 8px;font-size:13px;text-align:right}}td:first-child,th:first-child{{text-align:left}}.note{{color:#666;font-size:13px}}</style>
</head><body>
<h1>Vivienda en España: precios, stock y población</h1>
<p class="note">Vista previa estática de los marts (<code>make gates</code> en verde).
El visor Evidence está bloqueado por un bug upstream — estas son sus mismas consultas.</p>
{svg_dual("Precio: IPV (índice) vs valor tasado (€/m²) — Nacional", years, ipv, eur, "IPV base 2025", "€/m² libre")}
{svg_dual("Stock: viviendas por 1.000 hab. vs por hogar — Nacional", years, v1000, vhogar, "viv/1000 hab", "viv/hogar")}
{svg_dual("Asequibilidad (años de renta, 90 m²) vs hipotecas — Nacional", years, afford, hip, "años renta", "hipotecas")}
{svg_dual("Cuota 20–34 años (%) vs IPV — Nacional", years, yshare, ipv, "% 20–34", "IPV")}
<h3>CCAA 2025 (asequibilidad 2024)</h3>
<table><tr><th>CCAA</th><th>€/m²</th><th>años renta</th><th>viv/hogar</th><th>viv/1000</th><th>hipotecas</th><th>% tur/no-princ</th></tr>{table}</table>
<p class="note">Métodos y límites en <code>docs/methods.md</code>. Nulps pre-2021 en viv/hogar y renta (ventanas ECP/ECH).</p>
</body></html>"""

outdir = ROOT / "artifacts" / "preview"
outdir.mkdir(parents=True, exist_ok=True)
(outdir / "index.html").write_text(html, encoding="utf-8")
print(f"preview: {outdir / 'index.html'} ({len(html) // 1024} KiB)")
