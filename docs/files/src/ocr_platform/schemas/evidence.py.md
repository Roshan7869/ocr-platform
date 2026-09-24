# src/ocr_platform/schemas/evidence.py

## Role

Typed evidence nodes and `EvidenceSet`: `OcrObservation`, `NativeTextEvidence`, `RegionEvidence`, `HumanCorrectionEvidence` (later milestones), plus shared bbox + `coordinate_system` types. Evidence is immutable content-addressed input to decisions — never rewritten by normalization or acceptance.

## Contracts

- **Invariants:**
  - Every evidence node: immutable ID, `evidence_type`, source page, source region, content hash, creation metadata.
  - Every bbox carries explicit `coordinate_system` (`image_top_left_normalized` for page-space); crop-local coords stored separately and never mixed.
  - `OcrObservation` includes det+rec model versions, raw OCR confidence, render/preprocess metadata, field/row/col IDs where applicable.
  - `NativeTextEvidence` is `SourceEvidence`, not an OCR observation.
  - `RegionEvidence` proves empty / unreadable / not_applicable regions; required for `absent` / `unreadable` / `not_applicable` value states.
  - Duplicate detections remain separate nodes until a recorded policy operation collapses exact duplicates.
  - No composite `final_confidence`.
- **Outputs:** evidence model classes + `EvidenceSet` membership helper types.
- **Forbidden:** mutating raw text/bbox after creation; inventing evidence without a source region.

## Infrastructure

- **Python deps:** pydantic>=2.7
- **Config/artifacts:** coordinate convention from `configs/runtime.yaml`
- **Models/external:** none
- **Env vars:** none

## Depends on

- **Calls:** `schemas/provenance.py` (node IDs, content hashes)
- **Called by:** `worker/paddle/engine.py`, `worker/paddle/marks.py`, `worker/template/boundaries.py`, `worker/extraction/*`, `worker/provenance/validator.py`, `export/*`

## Tests

- Unit: bbox rejects missing coordinate_system
- Unit: evidence nodes immutable after construction
- Unit: RegionEvidence required for absent/unreadable/not_applicable (validator-level)
- Integration: R0 duplicate + conflicting OCR observations remain distinct nodes
- Integration: R0 region evidence for absent / not_applicable / unreadable fields

## Milestone

R0

## Status

SPEC

## Owner

engineering
