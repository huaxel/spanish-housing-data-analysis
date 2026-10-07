# The viv/1000 national flatness hides a selected-tails split

Question that started this: how does the national dwellings-per-1000
ratio stay basically flat across 2001–2025 while population grew ~+20%?
Answer: it does **not** stay flat (+7.8% national: 511.6 → 551.6), and the
national number hides sharply different CCAA trajectories.

**Correction 2026-10-06 (independent review):** the first version
framed this as an exhaustive "two-group decomposition." It is not —
the two groups below are manually selected tails (four falling, four
largest-rising); **nine of 17 CCAA sit outside both groups**, and the
middle (Valencia +0.1, Navarra +17, Murcia +21, Andalucía +33, País
Vasco +36, Aragón +59, Rioja +65, CLM +65, Cantabria +70) is unassigned.
Read the table as a tails contrast with population/stock weights, not a
partition of the national number.

Tested by `explorations/ratio_ccaa.py` (raw: `artifacts/ratio_ccaa.json`).
Ratio = `viviendas_total / poblacion * 1000` per CCAA at 2001/2007/2021/2025
(provincia mart 2001–21 + CCAA mart 2025). Real price change = IPV index
2007→2025 deflated by IPC (base 2021) per CCAA.

## The split

| Group | CCAA | Δ ratio 2007→25 | Real price Δ 2007→25 |
| --- | --- | --- | --- |
| Scarcity (ratio falling) | Madrid −29.7, Cataluña −27.6, Balears −13.3, Canarias −1.2 | −13.3…−29.7 | median **−8.6%** |
| Overstock (ratio rising) | Asturias +130.3, CyL +122.0, Galicia +107.4, Extremadura +100.0 | +100…+130 | median **−23.6%** |

National: stock +28.8% 2001→25, population +19.5% — the ratio rose because
the 2001–08 boom built ahead of the immigration wave. The national 2007→25
(+3.7%) is the difference of two big opposing forces, not a stable system.

- **Group 1 (Madrid, Cataluña, Balears, Canarias):** population ran ahead of
  stock. Madrid +25.7% pop vs +20.0% stock 2001→2021; the ratio fell ~30.
- **Group 2 (interior + north-west):** the boom built for a population that
  then shrank. CyL stock +26% but population **−3.9%** 2001→2021; Asturias −5.9%.
  Ratio +100 to +130 — the overhang, measured as dwellings per person.

## The price cross

Δ ratio (2007→25) vs real price change (2007→25) across 17 CCAA:

| | value | n |
| --- | --- | --- |
| Pearson | −0.385 (t = −1.62) | 17 |
| Spearman | −0.407 | 17 |

Negative as the overhang story predicts (more stock per person ⇒ weaker real
prices), but **not distinguishable from zero at n=17**. The group contrast
is substantial (median −8.6% vs −23.6% real), so the sign is directionally
consistent — this is a descriptor, not an estimate.

## Reading

- The "flat since 2007" reading of the national series is a composition
  artifact: demand regions fell ~−30, overstock regions rose +60…+130, and
  the two groups roughly cancel. Any use of the national ratio should carry
  this decomposition or it will mislead.
- The overstock group (Asturias 675.7, CyL 770.7, Galicia 652.9,
  Extremadura 671.3, CLM 642.7 at 2025) sits **above** the ~650 level the
  synthesis associates with surplus stock — the demand shortage is
  geographically concentrated in the south/Mediterranean, not the north.
- The scarcity group is where the synthesis's regime 3 (2021–25) lives —
  but it is not only Madrid and Cataluña. **Correction 2026-10-06
  (independent review): 13 of 17 CCAA have lower ratios in 2025 than
  2021** (Comunitat Valenciana −37.4, Balears −24.4, Murcia −17.5,
  CLM −16.4, Cataluña −15.9, Canarias −14.5, Madrid −11.8, …). Madrid
  (441 → 429) and Cataluña (506 → 490) are prominent cases of a
  broad-based post-2021 tightening as immigration returns against a
  slow construction pipeline — not the only two.
- Caveats: ratio uses stock (MIVAU estimate) and population that switches
  from padrón to ECP/censo-anual at 2021 (seam ≤0.9%, quantified in
  `coverage.json`); 2001 stock is MIVAU-modeled, census-anchored at 2011
  (see `docs/methods.md`). Cross-section of 17, no clustering — treat the
  correlations as a floor on uncertainty, not a standard error.

## Vacancy (electricity-based, censo2021_intensidad 59531) confirms it

The 2021 census replaced the classic principal/secundaria/vacía split with
an **objective vacancy measure from electricity consumption** (below-threshold
use over the year to 1-Jan-2021), published at municipal grain (3,139 named
municipios + per-province Resto aggregates; see
`docs/explorations/censo_anual_probe.md`). This gives the other side of the
overhang that the viv/1000 ratio only suggests:

| CCAA | Vacancy share 2021 | Δ ratio 2007→25 |
| --- | --- | --- |
| Galicia | **28.81%** | +107.4 |
| Castilla - La Mancha | 22.51% | +65.5 |
| Castilla y León | 19.38% | +122.0 |
| Extremadura | 17.61% | +100.0 |
| Madrid | **6.34%** | −29.7 |
| País Vasco | 6.48% | +36.2 |
| Cataluña | 10.67% | −27.6 |

Cross-section across 17 CCAA: Δ ratio vs vacancy share, Pearson **+0.523**,
Spearman **+0.475** — stronger than the price cross (−0.385). The regions
where the boom built most per person are the ones with the highest share of
dwellings whose consumption is below the occupancy threshold: **Galicia has
4.5× Madrid's vacancy rate (28.8% vs 6.3%)**. The overstock group of the
ratio decomposition is not a modeling artifact of the viv/1000 metric — it
shows up as objectively empty stock in the electricity data.

Caveat: electricity-based vacancy is a 2021 snapshot only (the 2011 census
used the field-agent classification; the two are not comparable). It
complements, does not replace, the vintage/vacancy data the repo already
has for 2011 (`censo2011_vintage`).