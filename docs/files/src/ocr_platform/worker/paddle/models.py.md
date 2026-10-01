# src/ocr_platform/worker/paddle/models.py

## Role

Pinned detection/recognition model registry: exact names, revisions, checksums, licenses, download availability. Single source for what `engine.py` loads and what the configuration fingerprint includes.

## Contracts

- **Invariants:**
  - No unpinned "latest" at runtime; pins only after `scripts/run_spike.py` go/no-go matrix passes.
  - Each entry: model id, revision, sha256, license, source URL, task (det/rec), language script (Devanagari).
  - Configuration fingerprint includes model checksums (design run identity).
  - Spike may prove v3 vs v5 rec model choice; record winner here, do not hardcode in engine.
  - Pins must match **cpu-spike** and **gpu-runtime** matrix rows (ADR-003); deviation = rebuild matrix.
- **Outputs:** registry structure + `get_model("det"|"rec")` API.
- **Forbidden:** downloading without checksum verify; silent version drift.

## Infrastructure

- **Python deps:** none (data + loaders)
- **Config/artifacts:** filled from spike report; checked into repo post-spike
- **Models/external:** PaddleOCR model zoo files
- **Env vars:** model cache dir (optional)

## Depends on

- **Calls:** none (leaf)
- **Called by:** `worker/paddle/engine.py`, fingerprint builder in `worker/pipeline.py` / `schemas/job.py`

## Tests

- Unit: every registry entry has checksum + license
- Unit: missing pin → clear error, not silent default
- Integration: engine loads only registered pins (post-spike)

## Milestone

R0

## Status

SPEC

## Owner

engineering
