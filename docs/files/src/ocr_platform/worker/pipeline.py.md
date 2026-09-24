# src/ocr_platform/worker/pipeline.py

## Role

Single-process R0 orchestrator: PDF → render → template apply (identity registration) → Paddle det+rec → normalization → validation → acceptance policy → decisions + provenance export. One bounded pipeline object; no distributed control plane, no Laya calls (config flag present but disabled).

## Contracts

- **Invariants:**
  - Order fixed by design data flow; no stage may skip provenance attachment.
  - Registration mode is `identity` in R0; missing/ambiguous registration never yields accepted field decisions.
  - Auto-accept only when AcceptancePolicy-v1 passes; otherwise review/exception export.
  - Re-run of same input+config → same decision IDs / canonical JSON within R0 comparison policy (GPU numerical tolerance where declared).
  - OCR and native text both gated for auto-acceptance until spike confirms adapters (design AcceptancePolicy note).
- **Outputs:** decisions, review candidates, provenance bundle, run record (in-memory R0; persistence is R1).
- **Forbidden:** guessing field↔text assignment (must go template → boundary → field extraction); composite confidence; silent coercion of unknown codes.

## Infrastructure

- **Python deps:** pydantic, pypdf (via renderer), pillow
- **Config/artifacts:** `configs/runtime.yaml`, `configs/acceptance_policy_v1.yaml`, full `templates/family_survey_v1/*` package
- **Models/external:** Paddle det+rec models pinned in `worker/paddle/models.py` (post-spike)
- **Env vars:** none in R0 core (spike may set CUDA_*)

## Depends on

- **Calls:** `schemas/job|evidence|decision|provenance`, `worker/render/*`, `worker/template/*`, `worker/paddle/*`, `worker/extraction/*`, `worker/validation/*`, `worker/provenance/*`, `export/*`, `fixtures/loader.py`
- **Called by:** `scripts/extract.py`

## Tests

- Unit: stage order cannot short-circuit provenance
- Integration: R0 scanned-only, native-only, mixed pages
- Integration: valid two-page survey through deterministic path (identity transform boundary assignment)
- Integration: template mismatch, OCR model failure, page-set mismatch
- Integration: canonical JSON + artifact comparison under R0 policy
- E2E: `tests/test_pipeline_e2e.py` on classified fixtures

## Milestone

R0

## Status

SPEC

## Owner

engineering
