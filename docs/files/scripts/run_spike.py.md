# scripts/run_spike.py

## Role

Runtime compatibility spike: produce the dated go/no-go matrix required **before** R0 extraction. Pins Python, PaddleOCR, PaddlePaddle, CUDA, driver/container, det/rec model revisions+checksums, licenses; runs two-page fixture ingestion; repeated-run comparison under R0 canonical JSON + numerical-tolerance policy; CPU fallback + max resolution; records RACE strategy (custom image vs template bootstrap).

## Contracts

- **Invariants:**
  - Writes a machine-readable + human matrix artifact (path documented in output); failure is a **design result**, never a silent unpinned fallback (design Compatibility Spike).
  - Must exercise real det+rec (not mock) when GPU/CPU available; records which path.
  - Model pin candidates tested here become sole inputs to `worker/paddle/models.py`.
  - Idempotent re-runs append/replace matrix revision, not duplicate uncontrolled files.
- **Outputs:** spike report (JSON/MD) + exit code 0 go / 1 no-go.
- **Forbidden:** shipping pins into `models.py` without matrix pass; downloading models without checksum.

## Infrastructure

- **Python deps:** same as project + paddleocr/paddlepaddle (spike extra)
- **Config/artifacts:** draft `configs/runtime.yaml` values under test; one classified two-page fixture via `fixtures/loader.py`
- **Models/external:** candidate det/rec checkpoints
- **Env vars:** CUDA_* as needed; matrix records resolved versions

## Depends on

- **Calls:** `fixtures/loader.py`, `worker/paddle/engine.py` + `models.py` (once present), `worker/provenance/hashing.py`
- **Called by:** human/CI gate before enabling OCR in pipeline tests

## Tests

- Manual/CI: matrix sections all non-empty
- Manual/CI: repeated-run comparison section filled
- Manual/CI: license + download availability recorded
- Exit non-zero on any missing section

## Milestone

R0 (gate before extraction implementation use)

## Status

SPEC

## Owner

engineering / platform
