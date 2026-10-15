# Multi-target image (ADR-003): cpu-runtime (default) · gpu-runtime.
# Exact paddle/paddleocr/CUDA pins recorded by scripts/run_spike.py go/no-go matrix.
# Production OCR = cloud GPU workers; local CPU = dev/spike only (docs/capacity.md).
# Rasterizer: pypdfium2 primary (ADR-001) after spike.
FROM python:3.11-slim-bookworm AS base

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

COPY pyproject.toml README.md ./
COPY src ./src
COPY configs ./configs
COPY templates ./templates
COPY scripts ./scripts
COPY fixtures ./fixtures

# Non-root; resource limits applied via compose/orchestrator in R1+.
RUN useradd --create-home --uid 10001 appuser

# gpu-runtime (post-spike): CUDA base + GPU paddle pins land here once the spike
# matrix records them (ci-spec.md §2.8). Pre-spike placeholder stays buildable on
# CPU-only CI hosts; CPU CI is not required to build this target until pins exist.
FROM base AS gpu-runtime

RUN pip install -e .

USER appuser

ENTRYPOINT ["python", "scripts/extract.py"]

# cpu-runtime is LAST so a bare `docker build` (no --target) preserves the
# previous single-stage CPU behavior; CI builds this target explicitly.
FROM base AS cpu-runtime

RUN pip install -e .

USER appuser

ENTRYPOINT ["python", "scripts/extract.py"]
