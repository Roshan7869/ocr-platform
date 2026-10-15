# src/ocr_platform/runtime_config.py

## Role

Fail-closed loader for `configs/runtime.yaml`: parses the global render + coordinate + comparison-policy settings into a typed `RuntimeConfig` and computes the `configuration_fingerprint` (sha256 over canonical JSON via `worker/provenance/hashing.py` — one implementation, no fork).

## Contracts

- **Invariants:**
  - Exact key set enforced: unknown keys rejected, missing required keys fail closed (`RuntimeConfigError`, a `ValueError`).
  - `coordinates.coordinate_system` must equal `image_top_left_normalized` (single SoT).
  - `comparison_policy.cpu_render_pixel_tolerance` must be `0` in R0.
  - `comparison_policy.canonical_json` must match `hashing.py` behavior exactly (`sort_keys: true, ensure_ascii: false, float_format: "repr"`).
  - Fingerprint changes on any settings change (e.g. DPI) → new run identity, never a silent override.
- **Outputs:** `RuntimeConfig` (frozen dataclass) with `fingerprint` hex digest.
- **Forbidden:** silent defaults for missing keys; a second canonical-JSON implementation.

## Infrastructure

- **Python deps:** pyyaml; stdlib dataclasses/pathlib.
- **Config/artifacts:** reads `configs/runtime.yaml` (default path resolved from module location).
- **Models/external:** none.
- **Env vars:** none.

## Depends on

- **Calls:** `worker/provenance/hashing.py` (`canonical_json`, `content_hash`), `fixtures/loader.py`-style fail-closed pattern.
- **Called by:** `scripts/run_spike.py` (determinism check reads `comparison_policy`), render/pipeline fingerprint consumers.

## Tests

- Unit (`tests/unit/test_runtime_config.py`): required keys present; unknown key rejected (top-level + nested); missing key/section fails closed; fingerprint changes when DPI changes; `cpu_render_pixel_tolerance == 0`; nonzero tolerance rejected.

## Milestone

R0

## Status

IMPLEMENTED (not GitNexus VERIFIED).

## Owner

engineering
