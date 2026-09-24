# src/ocr_platform/worker/extraction/vocabulary.py

## Role

Versioned code/word vocabularies and raw→code→canonical mapping for religion, gender, caste, occupation, relation, education, resident status, etc. Only mappings present in `vocabularies.yaml` (hash-bound in template manifest) are applied.

## Contracts

- **Invariants:**
  - Religion: `H|h → H → Hindu`, `M|m → M → Muslim` only; `J`, `C`, `R` (and any other) → `value_state=unknown` + `UNKNOWN_VOCABULARY_CODE` until codebook says otherwise (design + FAMILY_SURVEY_V1 §22).
  - Gender: `M|F` with case fold; `X|O|?` → unknown → human review.
  - Caste: store `caste_raw` / `caste_code` / `caste_canonical`; `OBC|oBc|obc` → one code after vocabulary validation; unknown → UNKNOWN_VALUE.
  - Education: known vocabulary → normalized; unknown abbreviation → review; never auto-promote unclear abbreviation to higher category.
  - Occupation: exact phrase / known abbreviation → normalized; uncertain → review (Laya only at R4); new word → UNKNOWN_VALUE.
  - Resident status: integer `allowed: [1,2,3,4,5,6]`; outside → INVALID/REVIEW.
  - Three-layer storage for coded fields (`*_raw`, `*_code`, `*_canonical`) where applicable.
  - Gender `M` and religion `M` are field-scoped — no cross-field collision.
- **Outputs:** `resolve(field_id, raw) -> (code, canonical|None, reasons[])`.
- **Forbidden:** semantic guessing beyond vocabulary; auto-accepting unknown codes.

## Infrastructure

- **Python deps:** pydantic, pyyaml
- **Config/artifacts:** `templates/family_survey_v1/vocabularies.yaml` (+ religion/gender/caste tables inside)
- **Models/external:** none
- **Env vars:** none

## Depends on

- **Calls:** `schemas/decision.py`, `worker/extraction/normalizer.py`
- **Called by:** `worker/pipeline.py`, `worker/extraction/acceptance_policy.py`, `worker/validation/rules.py`

## Tests

- Unit: gold cases H/h/M/m/R/J/C; gender; OBC casefold; resident 1–6 boundary
- Unit: unknown code never returns canonical
- Integration: R0 code vocabulary behavior (design unit list); zero unknown-code misacceptances shape

## Milestone

R0

## Status

SPEC

## Owner

engineering (code) / survey (codebook approval for any new code)
