# Cadastre vs Censo 2021 households per barrio (Sevilla)

Added 2026-10-09. Descriptive definitional comparison joining the cadastre
pilot's declared housing-property counts with the official Censo 2021
municipal household count (INE 59543) and SIM's per-barrio household series
(latest year 2021). Coverage ratios — properties per household — are
documented as what they are: a comparison of different units (cadastral
properties vs census dwellings vs households), not occupancy rates.
Artifact: `artifacts/cadastre_household_alignment.json` (exploration:
`explorations/cadastre_household_alignment.py`).

## Method

The city total uses the official INE municipal count (table 59543, 1
January 2021, retained in the [data dictionary](../data_dictionary.md));
the per-barrio breakdown uses SIM's household series, which has no census
counterpart at barrio grain. Denominators therefore mix sources by design —
the city anchor is census-official, the barrio ratios are SIM-cadastre.
No occupancy, absorption or causal claim.

Coverage: 107 cadastre barrios, 108 SIM 2021 rows, **107 join**;
Valdezorras (05061) is SIM-only.

## Findings

**City: about 60,500 more declared properties than census households.**

| Measure (Sevilla) | Value |
|---|---|
| Census households 2021 (INE 59543) | 266,703 |
| Cadastre properties, barrio-assigned | 323,737 |
| Cadastre properties, full extract | 327,237 |
| SIM households 2021, joined barrios | 267,970 |
| Properties per census household | **1.227** |
| Properties per SIM household | 1.2081 |

The property surplus is consistent with the
[vacancy alignment](cadastre_vacancy_alignment.md): census non-occupied
classes (empty 24,621 + low consumption + sporadic use = 46,811) absorb
most but not all of it; the remainder is registration mismatch, mixed-use
units and second homes above the sporadic-use threshold. Properties per
household is a coverage ratio, not a vacancy rate.

**Barrio: properties exceed households almost everywhere.**

| Measure (107 joined barrios) | Value |
|---|---|
| Spearman, properties vs SIM households | 0.985398 |
| Households per property, median | 0.8278 (min 0.5769, max 1.257) |

| Fewest households per property | Ratio |  | Most households per property | Ratio |
|---|---|---|---|---|
| Santa Cruz | 0.5769 |  | El Gordillo | 1.257 |
| Alfalfa | 0.6203 |  | Aeropuerto Viejo | 1.0626 |
| El Plantinar | 0.6564 |  | El Prado-Parque María Luisa | 1.0506 |
| Bami | 0.6736 |  | La Barzola | 1.0305 |
| San Bartolomé | 0.6821 |  | La Corza | 1.0247 |

The low-ratio end is the historic core, where secondary and tourist uses
concentrate declared properties above the resident-household count. All
five high-ratio barrios are tiny (under 700 declared properties), where
small-count geometry mismatches dominate — none shows a meaningful
household surplus over properties.

## Limitations

- Different units: cadastral property units, census dwellings and
  households are not interchangeable; properties per household is not an
  occupancy rate.
- The official census household count has no barrio breakdown; per-barrio
  ratios use SIM households of unknown method and unknown snapshot date.
- SIM household figures are annual-series values; the cadastre snapshot is
  newer. Mismatches combine definition, timing and classification effects.
- Values above 1.0 in tiny barrios are assignment noise, not over-occupancy.

## Relation to existing work

This is the households leg of the stock accounting alongside the
[vacancy alignment](cadastre_vacancy_alignment.md): three independently
collected city totals (census dwellings ≈ cadastre properties to 99.95%;
census households 1.227 properties each) tell one coherent story — Sevilla's
declared stock substantially exceeds its resident households, and the gap
lives in secondary, vacant and mixed-use units rather than in any
denominator choice.
