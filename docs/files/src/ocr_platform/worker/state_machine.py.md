# src/ocr_platform/worker/state_machine.py

## Role

Explicit job/page/field lifecycle transitions for R0 in-memory runs (persisted job table is R1). Validates legal transitions only — no OCR, no policy thresholds.

## Contracts

- **Invariants:**
  - Transitions are explicit; no implicit skip to accepted without policy pass.
  - Document-level terminal states align with capability matrix (`errored` for encrypted/corrupt before field decisions).
  - Page `review` with reasons like `PAGE_SET_MISMATCH` / `REGISTRATION_RESIDUAL_HIGH` blocks field acceptance on that page.
  - Illegal transition raises; never silently no-ops.
- **Outputs:** transition function/table + guards.
- **Forbidden:** side effects (DB, files); acceptance logic (delegates to policy).

## Infrastructure

- **Python deps:** stdlib / pydantic enums
- **Config/artifacts:** reason codes consistent with decision schema + acceptance policy
- **Models/external:** none
- **Env vars:** none

## Depends on

- **Calls:** `schemas/job.py`, `schemas/decision.py`
- **Called by:** `worker/pipeline.py`

## Tests

- Unit: every legal transition allowed; representative illegal transitions rejected
- Unit: page-level review blocks child field accept
- Integration: encrypted/corrupt never reaches field states

## Milestone

R0

## Status

SPEC

## Owner

engineering
