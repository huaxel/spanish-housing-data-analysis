"""Source-bound contract for the four-province occupancy pilot."""

from pathlib import Path

import duckdb
import pytest

from spanish_housing.data_paths import PROCESSED, RAW, ROOT


def test_pilot_csv_results_match_mart_and_keep_unmatched_tax_year_null(monkeypatch):
    mart = PROCESSED / "marts.duckdb"
    inputs = [RAW / "parque_viviendas.csv", RAW / "parquet/aeat_viviendas_uso.parquet", mart]
    if not all(p.is_file() for p in inputs):
        pytest.skip("requires pinned stock and tax inputs and the verified mart")
    monkeypatch.chdir(ROOT)
    query = Path("explorations/occupancy_province_pilot.sql").read_text()
    with duckdb.connect(str(mart), read_only=True) as con:
        rows = con.execute(query).fetchall()
        expected = con.execute("""
            with stock as (
                select cpro, anyo, viviendas_total-lag(viviendas_total) over w total,
                       viviendas_principales-lag(viviendas_principales) over w principal,
                       viviendas_no_principales-lag(viviendas_no_principales) over w nonprincipal
                from mart_provincia_anual where cpro in ('03','08','28','46')
                window w as (partition by cpro order by anyo)
            ), tax as (
                select cpro, anyo, n_disposicion-lag(n_disposicion) over (
                    partition by cpro order by anyo
                ) disposal
                from aeat_viviendas_uso where cpro in ('03','08','28','46')
            )
            select stock.cpro, stock.anyo, total, principal, nonprincipal, disposal
            from stock left join tax on tax.cpro=stock.cpro and tax.anyo=stock.anyo
                and tax.anyo=2024
            where stock.anyo in (2024,2025) order by stock.anyo, stock.cpro
        """).fetchall()
    assert len(rows) == 8
    assert [
        (code, year, total, main, other, tax) for code, _, year, total, main, other, tax in rows
    ] == expected
    assert all(total == main + other for _, _, _, total, main, other, _ in rows)
    assert all((tax is None) == (year == 2025) for _, _, year, _, _, _, tax in rows)
