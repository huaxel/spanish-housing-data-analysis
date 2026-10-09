"""Offline AEAT dwelling-use table tests. No network, no data/ dependency."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from fetch_aeat_viviendas import (  # noqa: E402
    AEAT_CCAA_CPROS,
    AEAT_PROV_CPRO,
    AEAT_SINGLES,
    EXPECTED_CCAA,
    parse_aeat_table,
)


def dot(n):
    return f"{n:,}".replace(",", ".")


def share(part, total):
    return f"{100.0 * part / total:.2f}".replace(".", ",")


def prov_cells(n=1200, hab=720, alq=300, dis=150):
    return [
        dot(n),
        "50.000",
        dot(hab),
        share(hab, n),
        "55.000",
        dot(alq),
        share(alq, n),
        "48.000",
        dot(dis),
        share(dis, n),
        "40.000",
    ]


def render(rows, year=2024):
    body = "".join(
        f'<tr class="depth_{d}"><th>{label}</th>'
        + "".join(f"<td>{c}</td>" for c in cells)
        + "</tr>"
        for d, label, cells in rows
    )
    title = f"Estadística de viviendas declaradas en IRPF: {year}: uso"
    return (
        f"<html><head><title>{title}</title></head>"
        f"<body><p>Ejercicio {year}</p>"
        '<table id="table01"><thead><tr>'
        "<th>Localización de la vivienda</th><th>Viviendas con valor catastral</th>"
        "<th>Vivienda habitual</th><th>Arrendadas</th><th>A disposición</th>"
        "</tr></thead>" + body + "</table></body></html>"
    )


def fixture_rows():
    """Full 56-row table with production labels, exact shares and sums."""
    cpro_of = dict(AEAT_PROV_CPRO)
    singles = dict(AEAT_SINGLES)
    rows = []
    totals = [0, 0, 0, 0]
    ccaa_sums = {}
    for label, cpro in cpro_of.items():
        cells = prov_cells()
        rows.append((2, label, cells))
        vals = [1200, 720, 300, 150]
        for i, v in enumerate(vals):
            totals[i] += v
        ccaa = next(c for c, cpros in AEAT_CCAA_CPROS.items() if cpro in cpros)
        sums = ccaa_sums.setdefault(ccaa, [0, 0, 0, 0])
        for i, v in enumerate(vals):
            sums[i] += v
    for ccaa in sorted(ccaa_sums):
        n, hab, alq, dis = ccaa_sums[ccaa]
        rows.append((1, ccaa, prov_cells(n, hab, alq, dis)))
    for label in singles:
        rows.append((1, label, prov_cells(300, 180, 75, 45)))
        for i, v in enumerate((300, 180, 75, 45)):
            totals[i] += v
    rows.insert(0, (0, "Total", prov_cells(*totals)))
    return rows


def test_parses_all_grains():
    rows = parse_aeat_table(render(fixture_rows()), 2024)
    by_key = {(r["cpro"], r["grano"]): r for r in rows}
    assert len(rows) == 56
    assert by_key[("04", "provincia")]["territorio"] == "Almería"
    assert by_key[("04", "provincia")]["n_total"] == 1200
    assert by_key[("04", "provincia")]["pct_habitual"] == pytest.approx(60.0)
    assert by_key[("28", "ccaa_uniprovincial")]["n_disposicion"] == 45
    assert by_key[(None, "total_nacional")]["n_arrendadas"] == 300 * 40 + 75 * 6
    assert by_key[(None, "ccaa")]["territorio"] == "Galicia"


def mutate(rows, label, cell, new):
    out = []
    for depth, lab, cells in rows:
        if lab == label:
            cells = list(cells)
            cells[cell] = new
        out.append((depth, lab, cells))
    return out


def test_year_and_header_drift_fail():
    with pytest.raises(SystemExit, match="title year drift"):
        parse_aeat_table(render(fixture_rows(), year=2023), 2024)
    no_header = render(fixture_rows()).replace("A disposición", "Otros usos")
    with pytest.raises(SystemExit, match="header order drift"):
        parse_aeat_table(no_header, 2024)
    swapped = render(fixture_rows()).replace(
        "Vivienda habitual</th><th>Arrendadas", "Arrendadas</th><th>Vivienda habitual"
    )
    with pytest.raises(SystemExit, match="header order drift"):
        parse_aeat_table(swapped, 2024)


def test_row_count_and_unknown_labels_fail():
    with pytest.raises(SystemExit, match="want 56"):
        parse_aeat_table(render(fixture_rows()[:50]), 2024)
    bad = mutate(fixture_rows(), "Almería", 0, "1.200")
    bad = [(d, "Almeria Nueva" if lab == "Almería" else lab, c) for d, lab, c in bad]
    with pytest.raises(SystemExit, match="unmapped provinces"):
        parse_aeat_table(render(bad), 2024)


def test_share_and_aggregation_mismatch_fail():
    bad = mutate(fixture_rows(), "Almería", 3, "61,00")
    with pytest.raises(SystemExit, match="share/count mismatch"):
        parse_aeat_table(render(bad), 2024)
    bad = mutate(fixture_rows(), "Andalucía", 2, dot(8 * 720 + 1))
    bad = mutate(bad, "Andalucía", 3, "60,01")
    with pytest.raises(SystemExit, match="disagrees with its provinces"):
        parse_aeat_table(render(bad), 2024)


def test_known_publisher_gap_drops_only_the_total_row(monkeypatch):
    import fetch_aeat_viviendas as mod

    monkeypatch.setitem(
        mod.NACIONAL_KNOWN_GAPS,
        2024,
        {"n_total": 2, "n_habitual": 0, "n_arrendadas": 0, "n_disposicion": 0},
    )
    inflated = []
    for depth, lab, cells in fixture_rows():
        if lab == "Total":
            cells = [
                "49.802",
                cells[1],
                cells[2],
                "59,99",
                cells[4],
                cells[5],
                "25,00",
                cells[7],
                cells[8],
                "12,59",
                cells[10],
            ]
        inflated.append((depth, lab, cells))
    rows = parse_aeat_table(render(inflated), 2024)
    assert len(rows) == 55
    assert all(r["grano"] != "total_nacional" for r in rows)
    parts = [r["n_total"] for r in rows if r["grano"] in ("provincia", "ccaa_uniprovincial")]
    assert sum(parts) == 49800


def test_wrong_gap_still_fails_loudly(monkeypatch):
    import fetch_aeat_viviendas as mod

    monkeypatch.setitem(
        mod.NACIONAL_KNOWN_GAPS,
        2024,
        {"n_total": 3, "n_habitual": 0, "n_arrendadas": 0, "n_disposicion": 0},
    )
    inflated = []
    for depth, lab, cells in fixture_rows():
        if lab == "Total":
            cells = [
                "49.802",
                cells[1],
                cells[2],
                "59,99",
                cells[4],
                cells[5],
                "25,00",
                cells[7],
                cells[8],
                "12,59",
                cells[10],
            ]
        inflated.append((depth, lab, cells))
    with pytest.raises(SystemExit, match="nacional mismatch"):
        parse_aeat_table(render(inflated), 2024)


def test_foral_labels_are_rejected_not_mapped():
    bad = mutate(fixture_rows(), "Rioja, La", 0, "300")
    bad = [(d, "Navarra" if lab == "Rioja, La" else lab, c) for d, lab, c in bad]
    with pytest.raises(SystemExit, match="CCAA drift"):
        parse_aeat_table(render(bad), 2024)


def test_crosswalks_cover_production_labels():
    assert len(AEAT_PROV_CPRO) == 40
    full = {f"{i:02d}" for i in range(1, 51)} - {"01", "20", "31", "48"}
    assert set(AEAT_PROV_CPRO.values()) | set(AEAT_SINGLES.values()) == full
    grouped = sorted(c for cpros in AEAT_CCAA_CPROS.values() for c in cpros)
    assert grouped == sorted(AEAT_PROV_CPRO.values())
    assert len(EXPECTED_CCAA) == 15
    assert set(AEAT_SINGLES) <= EXPECTED_CCAA


def test_pct_tolerance_is_pinned():
    import fetch_aeat_viviendas as mod

    assert mod.PCT_TOL == 0.015
