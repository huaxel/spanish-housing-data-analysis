# Valencia: rents without sale prices at municipal grain

> Added 2026-10-07. No municipal sale-price source exists for Valencia:
> MIVAU publishes valor tasado municipal only through regional mirrors
> (Madrid, Cantabria, Canarias — no Valencian mirror on datos.gob.es or the
> GVA CKAN), and the GVA statistics portal (PEGV Banco de datos territorial)
> times out from the fetch network, so no automated fetcher can reach it.
> Revisit only with a reachable official endpoint or a pinned manual drop
> (censo2021 precedent). Everything below is rents, population, vacancy.

From `muni_vlc` (INE Padrón DPOP 2903 + SERPAVI median rent
`ALQM2_LV_M_VC` + Censo 2011 vacancy): 266 municipios, population
1996–2025, rents 2011–2024 (159 municipios with rent in 2024), 2011 vacancy
for 133. Two cross-province homonyms (`l'Alcúdia`, `Oliva`) get no vacancy —
omission, never a guess (build asserts the skip list).

## Capital and corona, 2011→2024

| municipio | rent €/m²/mes | pop |
| --- | --- | --- |
| València | 5.15 → 8.18 (+59%) | 798k → 841k |
| Torrent | 4.22 → 6.28 (+49%) | 81k → 91k |
| Gandia | 3.93 → 5.22 (+33%) | 79k → 83k |
| Sagunt/Sagunto | sin renta publicada | 66k → 73k |

València city holds 30.5% of the provincial population (840,792 in 2025).
The highest 2024 rents are Canet d'En Berenguer (8.33), Loriguilla (8.26)
and the capital (8.18): coast-plus-metro-corona, not a single-centre story.

## Vacancy 2011: rural interior vs capital

València city: 57,193 vacant dwellings, 13.6% of its 2011 stock. The maxima
are small interior municipios — Font de la Figuera (44.4%), Villar del
Arzobispo (29.7%) — against the capital's 13.6%. Same overhang geography
as the ratio analysis: empty interior, tight coast. Descriptive only.

## What this does not show

No sale prices, no burdens, no tourist series at this grain. The
Madrid-vs-Valencia comparison stays provincial for prices; Valencia
municipal is rents + vacancy until a price source appears.
