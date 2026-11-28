"""Pin INE table 60130 for family-dwelling population across Spain."""

import json
import sys
from datetime import date
from pathlib import Path
from urllib.request import urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from spanish_housing import ecp, manifest  # noqa: E402
from spanish_housing.data_paths import RAW, ROOT  # noqa: E402


def main():
    with urlopen(ecp.FAMILY_URL, timeout=30) as response:
        raw = response.read()
    areas = ecp.parse_family_population(json.loads(raw))
    path = RAW / ecp.FAMILY_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_bytes(raw)
    tmp.replace(path)
    manifest.record(
        str(path.relative_to(ROOT)),
        {
            "api": ecp.FAMILY_URL,
            "url": ecp.FAMILY_TABLE,
            "publisher": "INE · Estadística Continua de Población (ECP)",
            "accessed": date.today().isoformat(),
            "note": (
                "Full publisher response. Analysis uses all-person totals for Spain, "
                "the 50 provinces and 2 autonomous cities."
            ),
        },
    )
    rows = areas["Total Nacional"]
    print(
        f"ECP family population: {len(areas)} series, {len(rows)} quarters, "
        f"{min(rows)} to {max(rows)}"
    )


if __name__ == "__main__":
    main()
