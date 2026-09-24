# templates/family_survey_v1/cross_field_rules.yaml

## Role

Declarative cross-field/conditional rules consumed by `worker/validation/cross_field.py`: resident_status → new_address required set; migration_nature applicability; ditto expansion enabled columns; non-inference pairs (sanitation ⫫ housing_type, toilet ⫫ drainage, etc.).

## Contracts

- **Invariants:**
  - Rules are explicit allow-lists of dependencies; absence of rule ⇒ no inference (fail closed to independence).
  - Each rule: id, trigger fields, condition expression (safe declarative form — no arbitrary code eval in YAML), action (require | optional | relevant | forbid_inference), reason_code.
  - Ditto: list of column_ids where DITTO semantic allowed; expansion produces derived decision with provenance op (rule id + versions).
  - Unresolved condition → hard review reason (policy reads outcome).
  - Design §32–33 conditional logic represented here, not in pipeline Python branches.
- **Outputs:** rule list.
- **Forbidden:** embedding raw bboxes; acceptance thresholds.

## Boundary classes

n/a.

## Entity owner

n/a.

## Infrastructure

- **Python deps:** pyyaml
- **Config/artifacts:** hash in template_manifest
- **Models/external:** none
- **Env vars:** none

## Depends on

- **Calls:** none (data)
- **Called by:** `worker/validation/cross_field.py`

## Tests

- Unit: address required codes match design intent; ditto columns list
- Unit: unknown rule id fails load
- Unit: no-inference pairs enforced
- Integration: multi-row ditto fixture exercises rules end-to-end

## Milestone

R0

## Status

SPEC

## Owner

engineering (draft) / survey (business rule confirmation)
