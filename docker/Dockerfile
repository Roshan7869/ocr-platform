# Multi-target image (ADR-003): cpu-spike (default) · cpu-runtime · gpu-runtime (post-spike pins).
# Exact paddle/paddleocr/CUDA pins recorded by scripts/run_spike.py go/no-go matrix.
# Production OCR = cloud GPU workers; local CPU = dev/spike only (docs/capacity.md).
# Rasterizer: pypdfium2 primary (ADR-001) after spike.
FROM python:3.11-slim-bookworm
# gpu-runtime (post-spike): FROM nvidia/cuda:...-cudnn-runtime-ubuntu... + matching python

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

COPY pyproject.toml README.md ./
COPY src ./src
COPY configs ./configs
COPY templates ./templates
COPY scripts ./scripts
COPY fixtures ./fixtures

RUN pip install -e .

# Non-root; resource limits applied via compose/orchestrator in R1+.
RUN useradd --create-home --uid 10001 appuser
USER appuser

ENTRYPOINT ["python", "scripts/extract.py"]
