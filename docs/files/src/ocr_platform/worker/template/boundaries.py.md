# src/ocr_platform/worker/template/boundaries.py

## Role

Apply typed template boundaries to a registered page: resolve FIELD / CHECKBOX_* / TABLE* / LEGEND / ANCHOR regions into page-space bboxes; assign detected text boxes to field regions with overlap rules; compute cell bboxes via `INTERSECT(row_bbox, col_bbox)`. Does not run OCR or decide acceptance.

## Contracts

- **Invariants:**
  - Boundary classes from template YAML only; no freehand regions at runtime.
  - Box assignment: single unambiguous region with `overlap_ratio >= 0.80`; tie / boundary crossing / lower ratio → review signal (provisional, benchmarked before production).
  - Table geometry fixed; row count dynamic; populated rows only produce records; blank trailing rows → no member record (not empty fake rows).
  - Never reconstruct table from full-page OCR text order.
  - Every output region keeps `coordinate_system=image_top_left_normalized` and `boundary_class`.
  - Signals for boundary quality: text_inside/touching/outside bbox, neighbor_overlap, crop_quality — emitted for policy, not decided here.
  - Consumes only **registered** pages (R0 identity+normalize or R0.5 affine); registration failure surfaces as page review, not silent full-page accept (`docs/adr/adr-002-registration-strategy.md`).
- **Outputs:** page-space region list + cell candidates + boundary-quality signals.
- **Forbidden:** ACCEPT decisions; Laya calls; guessing which printed option is selected (that is `paddle/marks.py`); applying template bounds before registration.

## Infrastructure

- **Python deps:** pydantic
- **Config/artifacts:** `page_1_boundaries.yaml`, `page_2_boundaries.yaml`, `table.yaml`, `field_types.yaml`, `template_manifest.json`
- **Models/external:** none
- **Env vars:** none

## Depends on

- **Calls:** `worker/render/coordinates.py`, `worker/template/manifest.py`, `worker/template/registration.py`, `schemas/evidence.py`
- **Called by:** `worker/pipeline.py`, `worker/paddle/engine.py`, `worker/paddle/marks.py`, `export/review_candidates.py`

## Tests

- Unit: overlap ≥0.80 accepts; below/tie routes review signal
- Unit: INTERSECT cell derivation for fixed columns × dynamic rows
- Unit: blank rows produce no NO_MEMBER fake records
- Unit: boundary class present on every region
- Integration: R0 identity-transform boundary assignment; duplicate/conflicting observation fixtures
- Integration: ditto raw preserved (structure supports reference_row; logic in cross_field)

## Milestone

R0

## Status

SPEC

## Owner

engineering
