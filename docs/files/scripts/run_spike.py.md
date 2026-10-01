# scripts/run_spike.py

## Role

Runtime compatibility spike: produce the dated go/no-go matrix required **before** R0 extraction. Pins Python, PaddleOCR, PaddlePaddle, CUDA, driver/container, det/rec model revisions+checksums, licenses; **rasterizer choice (ADR-001)**; runs two-page fixture ingestion; repeated-run comparison under R0 canonical JSON + numerical-tolerance policy; CPU fallback + max resolution; records RACE strategy (custom image vs template bootstrap). Production capacity assumptions flow to `docs/capacity.md` (ADR-003).

## Contracts

- **Invariants:**
  - Writes a machine-readable + human matrix artifact (path documented in output); failure is a **design result**, never a silent unpinned fallback (design Compatibility Spike).
  - Must exercise real det+rec (not mock) when GPU/CPU available; records which path; **CPU section always required**; GPU section optional on laptop.
  - Model pin candidates tested here become sole inputs to `worker/paddle/models.py`.
  - Matrix includes **rasterizer determinism** rows (pypdfium2 primary per ADR-001).
  - Idempotent re-runs append/replace matrix revision, not duplicate uncontrolled files.
  - Spike **go ≠ auto-accept enablement** (calibration gate ADR-005 separate).
- **Outputs:** spike report (JSON/MD) + exit code 0 go / 1 no-go; capacity snippet for `docs/capacity.md`.
- **Forbidden:** shipping pins into `models.py` without matrix pass; downloading models without checksum; treating spike go as permission to flip auto-accept flags.

## Go / No-Go criteria (quantitative)

Structural completeness (all sections non-empty) is necessary but **not sufficient**. `go` (exit 0) requires every criterion below to pass; any hard failure ⇒ `no-go` (exit 1). Exit codes are defined in `docs/reason-codes.md §1`.

| # | Criterion | Threshold (R0) | Fail ⇒ |
|---|---|---|---|
| C1 | **Determinism** — N≥3 repeated CPU runs on the same fixture | canonical-JSON identical under `runtime.yaml comparison_policy`; `cpu_render_pixel_tolerance == 0` (zero pixel drift) | no-go |
| C2 | **Canonical-JSON compare** — decision IDs + serialized output stable across the N runs | byte-equal for non-float artifacts; float paths within declared `gpu_float_*` tol only | no-go |
| C3 | **Min CPU resolution** — real det+rec produces non-empty regions on the two-page fixture at the pinned DPI | ≥ 1 detected region per expected populated field band; no OOM within measured RAM (`capacity.md:12`) | no-go |
| C4 | **Python reconciliation** — resolved interpreter vs `pyproject` target | single version pinned that satisfies `requires ≥3.11` **and** the host 3.12.3 (`capacity.md:15`); mismatch unresolved | no-go |
| C5 | **Model tie-break** — v3 vs v5 rec candidate | exactly one rec model chosen + checksum recorded (`models.py.md:13`); "latest"/unpinned present | no-go |
| C6 | **Rasterizer determinism** — pypdfium2 primary (ADR-001) | repeated render byte-stable; if not, record amended pin + rationale | no-go unless amended pin recorded |
| C7 | **License + availability** — each pinned artifact | license recorded + checksum download reproducible | no-go |
| C8 | **RACE strategy** — custom image vs template bootstrap | one strategy recorded with justification (`Dockerfile.md:24` TBD resolved) | no-go |

**Conditional-go** = exit 0 with one or more `caveats[]` entries in the matrix (e.g. GPU section skipped on laptop per C-note below). A conditional-go is still a go for R0 CPU work but records the deferred item; it never silently masks a C1–C7 hard failure.

- **GPU section** is optional on laptop-class hosts (no CUDA); skipping it is a recorded caveat, not a failure. CPU section (C1–C7) is always mandatory.
- **Determinism N** and tolerances come from `configs/runtime.yaml comparison_policy` — the spike does not define its own; it reads that SoT.

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
- Manual/CI: repeated-run comparison section filled; C1 determinism (N≥3) passes under `runtime.yaml comparison_policy`
- Manual/CI: C3 min-CPU-resolution — non-empty det+rec regions on the two-page fixture
- Manual/CI: C4 Python version reconciled to a single pin; C5 exactly one rec model + checksum
- Manual/CI: license + download availability recorded (C7)
- Manual/CI: rasterizer section filled (ADR-001); C8 RACE strategy recorded
- Exit non-zero on any missing section **or** any C1–C7 hard failure; conditional-go records `caveats[]`

## Milestone

R0 (gate before extraction implementation use)

## Status

SPEC

## Owner

engineering / platform
