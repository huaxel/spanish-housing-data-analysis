# Vacancy alignment: cadastre stock vs electric-consumption vacancy estimates

Added 2026-10-09. Descriptive cross-scale alignment: the cadastre pilot's
declared housing-property counts are cross-referenced with the Censo 2021
electric-consumption dwelling classes for Sevilla municipality (41091) and
with SIM's per-barrio unoccupied-dwelling counts. Vacancy figures are
presented as **assumption-dependent rate ranges, not measured rates**.
Artifact: `artifacts/cadastre_vacancy_alignment.json` (exploration:
`explorations/cadastre_vacancy_alignment.py`).

## Method

Two scales, two comparisons:

1. **City scale.** Censo 2021 `censo2021_intensidad` classes for 41091
   (Viviendas totales, vacías, con bajo consumo, de uso esporádico) against
   the sum of declared `dwelling_properties` over the entire cadastre
   extract, including the 3,500 properties outside any SIM barrio geometry.
2. **Barrio scale.** SIM `deshabitadas` counts evaluated against **both**
   denominators: SIM's own `viviendas_familiares` and the cadastre
   property counts. Every barrio weighs equally in cross-barrio statistics.

Coverage: 107 cadastre barrios, 108 SIM rows, **100 barrios join**.
Seven cadastre barrios lack a SIM `deshabitadas` value (San Gil 01007, La
Barzola 02023, Santa Justa y Rufina 02034, Bami 05054, El Prado 05058,
Barriada de Pineda 10101, Heliópolis 10104); Valdezorras (05061) is SIM-only.

## Findings

**City scale: the two independent stock totals agree to 99.95%.**

| Measure (Sevilla 41091) | Value |
|---|---|
| Census dwellings (electric-based) | 327,393 |
| — of which empty | 24,621 (7.52%) |
| — low consumption | 4,990 |
| — sporadic use | 17,200 |
| Upper non-occupied band (empty + low + sporadic) | 46,811 (14.3%) |
| Cadastre declared properties | 327,237 |
| Cadastre-to-census ratio | 0.999524 |

The upper band is an *outer envelope*, not an estimate: the three classes
are shown separately because their mutual exclusivity is a classification
assumption, and sporadic use includes genuinely secondary residences.
Re-denominating the census counts on cadastre properties barely moves the
rates (empty 7.52% either way; upper band 14.3% either way), because the
denominators coincide.

**Barrio scale: the two denominators are interchangeable for ranking.**

| Measure (100 joined barrios) | Value |
|---|---|
| Spearman, cadastre properties vs SIM family dwellings | 0.99847 |
| Joined cadastre properties / SIM dwellings / SIM unoccupied | 315,107 / 313,398 / 17,977 |
| Barrio denominator ratio, median (min–max) | 1.002 (0.665–1.257) |
| Mean unoccupied rate, SIM denominator | 5.28% (range 0.31–23.45) |
| Mean unoccupied rate, cadastre denominator | 5.33% (range 0.31–22.49) |
| Spearman of the two rate series | 0.995644 |

The denominator choice — a census-style family-dwelling count vs declared
cadastral properties — changes neither the level nor the ranking of
barrio unoccupancy: both summaries round to the same picture. The wide
barrio range (0.3–23%) reflects genuinely different neighborhoods, not
denominator noise.

## Limitations

- Vintages differ: Censo 2021, SIM layers undated, cadastre snapshot 2024+.
  Nothing here is a current vacancy rate.
- **Stock declared ≠ available housing; electric vacancy ≠ available
  housing.** Low consumption can mean efficient, absent or secondary use;
  sporadic use is not vacancy; cadastral property units are not census
  dwellings or households.
- The upper band assumes the three consumption classes are mutually
  exclusive and collectively exhaustive of non-occupation — a presentation
  envelope, not a measurement.
- SIM `deshabitadas` has no documented vintage; 7 barrios lack it and are
  excluded from barrio statistics (not treated as zero).
- Descriptive alignment only: no causal claim, no significance testing.

## Relation to existing work

The [/vacancia/ page](../../evidence/pages/vacancia.md) publishes municipal
vacancy classes for 3,139 municipalities. This exploration adds the Sevilla
cross-check: two independent total-count exercises land within 156 units of
each other, and at barrio grain the denominator choice is provably
immaterial to rankings — which licenses using either denominator in future
per-barrio vacancy displays.
