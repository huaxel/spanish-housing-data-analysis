"""Series identity and civil reference dates for ECP quarterly observations."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from .ine_api import BASE, split_nombre

MADRID = ZoneInfo("Europe/Madrid")
MONTHS = {19: 1, 20: 4, 21: 7, 22: 10}
FAMILY_CODE = "ECP329968"
FAMILY_FILE = "ecp_family_population.json"
FAMILY_URL = f"{BASE}/DATOS_TABLA/60130"
FAMILY_TABLE = "https://www.ine.es/jaxiT3/Tabla.htm?t=60130"


def reference_date(item: dict) -> date:
    month = MONTHS.get(item["FK_Periodo"])
    ref = datetime.fromtimestamp(item["Fecha"] / 1000, MADRID).date()
    if month is None or ref != date(item["Anyo"], month, 1):
        raise ValueError(f"Inconsistent ECP quarter: {item}")
    return ref


def parse_family_population(table: list[dict]) -> dict[str, dict[date, int]]:
    """Keep all-person totals; other rows are sex, age and birthplace breakdowns."""
    if not isinstance(table, list):
        raise ValueError("Expected INE family-dwelling population table 60130")
    expected = ["Total", "Todas las edades", "Total", "Población en viviendas familiares", "Número"]
    result = {}
    for series in table:
        label = split_nombre(series["Nombre"])
        if label[1:] != expected:
            continue
        territory = label[0]
        if territory in result:
            raise ValueError(f"Duplicate ECP family-population territory: {territory}")
        if series.get("FK_Escala") != 1 or series.get("FK_Unidad") != 3:
            raise ValueError(f"Expected ECP family-dwelling population in persons: {territory}")
        if territory == "Total Nacional" and series.get("COD") != FAMILY_CODE:
            raise ValueError("Unexpected ECP national family-population series code")
        result[territory] = _family_series(series)
    if "Total Nacional" not in result or len(result) != 53:
        raise ValueError(
            "Expected family population for Spain, 50 provinces and 2 autonomous cities"
        )
    return result


def _family_series(series: dict) -> dict[date, int]:
    out = {}
    for item in series["Data"]:
        ref = reference_date(item)
        if ref in out:
            raise ValueError(f"Duplicate ECP family-population observation: {ref}")
        value = item["Valor"]
        if (
            item["Secreto"]
            or type(value) not in (int, float)
            or not 0 < value < float("inf")
            or int(value) != value
        ):
            raise ValueError(f"Invalid ECP family-population observation: {ref} {value}")
        out[ref] = int(value)
    if not out:
        raise ValueError("Empty ECP family-population series")
    return out
