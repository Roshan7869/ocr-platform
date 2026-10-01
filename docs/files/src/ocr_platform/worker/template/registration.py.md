# src/ocr_platform/worker/template/registration.py

## Role

Template selection vs page registration separation. **R0:** explicit identity transform (`registration_mode=identity`) with explicit **canonical page-box normalize** (recorded op, not silent deskew) + sanity checks using LEGEND/ANCHOR regions. **R0.5:** classical affine from form structure (rulings/table grid/anchors) + residual threshold fail-closed. R3 remains reserved for further enhanced registration (ADR-002).

## Contracts

- **Invariants:**
  - Template selection and registration are separate operations (design).
  - R0 uses identity only; stores transform/version on page observation even when identity.
  - Canonical page-box normalize is an **explicit recorded** pre-identity op (coordinates helper); still identity for template space.
  - Missing or ambiguous enhanced registration never produces accepted field decisions.
  - LEGEND/ANCHOR classes feed identity sanity (R0) and affine anchors (R0.5+).
  - **R0.5 affine:** residual above threshold or ambiguous anchors → page review (`REGISTRATION_RESIDUAL_HIGH`); never silent accept.
  - R0.5 implementation replaces the historical “R3 stub raises” path for affine; residual logic otherwise out of R0 identity runtime.
- **Outputs:** `RegistrationTransform` provenance node + applied transform for boundary stage.
- **Forbidden:** silent deskew/scale in R0; accepting fields when registration invalid; claiming corpus-ready identity accuracy (see `docs/accuracy-plan.md`).

## Infrastructure

- **Python deps:** stdlib; numpy optional for R0.5 affine
- **Config/artifacts:** template `registration` hints; `configs/runtime.yaml` coordinate convention + normalize flag
- **Models/external:** none
- **Env vars:** none

## Depends on

- **Calls:** `worker/render/coordinates.py`, `schemas/provenance.py`, `worker/template/manifest.py`
- **Called by:** `worker/pipeline.py`, `worker/template/boundaries.py`

## Tests

- Unit: identity transform is pure and recorded
- Unit: page-box normalize recorded as explicit op (not omitted from provenance)
- Unit: R0.5 affine residual above threshold does not accept fields
- Integration: R0 identity on layout-ref fixtures; residual baseline vs corpus sample (`docs/accuracy-plan.md` E1)
- Integration: R0.5 affine residual pass-rate metric on classified set (≥95% pages — accuracy-plan gate)

## Milestone

R0 (identity + normalize); **R0.5 (affine + residual)**; R3+ reserved

## Status

SPEC

## Owner

engineering
