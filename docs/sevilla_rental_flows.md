# Sevilla rental flows: deposit-register feasibility and the 2026 break

## Decision

Do not add a municipal rental-flow or availability indicator yet. No reusable
municipal residential-contract export was verified in the inspected AVRA pages
and public catalogue queries. A deposit register is a plausible administrative
source for historical formalised tenancies, but deposits are neither listings
nor unique homes entering the rental stock.

There is also a verified **legal collection break for contracts dated from
24 January 2026**, not evidence of a market contraction. Any future extraction
must preserve this break rather than joining deposit counts into a continuous
current-market series.

## Primary evidence

- [AVRA's current guidance on Law 5/2025](https://www.juntadeandalucia.es/organismos/avra/areas/fianzas/notas-ley-vivienda-andalucia-2025.html)
  gives entry into force as **24 January 2026**, inclusive. Public deposit remains
  required for contracts with contract/devengo date through **23 January 2026**;
  the obligation to deposit before the regional administration is removed for
  contracts concluded from the following day. Old deposits are returned as
  contracts extinguish, upon request.
- [Law 5/2025, BOJA 247 of 24 December 2025](https://www.juntadeandalucia.es/boja/2025/247/1.html),
  additional provision six, says the regional administration will no longer be
  depositary; final provision eight sets entry into force one month after
  publication. The BOJA HTML is an extracted presentation of the disposition;
  its page links the authentic signed PDF, CVE `00330701`.
- [LAU article 36](https://www.boe.es/buscar/act.php?id=BOE-A-1994-26003#a36)
  still establishes the tenant-to-landlord cash security deposit: one month's
  rent for dwelling leases and two for uses other than dwelling leases.
  **Removing the regional deposit obligation does not abolish that security.**
- [AVRA's deposit guide](https://www.juntadeandalucia.es/organismos/avra/areas/fianzas/deposita.html)
  describes the landlord's filing, a one-month filing period, the reference to
  the property and the contract. Read it with the newer legal-break notice,
  not as proof that all new contracts still require public deposit.
- [The administrative file's founding resolution](https://www.juntadeandalucia.es/boja/2014/7/16)
  describes receipt/refund records for **leases and supplies**, including
  financial and personal information. A generic cash-balance or receipt total
  is not a count of residential tenancies.

These sources establish the collection regime and record types, not completeness
of compliance, an observed municipal flow series or a sample of available homes.

## What was actually checked

The [AVRA fianzas index](https://www.juntadeandalucia.es/organismos/avra/areas/fianzas.html)
and [transparency index](https://www.juntadeandalucia.es/organismos/avra/estructura/transparencia.html)
were inspected, alongside targeted searches for statistical results and annual
fianza reports. The public CKAN catalogue endpoint
`https://www.juntadeandalucia.es/datosabiertos/portal/api/3/action/package_search`
returned successful responses with no matches for `fianzas`, `fianza*`,
`arrendamiento` and `alquiler`; a control query `vivienda` returned 24 datasets.
This is a bounded catalogue result, **not proof of global data absence**.

An indexed procedure URL containing `/index.php/servicios/sede/tramites/procedimientos/detalle/426`
returned HTTP 404 when fetched; it was not accepted as a functioning export or
as evidence that the underlying records no longer exist. No authenticated
filing, personal register lookup or information request was performed.

## Required measurement contract

| Distinction | What an extraction must retain | What must not be inferred |
| --- | --- | --- |
| Property versus collecting office | Property municipality's official code and vintage | Office location is not market geography |
| Residential versus other uses | Housing-use categories; commercial/other uses and supplies separate | Every fianza is a dwelling lease |
| Contract date versus filing/payment date | Counts by contract date, plus filing lag/completeness information | Receipts in a month equal leases signed that month |
| New tenancy versus event | New agreements, renewals, adjustments, late regularisations, cancellations and corrections separated | Every registration is a new tenancy or distinct dwelling |
| Agreement versus dwelling | Distinct agreements and, if releasable, internally deduplicated dwelling counts | Tenant turnover adds a dwelling to the rental stock |
| Expiry versus refund | Termination date, refund-request date and refund-payment date separate if available | A refund dates a vacancy or subsequent letting |
| Register coverage versus market coverage | Obligations, exemptions, compliance limits, general/concerted regimes and suppression | Legal obligation ensures exhaustive observation |
| Count versus money | Record counts distinct from deposited/refunded EUR and outstanding balances | Cash divided by typical rent recovers contract counts |
| Pre-reform versus legacy processing | Contract-date cut at 24 January 2026, not a payment-date cut | Lower post-reform public receipts show reduced rental supply |

Late filings of older contracts and returns from the legacy portfolio can
continue after the cut. They cannot stand in for post-reform new-contract
coverage. Missing, suppressed or no-longer-collected cells are not zeros.
Do not subtract refunds from receipts to estimate net available dwellings.

Even a clean historical new-tenancy flow includes turnover in previously rented
homes. It cannot identify mobilisation of electricity-classified vacant homes
without a lawful, explicitly defined longitudinal linkage that this project
does not possess. Nor does a completed tenancy show homes still advertised.

## Draft aggregate information request — not submitted

A feasible initial scope is Sevilla province, property municipality and
contract year 2019–2025, with any contracts dated 1–23 January 2026 kept in a
separate, incomplete-period extract. Prefer annual geography over sparse monthly
cells and respect the publisher's disclosure controls.

> Solicito información estadística agregada, sin datos personales, del registro
> de fianzas de arrendamiento para los inmuebles situados en los municipios de
> la provincia de Sevilla. Si existe una publicación o exportación pública,
> agradecería su enlace y documentación metodológica.
>
> Para los años de contrato 2019–2025, solicito códigos municipales del inmueble,
> categorías de uso residencial/no residencial/suministros, número de nuevos
> contratos diferenciados de renovaciones, modificaciones y regularizaciones,
> y las reglas de deduplicación y cobertura de los regímenes general y concertado.
> Si no es posible identificar nuevos contratos, solicito que se indique qué
> evento administrativo representa exactamente cada recuento disponible.
>
> Agradecería documentación de fechas de contrato frente a presentación/pago,
> retrasos de registro, supresión de celdas, revisiones y cambios de definición.
> Los datos relativos a contratos de enero de 2026 anteriores al cambio legal
> deben identificarse como un periodo parcial, y los movimientos posteriores
> del registro histórico no deben mezclarse con nuevos contratos posteriores
> al 24 de enero de 2026.
>
> No solicito nombres, NIF, direcciones, referencias catastrales, documentos
> contractuales ni identificadores individuales. Si hay recuentos de inmuebles
> únicos ya calculados internamente y divulgables, agradecería su definición,
> sin solicitar los identificadores usados para calcularlos.

No request has been sent. Submission needs explicit human authorisation and
an approved recipient/sender. If no matching aggregates are releasable, retain
the gap rather than using cash balances, a provincial allocation or synthetic
municipal counts. No production source, estimator or explorer value is changed
by this assessment.
