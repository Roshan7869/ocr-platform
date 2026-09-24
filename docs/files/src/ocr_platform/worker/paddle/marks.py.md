# src/ocr_platform/worker/paddle/marks.py

## Role

Checkbox / mark / glyph evidence extractor for CHECKBOX_OPTION and CHECKBOX_GROUP regions: classify physical marks inside option boundaries without asking PaddleOCR to read the question text as the answer.

## Contracts

- **Invariants:**
  - Per printed option: own bbox, own raw_mark, own selected_state (design FAMILY_SURVEY_V1 §5–§15).
  - Classification:
    - mark found inside option → SELECTED
    - blank → UNSELECTED only if form rule defines blank as no; otherwise region evidence for review/absent per policy (do not invent NO)
    - unclear mark → AMBIGUOUS → review
    - multiple marks in single-select group → VALUE_REVIEW
    - mark touching boundary → BOUNDARY_REVIEW
  - Multi-select groups: independent booleans per option (e.g. alternative energy, sanitation, scheme_beneficiary.option_NNN).
  - Never infer one question's status from another (sanitation ≠ housing type, etc.).
  - Emits mark evidence (RegionEvidence or mark-typed observation) into EvidenceSet — not `OcrObservation` text.
  - Ditto marks (`"`) in table cells: `raw=ditto`, `semantic_type=DITTO`, `reference_row` — raw never overwritten with expanded value (expansion via cross_field with provenance op).
- **Outputs:** per-option mark evidence + selected/ambiguous signals.
- **Forbidden:** OCR-reading the full question; collapsing multi-select to free text; treating blank as NO without form rule.

## Infrastructure

- **Python deps:** pillow, numpy (optional), pydantic
- **Config/artifacts:** option bboxes from `page_1_boundaries.yaml`, `symbols.yaml` rules folded into `vocabularies.yaml`
- **Models/external:** none (geometric/pixel heuristics in R0; learned mark detector later if needed)
- **Env vars:** none

## Depends on

- **Calls:** `schemas/evidence.py`, `worker/render/coordinates.py`, `worker/template/boundaries.py`
- **Called by:** `worker/pipeline.py` (checkbox path parallel to text OCR path)

## Tests

- Unit: mark/touching/multi/blank per decision table
- Unit: multi-select independence (two options selected both true)
- Unit: ditto raw preserved as `"`
- Integration: R0 checkbox sections on fixtures (solid waste, electricity, housing, schemes)
- Integration: conflicting checkbox marks → review exception record with crop

## Milestone

R0

## Status

SPEC

## Owner

engineering
