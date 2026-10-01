# ADR-006: Phased market form — on-prem CLI → R1 async API → R2 multi-tenant

## Status

Accepted · 2026-09-24 (user-locked sequencing decision)

## Context

Full SaaS (auth, multi-tenant, billing, review console) before accuracy/data gates maximizes rework risk. Pure forever-CLI delays revenue design. Hardware and corpus favor getting a provenance-correct extractor green first, then a thin API slice.

## Decision

| Phase | Form factor |
|---|---|
| R0 / R0.5 | On-prem **CLI + container** (single tenant, local files) |
| R1 | **Thin async API** + object store + queue + GPU workers + minimal privacy (API keys, encryption at rest, TTL) + review payload |
| R2 | Review **console**, human-correction provenance, multi-tenant RBAC, SLOs |
| R5+ | Template marketplace / alias ops (manifest spec) |

Sequencing lock: **docs + data gates → spike → R0 code → R0.5 → calibration → R1**.

## Consequences

- R0 ships without FastAPI/Postgres — by design, not oversight.  
- `docs/market-roadmap.md` defines R1 exit checklist and backlog specs.  
- Architecture sequences include R1/R2 diagrams now so R0 APIs are not painted into corners (`run_id`, export shapes).

## Alternatives considered

- API-first before kernel: long dark period, no accuracy signal.  
- CLI forever: weak multi-user/ops story for B2B.  
- Jump to multi-tenant: premature (privacy/auth unknowns).
