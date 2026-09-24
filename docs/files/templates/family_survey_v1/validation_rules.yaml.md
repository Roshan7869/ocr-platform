# templates/family_survey_v1/validation_rules.yaml

## Role

Per-field deterministic validation predicates referenced by `worker/validation/rules.py`: age range, mobile format, date feasibility, allowed enum ⇒ vocabulary version, requiredness overrides beyond catalog nullability, units for power_cut, income non-negative, etc. Data only — shared predicates implemented in Python.

## Contracts

- **Invariants:**
  - Rules reference field_id + vocabulary/normalization versions; no hardcoded thresholds that belong in AcceptancePolicy (review vs accept cutoffs stay there).
  - Failure reason codes enumerated and stable (align with decision reason registry).
  - Conditional requiredness for new_address etc. lives in `cross_field_rules.yaml`, not duplicated here (cross_field may call these for format checks when present).
  - Every rule has a test vector in unit tests (design Verification).
- **Outputs:** rule list YAML.
- **Forbidden:** network/DB lookups (e.g. municipality master lookup is R0 review-if-not-in-list when list provided; master list file if any is a fixture artifact not a live API).

## Boundary classes

n/a.

## Entity owner

n/a (keys match catalog).

## Infrastructure

- **Python deps:** pyyaml
- **Config/artifacts:** hash in template_manifest; catalog nullability
- **Models/external:** none
- **Env vars:** none

## Depends on

- **Calls:** none (data)
- **Called by:** `worker/validation/rules.py`

## Tests

- Unit: rule schema + sample pass/fail vectors per rule
- Unit: reason codes unique/stable
- Integration: validation outcomes feed policy correctly on fixtures

## Milestone

R0

## Status

SPEC

## Owner

engineering (draft) / survey (rule confirmation)
