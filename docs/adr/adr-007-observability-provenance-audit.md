# ADR-007: Provenance graph is the R0 audit trail; logs are PII-free by construction

## Status

Accepted · 2026-09-27

## Context

R0 has no observability contract. The trust-boundary table (`architecture.md:89`) and the PII rule ("never log raw PII", `data-plan.md:68`) exist, but nothing defines *what* the system logs, *what* it emits as metrics, or *how* an accepted value is audited after the fact. The platform already produces a complete, content-addressed provenance chain for every decision (the `FINAL_VALUE` invariant). Two competing postures were possible: (a) build a conventional structured-logging + audit-log stack, or (b) treat the provenance chain itself as the audit trail and keep runtime logs deliberately thin and PII-free.

The corpus is PII-heavy (names, mobile, address). Any log line that echoes a field value is a data-governance liability, and a second "audit log" that duplicates decisions would fork the source of truth against the provenance graph.

## Decision

1. **The provenance graph is the audit trail.** Reconstruction of "why was this value accepted?" is answered by the `EvidenceSet` → decision → `configuration_fingerprint` chain in the run artifacts — not by log scraping. No separate audit-log store in R0.
2. **Runtime logs are PII-free by construction.** Logs carry identifiers (`run_id`, `document_content_hash`, field_id, region_id, reason codes) and counts — **never** raw OCR text, field values, or crop contents. This is an invariant, tested, not a guideline.
3. **Reason codes are the log/metric vocabulary.** Error and review events reference `docs/reason-codes.md` tokens; no free-text error strings that could leak values.
4. **Metrics are aggregate only** (counts, latencies, disposition rates) — never per-value.
5. Full contract (event catalog, metric catalog, retention, access) lives in `docs/observability.md`.

## Consequences

- Cheap R0 observability: no logging infra, no audit DB; the artifacts on disk already are the audit record.
- A hard test asserts no log line contains a known fixture PII value (fail-closed).
- Debugging a specific value means opening its provenance JSON, not grepping logs — acceptable given the provenance completeness gate.
- R1 persistence/API (`market-roadmap.md`) inherits the same rule: structured logs stay PII-free; the provenance record remains the audit SoT.

## Alternatives considered

- **Conventional audit-log store in R0:** forks the source of truth against provenance; rejected until R1 when a job store exists.
- **Verbose value-level logging for debuggability:** direct PII-leak risk on a name/mobile/address corpus; rejected.
- **No observability contract (status quo):** leaves the R0 exit gate ("pytest green") with no operational visibility and no stated PII-safety for logs; rejected — this ADR closes that gap.
