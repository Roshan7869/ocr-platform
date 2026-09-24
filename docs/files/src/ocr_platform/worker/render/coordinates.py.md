# src/ocr_platform/worker/render/coordinates.py

## Role

Coordinate transforms and explicit coordinate-system algebra: PDF bottom-left ↔ image top-left, normalized vs pixel, page-space vs crop-local. Single place that may convert bboxes; all other modules pass through with `coordinate_system` attached.

## Contracts

- **Invariants:**
  - Page-space storage: `image_top_left_normalized` (design Important Technical Decisions).
  - PDF native bottom-left never silently equals image top-left; conversion is explicit and tested.
  - Crop-local intermediates tagged `crop_local_*` and never used as evidence page-space boxes.
  - No module may mix systems without going through these helpers.
- **Outputs:** `to_page_normalized`, `to_pixel`, `pdf_rect_to_image_bbox`, invariants/assert helpers.
- **Forbidden:** rounding policies that lose provenance (document any quantization).

## Infrastructure

- **Python deps:** stdlib math; pillow optional for pixel dims
- **Config/artifacts:** convention string from `configs/runtime.yaml`
- **Models/external:** none
- **Env vars:** none

## Depends on

- **Calls:** `schemas/evidence.py` (bbox type constants)
- **Called by:** `worker/render/renderer.py`, `worker/template/boundaries.py`, `worker/template/registration.py`, `worker/paddle/engine.py`, `worker/paddle/marks.py`, `worker/provenance/validator.py`

## Tests

- Unit: normalized↔pixel round-trip within epsilon
- Unit: PDF bottom-left → image top-left conversion (design unit list)
- Unit: reject cross-system ops without conversion
- Integration: R0 identity-transform boundary assignment uses same helpers as export

## Milestone

R0

## Status

SPEC

## Owner

engineering
