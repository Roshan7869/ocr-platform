# tests/unit/test_runtime_config.py

## Role

Fail-closed unit tests for the `configs/runtime.yaml` loader (`src/ocr_platform/runtime_config.py`).

## Contracts

No fixtures, no models, no network. Mutates in-memory copies of the real config in temp dirs only; never writes to `configs/`.

## Infrastructure

unittest; pyyaml; pytest runner optional.

## Depends on

Called by: pytest / unittest discover. Python module imports define direct collaborators.

## Tests

Required keys present; unknown key rejected (top-level + nested); missing key/section fails closed; fingerprint changes when DPI changes; `cpu_render_pixel_tolerance == 0`; nonzero tolerance rejected. See tests/unit/test_runtime_config.py.

## Milestone

R0

## Status

IMPLEMENTED (not GitNexus VERIFIED).

## Owner

engineering
