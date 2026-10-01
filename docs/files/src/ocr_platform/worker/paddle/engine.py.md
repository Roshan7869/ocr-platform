# src/ocr_platform/worker/paddle/engine.py

## Role

PaddleOCR adapter: whole-page **detection pass** + per-candidate **recognition pass**; assign detected text boxes to registered field regions; emit `OcrObservation`s. Records template crops separately from detected boxes. No acceptance, no vocabulary mapping.

## Contracts

- **Invariants:**
  - Detection + recognition both required; recognition-only must not pretend crop full-box is true text box (design).
  - Model names/versions from `models.py` (pinned post-spike; docs note current PaddleOCR v3.x docs advertise `devanagari_PP-OCRv5_mobile_rec` — spike chooses exact pin).
  - Overlapping/duplicate detections → separate observations until policy collapses exact duplicates.
  - Raw OCR confidence stored on observation; never combined into `final_confidence`.
  - Auto-acceptance path remains gated until spike **and** calibration evidence (AcceptancePolicy; ADR-005).
  - **Handwriting posture (ADR-004):** may set `handwriting_suspected` on FIELD observations (heuristics/print-model trust); policy forces review for text fields — engine never implies accept.
- **Outputs:** list of `OcrObservation` with page-space bboxes + model versions (+ optional handwriting signal).
- **Forbidden:** field-state machine mutations; Laya; normalization; auto-accept decisions.

## Infrastructure

- **Python deps:** paddleocr + paddlepaddle (pinned by spike; optional extra in pyproject)
- **Config/artifacts:** `models.py` pins; `configs/runtime.yaml` preprocessor settings
- **Models/external:** det + rec checkpoints (checksums in spike matrix)
- **Env vars:** CUDA_* as per spike; CPU fallback documented

## Depends on

- **Calls:** `schemas/evidence.py`, `worker/render/coordinates.py`, `worker/template/boundaries.py`, `worker/paddle/models.py`
- **Called by:** `worker/pipeline.py`

## Tests

- Unit: OCR adapter contract (mock backend) — shape of observations
- Unit: recognition-only misuse rejected
- Unit: handwriting signal does not imply acceptance
- Integration: R0 scanned-only + mixed pages; OCR model failure fixture
- Spike gate: two-page fixture ingestion + repeated-run comparison

## Milestone

R0

## Status

SPEC

## Owner

engineering
