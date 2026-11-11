# A1ERP Health TPA

Health insurance third party administration (TPA) for ERPNext, built for the Iraqi market.

The app is independent of `a1erp_insurance`: it has its own accounting engine, notification engine and defaults, and runs on a site that does not have the insurer app.

## Contents

- Members, families, plans, benefits, exclusions and medical cards with QR verification
- Medical provider networks, contracts, tariffs and the medical code library
- Pre-authorization and claim adjudication with a configurable calculation order and status workflow
- Provider settlements, TPA administration fee invoices and self-funded health funds
- Fraud, waste and abuse rule engine with alerts, watchlists and medical case management
- Service desk with SLA, role desks, reports, dashboards and the `/tpa` portal for providers, clients and members

## Install

```
bench get-app <repository-url>
bench --site <site> install-app a1erp_tpa
```
