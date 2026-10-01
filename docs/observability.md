# Observability — logging, metrics, audit (R0)

The R0 operational-visibility contract. Decision rationale is ADR-007: **the provenance graph is the audit trail, and runtime logs are PII-free by construction.** This doc enumerates the concrete log events, metrics, retention, and access so the R0 exit gate has operational visibility and a stated PII-safety guarantee.

**Invariant:** `FINAL_VALUE MUST NEVER EXIST WITHOUT PROVENANCE`
**Template:** `FAMILY_SURVEY_V1` · **Milestones:** R0 → R0.5 → R1 → R2 (see `docs/market-roadmap.md`)

---

## 1. The PII rule (hard invariant)

Logs and metrics **never** contain raw field values. Enforced, not advised (`data-plan.md:68`, ADR-007).

| Allowed in logs | Forbidden in logs |
|---|---|
| `run_id`, `document_content_hash`, `configuration_fingerprint` | OCR text / recognized values |
| `field_id`, `region_id`, `page_index`, `row_key` | names, mobile, address, any survey answer |
| reason codes (`docs/reason-codes.md`), dispositions, counts | crop bytes / image content |
| model pin ids, policy version, timings | file paths that embed PII (use ids) |

A test asserts no emitted log line contains a known fixture PII value (fail-closed) — see `docs/testing-plan.md`.

---

## 2. Audit: the provenance chain

There is **no separate audit-log store in R0.** "Why was this value accepted / sent to review?" is answered by walking the run artifacts:

```text
value → source_set (EvidenceSet) → evidence nodes (OcrObservation / RegionEvidence / …)
      → decision (disposition + reason_codes + primary_reason + accepted_by)
      → configuration_fingerprint (runtime.yaml + policy version + template hashes + model pins)
      → run_id
```

Every accepted value is reconstructable from `result.json` + `provenance.json` alone. The provenance validator (`worker/provenance/validator.py`) is the zero-tolerance gate; a hard fail demotes to review/exception (`architecture.md:80`) and is logged as a reason-coded event (§3).

---

## 3. Log event catalog (R0)

Structured events (one JSON object per line). `level` ∈ `INFO` | `WARN` | `ERROR`. All carry `run_id`.

| Event | Level | Key fields | Emitted by |
|---|---|---|---|
| `run.start` | INFO | `run_id`, `document_content_hash`, `template_hash`, `policy_version`, `configuration_fingerprint` | `scripts/extract.py` |
| `run.classify` | INFO | `page_index`, `page_class` (scanned/native/mixed/encrypted/corrupt/empty) | `schemas/job.py` path |
| `run.errored` | ERROR | `reason_code` (`ENCRYPTED_PDF`/`CORRUPT_PDF`/`EMPTY_DOCUMENT`) | `worker/pipeline.py` |
| `page.registered` | INFO | `page_index`, `registration_mode`, `residual` (R0.5) | `worker/template/registration.py` |
| `page.review` | WARN | `page_index`, `reason_code` (`PAGE_SET_MISMATCH`/`REGISTRATION_RESIDUAL_HIGH`) | `worker/state_machine.py` |
| `field.decision` | INFO | `field_id`, `disposition`, `primary_reason`, `accepted_by` | `worker/extraction/acceptance_policy.py` |
| `field.review` | WARN | `field_id`, `reason_codes[]` | acceptance policy |
| `provenance.fail` | ERROR | `field_id`\|`page_index`, `validator_reason` | `worker/provenance/validator.py` |
| `run.complete` | INFO | counts: `accepted`, `review`, `errored`; wall time | `scripts/extract.py` |

> Values are never fields on these events — only ids, codes, counts, timings. Exit codes map per `docs/reason-codes.md §1`.

---

## 4. Metric catalog (R0 — aggregate only)

Emitted at `run.complete` (and to stdout summary by the CLI). No per-value metrics.

| Metric | Type | Meaning |
|---|---|---|
| `docs_processed_total` | counter | documents in the run |
| `pages_rendered_total` | counter | pages rasterized |
| `fields_evaluated_total` | counter | candidate field evals (~344/doc, `accuracy-plan.md:14`) |
| `disposition_total{disposition}` | counter | accepted / review / rejected / errored |
| `review_reason_total{reason_code}` | counter | review drivers (feeds accuracy tuning) |
| `render_ms` / `ocr_ms` / `run_ms` | histogram | stage latencies (feeds `docs/capacity.md`) |
| `provenance_fail_total` | counter | must be 0 on accepted values |

---

## 5. Retention & access (R0)

| Aspect | R0 posture |
|---|---|
| Log sink | stdout / local file under `--out`; no remote shipping (no network from validation, `architecture.md:100`) |
| Log retention | tied to the run artifact lifecycle; PII-free so no special handling |
| Provenance/artifact retention | governed by `docs/data-plan.md` object lifecycle (crops are the PII-bearing artifacts, not logs) |
| Access | local operator only in R0; multi-tenant access controls are R2 (`architecture.md:147`) |
| Secrets | none in image or logs (`architecture.md:100`) |

---

## 6. Milestone evolution

| Milestone | Change |
|---|---|
| R0 | This contract: stdout/file logs, aggregate metrics, provenance = audit |
| R1 | Structured logs → collector; job store records run index; **same PII rule** |
| R2 | Multi-tenant access controls + retention SLOs; human-correction events (`DecisionRevision`) added to the audit chain |

---

## Related documents

- Decision: `docs/adr/adr-007-observability-provenance-audit.md`
- Codes vocabulary: `docs/reason-codes.md`
- Provenance model: `docs/architecture.md` §4, `worker/provenance/*` specs
- PII / data governance: `docs/data-plan.md`
- Latency metrics consumer: `docs/capacity.md`
- Test enforcement: `docs/testing-plan.md`
- Glossary: `docs/glossary.md`
