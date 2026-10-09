# Rental-household denominators: Sevilla 2021 source assessment

## Conclusion

The two inspected official municipal tenure tables do **not** supply a rental-
household denominator for the full Sevilla municipal profile. Both expose only
Alcalá de Guadaíra, Dos Hermanas, Sevilla and Utrera in the province. These four
municipalities already have validated SERPAVI rents; describing them does not
identify how much rental housing lies outside the larger rent-observed sample.
This is a finding about the inspected publications, not proof that no other
source or custom INE tabulation exists.

Keep `/stock-2021/` household-location coverage unchanged. Do not relabel its
all-tenure households as rental households, impute tenancy to smaller towns or
divide a numerator spanning the rent sample by a denominator restricted to four
cities. A limited tenure-context panel could be valid, but is not a solution to
province-wide contract/tenant coverage or available rental supply.

## Primary sources checked

| Source | Published unit and scope | Timing and interpretation | Fit |
| --- | --- | --- | --- |
| [INE ECEPOV table 56582](https://www.ine.es/jaxi/Tabla.htm?tpx=56582&L=0), **Hogares según régimen de tenencia de la vivienda y tipo de hogar** | Households; municipalities above 50,000 inhabitants and provincial capitals; inspected export has 151 named municipalities nationally | Survey estimates, not a census household enumeration at a single date | Rental-household context for four Sevilla municipalities only |
| [INE Census table 59529](https://www.ine.es/jaxi/Tabla.htm?tpx=59529&L=0), **Viviendas familiares principales convencionales según régimen de tenencia** | Dwellings, not households; same restricted municipal publication scope; inspected export has 151 municipality codes nationally | Census reference 1 January 2021; tenure combines administrative information and imputation | Separate conventional-primary-dwelling context, not a replacement household denominator |

Direct official exports inspected locally:

- <https://www.ine.es/jaxi/files/tpx/csv_bd/56582.csv>
- <https://www.ine.es/jaxi/files/tpx/csv_bd/59529.csv>

The household table's published note says `.` means data not provided because
of insufficient sample. Select `Tipo de hogar = Total` and `Régimen de tenencia
de la vivienda = Alquilada`; never sum total plus household-type categories.
Its CSV has names rather than official municipal codes. Any future integration
needs an explicit checked crosswalk, not an unrestricted name-only join.

The dwelling table carries codes `41004`, `41038`, `41091`, `41095`. Select the
published `En alquiler` category, keeping its **dwelling** unit explicit. The
inspected exports also differ in numeric grouping: household figures use dots,
dwelling figures use commas. A future parser must validate each export's
format; a shared blindly applied decimal or separator rule is unsafe.

## Survey dates are not the census snapshot

The final [ECEPOV methodology](https://www.ine.es/metodologia/metodologia_ECEPOV_2021.pdf),
section 3.3 (printed page 7), states that fieldwork ran in two phases:
April–August 2021 and October 2021–February 2022. In general, the reference is
the interview date; INE describes the survey broadly as the average of 2021.
Do not use the earlier project's planned fieldwork dates as the executed survey
schedule, or label these household estimates `1 January 2021`.

Sections 6.5–6.6 (printed pages 23–25) describe expansion, non-response
correction, ratio estimation and calibration, and sampling-error publication.
A production panel should retain the survey status and suppression, and inspect
matching published precision information before presenting sampling certainty.
The survey household total should not be forced to equal table 59543's census
household total by an undocumented rescaling.

## Census tenure is not wholly observed or independent

The [final Census 2021 methodology](https://www.ine.es/censos2021/censos2021_meto.pdf),
printed pages 85–86, describes tenure assignment using tax information
(including model 100 and use/ownership/usufruct variables) and cadastral title
information. It states that tenure was obtained for slightly more than 75% of
households this way; the remainder underwent automatic imputation using
external ECEPOV frequencies.

Consequently, census tenure and ECEPOV tenure are not independent replications.
Nor should tax-informed tenure automatically be described as independent of
the fiscal sources underlying SERPAVI. Shared inputs do not imply identical
concepts or coverage, but they do limit an independent-validation argument.
Both tenure publications include categories outside SERPAVI's VC typology.
Neither counts advertised, habitable or legally available homes.

## Inspection and next action

The initial assessment downloaded CSVs to `/tmp/ine-tenure-56582.csv` and
`/tmp/ine-tenure-59529.csv` only. Names/codes, dimensions, total/rental category
cells and the four-municipality overlap were checked against the sidecar.

A subsequent implementation pins **census table 59529 and its catalogue** as
`data/raw/censo2021_tenencia_59529.csv` / `.html`. The sidecar's separate
`tenencia_contexto` table and `/stock-2021/` expose only the four published
municipalities, with conventional-primary-dwelling units and explicit
imputation/scope warnings. Counts are validated by code and compatible labels,
unique category keys, source-specific comma grouping and conservation of
published totals when all categories are known. Missing cells remain null and
partial known category sums cannot exceed a known total. Source/code freshness
checks compare the exact context rows too. No household or contract coverage
denominator is changed; table 56582 remains inspection-only.

Any further extension must preserve the four-city context as a separate unit
and scope, with official metadata, numeric-format and identity contracts. For a
province-wide tenant-coverage claim, obtain a validated denominator at the
necessary geography, dates and rental typology (potentially an INE custom
request), rather than spreading the provincial or four-city rental rate over
unobserved municipalities. Even that would measure occupancy/tenure, not homes
available to let. Do not manufacture a new availability indicator from it.
