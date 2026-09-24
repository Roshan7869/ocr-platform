# src/ocr_platform/worker/validation/rules.py

## Role

Deterministic per-field validation rules from `validation_rules.yaml` + field catalog: type checks (integer range, date feasibility, mobile format, allowed enums), requiredness for present values, and pass/fail + reason codes for the acceptance policy. No I/O, no OCR.

## Contracts

- **Invariants:**
  - Rules are data-driven from template package (hash-bound), not hardcoded per field in Python except shared predicates.
  - Examples: age integer 0..120 (else INVALID); resident code in 1..6; mobile digit completeness; impossible dates; `person` field requiredness per catalog nullability.
  - Failure returns typed reasons for `reason_codes` — never silent drop.
  - Validation never mutates raw or normalized candidate inputs.
  - Cross-field/conditional requirements live in `cross_field.py`, not here.
- **Outputs:** `ValidationResult {ok, reasons[], confidence?}` per field/cell.
- **Forbidden:** accepting on validation alone (policy combines with evidence); vocab resolution (delegates).

## Infrastructure

- **Python deps:** pydantic, pyyaml
- **Config/artifacts:** `validation_rules.yaml`, `field_catalog.json` (requiredness, types)
- **Models/external:** none
- **Env vars:** none

## Depends on

- **Calls:** `schemas/decision.py`, `worker/extraction/normalizer.py` (normalized type), `worker/extraction/vocabulary.py`
- **Called by:** `worker/extraction/acceptance_policy.py`, `worker/pipeline.py`

## Tests

- Unit: age -4/200/999 INVALID; 30/6/29 OK
- Unit: resident_status outside 1..6 fails
- Unit: reason codes populated on each failure mode
- Integration: R0 validation rules listed in design Verification Strategy

## Milestone

R0

## Status

SPEC

## Owner

engineering
