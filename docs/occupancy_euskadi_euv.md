# What the Euskadi housing-use survey can tell us about availability

The Basque Government's [2023 Encuesta sobre el Uso de la Vivienda (EUV)](https://www.euskadi.eus/estadistica/tablas-estadisticas-de-la-encuesta-sobre-el-uso-de-la-vivienda-2023/web01-s2ekono/es/)
asks about use and whether dwellings are on offer. It is a regional sample
survey, not a listings feed, a national estimate or a proxy to apply to the
[four-province pilot](occupancy_province_pilot.md). Fieldwork spanned autumn
2023 to early 2024. The numbers below come from the official downloadable
workbooks for estimates and sampling errors (both table T1).

| Reported category, Euskadi | Estimated dwellings |
| --- | ---: |
| Non-primary | 78,359 |
| Of which: seasonal use | 35,306 |
| Of which: uninhabited | 43,053 |
| ↳ Offered for sale and/or rent | 11,682 |
| ↳ Classified *gestionables*: not on offer and not a second residence | 31,371 |
| ↳ Of the above, after excluding specified relocations and social emergency use | 25,450 |

**About 27% of uninhabited homes were already on offer.** The published 95%
sampling interval for the offered count is about **10,597 to 12,767**. That
interval concerns the count, not the share. *Gestionable* is an exclusion
rule in the survey, not a test of habitability, a legal declaration of
vacancy, or evidence the owner would rent it. The narrower category also
excludes specified work, education, health or dependency-related relocations
and social emergency use.

## What is downloadable, and what is not comparable

- T1 distinguishes on-market and off-market uninhabited dwellings for Euskadi
  and its three historical territories; the separate sampling-errors
  workbook also publishes those cuts. This is evidence about reported offer
  status at survey time, not about prices, current listings or rent duration.
- Separate sale and rental flags in T7 refer to all non-primary dwellings;
  do not add the flags or compare that sum with the union restricted to
  uninhabited dwellings in T1. The official [results report](https://observatoriovivienda.euskadi.eus/contenidos/documentacion/ovv_sectorvivienda_evv2023_inf/es_def/EUV23_Informe-de-Resultados_ES.pdf)
  prints some totals one dwelling apart from the workbook. This note uses
  the workbook consistently rather than mixing tables or formats.
- The workbook has a historical split of seasonal versus uninhabited use
  (T6), not a historical offer-status series. The municipal tables cover the
  three Basque capitals but do not have a direct, separate offer-status
  column. None of these estimates resolves availability in Madrid,
  Barcelona, Valencia or Alicante.

## From a survey category to an actual program

The [Bizigune case note](occupancy_euskadi_bizigune.md) tracks dwellings under
protected-rental management, new owner agreements and signed tenant leases
separately. Those counts cannot be divided by this survey’s off-market
estimate to measure take-up: they cover different homes and dates.

## Reproduce

Download the two XLSX files from the official tables page above. The checked
copies had SHA-256 `6f77d7eda62178e8c0021f222c302e654e8aa23879e71e509347d128863a214b`
(estimates) and `f6d33ccc03faa24cee7cd3449053c711869a8fec4040ec1cc81e305ee7bcfc91`
(sampling errors). Save them locally as `tables.xlsx` and `errors.xlsx`:

```sh
uv run python - <<'PY'
from openpyxl import load_workbook

est = load_workbook('tables.xlsx', read_only=True, data_only=True)['T1']
err = load_workbook('errors.xlsx', read_only=True, data_only=True)['T1']
base = dict(est.iter_rows(min_row=6, max_row=11, max_col=2, values_only=True))
assert base['No principales'] == base['Temporada'] + base['Deshabitada']
assert base['Deshabitada'] == base['- En oferta (1)'] + base['- Gestionables (2)']
assert err['B9'].value == '- En oferta (1)' and err['C9'].value == base['- En oferta (1)']
print(base, round(100 * base['- En oferta (1)'] / base['Deshabitada'], 1))
print('Published interval:', err['F9'].value, err['G9'].value)
PY
```

This is a source check: the workbooks were not added to the national mart or
used to fill missing indicators elsewhere.
