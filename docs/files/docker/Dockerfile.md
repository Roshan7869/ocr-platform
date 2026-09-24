# docker/Dockerfile

## Role

Reproducible container build for the R0 single-process extractor: Python 3.11 slim base, non-root user, package install, ENTRYPOINT `scripts/extract.py`. Placeholder pins until `scripts/run_spike.py` records the go/no-go matrix (CUDA/Paddle variants may fork this file or add a target stage).

## Contracts

- **Invariants:**
  - Exact Python/PaddleOCR/PaddlePaddle/CUDA/driver pins **only after spike matrix pass** — comments mark the gate; no floating `latest` base for production builds.
  - Non-root USER; no secrets baked in.
  - Copies pyproject, src, configs, templates, scripts (fixtures mounted or path-referenced, not assumed in image for sensitive data).
  - CI builds this image for dependency-pin + reproducibility checks (design Distribution Plan).
  - RACE: if custom images unsupported, this file documents the pin set for a template+bootstrap alternative (strategy recorded in spike matrix, not guessed here).
- **Outputs:** runnable image with extract CLI.
- **Forbidden:** embedding model weights without checksum policy; running as root; unpinned paddle in final stage.

## Infrastructure

- **Python deps:** project via pip install -e .
- **Config/artifacts:** configs/, templates/ copied in
- **Models/external:** models downloaded at runtime or bake stage post-spike (TBD by spike)
- **Env vars:** none required at build; runtime CUDA_* optional

## Depends on

- **Calls:** `scripts/extract.py` (ENTRYPOINT)
- **Called by:** CI, deploy (R1+), local docker run

## Tests

- Integration: image builds in CI
- Integration: `docker run … --help` / usage exit 4 on bad args
- Integration: smoke extract on mounted classified fixture (post-spike pins)
- Gate: Dockerfile pin block matches spike matrix text (manual/CI grep)

## Milestone

R0

## Status

SPEC

## Owner

engineering / platform
