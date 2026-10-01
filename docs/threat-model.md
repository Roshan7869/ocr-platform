# Threat model — ocr-platform (R0)

STRIDE-lite threat model for the R0 CPU pipeline. Grounded in the trust boundaries already defined in `architecture.md §3`; this doc turns that table into named threats, existing controls, and residual gaps. Scope is R0 (single-operator, local, CPU, no network from validation). Multi-tenant / API threats are R1+ and listed as deferred.

**Invariant:** `FINAL_VALUE MUST NEVER EXIST WITHOUT PROVENANCE`
**R0 non-goals (stated):** multi-tenant auth, secrets in image, network calls from validation (`architecture.md:100`).

---

## 1. Assets

| Asset | Sensitivity | Where |
|---|---|---|
| Survey PII (name, mobile, address, resident status) | High — regulated personal data | source PDFs, crops, `result.json` |
| Provenance chain / decisions | High — the integrity product | `provenance.json` |
| Template package (geometry, rules) | Medium — correctness-critical | `templates/family_survey_v1/*` |
| Model artifacts + pins | Medium — supply chain | `models.py`, spike matrix |
| Redaction approver identity | Medium — governance | data-plan (RG-18, **open**) |

---

## 2. Trust boundaries (from `architecture.md §3`)

External PDF → loader → pipeline → export → disk. Template package → runtime. Policy flags → auto-accept. Each row below maps a STRIDE category onto one of these crossings.

---

## 3. Threats (STRIDE-lite)

| ID | Threat | STRIDE | Boundary | Existing control | Residual / gap |
|---|---|---|---|---|---|
| T1 | **Malicious PDF** — parser exploit, zip/decompression bomb, deeply nested objects | Denial / Elevation | PDF → loader | classify step detects `ENCRYPTED_PDF`/`CORRUPT_PDF`/`EMPTY_DOCUMENT` → errored (`reason-codes.md §2`); no shell-out | **Gap:** no explicit resource cap (max pages / max decompressed size / render timeout). → RG-track; enforce in `pipeline.py` |
| T2 | **PII leakage via logs** | Info disclosure | pipeline → disk | logs PII-free by construction; test asserts no fixture PII in log lines | ADR-007 / `observability.md` — enforced |
| T3 | **PII leakage via crops/artifacts** | Info disclosure | export → disk | R0 local paths only; crops are governed artifacts (`data-plan` lifecycle) | R1 encryption-at-rest deferred; crop retention policy owned by data-plan |
| T4 | **Provenance forgery** — a `FINAL_VALUE` without/with fabricated evidence | Tampering / Repudiation | pipeline → export | validator zero-tolerance; value cannot serialize without complete chain (G1) | enforced; strongest control in the system |
| T5 | **Template tampering** — altered geometry/rules change extraction silently | Tampering | template → runtime | template hash root; approval-scope gate (`synthetic_baseline_approved` vs `production_approved`); unknown/deprecated rejected | **Gap:** immutable-hash + activation/rollback is R5 (RG-24); R0 relies on hash verify only |
| T6 | **Unclassified-fixture bypass** — raw PII PDF processed as if approved | Elevation / Info disclosure | loader | raw path requires explicit `--allow-unclassified`; smoke-vs-gold labels enforced; production never uses unclassified loader without explicit allow | flag exists; **operational risk** if `--allow-unclassified` misused — audit via run artifacts |
| T7 | **Model supply-chain** — swapped/poisoned model weights | Tampering | model artifacts | spike records checksum + license per pin (C5/C7); no unpinned "latest" | enforced at pin-time; **gap:** no re-verify of checksum at container build unless RACE strategy bakes+verifies (RG-04) |
| T8 | **Silent auto-accept of wrong values** | Repudiation (trust) | policy flags | auto-accept disabled in R0 (G3); flip needs calibration + sign-off (ADR-005) | enforced |
| T9 | **Coordinate confusion** → value mapped to wrong field | Tampering (integrity) | render/coords | single coordinate SoT; cross-system op without conversion rejected (G5) | enforced |
| T10 | **Config drift** — silent runtime override changes results without new identity | Repudiation | config → pipeline | any config change = fingerprint bump = new `run_id` (G4); loader rejects unknown keys | enforced |

---

## 4. Priority residual gaps (R0 actionable)

| Gap | Threat | Recommendation | Owner |
|---|---|---|---|
| **PDF resource caps** | T1 | Add max-pages, max-decompressed-size, per-render timeout to `pipeline.py`; emit `CORRUPT_PDF`/errored on breach | pipeline spec |
| **Model checksum re-verify at build** | T7 | Fold checksum verify into RACE strategy decision (RG-04) so baked images re-verify | `Dockerfile` + spike |
| **`--allow-unclassified` audit** | T6 | Ensure every unclassified run is reason-coded + visible in run summary (observability) | observability |

These are documentation-level recommendations; T1 in particular should be tracked as a hardening item before any non-fixture PDF is processed.

---

## 5. Deferred (R1+)

| Threat | Milestone | Note |
|---|---|---|
| Multi-tenant authz / isolation | R2 | no auth in R0 |
| API abuse / rate-limit / DoS at ingress | R1 | no API in R0 |
| Encryption-at-rest for PII artifacts | R1 | `architecture.md:89` |
| Secrets management | R1+ | none in R0 image |
| Tenant data cross-contamination | R2 | fair-share queue (RG-23) |

---

## Related documents

- Trust boundaries: `docs/architecture.md` §3
- Log PII rule: `docs/observability.md`, `docs/adr/adr-007-observability-provenance-audit.md`
- Data governance / redaction: `docs/data-plan.md`
- Model pinning: `docs/files/scripts/run_spike.py.md`, `docs/files/src/ocr_platform/worker/paddle/models.py.md`
- Open items: `docs/research-gaps.md`
- Codes: `docs/reason-codes.md`
