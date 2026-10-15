# docker/Dockerfile

## Role

Reproducible container builds for the extractor: **multi-target** — shared `base` (Python slim, non-root user, source copies), `cpu-runtime` (default, last stage so bare `docker build` preserves single-stage CPU behavior), `gpu-runtime` (production OCR on cloud GPU — ADR-003; pre-spike placeholder buildable on CPU-only hosts until the spike matrix records CUDA/Paddle pins). Python slim base, non-root user, package install, ENTRYPOINT `scripts/extract.py`. Placeholder pins until `scripts/run_spike.py` records the go/no-go matrix (CUDA/Paddle variants per target).

## Contracts

- **Invariants:**
  - Exact Python/PaddleOCR/PaddlePaddle/CUDA/driver pins **only after spike matrix pass** — comments mark the gate; no floating `latest` base for production builds.
  - **Targets:** `cpu-runtime` (default/last stage) for CI on CPU-only hosts; `gpu-runtime` for production (not required to build on laptop CI if no CUDA base available — optional job until spike pins land).
  - Non-root USER; no secrets baked in.
  - Copies pyproject, src, configs, templates, scripts (fixtures mounted or path-referenced, not assumed in image for sensitive data).
  - CI builds at least `cpu-spike` for dependency-pin + reproducibility checks (design Distribution Plan).
  - RACE: if custom images unsupported, this file documents the pin set for a template+bootstrap alternative (strategy recorded in spike matrix, not guessed here).
  - Rasterizer pin aligns with ADR-001 / spike matrix.
- **Outputs:** runnable images with extract CLI.
- **Forbidden:** embedding model weights without checksum policy; running as root; unpinned paddle in final stage; baking classified PDFs into image layers.

## Infrastructure

- **Python deps:** project via pip install -e .
- **Config/artifacts:** configs/, templates/, fixtures/ seed copied in (real PDFs mounted at runtime)
- **Models/external:** models downloaded at runtime or bake stage post-spike (TBD by spike)
- **Env vars:** none required at build; runtime CUDA_* optional on gpu-runtime

## Depends on

- **Calls:** `scripts/extract.py` (ENTRYPOINT)
- **Called by:** CI, deploy (R1+), local docker run

## Tests

- Integration: `cpu-runtime` image builds in CI (`docker build -f docker/Dockerfile --target cpu-runtime .`)
- Integration: `docker run … --help` / usage exit 4 on bad args
- Integration: smoke extract on mounted classified fixture (post-spike pins)
- Gate: Dockerfile pin block matches spike matrix text (manual/CI grep)
- Gate: gpu-runtime target documented even when CI skips CUDA build

## Milestone

R0 (cpu-runtime) / R0.5–R1 (gpu-runtime pins)

## Status

SPEC

## Owner

engineering / platform
