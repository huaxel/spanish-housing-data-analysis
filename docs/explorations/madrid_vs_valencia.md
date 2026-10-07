# Madrid vs Valencia: absolute scarcity vs composition crisis

Computed by `explorations/madrid_vs_valencia.py`
(`artifacts/deepcut_mad_val.json`). Same marts, no new data — this is what
the assembled layers say about Spain's two archetypal markets.

## Madrid: the magnet that never overbuilt

Fewest dwellings per capita in Spain since 2010 (459→429/1000, 2007–25
endpoints; País Vasco was lower in 2007 at 454), low and falling
non-primary share (19→12%), most expensive (€3,686/m² in 2025;
second-worst affordability at 6.2 years in 2024, after Balears 6.4).
Madrid's bust (−33% €/m², affordability 8.0→5.8 years)
was pure credit: mortgages collapsed 137k→32k while the stock barely moved.
Its recovery is young migrants (20–34 share 17.1→18.5% 2021–25, +160k young ≈
+162k households). Every margin binds at once: land, credit history,
demographic inflow. Building more is the necessary (not sufficient) answer.
**Correction 2026-10-07 (repo review):** this paragraph overstated
superlatives (fewest since 2007, lowest non-primary share, worst
affordability — País Vasco was lower on stock and non-primary share in
2007, Balears less affordable in 2024) and carried stale endpoints
(non-primary 14% is ~2021, 2025 is 12%; share 16.9% is 2019, the
2021–25 window runs 17.1→18.5%).

## Valencia: tight statistics on top of abundant bricks

The CCAA built 0.23 dwellings per new household 2021–25 (tightest in Spain)
— yet Alicante holds 676 dwellings per 1,000 people and Castellón 717
(vs Madrid's 429), because **44–46% of those dwellings weren't primary
residences in 2020**. And the tourist-flat suspect is acquitted: registered tourist
dwellings are only **4.3% of Valencia's non-primary stock** (48k of 1.12M,
2025), 5–6% in Cataluña, 4% in Madrid — *falling* 2021→25 in most markets
(Balears 29k→19k) while prices rose. The sea beside primary housing is
second homes and vacant inheritance, not tourist flats. Prices recovered from 2021 lows (Castellón €1,070→€1,299; CCAA mean €1,254→€1,708) and mortgages roughly tripled off the 2013 trough (20k→61k) without the magnet's demographics (young share only 15.9→16.7% 2021–25).

## Update 2026-10-06: the 2011 split decomposes the sea (`censo2011_val`)

Second vs vacant, 2011: Torrevieja **51% second + 16% vacant** (two-thirds
non-primary) · Benidorm 43% + 9% · Orihuela 40% + 16% · Gandía 37% + 9% ·
Dénia 29% + **31% vacant** (highest vacancy in the set) · Alicante 15% + 14% ·
Castellón 9% + 15% · Valencia city 8% + 14%. The composition crisis is *both*:
a second-home coast (Torrevieja/Benidorm/Orihuela) *and* a vacant stock
(Dénia, Castellón, Valencia city at 14–31%). Tourist flats (4.3%) are a
footnote to both.

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
