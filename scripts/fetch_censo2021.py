"""Fetch 2021 census dwelling totals by provincia (third stock anchor).

Source: INE jaxi viewer tpx=59521 (provincial tipo x construcción).
No static CSV exists, so this drives the public viewer with the global
playwright-cli (same requirement as scripts/smoke_browser.sh): select all
provinces, consult, export tab-separated CSV. Fully re-runnable;
fails loudly without playwright-cli.
Writes data/raw/censo2021_viviendas.csv + .parquet
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from spanish_housing import csvx, manifest  # noqa: E402
from spanish_housing.data_paths import RAW  # noqa: E402

URL = "https://www.ine.es/jaxi/Tabla.htm?tpx=59521&L=0"
RAW_CSV = RAW / "censo2021_viviendas.csv"
RAW_PARQUET = RAW / "parquet" / "censo2021_viviendas.parquet"
SESSION = "censo2021-fetch"

JS = """async (page) => {
  await page.goto('%URL%', { waitUntil: 'domcontentloaded' });
  // Expand the Provincias group, then its Seleccionar todos (2nd on page:
  // tipo, geography, construction band).
  await page.getByText('Provincias(0)', { exact: false }).first().click({ timeout: 30000 });
  const alls = page.getByRole('button', { name: 'Seleccionar todos' });
  await alls.nth(1).click({ timeout: 30000 });
  await page.getByRole('button', { name: 'Consultar selección' }).click({ timeout: 30000 });
  await page.waitForTimeout(8000);
  const dl = page.getByRole('button', { name: 'Formatos de descarga disponibles' });
  await dl.click({ timeout: 30000 });
  await page.waitForTimeout(3000);
  const csv = page.frameLocator('iframe')
    .getByRole('button', { name: /CSV: separado por tabuladores/ });
  const dlEvt = page.waitForEvent('download', { timeout: 60000 });
  await csv.click({ timeout: 30000 });
  const download = await dlEvt;
  await download.saveAs('%OUT%');
  return 'saved';
}"""


def num(v: str) -> int | None:
    v = (v or "").strip()
    if v in ("", "..", "."):
        return None
    return int(v.replace(".", "").replace(",", ""))


def main() -> None:
    if shutil.which("playwright-cli") is None:
        raise SystemExit("playwright-cli not installed — required for the 2021 viewer export")
    RAW_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["playwright-cli", f"-s={SESSION}", "open", "about:blank"],
        check=True,
        capture_output=True,
    )
    # The public viewer is slow/flaky: retry the whole flow a few times.
    raw_bytes = None
    last_err = ""
    for _attempt in range(3):
        with tempfile.TemporaryDirectory() as tmp:
            out = str(Path(tmp) / "censo2021.csv")
            js = JS.replace("%URL%", URL).replace("%OUT%", out)
            r = subprocess.run(
                ["playwright-cli", f"-s={SESSION}", "run-code", js],
                capture_output=True,
                text=True,
                timeout=300,
            )
            if r.returncode == 0 and "saved" in (r.stdout + r.stderr):
                raw_bytes = Path(out).read_bytes()
                break
            last_err = f"{r.stdout[-2000:]}\n{r.stderr[-2000:]}"
    subprocess.run(["playwright-cli", f"-s={SESSION}", "close"], capture_output=True)
    if raw_bytes is None:
        raise SystemExit(f"viewer export failed after 3 attempts:\n{last_err}")
    # Viewer exports cp1252; normalize to UTF-8 at pin time.
    text = raw_bytes.decode("cp1252")
    if "Almer" not in text or "Total" not in text.splitlines()[0]:
        raise SystemExit("export looks wrong — viewer format changed?")
    RAW_CSV.write_text(text, encoding="utf-8")
    _, rows = csvx.read_csv_records(RAW_CSV, delimiter="\t")
    out_rows = []
    for r in rows:
        prov = r["Provincias"].strip()
        if not prov:
            continue
        cpro, _, name = prov.partition(" ")
        out_rows.append(
            {
                "cpro": cpro,
                "provincia": name,
                "tipo": r["Tipo de vivienda (principal o no)"],
                "banda": r["Año de construcción del edificio"],
                "viviendas": num(r["Total"]),
            }
        )
    out_rows = [r for r in out_rows if r["viviendas"] is not None]
    if not out_rows:
        raise SystemExit("censo2021: zero rows — format changed?")
    n = csvx.write_parquet(out_rows, RAW_PARQUET)
    manifest.record(
        "data/raw/censo2021_viviendas.csv",
        {
            "url": URL,
            "publisher": "INE",
            "operation": "Censo 2021 tpx=59521",
            "accessed": date.today().isoformat(),
            "note": "browser-exported CSV via playwright-cli; normalized cp1252->UTF-8",
        },
    )
    manifest.record(
        "data/raw/parquet/censo2021_viviendas.parquet",
        {
            "url": URL,
            "publisher": "INE",
            "operation": "Censo 2021 tpx=59521",
            "accessed": date.today().isoformat(),
            "note": "all tipo x banda cells; anchor uses Total x Total",
        },
    )
    print(f"censo2021: {n} cells")


if __name__ == "__main__":
    main()
