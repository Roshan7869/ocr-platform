# configs/runtime.yaml

## Role

Global render + coordinate + environment settings for deterministic R0 runs: DPI, colorspace, coordinate convention string, crop padding, preprocessor toggles, output comparison policy flags. Part of `configuration_fingerprint`.

## Contracts

- **Invariants:**
  - `coordinate_system: image_top_left_normalized` documented once here; all modules read this (or constants generated from it).
  - DPI + colorspace fixed for R0; any change = new fingerprint = new run identity.
  - Comparison policy section: exact-byte vs numerical tolerance rules for images/GPU outputs.
  - No secrets, no model pins (those are `models.py` / spike matrix).
- **Outputs:** loaded YAML → typed settings object.
- **Forbidden:** per-run silent overrides without fingerprint change.

## Infrastructure

- **Python deps:** pyyaml
- **Config/artifacts:** this file; consumed by renderer, coordinates, pipeline fingerprint
- **Models/external:** none
- **Env vars:** none (file is SoT)

## Depends on

- **Calls:** none (leaf config)
- **Called by:** `worker/render/renderer.py`, `worker/render/coordinates.py`, `worker/pipeline.py` (fingerprint), `scripts/annotate_template.py`

## Tests

- Unit: required keys present; coordinate_system enum valid
- Unit: fingerprint contribution changes when DPI changes
- Integration: render determinism tests load this file

## Milestone

R0

## Status

SPEC

## Owner

engineering
