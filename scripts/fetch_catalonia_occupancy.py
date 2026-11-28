"""Pin the Catalan occupied-housing workbooks and the registration denominators.

Five notes analyse these files with their own executable snippets:

- docs/occupancy_barcelona_mediation.md — social-rental mediation (dwellings
  rented during the year, contracts active at year-end), by municipality and
  aggregated to Catalonia, plus the Idescat deposit-registration counts used
  only as a scale denominator;
- docs/occupancy_catalonia_deposit_balances.md — INCASÒL deposit entries,
  cancellations and the net balance, habitual and seasonal;
- docs/occupancy_city_programs.md — the programme statements quoted there;
- docs/occupancy_availability.md — the occupied-dwelling context.

The script therefore pins bytes rather than building a processed table: the
numbers in the notes come from the workbooks' own sheets, and a rebuilt Parquet
would add a second, silent definition of them. What it buys is the ability to
re-download the exact vintages a note was written against and to detect when
the publisher has replaced them.

What these files do **not** measure: the mediation municipal workbooks exclude
cessions managed by the Catalan Housing Agency in these years, so the counts are
not all assisted rentals; the *saldos* files count Registry filings (altes,
baixes) and their difference is a net flow, not a stock of active leases or of
available homes; the Idescat `.ssv` exports are deposit counts, used here only
to express mediated activity per thousand filings, never as market share,
because no source links an individual mediation contract to a deposit.

Writes nothing but data/input_manifest.json pins. Use --check to verify the
pinned bytes without touching the network.
"""

from __future__ import annotations

import argparse
import sys
import urllib.request
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from spanish_housing import manifest  # noqa: E402
from spanish_housing.data_paths import RAW, ROOT  # noqa: E402

PROGRAMMES = (
    "https://habitatge.gencat.cat/web/.content/home/dades/estadistiques/"
    "02_Estadistiques_de_la_politica_d_habitatge/04_Habitatge_de_lloguer_amb_mediacio_social"
)
MARKET = (
    "https://habitatge.gencat.cat/web/.content/home/dades/estadistiques/"
    "01_Estadistiques_de_construccio_i_mercat_immobiliari/03_Mercat_de_lloguer"
)
GENCAT = "Generalitat de Catalunya, Secretaria d'Habitatge"

RAW_FILES = {
    "mediacio_municipis": (
        RAW / "cat_incasol_mediacio_municipis.xlsx",
        f"{PROGRAMMES}/docs/mediacio_mun.xlsx",
        GENCAT,
        "Dwellings rented during the year through the social-rental mediation "
        "network, by municipality",
    ),
    "mediacio_vigents_municipis": (
        RAW / "cat_incasol_mediacio_vigents_municipis.xlsx",
        f"{PROGRAMMES}/docs/MediacioVigents_mun.xlsx",
        GENCAT,
        "Dwellings with an active mediated rental contract at year-end, by municipality",
    ),
    "mediacio_catalunya": (
        RAW / "cat_incasol_mediacio_catalunya.xlsx",
        f"{PROGRAMMES}/docs/Mediacio_CAT.xlsx",
        GENCAT,
        "Published mediation aggregates for Catalonia and the four "
        "demarcations (rented during the year)",
    ),
    "mediacio_vigents_catalunya": (
        RAW / "cat_incasol_mediacio_vigents_catalunya.xlsx",
        f"{PROGRAMMES}/docs/MediacioVigents_CAT.xlsx",
        GENCAT,
        "Published mediation aggregates for Catalonia and the four "
        "demarcations (active at year-end)",
    ),
    "saldos_municipis": (
        RAW / "cat_incasol_saldos_municipis.xlsx",
        f"{MARKET}/07_Saldos/Saldos-contractes_lloguer.xlsx",
        GENCAT,
        "Habitual rental deposit entries, cancellations and balance "
        "(2019–latest) by municipality and area",
    ),
    "saldos_habitual_temporada": (
        RAW / "cat_incasol_saldos_habitual_temporada.xlsx",
        f"{MARKET}/07_Saldos/Saldo_contractes_Htge_i_Temp.xlsx",
        GENCAT,
        "Habitual and seasonal rental deposit entries, cancellations and "
        "balance (2023–latest), Catalonia only",
    ),
    "temporada_catalunya": (
        RAW / "cat_incasol_temporada_catalunya.xlsx",
        f"{MARKET}/08_Lloguer-de-temporada/lloguer_temporada.xlsx",
        GENCAT,
        "Seasonal rental contracts by territorial aggregate, used to "
        "reconcile municipal seasonal sums",
    ),
    "idescat_registre_2017": (
        RAW / "idescat_lloguers_registre_2017.ssv",
        "https://www.idescat.cat/indicadors/?id=aec&n=15708&t=201700&f=ssv",
        "Idescat, from the INCASÒL rental-deposit register",
        "Habitual rental deposit counts by municipality and Catalonia, 2017 "
        "(semicolon-separated export)",
    ),
    "idescat_registre_2024": (
        RAW / "idescat_lloguers_registre_2024.ssv",
        "https://www.idescat.cat/indicadors/?id=aec&n=15708&t=202400&f=ssv",
        "Idescat, from the INCASÒL rental-deposit register",
        "Habitual rental deposit counts by municipality and Catalonia, 2024 "
        "(semicolon-separated export)",
    ),
    "idescat_registre_2025": (
        RAW / "idescat_lloguers_registre_2025.ssv",
        "https://www.idescat.cat/indicadors/?id=aec&n=15708&t=202500&f=ssv",
        "Idescat, from the INCASÒL rental-deposit register",
        "Habitual rental deposit counts by municipality and Catalonia, 2025 "
        "(semicolon-separated export)",
    ),
}


def download_all() -> None:
    for key, (path, url, publisher, note) in RAW_FILES.items():
        req = urllib.request.Request(url, headers={"User-Agent": "housing-data-analysis/1.0"})
        with urllib.request.urlopen(req, timeout=120) as resp:  # noqa: S310 (pinned official hosts)
            payload = resp.read()
        if path.suffix == ".xlsx" and not payload.startswith(b"PK"):
            raise SystemExit(f"{key}: expected XLSX/ZIP payload, got {payload[:40]!r}")
        if path.suffix == ".ssv" and b"Barcelona" not in payload:
            raise SystemExit(f"{key}: expected the Idescat semicolon export, got {payload[:60]!r}")
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_bytes(payload)
        tmp.replace(path)
        manifest.record(
            str(path.relative_to(ROOT)),
            {
                "url": url,
                "publisher": publisher,
                "accessed": date.today().isoformat(),
                "note": note,
            },
        )
        print(f"fetched {path.name} ({len(payload):,} bytes)")


def check() -> int:
    man = manifest.load()
    pinned = man.get("sha256", {})
    failures = 0
    for key, (path, url, _publisher, _note) in RAW_FILES.items():
        rel = str(path.relative_to(ROOT))
        if rel not in pinned:
            print(f"[FAIL] {key}: {rel} has no manifest pin")
            failures += 1
            continue
        if not path.exists():
            print(f"[FAIL] {key}: {rel} is pinned but missing on disk (run make fetch)")
            failures += 1
            continue
        actual = manifest.sha256(path)
        if actual != pinned[rel]:
            print(f"[FAIL] {key}: {rel} bytes changed since pinning ({url})")
            failures += 1
            continue
        print(f"[OK] {key}: pinned as {rel}")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify pins without the network")
    args = parser.parse_args()
    if args.check:
        return check()
    download_all()
    return check()


if __name__ == "__main__":
    sys.exit(main())
