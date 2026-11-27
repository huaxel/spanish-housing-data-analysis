"""Offline rent-income proxy table validation contracts."""

import sys
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_rent_income as br  # noqa: E402


def full_window(mutate=None):
    """Rows covering all 52 provinces x 2015-2023 (dataset-level minimum)."""
    rows = []
    for p in range(1, 53):
        for y in range(2015, 2024):
            row = {
                "codigo": f"{p:02d}001",
                "municipio": f"Muni {p:02d}001",
                "cpro": f"{p:02d}",
                "anyo": y,
                "alquiler_med": 500.0,
                "contratos": 100,
                "renta_neta_hogar": 35000,
                "ratio_pct": 17.1,
            }
            if mutate is not None:
                row = mutate(row)
            rows.append(row)
    return rows


def table(rows):
    return pa.Table.from_pylist(rows, schema=br.SCHEMA)


def test_expected_years_accepts_full_window():
    br.expected_years(table(full_window()))


def test_missing_year_rejected():
    def shift(r):
        return {**r, "anyo": 2014} if r["anyo"] == 2015 else r

    with pytest.raises(ValueError, match="year coverage"):
        br.expected_years(table(full_window(shift)))


def test_thin_province_coverage_rejected():
    rows = [r for r in full_window() if r["cpro"] in ("01", "02", "28")]
    with pytest.raises(ValueError, match="province coverage"):
        br.expected_years(table(rows))


def test_no_observed_ratios_rejected():
    with pytest.raises(ValueError, match="no observed ratios"):
        br.expected_years(table(full_window(lambda r: {**r, "ratio_pct": None})))


def test_out_of_bounds_ratio_rejected():
    def over(r):
        return {**r, "ratio_pct": 120.0} if r["anyo"] == 2023 else r

    def zero(r):
        return {**r, "ratio_pct": 0.0} if r["anyo"] == 2023 else r

    with pytest.raises(ValueError, match="out of bounds"):
        br.expected_years(table(full_window(over)))
    with pytest.raises(ValueError, match="out of bounds"):
        br.expected_years(table(full_window(zero)))


def test_proxy_stays_at_2023_when_both_inputs_reach_2024(tmp_path, monkeypatch):
    income = tmp_path / "adrh.parquet"
    pq.write_table(
        pa.Table.from_pylist(
            [
                {"codigo": "28079", "indicador": "neta_hogar", "anyo": y, "renta_eur": 36000}
                for y in (2023, 2024)
            ]
        ),
        income,
    )
    marts = tmp_path / "marts.duckdb"
    with duckdb.connect(str(marts)) as con:
        con.execute(
            "create table serpavi_municipal (codigo varchar, municipio varchar, "
            "cpro varchar, anyo bigint, medida varchar, valor double)"
        )
        for year in (2023, 2024):
            for measure, value in (("ALQTBID12_M_VC", 600.0), ("BI_ALVHEPCO_TVC", 80.0)):
                con.execute(
                    "insert into serpavi_municipal values ('28079','Madrid','28',?,?,?)",
                    [year, measure, value],
                )
    monkeypatch.setattr(br, "MARTS", marts)
    monkeypatch.setattr(br, "QUERY", br.QUERY.replace(str(br.ADRH_PARQUET), str(income)))
    rows = br.compute_rows().to_pylist()
    assert [(r["anyo"], r["ratio_pct"]) for r in rows] == [(2023, 20.0)]
