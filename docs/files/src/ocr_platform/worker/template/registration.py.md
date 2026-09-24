# src/ocr_platform/worker/template/registration.py

## Role

Template selection vs page registration separation. R0: explicit identity transform (`registration_mode=identity`) with sanity checks using LEGEND/ANCHOR regions. R3 replaces with per-page affine + residual thresholds (stub interface only in R0).

## Contracts

- **Invariants:**
  - Template selection and registration are separate operations (design).
  - R0 uses identity only; stores transform/version on page observation even when identity.
  - Missing or ambiguous enhanced registration never produces accepted field decisions.
  - LEGEND/ANCHOR classes feed identity sanity (R0) and future affine anchors (R3).
  - Residual/threshold logic for R3 is out of R0 runtime (interface reserved, raises/flags if invoked without R3).
- **Outputs:** `RegistrationTransform` provenance node + applied transform for boundary stage.
- **Forbidden:** silent deskew/scale in R0; accepting fields when registration invalid.

## Infrastructure

- **Python deps:** none beyond stdlib/numpy optional later (R3)
- **Config/artifacts:** template `registration` hints; `configs/runtime.yaml` coordinate convention
- **Models/external:** none
- **Env vars:** none

## Depends on

- **Calls:** `worker/render/coordinates.py`, `schemas/provenance.py`, `worker/template/manifest.py`
- **Called by:** `worker/pipeline.py`, `worker/template/boundaries.py`

## Tests

- Unit: identity transform is pure and recorded
- Unit: R3 path without implementation does not accept fields
- Integration: R0 identity on fixtures; residual thresholds deferred (listed in design R3 tests)

## Milestone

R0 (identity); R3 (affine) reserved

## Status

SPEC

## Owner

engineering
