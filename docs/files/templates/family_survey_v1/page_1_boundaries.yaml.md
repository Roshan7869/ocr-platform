# templates/family_survey_v1/page_1_boundaries.yaml

## Role

Typed normalized bboxes for page 1: admin header fields (municipality, zone, ward_no, ward_name, survey_date, enumerator_*), household identity (head name/mobile, family_structure), and all checkbox groups (solid waste, electricity connection + power cut, alternative energy, sanitation options, drinking water, housing type, housing ownership, scheme beneficiary multi-select, financial inclusion, communication, CCTV). One region per printed option for checkbox fields.

## Contracts

- **Invariants:**
  - Every region: `field_id` (entity-qualified), `boundary_class`, `bbox: [x1,y1,x2,y2]`, `coordinate_system: image_top_left_normalized`.
  - Checkbox option granularity: each printed option own bbox + own field_id or option key (design §5–§15).
  - Multi-select groups declare `selection_mode: single|multi` (scheme_beneficiary = multi; power_cut numeric field not checkbox).
  - Numeric/text fields declare link to `field_types.yaml` profile (NAME/INTEGER/DATE/MOBILE/…).
  - Admin vs household identity fields deduped (one head_name entry).
  - LEGEND/ANCHOR regions included if used for identity sanity (code legend may be page 1 or 2 — follow actual form).
  - Geometry from annotation pass over WARD-42 PDFs, not estimated from prose.
- **Outputs:** YAML list of regions for page 1.
- **Forbidden:** free-text “question sentence” regions as values; guessed coordinates without annotation source hash.

## Boundary classes

FIELD, CHECKBOX_OPTION, CHECKBOX_GROUP, LEGEND, ANCHOR (as applicable).

## Entity owner

Mixed: `document.*` (admin) + `household.*` (services/identity).

## Infrastructure

- **Python deps:** pyyaml
- **Config/artifacts:** hash in template_manifest; render settings from runtime.yaml when annotating
- **Models/external:** none
- **Env vars:** none

## Depends on

- **Calls:** none (data); consumed by `worker/template/boundaries.py`, `scripts/annotate_template.py`
- **Called by:** boundaries.py via manifest resolve

## Tests

- Unit: all field_ids exist in field_catalog; all bboxes normalized + ordered
- Unit: every checkbox_group has ≥1 option child
- Integration: identity-transform apply on fixture → non-empty region set; overlap tests
- Integration: coverage vs catalog for page-1 fields

## Milestone

R0

## Status

SPEC

## Owner

survey (bbox approval) / engineering (schema + annotation tooling)
