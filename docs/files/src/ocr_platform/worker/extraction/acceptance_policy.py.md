# src/ocr_platform/worker/extraction/acceptance_policy.py

## Role

Versioned `AcceptancePolicy-v1` evaluator: given evidence set, validation results, boundary signals, and vocabulary outcomes, produce `disposition` + `reason_codes` + `accepted_by`/`acceptance_policy_version`. Implements FAMILY_SURVEY_V1 acceptance contract as policy rules — not ad-hoc ladders inside boundaries/pipeline.

## Contracts

- **Invariants (design AcceptancePolicy-v1 + §36/§44 reconciliation):**
  - `present` requires ≥1 text (or valid) evidence node **and** successful field validation.
  - `absent` requires `RegionEvidence` empty/blank region.
  - `unreadable` requires RegionEvidence + reason; never accepted.
  - `not_applicable` requires applicability rule + RegionEvidence (policy-only basis insufficient in R0).
  - Box assignment threshold `overlap_ratio >= 0.80` (provisional; benchmarked before production).
  - Native/OCR comparison: normalized exact equality after Unicode normalize + whitespace collapse + punctuation-preserving compare; disagreement → review; OCR scores not used for that decision.
  - Duplicate detections: identical text + identical page-space box within pixel tolerance may collapse only via recorded policy op; conflicting → review.
  - OCR + native both disabled for auto-acceptance in R0 until **spike go AND calibration evidence** (design L282 + ADR-005) — encode as explicit gates.
  - Unknown vocabulary, failed validation, unsupported model outputs, missing provenance → review.
  - Numeric/category/religion thresholds disabled until calibrated; conservative defaults favor review.
  - Every accepted decision: `accepted_by=policy`, `acceptance_policy_version`.
  - Auto-accept predicate: `OCR_VALID ∧ BOUNDARY_VALID ∧ VOCABULARY_VALID ∧ VALIDATION_PASS ∧ no_hard_review_reason ∧ no_handwriting_suspected` — otherwise `REVIEW_REQUIRED`. No third “guess” branch.
  - Hard review reasons (14-item list: low OCR, multi candidates, boundary cross/touch/overlap, unstable OCR, unknown code, invalid numeric, conflicting marks, multi single-select, unknown symbol, unresolved ditto, cross-field conflict, wrong template) evaluated here from inputs; **handwriting_suspected** forces review on text fields (ADR-004).
  - Boundary ladder from §36 implemented as policy rules consuming signals from `boundaries.py`, not reimplemented there.
  - No composite calibrated `final_confidence`.
  - Flag flip procedure: see `docs/accuracy-plan.md` §4 (policy version bump + calibration report path).
- **Outputs:** updated `FieldDecision` disposition fields (still via decision schema enums only).
- **Forbidden:** inventing values; promoting `AUTO_ACCEPTED` to enum; calling Laya (R4 flag only, default off).

## Infrastructure

- **Python deps:** pydantic
- **Config/artifacts:** `configs/acceptance_policy_v1.yaml` (thresholds, precedence), `templates/.../review_triggers.yaml` (per-field trigger applicability)
- **Models/external:** none
- **Env vars:** none

## Depends on

- **Calls:** `schemas/decision.py`, `schemas/evidence.py`, `worker/extraction/vocabulary.py`, `worker/validation/rules.py`, `worker/validation/cross_field.py`
- **Called by:** `worker/pipeline.py`

## Tests

- Unit: each required rule true/false table-driven (including 0.80 boundary)
- Unit: hard review reasons force review even if other checks pass
- Unit: unreadable/absent/NA evidence requirements
- Unit: OCR/native disabled gate in R0
- Unit: handwriting_suspected forces review on text fields
- Integration: R0 identity-transform acceptance paths; review-candidate rate metric on smoke fixtures
- Benchmark gate shape: provenance completeness 100% on accepted; calibration report required before flag flip (ADR-005)

## Milestone

R0

## Status

SPEC

## Owner

engineering
