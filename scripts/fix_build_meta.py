"""Post-process Evidence build HTML: lang=es + per-route meta descriptions.

Evidence renders `<html lang="en">` from its own app template (which build
regenerates, so editing the template does not stick). Run after every
`evidence-build` (wired in the Makefile) and before deploy.
Idempotent: skips files already fixed.
"""

from __future__ import annotations

from pathlib import Path

BUILD = Path(__file__).resolve().parents[1] / "evidence" / "build"

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
    "vacancia/index.html": (
        "Vivienda vacía por consumo eléctrico (Censo 2021): mapa municipal "
        "de la desocupación en España."
    ),
}


def main() -> None:
    if not BUILD.is_dir():
        raise SystemExit(f"no build dir at {BUILD} — run make evidence-build first")
    fixed = 0
    for rel, desc in DESCRIPTIONS.items():
        page = BUILD / rel
        if not page.exists():
            print(f"SKIP {rel}: not in build")
            continue
        html = page.read_text(encoding="utf-8")
        updated = html.replace('<html lang="en">', '<html lang="es">')
        tag = f'<meta name="description" content="{desc}" />'
        if tag not in updated:
            anchor = '<meta charset="utf-8" />'
            if anchor not in updated:
                raise SystemExit(f"{rel}: charset anchor missing, template changed?")
            updated = updated.replace(anchor, f"{anchor}\n\t\t{tag}", 1)
        if updated != html:
            page.write_text(updated, encoding="utf-8")
            fixed += 1
    print(f"build meta: {fixed} pages updated (lang=es + description)")


if __name__ == "__main__":
    main()
