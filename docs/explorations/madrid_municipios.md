# Capital vs corona: Madrid's permanent repricing of the south

From `valor_municipal_madrid` (MIVAU via datos.comunidad.madrid mirror, Libre
€/m², 28 municipios, 2005–2025). No new script — the table below *is* the
evidence; rerun against the mart table. Padrón municipal join queued (DPOP
Madrid-municipios table) for per-capita context.

## Levels 2007 → 2013 → 2025 (only 2025 shown for corona detail)

| municipio | 2007 | 2013 | 2025 | 2007→25 |
| --- | --- | --- | --- | --- |
| Madrid capital | 3,845 | 2,432 | 4,993 | +30% |
| Pozuelo de Alarcón | 3,631 | 2,412 | 4,794 | +32% |
| Majadahonda | 3,644 | 2,370 | 4,437 | +22% |
| Alcobendas | 3,520 | 2,529 | 4,327 | +23% |
| Getafe | 2,872 | 1,542 | 2,812 | −2% |
| Leganés | 3,018 | 1,523 | 2,869 | −5% |
| Torrejón de Ardoz | 2,696 | 1,326 | 2,644 | −2% |
| Alcalá de Henares | 2,801 | 1,391 | 2,514 | −10% |
| Fuenlabrada | 2,552 | 1,354 | 2,566 | +1% |
| Valdemoro | 2,448 | 1,323 | 2,356 | −4% |
| Parla | 2,412 | 1,083 | 2,097 | −13% |

## Reading: the bust drew a line the recovery didn't erase

North-west premium markets fell ~30% and recovered past boom prices; the
southern corona fell ~50–55% (Parla €1,083!) and *never nominally recovered*
— Fuenlabrada took eighteen years to reach +0.5%. All municipal €/m² here
are nominal: in real terms the south's shortfall is larger (IPC deflation
is queued — no price level in this doc is inflation-adjusted). The capital
(+30%) detached from
its own south, which now prices like 2007 Castilla-La Mancha towns. This is
the municipal face of the CCAA story: Madrid's aggregate recovery was
capital-plus-northwest; the provinces' analogue needs the same municipal cut
elsewhere (queued: Barcelona via IDESCAT/AMB mirrors, Valencia via GVA).

## Update: people vs prices 2007–2025 (`muni_madrid` join)

Padrón municipal (DPOP 2881; the 'Madrid' province/city name collision
resolved against the pinned provincial total) joined to valor tasado:

| municipio | pob 2007→25 | €/m² 2007→25 |
| --- | --- | --- |
| Rivas-Vaciamadrid | +74% | +21% |
| Boadilla del Monte | +67% | +20% |
| Valdemoro | +62% | −4% |
| Parla | +39% | −13% |
| Madrid capital | +12% | +30% |

Growth doesn't lift all prices: Rivas absorbed +74% people at +21% prices
(building kept up, family suburb); Parla absorbed +39% at −13% (demand
without purchasing power — filtering down, not gentrification); the capital
grew least (+12%) and appreciated most (+30%). Municipal absorption *does*
discriminate, unlike the CCAA ratio — grain matters.

## Update: the 2011 split — vacancy, not second homes (`censo2011_mad`)

The 2011 census classified municipal dwellings (principal/secundaria/vacía;
the 2021 register-census dropped the split, which is why it stays open).
Vacant share of all dwellings, 2011:

Madrid city 10.0% · Valdemoro 8.3% · Torrejón 8.1% · Alcalá 7.3% ·
Getafe 7.0% · Parla 6.0% · Leganés 5.2% · Fuenlabrada 4.9% ·
Pozuelo 4.7% (but secundaria 5.5% — rich second homes) ·
Alcobendas 3.7% · Rivas 1.9%.

The south's overhang was vacant crash-leftover from the start, not second
homes; Rivas (the growth absorber) had almost no vacancy. Madrid city's
153k vacant + 57k secundaria dwellings in 2011 are the scale reminder:
the capital's 2025 tightness was built on a decade of absorbing exactly
this slack — plus migrants.

## Limits

- Mirror source (Base 2005): third-party copy of MIVAU; provincial VDP006
  cross-checks Madrid's mean, not each municipio. Treat municipal decimals
  as indicative.
- No municipal stock/population yet — price-only cut. Per-capita context
  needs the DPOP Madrid-municipios table.
- Missing cells ('-') cluster in small municipios and early years; the 11
  shown are the complete 2005–2025 core.
