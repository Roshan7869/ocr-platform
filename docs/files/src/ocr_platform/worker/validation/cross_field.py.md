# src/ocr_platform/worker/validation/cross_field.py

## Role

Conditional and relational field rules: `resident_status_code → new_address required?`, `resident_status → migration_nature relevance`, ditto expansion with provenance operation records, and hard review on unresolved cross-field conflict. Owns relationships the design puts outside single-field validation.

## Contracts

- **Invariants:**
  - `if resident_status_code_requires_new_address(code): new_address REQUIRED else blank allowed` (design §32).
  - `if resident_status indicates migration: migration_nature relevant; else may be EMPTY` (§33).
  - Ditto: store raw mark + `semantic_type=DITTO` + `reference_row`; expanded value is a **derived** decision with operation ID, input hash (previous row evidence), output hash, rule version, template version — never overwrite raw `"` with `OBC`.
  - Unresolved ditto or cross-field conflict → hard review reason.
  - Never infer housing_type from unrelated household question when cell blank (§25); independence rules enforced as “no inference edges” checks.
  - Cross-field failure does not fabricate evidence.
- **Outputs:** field/cell adjustments + derived decision metadata + conflict reasons.
- **Forbidden:** silently filling blanks from other fields without explicit rule + provenance op.

## Infrastructure

- **Python deps:** pydantic, pyyaml
- **Config/artifacts:** `cross_field_rules.yaml`
- **Models/external:** none
- **Env vars:** none

## Depends on

- **Calls:** `schemas/decision.py`, `schemas/evidence.py`, `schemas/provenance.py`, `worker/validation/rules.py`
- **Called by:** `worker/extraction/acceptance_policy.py`, `worker/pipeline.py`

## Tests

- Unit: address required only for selected codes
- Unit: ditto expansion preserves raw + records op hashes
- Unit: unresolved ditto → review
- Unit: no cross-inference sanitation↔housing
- Integration: multi-member fixture with ditto column

## Milestone

R0

## Status

SPEC

## Owner

engineering
