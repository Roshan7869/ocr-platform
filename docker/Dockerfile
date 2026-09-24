# R0 base image. Exact paddle/paddleocr/CUDA pins recorded by scripts/run_spike.py
# go/no-go matrix; this file is updated only after the spike passes.
FROM python:3.11-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

COPY pyproject.toml README.md ./
COPY src ./src
COPY configs ./configs
COPY templates ./templates
COPY scripts ./scripts

RUN pip install -e .

# Non-root; resource limits applied via compose/orchestrator in R1+.
RUN useradd --create-home --uid 10001 appuser
USER appuser

ENTRYPOINT ["python", "scripts/extract.py"]
