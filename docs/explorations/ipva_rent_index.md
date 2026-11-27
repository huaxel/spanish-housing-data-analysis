# Does an independent official series corroborate SERPAVI's municipal rents?

SERPAVI (MIVAU's exploitation of rental *fianzas*) is the repo's only
municipal rent **level** series, and every municipal rent claim rests on it.
The only cross-check so far is the DIBA comparison for Barcelona province.
INE publishes a second municipal rent series from a different instrument:
the **IPVA** (`Índice de Precios de Vivienda en Alquiler`, operation 432,
table 59060) — a quality-controlled price index for the 752 municipios above
10,000 inhabitants, annual, 2012–2023.

The two answer different questions, so only **changes** are comparable: an
index has no level in euros, and SERPAVI's median of filed contracts is not a
quality-controlled index. The test is whether the municipal *trajectories*
agree.

## Method

- Both sides are name-keyed (the IPVA publishes no municipality codes), joined
  through `muni_names.muni_key` with a bilingual fallback that retries each half
  of `Alicante/Alacant`-style names. Of the 752 IPVA municipios, **686** match a
  SERPAVI row and **66** do not (mostly Valencian and Balearic bilingual names
  and small Costa Brava municipalities); nothing is dropped silently.
- Two windows are reported, 2013→2023 and 2019→2023, so a result does not hinge
  on one base year.
- Agreement is measured twice: **rank** (Spearman — do they order municipios the
  same way?) and **level** (the per-municipality gap in percentage points).

## What the two series say

| Window | n | IPVA median change | SERPAVI median change | Pearson | Spearman | Gap (IPVA − SERPAVI) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2013→2023 | 678 | +15.8% | +32.1% | +0.618 | +0.670 | −16.2 pp (p10 −27.3, p90 −7.6) |
| 2019→2023 | 683 | +8.0% | +16.1% | +0.679 | +0.690 | −8.0 pp (p10 −13.9, p90 −4.2) |

They agree on **direction and ordering** (ρ ≈ 0.67–0.69, r ≈ 0.62–0.68) and
disagree on **magnitude**: SERPAVI's municipal median rent rises roughly twice
as much as INE's index over the same window. The gap is not a base-year
artefact — it survives when both windows are cut.

## Why the gap is not a constant offset

Sorting municipios by SERPAVI's own change splits the gap cleanly (2013→2023):

| Quartile | SERPAVI change | Gap (IPVA − SERPAVI) |
| --- | ---: | ---: |
| 1 (weakest) | +21.0% | −9.6 pp |
| 2 | +28.2% | −14.0 pp |
| 3 | +34.9% | −17.6 pp |
| 4 (strongest) | +45.9% | −24.6 pp |

Where SERPAVI rises most, the disagreement is largest. A constant instrument
offset would leave the gap flat across quartiles; this pattern is what
composition or quality drift looks like — the mix of dwellings and contracts
behind a median of filed deposits can change faster than a quality-controlled
index — but the decomposition is not identified here (no dwelling-level mix in
either series).

## What this changes, and what it does not

- **Supported:** SERPAVI's municipal *ordering* is corroborated by an
  independent official instrument. Claims that compare municipios ("this market
  is tighter than that one") are not overturned.
- **Weakened:** any claim that treats SERPAVI's municipal percentage changes as
  precise magnitudes, and any chained calculation that multiplies them over
  several years. The repo's own caveat that SERPAVI is a proxy already said this
  qualitatively; this is the quantitative version, and the divergence grows with
  the size of the move.
- **Not claimed:** that either series is wrong. The IPVA ends in 2023, covers
  only municipios above 10,000 inhabitants and carries INE's own weighting
  choices; SERPAVI is a median of filed contracts with nationwide coverage. Both
  are published official statistics measuring different objects.

## Reproduce

```bash
uv run python scripts/fetch_ipva.py --offline
uv run python explorations/ipva_rent_index.py
```

Pinned input: `data/raw/ipva_municipal_59060.json` (table 59060, 2012–2023).
Output artifact: `artifacts/ipva_rent_index.json`; `--check` verifies it against
the pinned parquet and the marts.
