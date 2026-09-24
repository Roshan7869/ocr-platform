# templates/family_survey_v1/page_2_boundaries.yaml

## Role

Page 2 layout: overall table region, fixed column definitions for the 18 member-table columns (including education as `education.*` entity columns), resident-status code legend geometry, header/anchor points. Row bands are **dynamic** at runtime — this file fixes columns and table data region only.

## Contracts

- **Invariants:**
  - `table_geometry = fixed`, `row_count = dynamic`, `column_count = fixed` (design §16).
  - Each column: `column_id`, `field_id` (entity-qualified; education → `education.*`), `boundary_class: TABLE_CELL` (column strip), data profile from field_types, width/bbox in normalized page coords.
  - 18-column member schema from FAMILY_SURVEY_V1 §17 mapped: member_name … migration_nature (education column owned by EducationRecord entity when catalog says so).
  - Legend region for resident_status codes 1–6 as LEGEND class with code positions if used for hard validation cross-check.
  - Ditto-mark columns still use cell geometry; ditto semantics in cross_field, not special bbox type.
  - No hardcoded populated row count; `table.yaml` holds dynamic-row algorithm params.
- **Outputs:** page 2 region + column defs.
- **Forbidden:** baking row count = N from one sample; mixing entity prefixes on columns.

## Boundary classes

TABLE, TABLE_CELL, LEGEND, ANCHOR, FIELD (non-table page-2 fields if any).

## Entity owner

Mixed: `member.*` + `education.*` + document-level legend as needed.

## Infrastructure

- **Python deps:** pyyaml
- **Config/artifacts:** hash in template_manifest
- **Models/external:** none
- **Env vars:** none

## Depends on

- **Calls:** none (data); consumed by boundaries.py
- **Called by:** boundaries.py, annotate_template.py

## Tests

- Unit: column set matches catalog table-backed fields exactly (no extra/missing)
- Unit: normalized bboxes non-overlapping within row band definition (columns)
- Integration: INTERSECT cells for synthetic populated rows; blank rows → no records
- Integration: legend codes 1–6 present if legend referenced

## Milestone

R0

## Status

SPEC

## Owner

survey (bbox + column list approval) / engineering
