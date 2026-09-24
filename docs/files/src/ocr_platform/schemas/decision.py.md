# src/ocr_platform/schemas/decision.py

## Role

`FieldDecision` / cell decision models and the orthogonal status vocabulary: `scope`, `value_state`, `disposition`, multi-label `reason_codes`, `primary_reason` (documented precedence), `accepted_by`, `acceptance_policy_version`. Single source of truth for how FAMILY_SURVEY_V1 field-state labels map onto storage.

## Contracts

- **Invariants:**
  - Do not collapse into one overloaded status enum across document/page/field/cell.
  - `value_state`: `present` | `absent` | `unknown` | `unreadable` | `not_applicable`.
  - `disposition`: `accepted` | `review` | `rejected` | `errored`.
  - `AUTO_ACCEPTED` / `NORMALIZED_ACCEPTED` are **not** enum values — both are `accepted` distinguished by `accepted_by` + `acceptance_policy_version`.
  - `BOUNDARY_EXPAND` is a proposal action, never a field disposition.
  - Final value not writable unless `source_set` resolves through a valid `EvidenceSet` (design: FINAL_VALUE rule).
  - Missing ≠ `""`; `absent`/`not_applicable`/`unknown`/`unreadable` still require region + decision.
  - Conflicts: multiple `source_set` entries + reason codes; corrections create `DecisionRevision`, never overwrite.
- **Field-state mapping (FAMILY_SURVEY_V1 labels → storage):**

  | Label | Stored as |
  |---|---|
  | CLEAR, NORMALIZED | `value_state=present`, `disposition=accepted`, `accepted_by=policy` |
  | AMBIGUOUS, INVALID, OUT_OF_BOUNDARY | `disposition=review` + reason codes |
  | UNREADABLE | `value_state=unreadable` + RegionEvidence; never accepted |
  | MISSING | `value_state=absent` + RegionEvidence |
  | UNKNOWN_VALUE | `value_state=unknown` + `UNKNOWN_VOCABULARY_CODE` |

- **Outputs:** `FieldDecision`, enums, reason-code registry, `DecisionRevision` stub (R2 fills human correction).
- **Forbidden:** inventing values without evidence links; storing composite `final_confidence` as calibrated probability.

## Infrastructure

- **Python deps:** pydantic>=2.7
- **Config/artifacts:** reason-code list aligned with `configs/acceptance_policy_v1.yaml` + `templates/.../review_triggers.yaml`
- **Models/external:** none
- **Env vars:** none

## Depends on

- **Calls:** `schemas/evidence.py` (`source_set` / EvidenceSet refs)
- **Called by:** `worker/extraction/acceptance_policy.py`, `worker/validation/rules.py`, `worker/validation/cross_field.py`, `export/*`, `worker/provenance/validator.py`

## Tests

- Unit: enum exhaustiveness; AUTO_ACCEPTED rejected as disposition value
- Unit: present-without-evidence construction fails
- Unit: primary_reason precedence over multi reason_codes
- Integration: R0 schema validation for every pipeline output
- Integration: religion unknown code → unknown + UNKNOWN_VOCABULARY_CODE (not accepted)

## Milestone

R0

## Status

SPEC

## Owner

engineering
