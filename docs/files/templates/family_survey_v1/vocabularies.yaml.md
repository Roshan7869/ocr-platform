# templates/family_survey_v1/vocabularies.yaml

## Role

All controlled vocabularies and codebooks: religion (H/M + variants), gender (M/F), caste (OBC…), education codes, occupation phrases/abbreviations, relation-to-head, resident status 1–6 labels, family structure options, housing type/ownership option lists, power-cut acceptable numerics/units, income shorthand rules pointer, symbol/mark legend (tick/cross/ditto/blank semantics as data).

## Contracts

- **Invariants:**
  - Religion approved mapping only H→Hindu, M→Muslim with case variants listed; J/C/R and others **absent** from mapping ⇒ vocabulary.py yields unknown (design §22).
  - Gender M/F only; other codes listed under `unknown_pending` not `map`.
  - Resident status `allowed: [1,2,3,4,5,6]` with label text from printed legend.
  - Each vocabulary: `vocabulary_version` string (goes to field catalog + decision).
  - Variants lists are exhaustive for casefold/spacing; no fuzzy edit-distance maps in R0.
  - Ditto/blank/tick symbols documented with semantic meaning for marks.py + cross_field (blank≠NO unless form rule `blank_means_no: true` per field).
  - Multi-select option enums for solid_waste, alternative_energy, sanitation, drinking_water, housing, schemes, loan source/purpose, banking, mobile network quality, broadband, cctv — option keys stable for export.
- **Outputs:** versioned vocab tables.
- **Forbidden:** semantic expansions beyond codebook; learning updates (R5 proposals only).

## Boundary classes

n/a (values); legend geometry lives in page YAML — this file is semantics only.

## Entity owner

n/a (shared); applied per field.

## Infrastructure

- **Python deps:** pyyaml
- **Config/artifacts:** hash in template_manifest; versions into field_catalog
- **Models/external:** none
- **Env vars:** none

## Depends on

- **Calls:** none (data)
- **Called by:** `worker/extraction/vocabulary.py`, `worker/paddle/marks.py`, validation_rules

## Tests

- Unit: H/h/M/m/R/J/C gold cases; gender; resident labels 1–6
- Unit: unknown_pending never maps
- Unit: blank_means_no default false
- Integration: zero unknown-code misacceptance test shape
- Integration: vocabulary_version appears on coded decisions

## Milestone

R0

## Status

SPEC

## Owner

survey (codebook SoT) / engineering (wiring)
