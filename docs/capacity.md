# Capacity & cost model — ocr-platform

Measured on development host (2026-09-24) + corpus stats. Update when spike/GPU numbers land.

---

## 1. Development host (measured)

| Resource | Value |
|---|---|
| CPU | Intel i5-5300U, 2c/4t, ~2.30 GHz (2015-class) |
| RAM | 15 GiB total; ~5 GiB available during session |
| GPU | **None** (`no nvidia devices`) |
| Disk | ~90 GiB free on root |
| Python | 3.12.3 (`pyproject` target py311 / requires ≥3.11 — spike must reconcile) |
| Docker | 29.1.3 available |
| PaddleOCR | not installed; registry offers **3.7.0** |
| Render (PyMuPDF, 2 pages) | **~413–454 ms** @150–200 DPI; **~1.5 s** @300 DPI |

**Verdict:** fine for schema work, fixture hashing, render tests, spike; **not** a production OCR worker.

---

## 2. Workload shape (per document)

| Item | Estimate | Basis |
|---|---|---|
| Pages | 2 | entire WARD-42 sample |
| Page box | ~808–837 × 604–618 pt | layout refs + 50-doc sample |
| Embedded scan | ~1-bit grayscale PNG ~2100–2330 px wide (~200 effective DPI) | PyMuPDF image_info |
| Candidate regions | **~344** field evaluations max | ~64 checkbox options + ~10 page-1 text + up to 15×18=270 table cells |
| Provenance nodes | O(hundreds) per doc | graph design |
| Fixture corpus | **1,446** PDFs, 10 layout refs (95–99 × 2 batches) | `~/Documents/WARD-42` |

Render-only full corpus (CPU): ~0.4 s × 1446 ≈ **10 min** (ignoring I/O).  
OCR dominates cost.

---

## 3. OCR throughput scenarios

Assumptions: PP-OCRv5 **mobile** det+rec; full-page det + per-box rec; conservative bands pending spike.

| Environment | Est. wall time / doc (2 pp) | 1,446 docs | Interactive? | SLA fit |
|---|---|---|---|---|
| Local CPU (dev host) | **15–90 s** | 6–36 h serial | No | Dev/spike only |
| Cloud CPU 4 vCPU | 8–40 s | 3–16 h | No | Overnight batch |
| Cloud GPU (single modern GPU) | **2–8 s** | 1–3 h | Marginal | Batch + near-interactive |
| GPU pool (N workers) | wall ≈ serial/N | scales linearly until queue overhead | Yes with N | R1 target |

Numbers **must be replaced** by `scripts/run_spike.py` matrix (CPU section required; GPU section when available).

---

## 4. Production placement (decision)

| Path | Role |
|---|---|
| Local laptop | Dev, unit/integration tests, spike CPU matrix, annotation tooling |
| On-prem Docker `cpu-runtime` | Small offline installs; demo; low volume |
| **Cloud GPU workers** (`gpu-runtime`) | **Production OCR** — required for market SLA (locked decision) |
| Ollama/VLM | Not in R0 path; optional R2 handwriting hybrid only if ADR updates |

`docs/adr/adr-003-cloud-gpu-workers.md` records the decision.

---

## 5. Cost sketch (order-of-magnitude; refine on spike + cloud quotes)

Let \( t_g \) = GPU seconds/doc (target ≤8 s), \( D \) = docs.

| Config | Rough compute | Notes |
|---|---|---|
| 1× GPU worker | \( 8s × D \) GPU-seconds | e.g. 10k docs ≈ 22 GPU-hours |
| Throughput goal | ≥ **500 docs/GPU-hour** after warm models | = 7.2 s/doc average |
| Local CPU only | laborious for 1,446 | use for 10-doc smoke only |

Storage: PDF ~70–80 KB → corpus ~110 MB; crops larger (order 0.5–2 MB/doc) — object-store lifecycle + retention (`market-roadmap` privacy).

---

## 6. Latency tiers (product)

| Tier | Use | Target (R1 design, not yet measured) |
|---|---|---|
| Smoke fixture | CI | < 60 s end-to-end CPU |
| Single doc GPU | API sync-ish | p95 < 15 s extract compute |
| Batch 1k | Offline | < 2 h on 1 GPU (validate post-spike) |
| Review path | Human | no compute SLA; queue depth metric |

---

## 6.5 Optimization lever register

Performance levers that could move throughput/latency but are **not yet evaluated**. Listed so they are tracked decisions, not forgotten optimizations. None are assumed in the estimates above; each is a spike/benchmark item (mirrored in `docs/research-gaps.md`).

| Lever | Expected effect | Status | Evaluate in | Gap |
|---|---|---|---|---|
| **GPU vs CPU** | ~5–10× (15–90s → 2–8s/doc) | decided (ADR-003), unmeasured | spike GPU section (when hardware available) | RG-01 |
| **Model tier** (mobile vs server rec) | accuracy↑ vs latency↑ | undecided | spike C5 tie-break | RG-02 |
| **Quantization** (int8/fp16 rec/det) | latency↓, mem↓, possible accuracy cost | **never evaluated** | perf spike post-pin | RG-26 |
| **Batching** (multi-page / multi-doc per GPU call) | throughput↑ via GPU utilization | not designed | R1 perf spike | RG-23-adjacent |
| **Warm model pool** (avoid cold-load per doc) | assumed in ≥500 docs/GPU-hr goal | assumed, unvalidated | R1 worker design | — |
| **I/O cost** (PDF read, crop write, object store) | **excluded from current throughput math** | unmeasured | perf spike | RG-27 |
| **Render DPI** (lower DPI = faster, accuracy risk) | latency↓ | pinned at 200 (spike-tunable) | spike + accuracy E-series | RG-01 |
| **Parallelism N workers** | wall ≈ serial/N until queue overhead | modeled, not built | R1 queue design | RG-23 |

> Rule: no lever is "banked" in a capacity claim until a spike/benchmark measures it. The GPU 2–8s and ≥500 docs/GPU-hr figures are **targets**, not measured — `scripts/run_spike.py` replaces them.

---


- Promise accuracy or auto-accept rates (see `docs/accuracy-plan.md`).
- Pin CUDA/driver versions (spike matrix / ADR-003 / Dockerfile post-spike).
- Assume multi-tenant fair-share before R1 queue design exists.

---

## 8. Update log

| Date | Change |
|---|---|
| 2026-09-24 | Initial: host metrics, render timings, region estimate, corpus size, placement decision |
| 2026-09-27 | Added §6.5 optimization lever register (quantization, batching, I/O, warm pool — flagged unmeasured); linked levers to `research-gaps.md` |
