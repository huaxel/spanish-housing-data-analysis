# Probe: construction flows (licencias / ECB completions) at province grain

**Date:** 2026-10-06 · **Status:** reachable but access is app/PDF work

## What the repo lacks

No national supply-flow variable: `mart_provincia_anual` stock is a
level (MIVAU estimate), and starts/completions exist only for Barcelona
municipios (DIBA). The core question (stock built ↔ prices) has no
province-grain construction flow.

## Access routes (verified)

1. **Fomento/Mitma "Construcción de edificios (licencias municipales de
   obra)"** — the licencias series (number of permits, viviendas by CCAA).
   Landing page is 200-able with a Chrome UA, but the data sits in a JS
   app (`apps.fomento.gob.es/BoletinOnline`), not static files. The
   published tables are Excel/PDF attachments per period with
   **documented gaps** (Andalucía missing from Sep-2019, CLM from
   Jul-2018, Extremadura from May-2018 — per the source itself).
2. **INE ECB (Estadística de Construcción de Edificios)** — viviendas
   terminadas by province. **Not in the current Tempus3
   OPERACIONES_DISPONIBLES list** (probed: only sector-construction and
   production-index operations are live). The ECB is published
   separately (historical) or via ISTAC for Canarias detail.
3. **INE Índice de Producción de la Construcción (30293)** and
   **Índice de Precios de Vivienda en Alquiler / IRAV** are live in
   Tempus3 — the rent index is redundant with SERPAVI, and the
   production index is a national activity gauge, not a dwelling flow.

## Verdict

**Reachable in principle, poor value-per-effort now.** The licencias
series has coverage gaps in exactly the boom years that matter (2018+),
and its access is app/PDF. The ECB completions table is not in the
current API. The DIBA municipal starts/completions already give the
cleanest flow series for the one market with municipal price data.
Parked: revisit only if a province-grain supply-flow design is needed
and the Fomento Excel attachments (pre-2019, clean) are extracted
manually once. Same class as the valor-referencia verdict: real data,
fragile access, cross-section or dated — not a quick win.