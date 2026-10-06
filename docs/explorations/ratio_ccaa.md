# The viv/1000 national flatness is a two-group accident

Question that started this: how does the national dwellings-per-1000
ratio stay basically flat across 2001–2025 while population grew ~+20%?
Answer: it does **not** stay flat (+7.8% national: 511.6 → 551.6), and the
national number hides a **two-group split** with different price outcomes.

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
  stock. Madrid +25.7% pop vs +20.0% stock since 2001; the ratio fell ~30.
- **Group 2 (interior + north-west):** the boom built for a population that
  then shrank. CyL stock +26% but population **−3.9%**; Asturias −5.9%.
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
- The scarcity group is where the synthesis's regime 3 (2021–25) lives:
  Madrid and Cataluña are the two CCAA whose ratio keeps falling after 2021
  (441 → 429 and 506 → 490) as immigration returns against a frozen
  construction pipeline.
- Caveats: ratio uses stock (MIVAU estimate) and population that switches
  from padrón to ECP/censo-anual at 2021 (seam ≤0.9%, quantified in
  `coverage.json`); 2001 stock is MIVAU-modeled, census-anchored at 2011
  (see `docs/methods.md`). Cross-section of 17, no clustering — treat the
  correlations as a floor on uncertainty, not a standard error.