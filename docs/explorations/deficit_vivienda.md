# CaixaBank-style housing-deficit arithmetic

**Date:** 2026-10-09, corrected 2026-11-26 · **Status:** implemented (`explorations/deficit_vivienda.py`,
`scripts/fetch_mivau_terminadas.py`) · **Result:** reproducible with disclosed
deltas, not an exact clone

Descriptive exploration only: per-province and national gaps between ECP
household creation and Ministerio finished dwellings, following CaixaBank
Research's published variants. No causal claim, no p-values, no model, no
forecast. The gap is an arithmetic residual, never a count of missing homes.

## What CaixaBank publishes

CaixaBank Research estimates the 2021–2024 provincial deficit in three
complementary variants: visados vs household creation (their first variant,
not reproduced here), finished dwellings vs household creation
(600,000), and finished
dwellings minus tourist use and non-resident foreign purchases. A 2026
update extends the finished-dwellings variant to 734,000 over 2021–2025,
with about one half of the national gap concentrated in Madrid, Barcelona,
Valencia, Alicante and Murcia, and only Guipúzcoa, Cáceres and Soria
escaping a positive gap. Their forward scenarios are forecasts with
CaixaBank assumptions and are not reproduced here. Sources: the
[2024 deficit article](https://www.caixabankresearch.com/es/analisis-sectorial/inmobiliario/falta-vivienda-nueva-mas-se-necesita-deficit-creciente-y)
and the [IS IMMO 2026-1S deficit note](https://www.caixabankresearch.com/sites/default/files/content/file/2026/03/19/91184/is-immo-2026-1s-es_deficit-vivienda.pdf).

## What is reproduced here (and what is not)

- **Households:** ECP January-1 stocks from the marts (2021–2025) plus the
  same pinned ECP file for 2026. Creation during years a..b is stock(b+1)
  minus stock(a). The 2021 base equals the census value because ECP was
  benchmarked to the census that year — there is no hidden splice.
- **Completions:** MIVAU monthly finished dwellings by province, summed over
  calendar years (`fetch_mivau_terminadas.py`): free-market completions from
  VDP005_01 plus protected final approvals ("calificación definitiva") from
  VDP007_01. Blank months are kept null, never filled. The visados variant is
  not reproduced: visados proper (CSCAE) are a different series from
  iniciadas and are not in the pipeline. (The bulletin says its free-market
  starts and completions series is itself built from visados of the
  architects' colleges.)
- **Variant v2** (creation minus finished): 607,250 over 2021–2024 and
  754,613 over 2021–2025, against published 600,000 and 734,000 — deltas
  of 7,250 and 20,613. 2025–2026 inputs are still provisional here; the
  remaining differences have not been decomposed and are disclosed rather
  than tuned away.
- **Variant v3p** (minus tourist conversions, partial): 552,283 over
  2021–2024 and 746,345 over 2021–2025, subtracting the December-snapshot
  tourist-stock net flow from the mart VTE series. The non-resident
  foreign-purchase adjustment is not reproducible from in-repo inputs
  (no buyer-nationality split) and is omitted — hence partial, never
  presented as their third variant.
- **Geography check:** the top-five order reproduces exactly (Madrid,
  Barcelona, Valencia, Alicante, Murcia). The top-five share does not: 0.4827
  over 2021–2024 against the published 0.49. Soria reproduces as a negative-gap exception.
  Cáceres is near-zero positive while Gipuzkoa (Guipúzcoa in their text)
  stays positive, so two of the three published exceptions do not replicate —
  recorded here rather than smoothed over.
- **Known gaps:** the final-approval block has a value in every
  province-month cell of both windows, but that does not show every region
  reported. For Canarias, July–December 2022 (blank in the earlier input), it
  publishes zero while VDP007_01 leaves blank one of the two protected
  provisional entries and two rehabilitation entries for the same 12
  province-months. These zeros may be non-reporting (an inference, not
  established). They are kept as published; blanking them would not change any
  sum, only whether the affected residuals are labelled exact or upper bounds.
  2025 completions and 2026 stocks are provisional and revisable, and the
  bulletin check covers protected approvals only through 2024. Unformed
  households are missing from every variant (as in the published estimates).

Reading guide: compare variants and windows, not point estimates. A larger
gap in one province than another does not identify where building would
lower prices, which homes are available, or which households are
unformed — see the [access chapter](../housing_access.md) for what those
questions would need.

## Correction (2026-11-26): protected completions

Results published here before this date took protected completions from the
protected rows then in VDP005_01, which fell far short of the Ministry's own
figures: 1,134 in 2024 against 14,371 in table 1.2 of the [Observatorio de
Vivienda y Suelo annual bulletin 2024](https://www.lamoncloa.gob.es/serviciosdeprensa/notasprensa/vivienda-agenda-urbana/Documents/2025/040725-ObservatoriodeviviendaysueloBoletnanual24.pdf),
which counts protected completions as final approvals. Why the earlier series
fell short is unknown. The fetch now requires national totals to equal that
table for 2008–2024. The superseded v2 gaps were 646,035 (2021–2024) and
804,905 (2021–2025).
