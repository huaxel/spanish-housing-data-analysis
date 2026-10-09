# Probe: Catastro Valor de Referencia — municipal MBR/MBC modules

**Date:** 2026-10-06 · **Status:** reachable, PDF-only, parser-fragile

## What it is

The Dirección General del Catastro publishes, annually (~25 Sept), a
Resolución with the elements for computing the **Valor de Referencia**
(transfer-tax reference value) of urban real estate. Anexo II lists, per
municipio, the **Módulos Básicos de Repercusión (MBR, land) and
Construcción (MBC, building)** that feed the reference-value formula.
Anexo X lists municipalities by province/code.

This is the only all-municipio price-like measure: every one of the
~8,131 municipios gets an MBR/MBC, including the steep/village ones the
Madrid leg of the terrain work said had "no price series".

## Access (verified)

- Resolución page: `sedecatastro.gob.es/Accesos/SecACCResolucion.aspx?ejercicio=2024&resolucion=resolucion&tipo=B`
- Anexo files are served behind a JS token: the page's `CargarFichero('TOKEN')`
  calls `../DocumentosCatalogo/SECRecuperarDocumento.aspx?csv=TOKEN`.
- Anexo II token (2024): `0YVSFVSD5578A8BN` → 113-page PDF, 1.9 MB.
- Anexo X token (2024): `GGQ874G64NMWJJ61` → 2 MB PDF.

## Format (the blocker)

Both anexos are **PDFs only** — no CSV/Excel download. Anexo II rows look
like:

```
ALBACETE 02069 LA RODA 5 210 3 600
ALBACETE 02044 LIETOR 7 37,8 5 500
```

i.e. `PROVINCIA CODIGO MUNICIPIO MBR MBC` with **thousands separated by
spaces** (MBR "5 210" = 5,210 €/m²) and **comma decimals** (37,8 = 37.8),
and NBSP (`\xa0`) between name tokens. Extracting this cleanly requires a
per-line parser keyed on the 5-digit code and the trailing two value
triples — feasible but fragile (name tokens, missing pages, value
collisions). pypdf extracts the text fine.

Note: MBR/MBC are **technical formula inputs, not prices**. They scale
with municipal land/building value but the reference value is computed
per-property from them plus property characteristics. As a municipal
price level they are a strong ordinal/cross-section proxy; not a
transaction series, and there is no time series (annual Resoluciones
only, 2022+).

## Verdict

**Reachable, but PDF-parser work for a cross-section proxy.** This is the
only route to all-municipio price-like levels — which is exactly what the
Madrid terrain leg said was missing ("no municipal price series for steep
municipios"). Worth building **only if** the terrain/price question is
reopened with a levels design; the parser cost (~1 day incl. validation)
and the MBR/MBC-as-price caveat make it a Tier-2 build, not a quick win.
Decision: **parked** — same reopen condition as design B (a design that
compares terrain to terrain at municipal grain).

## VDP001 check (2026-10-09): not valor de referencia — park stands

MIVAU's open-data CDN serves `VDP001_01.csv`, sampled 2026-10-09
(531,585 rows over 7,331 municipio codes, years 2011–2024; grain is
municipio — the `COD_POSTAL` column carries the 5-digit INE municipio
code, not a postal code). Its `PRECIO` element is
**monthly rent** (SERPAVI aggregates from IRPF rental declarations:
median/P25/P75 plus `SUPERFICIE` medians and `VIVIENDA` witness counts,
by colectiva/unifamiliar) — not purchase reference values, so it has
**zero fit** for the MBR/MBC question above. Rental content duplicates
the already-built SERPAVI marts (see `serpavi_probe.md`); the file is
also uncatalogued (datos.gob.es lists VDP002–VDP007 only, no readme),
so it is a fragile route. No action; park stands.