# configs/runtime.yaml

## Role

Global render + coordinate + environment settings for deterministic R0 runs: DPI, colorspace, coordinate convention string, crop padding, preprocessor toggles, output comparison policy flags. Part of `configuration_fingerprint`.

## Contracts

- **Invariants:**
  - `coordinate_system: image_top_left_normalized` documented once here; all modules read this (or constants generated from it).
  - DPI + colorspace fixed for R0; any change = new fingerprint = new run identity.
  - Comparison policy section: exact-byte vs numerical tolerance rules for images/GPU outputs (concrete values in **Key set** below).
  - No secrets, no model pins (those are `models.py` / spike matrix).
  - Full key set enumerated below is **normative** — the loader rejects unknown keys and missing required keys (fail-closed).
- **Outputs:** loaded YAML → typed settings object.
- **Forbidden:** per-run silent overrides without fingerprint change.

## Key set (R0 — normative shape)

Every key below is required and contributes to `configuration_fingerprint`. Values marked *(spike-tunable)* may be repinned by `scripts/run_spike.py`; repinning is a config change → fingerprint bump → new run identity (never a silent override).

```yaml
render:
  dpi: 200                       # (spike-tunable) effective scan DPI ~200 (capacity.md); spike sets max CPU resolution
  colorspace: grayscale          # 1-bit/grayscale corpus (accuracy-plan.md evidence base)
  rasterizer: pypdfium2          # (spike-tunable) primary per ADR-001; spike may amend pin
  crop_padding_px: 8             # padding around resolved field regions before rec

coordinates:
  coordinate_system: image_top_left_normalized   # single SoT; crop-local coords stored separately, never mixed

preprocess:
  deskew: false                  # R0 forbids silent deskew; page-box normalize is an explicit recorded op, not here
  binarize: false                # (spike-tunable) only if spike proves it improves det/rec determinism

comparison_policy:
  # exact-byte where the runtime guarantees determinism (CPU render); tolerance only where GPU/image encoding requires it
  artifact_byte_equality: true                 # non-float artifacts (JSON, masks) compared byte-for-byte
  cpu_render_pixel_tolerance: 0                 # CPU raster is deterministic → zero pixel drift allowed
  gpu_float_abs_tol: 1.0e-6                     # (spike-tunable) abs tolerance for GPU/float paths, declared per ADR
  gpu_float_rel_tol: 1.0e-4                     # (spike-tunable) rel tolerance for GPU/float paths
  canonical_json: { sort_keys: true, ensure_ascii: false, float_format: "repr" }  # aligns with provenance/hashing.py
```

> The `comparison_policy` block is the SoT the spike's determinism check (`scripts/run_spike.py`) and the provenance hasher (`worker/provenance/hashing.py`) both read — one definition, no fork. GPU tolerances stay unused in R0 (CPU-only) and activate at R0.5/R1 GPU (`docs/capacity.md`).

## Infrastructure

- **Python deps:** pyyaml
- **Config/artifacts:** this file; consumed by renderer, coordinates, pipeline fingerprint
- **Models/external:** none
- **Env vars:** none (file is SoT)

## Depends on

- **Calls:** none (leaf config)
- **Called by:** `worker/render/renderer.py`, `worker/render/coordinates.py`, `worker/pipeline.py` (fingerprint), `scripts/annotate_template.py`, `scripts/run_spike.py` (determinism check reads `comparison_policy`), `worker/provenance/hashing.py` (reads `comparison_policy.canonical_json`)

## Tests

- Unit: required keys present; coordinate_system enum valid
- Unit: unknown key rejected; missing required key fails closed
- Unit: fingerprint contribution changes when DPI changes
- Unit: `comparison_policy` parses; `cpu_render_pixel_tolerance == 0` in R0
- Integration: render determinism tests load this file and honor `comparison_policy`

## Milestone

R0

## Status

SPEC

## Owner

engineering
