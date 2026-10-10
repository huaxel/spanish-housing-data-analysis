"""Build the SERPAVI-rent / ADRH-income municipal proxy table.

Descriptive, explicitly-gated proxy (semantics accepted 2026-10-09, see
docs/housing_access.md): median monthly contract rent of new/rolling
tax-deposit signings (SERPAVI ALQTBID12_M_VC, colectiva) divided by mean
NET annual household income over ALL households (ADRH neta_hogar / 12),
per municipio and year over the 2015-2023 overlap.

This is a signing-market proxy, never an overburden rate: the numerator
is not the sitting-tenant stock and the denominator is not renter income.
Suppressed cells stay null; rows exist only where SERPAVI publishes the
municipio-year (about 1.9k-2.4k of ~8.1k municipios per year). From 2020
ADRH can substitute comarca/province averages for municipios under 100
residents (not flagged per row).

Reads marts.duckdb (serpavi_municipal) and the pinned ADRH parquet;
writes table `rent_income` into the housing_access.duckdb sidecar
(queried by the site as access.rent_income). --check recomputes and
verifies the stored table without writing.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import duckdb
import pyarrow as pa

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from spanish_housing import manifest  # noqa: E402
from spanish_housing.data_paths import PROCESSED, RAW, ROOT  # noqa: E402

MARTS = PROCESSED / "marts.duckdb"
ADRH_PARQUET = RAW / "parquet" / "adrh_renta_municipal.parquet"
DATABASE = PROCESSED / "housing_access.duckdb"
TABLE = "rent_income"
YEARS = tuple(range(2015, 2024))
SCHEMA = pa.schema(
    [
        ("codigo", pa.string()),
        ("municipio", pa.string()),
        ("cpro", pa.string()),
        ("anyo", pa.int64()),
        ("alquiler_med", pa.float64()),
        ("contratos", pa.int64()),
        ("renta_neta_hogar", pa.int64()),
        ("ratio_pct", pa.float64()),
    ]
)

QUERY = f"""
with rent as (
    select codigo, municipio, cpro, anyo, valor as alquiler_med
    from serpavi_municipal
    where medida = 'ALQTBID12_M_VC' and anyo between 2015 and 2023
), con as (
    select codigo, anyo, cast(valor as bigint) as contratos
    from serpavi_municipal
    where medida = 'BI_ALVHEPCO_TVC' and anyo between 2015 and 2023
      and valor = cast(valor as bigint)
), adr as (
    select codigo, anyo, renta_eur as renta_neta_hogar
    from read_parquet('{ADRH_PARQUET}')
    where indicador = 'neta_hogar' and anyo between 2015 and 2023
)
select r.codigo, r.municipio, r.cpro, r.anyo,
       r.alquiler_med, c.contratos, a.renta_neta_hogar,
       case when r.alquiler_med is not null and a.renta_neta_hogar > 0
            then round(100.0 * 12 * r.alquiler_med / a.renta_neta_hogar, 2) end as ratio_pct
from rent r
left join con c on c.codigo = r.codigo and c.anyo = r.anyo
join adr a on a.codigo = r.codigo and a.anyo = r.anyo
where r.alquiler_med is not null or a.renta_neta_hogar is not null
order by r.anyo, r.codigo
"""


def compute_rows() -> pa.Table:
    con = duckdb.connect(str(MARTS), read_only=True)
    try:
        return con.execute(QUERY).to_arrow_table()
    finally:
        con.close()


def expected_years(table: pa.Table) -> None:
    years = set(table.column("anyo").to_pylist())
    if years != set(YEARS):
        raise ValueError(f"rent_income: year coverage {sorted(years)} != {YEARS}")
    codes = {c[:2] for c in table.column("codigo").to_pylist()}
    if not codes or len(codes) < 50:
        raise ValueError(f"rent_income: province coverage implausible ({len(codes)})")
    ratios = table.column("ratio_pct").to_pylist()
    observed = [x for x in ratios if x is not None]
    if not observed:
        raise ValueError("rent_income: no observed ratios")
    if min(observed) <= 0 or max(observed) > 100:
        raise ValueError(f"rent_income: ratio out of bounds [{min(observed)}, {max(observed)}]")


def write_table(table: pa.Table) -> None:
    con = duckdb.connect(str(DATABASE))
    try:
        con.register("new_rows", table)
        con.execute(f"create or replace table {TABLE} as select * from new_rows")
    finally:
        con.close()


def read_table() -> pa.Table:
    con = duckdb.connect(str(DATABASE), read_only=True)
    try:
        return con.execute(f"select * from {TABLE}").to_arrow_table()
    finally:
        con.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    table = compute_rows().cast(SCHEMA)
    expected_years(table)
    n = table.num_rows
    ratios = [x for x in table.column("ratio_pct").to_pylist() if x is not None]
    if args.check:
        current = read_table().cast(SCHEMA)
        if not current.equals(table):
            raise ValueError(
                f"rent_income: stored table stale vs inputs ({current.num_rows}/{n} rows)"
            )
        print(f"rent_income: {n} rows ({len(ratios)} ratios) verified against inputs")
        return
    write_table(table)
    manifest.record(
        str(DATABASE.relative_to(ROOT)),
        {
            "publisher": "SERPAVI (MIVAU) + ADRH (INE) proxy",
            "accessed": date.today().isoformat(),
            "note": (
                "Derived from marts.duckdb serpavi_municipal and pinned "
                "adrh_renta_municipal.parquet by build_rent_income.py "
                "(table rent_income); other tables in this sidecar unchanged"
            ),
        },
    )
    print(
        f"rent_income: {n} municipio-year rows, {len(ratios)} with ratio "
        f"(median {sorted(ratios)[len(ratios) // 2]:.1f}%); table {TABLE} in {DATABASE.name}"
    )


if __name__ == "__main__":
    main()
