# Todos los municipios: alquiler y vacancia a escala nacional

> Added 2026-10-07. `muni_all` merges all 52 DPOP municipal tables
> (8,136 municipios, 1996–2025) with SERPAVI median rent (2011–2024,
> 2,515 municipios with rent in 2024) and Censo 2011 vacancy (2,270 rows).
> Same omission policy as the Valencia/Sevilla tables: 3 national censo
> homonym keys, 52 cross-province homonym keys and the Granada
> Pinar/Píñar twins carry no vacancy; twins keep population only.
> No sale prices at this grain anywhere (Madrid valor tasado and DIBA
> Barcelona remain the only municipal price series).

## National maxima, 2024 rents and 2011 vacancy

Highest 2024 rents: Sant Josep de sa Talaia (14.63), Donostia/San
Sebastián (13.99), Madrid city (13.97). Highest 2011 vacancy shares:
Yebes (60.0%), Ezcaray (49.1%), Chilches/Xilxes (45.1%) — small
municipios with large second-home or empty stocks, against Madrid
city's 13.97 €/m² rent and 3,506,730 inhabitants in 2025.

Cross-checks against the single-province tables are exact: València
840,792 inhabitants in 2025, Sevilla city rent 9.17 €/m² in 2024 —
`muni_all` reproduces `muni_vlc`/`muni_sev` cell for cell on the overlap.

## National findings (`explorations/municipios_nacional.py`, descriptive)

2024 rents (2,515 municipios, unweighted): median 5.22 €/m² (P25 3.97,
P75 6.77), from Carballeda de Valdeorras (1.84) to Sant Josep de sa
Talaia (14.63). Paired 2011→2024 growth (1,678 municipios): median
+29.0%; the extreme (Sahún, +223.4%) is a thin-cell village — small
cells dominate both tails, read maxima as anecdotes not markets.

2024 rent vs 2011 vacancy (1,927 municipios): Pearson −0.393, Spearman
−0.434 — the overhang geography holds nationally (emptier places rent
cheaper), matching the SERPAVI–2021-vacancy read (−0.429/−0.507).
Population growth 2011→2024 vs rent growth (1,678): Pearson 0.051,
Spearman 0.115 — rents rose ~everywhere regardless of local headcount:
a national price level shift, not local demand sorting. Descriptive only.

## What this does not show

No sale prices, no burdens, no tourist series at this grain. The 8,136
count is DPOP municipal series (aggregates dropped with pinned-total
guards, one per table); it is not a LAU census and small municipios
without 2011 census rows have no vacancy.
