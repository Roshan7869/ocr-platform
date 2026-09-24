# configs/acceptance_policy_v1.yaml

## Role

Versioned AcceptancePolicy-v1 artifact: thresholds, hard-review reason list, precedence for `primary_reason`, which checks are enabled in R0 (OCR/native auto-accept gates off until spike), overlap_ratio, duplicate pixel tolerance, calibration-disabled numeric/category/religion thresholds. Loaded by `acceptance_policy.py`.

## Contracts

- **Invariants:**
  - `policy_version: AcceptancePolicy-v1` immutable once used in a run; changes bump version (fingerprint).
  - Required rules from design AcceptancePolicy-v1 all present (present/absent/unreadable/NA evidence rules, overlap 0.80, native/OCR compare, duplicates, unknown vocab, disabled calibrated thresholds, accepted_by fields).
  - Hard review reasons: full 14-item list (OCR confidence, multi candidates, boundary cross/touch/overlap, unstable OCR, unknown code, invalid numeric, conflicting marks, multi single-select, unknown symbol, unresolved ditto, cross-field conflict, wrong template).
  - R0: `ocr_auto_accept_enabled: false`, `native_auto_accept_enabled: false` until spike sign-off flips them (config change + fingerprint).
  - Conservative defaults favor review.
  - Per-field trigger applicability lives in template `review_triggers.yaml` — this file owns **thresholds and global gates**, not per-field lists (avoid fork).
- **Outputs:** typed policy config.
- **Forbidden:** embedding template geometry; composite final_confidence formula.

## Infrastructure

- **Python deps:** pyyaml
- **Config/artifacts:** this file; hash into configuration_fingerprint + decision.acceptance_policy_version
- **Models/external:** none
- **Env vars:** none

## Depends on

- **Calls:** none (leaf)
- **Called by:** `worker/extraction/acceptance_policy.py`, fingerprint in pipeline

## Tests

- Unit: schema validates; required rule keys present
- Unit: version string flows to decisions
- Unit: disabling OCR auto-accept forces review on OCR-only present fields in R0 mode
- Integration: policy version appears in every accepted decision export

## Milestone

R0

## Status

SPEC

## Owner

engineering
