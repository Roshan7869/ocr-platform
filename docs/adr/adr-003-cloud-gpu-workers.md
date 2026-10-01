# ADR-003: Production OCR on cloud GPU workers; local CPU = dev/spike only

## Status

Accepted · 2026-09-24

## Context

Dev host: i5-5300U (2c/4t, 2015-class), 15GB RAM, **no GPU**. Render is cheap (~0.4–1.5s/2pp); Paddle det+rec on ~344 regions/doc will dominate. Local CPU cannot meet interactive or small-batch SLA for market path. Docker available; CUDA image path feasible for cloud.

## Decision

1. **Local:** development, unit/integration tests, spike CPU matrix, annotation — **not** production OCR.  
2. **Production OCR:** **cloud GPU worker pool** running pinned `gpu-runtime` container.  
3. **On-prem CPU image** (`cpu-runtime`) supported for low-volume offline installs/demo only.  
4. Spike records CPU numbers always; GPU numbers when hardware available; capacity doc updated from both.

## Consequences

- Dockerfile multi-target: `cpu-spike` / `cpu-runtime` / `gpu-runtime` (pins post-spike).  
- `docs/capacity.md` owns SKU/throughput; no laptop-based SLA promises.  
- R1 API design assumes queue + horizontal workers (see architecture deployment 4.3).

## Alternatives considered

- CPU-only product: fails latency/throughput at scale.  
- Wait for local GPU procurement: blocks capacity planning.  
- Ollama VLM as primary OCR: out of R0 scope; optional R2 hybrid only (separate ADR).
