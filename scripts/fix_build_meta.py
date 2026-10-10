"""Post-process Evidence build HTML: lang=es + per-route meta descriptions.

Evidence renders `<html lang="en">` from its own app template (which build
regenerates, so editing the template does not stick). Run after every
`evidence-build` (wired in the Makefile) and before deploy.
Idempotent: skips files already fixed.
"""

from __future__ import annotations

from pathlib import Path

BUILD = Path(__file__).resolve().parents[1] / "evidence" / "build"
STATIC = Path(__file__).resolve().parents[1] / "evidence" / "static" / "social"
SITE = "https://vivienda.juanbenjumea.me"
DEFAULT_CARD = "default.png"

DESCRIPTIONS = {
    "index.html": (
        "Precios, stock de vivienda y población en España 2007–2025: "
        "IPV, valor tasado, viviendas por 1.000 habitantes, esfuerzo de renta y crédito."
    ),
    "ccaa/index.html": (
        "Detalle por comunidades autónomas: precios, stock por habitante, "
        "esfuerzo de renta y crédito hipotecario 2007–2025."
    ),
    "comparar/index.html": (
        "Compara dos territorios españoles en precios, stock, esfuerzo de renta, "
        "población joven e hipotecas para el periodo que elijas."
    ),
    "municipios/index.html": (
        "Grano municipal en Madrid y Barcelona: valor tasado, población "
        "y vivienda vacía por municipio 2005–2025."
    ),
    "renta/index.html": (
        "Renta de alquiler por municipio (SERPAVI 2011–2024): niveles, "
        "esfuerzo y relación con la vivienda vacía."
    ),
    "incertidumbre/index.html": (
        "Incertidumbre del panel municipal de turismo: coeficientes, rangos "
        "normales aproximados y pruebas wild-bootstrap, sin equivalencia causal."
    ),
    "compra/index.html": (
        "Escenarios hipotéticos de compra: entrada, gastos iniciales, "
        "cuotas hipotecarias y sensibilidad a tipos bajo supuestos editables."
    ),
    "acceso/index.html": (
        "Acceso a la vivienda en Madrid, Barcelona y la costa valenciana: "
        "stock, disponibilidad, esfuerzo medio y sensibilidad descriptiva."
    ),
    "stock-2021/index.html": (
        "Sevilla municipal con referencia 2021: viviendas y hogares censales, "
        "alquiler anual y contexto de uso eléctrico, con fechas y cobertura explícitas."
    ),
    "stock/index.html": (
        "Stock físico catastral de Sevilla: huellas, fechas constructivas y "
        "superficies por barrio, con unidades y cobertura espacial explícitas."
    ),
    "vacancia/index.html": (
        "Vivienda vacía por consumo eléctrico (Censo 2021): mapa municipal "
        "de la desocupación en España."
    ),
    "renta-ingresos/index.html": (
        "Alquiler de firma frente a renta neta municipal (SERPAVI + ADRH, "
        "2015–2023): la mediana es plana, las grandes ciudades suben. "
        "Proxy de mercado, no tasa de sobrecarga."
    ),
}


def card_for(rel: str) -> str:
    """Social image URL: per-route card when the asset exists, else the default."""
    stem = Path(rel).parent.name if rel != "index.html" else "index"
    name = f"{stem}.png" if stem != "index" else DEFAULT_CARD
    if not (STATIC / name).exists():
        name = DEFAULT_CARD
    return f"{SITE}/social/{name}"


def fix_page(page: Path, desc: str) -> bool:
    html = page.read_text(encoding="utf-8")
    updated = html.replace('<html lang="en">', '<html lang="es">')
    anchor = '<meta charset="utf-8" />'
    if anchor not in updated:
        raise SystemExit(f"{page}: charset anchor missing, template changed?")
    rel = str(page.relative_to(BUILD))
    tags = [
        f'<meta name="description" content="{desc}" />',
        f'<meta property="og:description" content="{desc}" />',
        f'<meta name="twitter:description" content="{desc}" />',
        f'<meta property="og:image" content="{card_for(rel)}" />',
        f'<meta name="twitter:image" content="{card_for(rel)}" />',
    ]
    for tag in tags:
        if tag not in updated:
            updated = updated.replace(anchor, f"{anchor}\n\t\t{tag}", 1)
    # The template ships a wrong twitter:site handle; drop it.
    updated = updated.replace('<meta name="twitter:site" content="@evidence_dev">\n\t\t', "")
    updated = updated.replace('<meta name="twitter:site" content="@evidence_dev">', "")
    if updated != html:
        page.write_text(updated, encoding="utf-8")
        return True
    return False


def main() -> None:
    if not BUILD.is_dir():
        raise SystemExit(f"no build dir at {BUILD} — run make evidence-build first")
    if not (STATIC / DEFAULT_CARD).exists():
        raise SystemExit(f"missing default social card at {STATIC / DEFAULT_CARD}")
    fixed = 0
    for rel, desc in DESCRIPTIONS.items():
        page = BUILD / rel
        if not page.exists():
            print(f"SKIP {rel}: not in build")
            continue
        if fix_page(page, desc):
            fixed += 1
    print(f"build meta: {fixed} pages updated (lang=es + description + social)")


if __name__ == "__main__":
    main()
