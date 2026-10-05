# Madrid vs Valencia: absolute scarcity vs composition crisis

Computed by `explorations/madrid_vs_valencia.py`
(`artifacts/deepcut_mad_val.json`). Same marts, no new data — this is what
the assembled layers say about Spain's two archetypal markets.

## Madrid: the magnet that never overbuilt

Fewest dwellings per capita in Spain (459→429/1000, 2007–25 — *falling* the
whole period), lowest non-primary share (19→14%), most expensive (€3,686/m²,
6.15 years of income). Madrid's bust (−33% €/m², affordability 8.0→5.8 years)
was pure credit: mortgages collapsed 137k→32k while the stock barely moved.
Its recovery is young migrants (20–34 share 16.9→18.5%, +160k young ≈
+162k households 2021–25). Every margin binds at once: land, credit history,
demographic inflow. Building more is the necessary (not sufficient) answer.

## Valencia: tight statistics on top of abundant bricks

The CCAA built 0.23 dwellings per new household 2021–25 (tightest in Spain)
— yet Alicante holds 720 dwellings per 1,000 people and Castellón 762
(vs Madrid's 429), because **44–46% of those dwellings aren't primary
residences**. And the tourist-flat suspect is acquitted: registered tourist
dwellings are only **4.3% of Valencia's non-primary stock** (48k of 1.12M,
2025), 5–6% in Cataluña, 4% in Madrid — *falling* 2021→25 in most markets
(Balears 29k→19k) while prices rose. The sea beside primary housing is
second homes and vacant inheritance, not tourist flats. Prices (€1,070
Castellón → €1,708 CCAA mean, 2021–25) and mortgages (20k→61k) recovered
without the magnet's demographics (young share only 15.9→16.7%).

## Update 2026-10-06: tourist flats acquitted (VTE layer)

`viv_turisticas` / `share_turistica_no_princ` (2020–) now in both marts.
Only Canarias (19%) and Balears (9–14%) have double-digit tourist shares of
non-primary stock; everywhere else it's 4–6% and shrinking under licensing
freezes. The queued distinction is now sharper: *second homes vs vacant*
— neither is observable yet in Tempus at this grain.

## The policy moral the data supports

National ratios mislead in opposite directions: Madrid looks "average" on
dwellings-per-household (1.13) while being absolutely scarcest; Valencia
looks abundant per capita (614) while being tightest per new household.
Neither "build everywhere" nor "there are enough homes" survives contact
with the provinces. The two levers differ by market: Madrid needs net new
primary stock; coastal Valencia needs mobilizing existing non-primary stock
(and the data to tell vacant from touristic — `share_no_principal` can't
split them, a queued distinction).
