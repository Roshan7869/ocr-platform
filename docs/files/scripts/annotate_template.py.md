# scripts/annotate_template.py

## Role

Template annotation pass: open layout-reference PDFs (WARD-42 95–99.pdf batches), capture/derive normalized bboxes for every FIELD / CHECKBOX_* / TABLE / LEGEND / ANCHOR region on page 1 and page 2, and emit draft YAML fragments for `page_1_boundaries.yaml`, `page_2_boundaries.yaml`, `table.yaml`. Coordinates come from annotation — never guessed from prose (design §45).

## Contracts

- **Invariants:**
  - All output bboxes in `image_top_left_normalized` with explicit `coordinate_system`.
  - Every field_id produced must match entity-qualified IDs destined for `field_catalog.json` (prefix `document.|household.|member.|education.`).
  - One annotation session records: operator, timestamp, source PDF hash, template version draft, DPI/render settings matching `runtime.yaml`.
  - Multi-document: annotation may start from one PDF; disagreement across 95–99 must be resolved (union/approved layout) and recorded — template is geometry-stable across the five forms.
  - Output is **draft** until survey owner + engineering review sets `synthetic_baseline_approved` in manifest.
  - Checkbox options get individual bboxes (one per printed option), not one group blob without option children.
  - Page-2: table bbox + fixed column bboxes + row pitch assumptions left for dynamic row detection — do not hardcode row count.
- **Outputs:** draft YAML snippets + annotation report (coverage: every catalog field has ≥1 region or explicit exception).
- **Forbidden:** inventing fields not in catalog draft; final approval status.

## Infrastructure

- **Python deps:** pypdf, pillow, pyyaml; optional interactive overlay later (R0 can be semi-manual JSON input → YAML)
- **Config/artifacts:** draft `field_catalog.json`; `runtime.yaml` render settings; fixture hashes from loader
- **Models/external:** none
- **Env vars:** none

## Depends on

- **Calls:** `worker/render/renderer.py`, `worker/render/coordinates.py`, `fixtures/loader.py`, `worker/provenance/hashing.py`
- **Called by:** template authoring workflow (human); not called by runtime pipeline

## Tests

- Unit: emitted YAML validates against boundary schema
- Unit: normalized coords in [0,1]; x1<x2, y1<y2
- Integration: coverage report — every field_id in catalog draft appears in some boundary or is marked exception
- Integration: both WARD-42 batches annotated or explicitly deferred

## Milestone

R0 (authoring tool; not in runtime path)

## Status

SPEC

## Owner

engineering (tool) / survey (bbox review approval)
