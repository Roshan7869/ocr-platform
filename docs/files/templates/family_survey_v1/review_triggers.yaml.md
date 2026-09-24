# templates/family_survey_v1/review_triggers.yaml

## Role

Per-field applicability of review triggers (which of the global hard-review reasons can fire for which field_id/field class). Thresholds and the global reason list stay in `configs/acceptance_policy_v1.yaml` — this file only scopes applicability so the policy is not forked.

## Contracts

- **Invariants:**
  - Structure: `field_id | field_class -> set of trigger ids` where trigger ids ⊆ policy hard-review reason registry.
  - Defaults: conservative (unknown class → all applicable triggers on).
  - Boundary triggers apply to all FIELD/checkbox text regions; vocab triggers only to coded fields; ditto triggers only to ditto-enabled columns from cross_field_rules.
  - Explicit `enabled: false` for a trigger on a field requires survey/engineering note field `exception_justification`.
  - Does **not** redefine 0.80 overlap or OCR score cutoffs.
- **Outputs:** applicability map merged by policy evaluator.
- **Forbidden:** thresholds; new reason codes not in decision registry; AUTO_ACCEPTED shortcuts.

## Boundary classes

n/a (references classes only for defaults grouping).

## Entity owner

n/a.

## Infrastructure

- **Python deps:** pyyaml
- **Config/artifacts:** hash in template_manifest; ids match acceptance_policy_v1.yaml
- **Models/external:** none
- **Env vars:** none

## Depends on

- **Calls:** none (data)
- **Called by:** `worker/extraction/acceptance_policy.py`

## Tests

- Unit: every trigger id known to policy registry
- Unit: default-all-on for unknown class
- Unit: disabled trigger requires justification key
- Integration: policy evaluation respects per-field scoping on mixed fixture

## Milestone

R0

## Status

SPEC

## Owner

engineering
