"""Tests for the /alquiler/ page, its SQL queries, and the rental_registers sidecar."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import export_rental_registers as exporter  # noqa: E402

PAGE = ROOT / "evidence/pages/alquiler.md"
SERPAVI_SOURCE = ROOT / "evidence/sources/housing/serpavi_contratos.sql"
EVIDENCE_PANEL = ROOT / "evidence/components/EvidencePanel.svelte"


def _sql_blocks(text: str) -> dict[str, str]:
    return {name: sql.strip() for name, sql in re.findall(r"```sql (\w+)\n(.*?)```", text, re.S)}


def test_export_rental_registers_builds_expected_tables():
    occupancy = {
        "balances": {
            "history": {
                "barcelona_habitual": {
                    "2020": {"entries": 40416, "cancellations": 45236, "balance": -4820},
                    "2024": {"entries": 32903, "cancellations": 30179, "balance": 2724},
                    "2025": {"entries": 30789, "cancellations": 30255, "balance": 534},
                }
            }
        }
    }
    contrast = {
        "reconciliation": {
            "2020": {"deposit_balance": -4820, "declared_stock_change": 2414},
            "2024": {"deposit_balance": 2724, "declared_stock_change": 2630},
        }
    }
    vut = {"tourist_stock": {"2020-08": 63199, "2026-05": 51305}}

    bcn, vut_tbl = exporter.build_tables(occupancy, contrast, vut)
    rows = bcn.to_pylist()
    assert [r["anyo"] for r in rows] == [2020, 2024, 2025]
    assert rows[0]["saldo_fianzas"] == -4820
    assert rows[0]["cambio_stock_declarado"] == 2414
    # 2025 is not yet published in SERPAVI — must remain NULL, never imputed
    assert rows[2]["saldo_fianzas"] == 534
    assert rows[2]["cambio_stock_declarado"] is None
    assert vut_tbl.to_pylist() == [
        {"periodo": "2020-08", "viviendas_turisticas": 63199},
        {"periodo": "2026-05", "viviendas_turisticas": 51305},
    ]


def test_export_rental_registers_rejects_balance_mismatch():
    occupancy = {
        "balances": {
            "history": {
                "barcelona_habitual": {
                    "2024": {"entries": 32903, "cancellations": 30179, "balance": 2724},
                }
            }
        }
    }
    contrast = {
        "reconciliation": {"2024": {"deposit_balance": 9999, "declared_stock_change": 2630}}
    }
    vut = {"tourist_stock": {"2026-05": 51305}}
    with pytest.raises(ValueError, match="balance mismatch"):
        exporter.build_tables(occupancy, contrast, vut)


def test_alquiler_page_queries_execute_against_mock_sources():
    blocks = _sql_blocks(PAGE.read_text(encoding="utf-8"))
    assert {
        "contratos_grandes",
        "crecimiento_grandes",
        "bcn_saldo_vs_stock",
        "cat_vut_banda",
    } <= set(blocks)

    con = duckdb.connect(":memory:")
    con.execute("create schema housing")
    con.execute("create schema rental_registers")
    con.execute(
        "create table serpavi_municipal("
        "codigo varchar, provincia varchar, municipio varchar, "
        "anyo integer, medida varchar, valor double)"
    )
    for year in range(2015, 2025):
        con.executemany(
            "insert into serpavi_municipal values (?, ?, ?, ?, ?, ?)",
            [
                (
                    "28079",
                    "Madrid",
                    "Madrid",
                    year,
                    "BI_ALVHEPCO_TVC",
                    190000 + (year - 2015) * 10000,
                ),
                ("28079", "Madrid", "Madrid", year, "BI_ALVHEPCO_TVU", 5000),
                (
                    "08019",
                    "Barcelona",
                    "Barcelona",
                    year,
                    "BI_ALVHEPCO_TVC",
                    105000 + (year - 2015) * 4000,
                ),
                (
                    "46250",
                    "Valencia",
                    "Valencia",
                    year,
                    "BI_ALVHEPCO_TVC",
                    40000 + (year - 2015) * 3000,
                ),
            ],
        )
    con.execute(f"create table housing.serpavi_contratos as {SERPAVI_SOURCE.read_text()}")
    con.execute(
        "create table rental_registers.bcn_depositos_vs_stock("
        "anyo bigint, altas_fianza bigint, bajas_fianza bigint, "
        "saldo_fianzas bigint, cambio_stock_declarado bigint)"
    )
    con.executemany(
        "insert into rental_registers.bcn_depositos_vs_stock values (?, ?, ?, ?, ?)",
        [
            (2020, 40416, 45236, -4820, 2414),
            (2024, 32903, 30179, 2724, 2630),
            (2025, 30789, 30255, 534, None),
        ],
    )
    con.execute(
        "create table rental_registers.cat_vut_banda(periodo varchar, viviendas_turisticas bigint)"
    )
    con.executemany(
        "insert into rental_registers.cat_vut_banda values (?, ?)",
        [("2020-08", 63199), ("2026-05", 51305)],
    )

    grandes = con.execute(blocks["contratos_grandes"]).fetchall()
    assert len(grandes) == 30
    crec = con.execute(blocks["crecimiento_grandes"]).fetchall()
    assert [r[0] for r in crec] == ["Madrid", "Barcelona", "Valencia"]

    saldo_rows = con.execute(blocks["bcn_saldo_vs_stock"]).fetchall()
    # 3 INCASOL rows + 2 SERPAVI rows (2025 is NULL and omitted)
    assert len(saldo_rows) == 5
    assert [r for r in saldo_rows if r[0] == "2025"] == [
        ("2025", "Saldo neto de fianzas (INCASÒL)", 534)
    ]

    vut_rows = con.execute(blocks["cat_vut_banda"]).fetchall()
    assert vut_rows == [("2020-08", 63199), ("2026-05", 51305)]


def test_alquiler_is_wired_in_evidence_panel_and_claim_ledger():
    panel = EVIDENCE_PANEL.read_text(encoding="utf-8")
    assert "alquiler: 'docs/occupancy_catalonia_deposit_balances.md'" in panel

    ledger_path = ROOT / "artifacts/claim_ledger.json"
    if ledger_path.is_file():
        claims = json.loads(ledger_path.read_text())["claims"]
        by_id = {c["claim_id"]: c for c in claims}
        assert by_id["C8_rentals_disappearing"]["deep_dive_path"] == "/alquiler/"
