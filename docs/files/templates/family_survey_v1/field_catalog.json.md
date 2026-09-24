# templates/family_survey_v1/field_catalog.json

## Role

Machine-readable `family-survey-v1.field-catalog.json`: every scalar field and table-backed cell with field_id, entity owner, cardinality, source page(s), template region reference, JSON type, nullability, allowed value states, allowed dispositions, vocabulary version, normalization-rule version, validation rules, linkage requirements — plus one complete expected-output example each for Household, Member, EducationRecord.

## Contracts

- **Invariants:**
  - **Source deliverable from survey owner** — engineering drafts from WARD-42 PDFs + FAMILY_SURVEY_V1 spec only as a draft until survey approves (design L42).
  - Entity-qualified IDs only: `document.*` (municipality, zone, ward, survey_date, enumerator_*), `household.*` (head, services/checkboxes, solid_waste, electricity, alternative_energy, sanitation, drinking_water, housing_type, housing_ownership_status, scheme_beneficiary, loan_*, banking, mobile_network, broadband, cctv, family_structure), `member.*` (name, gender, age, caste, religion, disability_lt_40, disability_ge_40, housing_type, housing_status, occupation, monthly_income, vehicle, relation_to_head, other_house_elsewhere, resident_status_code, new_address, migration_nature), `education.*` (highest_qualification / education column → EducationRecord entity).
  - Dedupe: single set for head name/mobile (no parallel `head_*` and `household_head_*`).
  - Checkbox groups expand to option-level entries (e.g. `household.sanitation.sewer_connection`, `household.scheme_beneficiary.option_001`…).
  - Education records link via explicit `member_key`/`row_key` requirements — not cross-page position inference.
  - Expected-output examples validate against export schema.
- **Outputs:** catalog JSON consumed by boundaries, validation_rules, export, tests.
- **Forbidden:** inferring full catalog from four example IDs alone without survey sign-off; entity-ambiguous bare IDs in final approved catalog.

## Boundary classes

Indirect: each entry’s `template region reference` must resolve to a typed boundary in page_1/page_2 YAML.

## Entity owner

Per-entry (document | household | member | education) — required field.

## Infrastructure

- **Python deps:** stdlib json
- **Config/artifacts:** this file; hash in template_manifest
- **Models/external:** none
- **Env vars:** none

## Depends on

- **Calls:** none (leaf data); referenced by validation, boundaries, export, cross_field
- **Called by:** `worker/template/manifest.py`, `worker/validation/rules.py`, `export/json_export.py`, `scripts/annotate_template.py`

## Tests

- Unit: schema validation (required keys per design L42)
- Unit: every field_id prefix matches entity_owner
- Unit: examples parse as Household/Member/EducationRecord
- Integration: no pipeline field decisions for IDs absent from catalog (unknown field → review/exception)
- Integration: survey approval flag/status field present before production_approved

## Milestone

R0

## Status

SPEC

## Owner

survey (primary) / engineering (schema enforcement + draft assist from 95–99.pdf)
