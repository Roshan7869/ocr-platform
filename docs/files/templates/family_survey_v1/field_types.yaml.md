# templates/family_survey_v1/field_types.yaml

## Role

Data type + normalization profile binding per field_id: `devanagari_text` | `name` | `integer` | `date` | `mobile` | `coded_text` | `checkbox` | `checkbox_group` | `numeric_decimal` | `income_shorthand` | `address_text` | … Drives which normalizer profile and validation bundle apply.

## Contracts

- **Invariants:**
  - Zone/ward_no/survey_date/mobile/age/income **never** share the NAME profile (design §3 boundary rule: NAME→Devanagari recognizer profile, INTEGER→numeric, DATE→date parser, MOBILE→digit parser).
  - Checkbox types require boundary_class CHECKBOX_* in page YAML (consistency check).
  - Every field_catalog entry has a type entry here (1:1 or default from catalog `JSON type` + explicit override).
  - Types are structural — they do not embed vocabularies (those in vocabularies.yaml) or thresholds (acceptance_policy).
- **Outputs:** map field_id → type + profile id + optional unit (e.g. power_cut hours/day).
- **Forbidden:** embedding allowed value lists for codes; acceptance booleans.

## Boundary classes

Types annotate FIELD vs CHECKBOX_* usage (checkbox types only on checkbox regions).

## Entity owner

n/a (types); keys must match catalog field_ids.

## Infrastructure

- **Python deps:** pyyaml
- **Config/artifacts:** hash in template_manifest
- **Models/external:** none
- **Env vars:** none

## Depends on

- **Calls:** none (data)
- **Called by:** normalizer, rules, boundaries, marks

## Tests

- Unit: every catalog field_id has a type
- Unit: mobile/integer/date not mapped to name profile
- Unit: checkbox type ⇒ checkbox boundary class
- Integration: normalizer dispatch uses these profiles end-to-end

## Milestone

R0

## Status

SPEC

## Owner

engineering (schema) / survey (type confirmation)
