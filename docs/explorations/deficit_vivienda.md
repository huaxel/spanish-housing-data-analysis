# CaixaBank-style housing-deficit arithmetic

**Date:** 2026-10-09 · **Status:** implemented (`explorations/deficit_vivienda.py`,
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
- **Completions:** MIVAU VDP005_01 monthly finished dwellings (libre +
  protegida) by province, summed over calendar years
  (`fetch_mivau_terminadas.py`; missing months kept null, never filled).
  The visados variant is not reproduced: visados proper (CSCAE) are a
  different series from iniciadas and are not in the pipeline.
- **Variant v2** (creation minus finished): 646,035 over 2021–2024 and
  804,905 over 2021–2025, against published 600,000 and 734,000 — deltas
  of 46,035 and 70,905. The supply side matches their Ministerio source;
  the remaining level gap is window and vintage effects (their cuts use
  earlier releases; 2025–2026 inputs are still provisional here), and it
  is disclosed rather than tuned away.
- **Variant v3p** (minus tourist conversions, partial): 591,068 over
  2021–2024 and 796,637 over 2021–2025, subtracting the December-snapshot
  tourist-stock net flow from the mart VTE series. The non-resident
  foreign-purchase adjustment is not reproducible from in-repo inputs
  (no buyer-nationality split) and is omitted — hence partial, never
  presented as their third variant.
- **Geography check:** the top-five order reproduces exactly (Madrid,
  Barcelona, Valencia, Alicante, Murcia) with a top-five share of 0.49
  over 2021–2024, and Soria reproduces as a negative-gap exception.
  Cáceres is near-zero positive while Gipuzkoa (Guipúzcoa in their text)
  is positive by a few thousand, so two of the three published exceptions
  do not replicate — recorded here rather than smoothed over.
- **Known gaps:** a dozen monthly cells are missing (Canarias protegidas
  completions, July–December 2022, inventoried in the artifact); sums
exclude them, so national totals are lower bounds missing only that
  small regime. 2025 completions and 2026 stocks are provisional and
  revisable. Unformed households are missing from every variant (as in
  the published estimates).

Reading guide: compare variants and windows, not point estimates. A larger
gap in one province than another does not identify where building would
lower prices, which homes are available, or which households are
unformed — see the [access chapter](../housing_access.md) for what those
questions would need.
