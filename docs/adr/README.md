# ADR index

| ADR | Title | Status |
|---|---|---|
| [001](adr-001-pdf-rasterizer.md) | PDF rasterizer primary = pypdfium2 | Accepted |
| [002](adr-002-registration-strategy.md) | Identity + normalize (R0); affine (R0.5) | Accepted |
| [003](adr-003-cloud-gpu-workers.md) | Cloud GPU production OCR | Accepted |
| [004](adr-004-handwriting-posture.md) | Handwriting review-only until dedicated path | Accepted |
| [005](adr-005-fail-closed-calibration.md) | Fail-closed + calibration before auto-accept | Accepted |
| [006](adr-006-phased-market-form.md) | Phased market: CLI → API → multi-tenant | Accepted |
| [007](adr-007-observability-provenance-audit.md) | Provenance graph is the audit trail; logs PII-free | Accepted |

Supersedes: historical “registration = R3 only” for milestone ordering (see ADR-002).  
Related: `docs/architecture.md`, `docs/accuracy-plan.md`, `docs/market-roadmap.md`, `docs/capacity.md`, `docs/observability.md`, `docs/threat-model.md`.
