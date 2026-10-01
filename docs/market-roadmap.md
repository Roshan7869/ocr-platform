# Market roadmap — phased path to revenue-ready extraction

**Form factor (locked):** phased — **R0/R0.5 on-prem CLI/container** → **R1 thin async API + privacy** → **R2 review console + multi-tenant SaaS hardening**.

**Honest status:** after R0 the product is a *provenance-correct offline extractor with auto-accept disabled* — **not** market-ready. Gates below define readiness.

---

## Phase map

```text
R0 kernel ──► R0.5 accuracy ──► calibration ──► R1 thin slice ──► R2 review + multi-tenant
   │               │                  │               │                    │
   └─ docs+data    └─ affine+hand     └─ flip flags   └─ API+GPU+privacy   └─ HITL+SLO
      gates           posture            (evidence)      (first revenue path)   (scale)
```

Depends on: `docs/data-plan.md` (inputs), `docs/accuracy-plan.md` (quality), `docs/capacity.md` (cost/latency).

---

## R0 — Offline extraction kernel

| Deliverable | Notes |
|---|---|
| Spike matrix + model pins | gate before paddle in runtime |
| 41-file implementation | per `docs/files` specs |
| CLI extract + provenance-valid JSON + review JSON | on-prem first form |
| Docker cpu-runtime | non-root; pins post-spike |
| Auto-accept **off** | commercial extraction value deferred |

**Not in R0:** API, DB, auth, review UI, multi-tenant, billing, calibrated accept.

**Exit gate:** smoke fixture end-to-end; provenance completeness 100% on accepted; ruff/pytest green.

---

## R0.5 — Accuracy that can be sold

| Deliverable | Gate (`docs/accuracy-plan.md`) |
|---|---|
| Affine registration + residual | ≥95% pages pass on classified set |
| Handwriting review-only enforced | 0 hand fields auto-accepted |
| Dynamic row metrics | recall/precision ≥0.95 on layout refs |
| Dev-gold baseline | review-rate + precision published |

**Exit:** accuracy-plan R0.5 gates green. Still no SaaS.

---

## Calibration — before any “auto-extract” claim

| Deliverable | Gate |
|---|---|
| Calibration gold ≥50 docs + holdout ≥30 | data-plan |
| Field precision on would-be auto-accept ≥97% | accuracy-plan |
| Policy version bump; flags flipped only with report | acceptance_policy_v1 |

---

## R1 — Thin market slice (first revenue-capable)

Design targets (specs to author under `docs/files/service/*` when implementation starts; outline now):

### API (async)

| Endpoint | Behavior |
|---|---|
| `POST /v1/extractions` | Upload PDF or reference; returns `job_id`; auth token |
| `GET /v1/extractions/{id}` | `queued\|running\|succeeded\|failed` + counts |
| `GET /v1/extractions/{id}/result` | canonical JSON (PII controls applied) |
| `GET /v1/extractions/{id}/review` | review-candidate payload |

- Idempotency: client key or content hash + config fingerprint (`run_id`).
- Queue: local threadpool (slice) → Redis/SQS (hardened).
- Workers: GPU image `gpu-runtime`; scale-out = N workers.

### Persistence (minimal)

- Jobs table: id, tenant, status, run_id, timestamps, error.
- Artifacts: object store keys for PDF + crops + result (encrypted at rest).
- Optional decisions store — can remain file-backed for slice.

### Privacy (minimal viable)

| Control | Slice |
|---|---|
| Auth | bearer / API key per tenant |
| TLS | terminate at edge |
| At-rest encryption | PDF + result + crops |
| Retention TTL | configurable; default short for demo |
| Logs | no raw field values; no unredacted PII |
| Fixture vs production paths | production never uses unclassified loader mode without explicit allow |

### Ops

| Item | Target |
|---|---|
| p95 extract compute (GPU) | < 15 s (validate) |
| Docs/GPU-hour | ≥ 500 after warm (validate) |
| Health + structured logs | run_id correlation |
| Metrics | queue depth, fail rate, review rate, provenance violations |

**R1 exit (thin slice definition):**

1. Classified PDF in → provenance-valid result over API.  
2. Review list retrievable (JSON or minimal HTML list + crops).  
3. GPU image builds; capacity numbers updated from real run.  
4. Privacy checklist above implemented for single tenant.  
5. Calibration flags state matches accuracy report.

---

## R2 — Review product + scale hardening

| Area | Scope |
|---|---|
| Review console | assignment, crops side-by-side, correction submit |
| Human correction | `HumanCorrectionEvidence` + `DecisionRevision` (never overwrite OCR) |
| Multi-tenant | isolation, RBAC, per-tenant templates/keys |
| SLO + alerting | latency, queue, provenance violation = page |
| Handwriting hybrid | optional VLM/fine-tune path (new ADR before accept) |
| Template multi-version ops | still hash-rooted; alias/rollback ideas from manifest spec |

---

## Explicit non-goals until gates pass

- Multi-tenant SaaS GA, billing, marketplace  
- Auto-accept on handwriting  
- Full 1,446-doc gold labeling  
- Identity registration marketed as corpus-ready  
- Spinning paddle pins without spike matrix  

---

## Scoreboard (market dimensions)

| Dimension | Now | After R0 | After R0.5+calib | After R1 slice | After R2 |
|---|---|---|---|---|---|
| Market readiness | 2/10 | 3/10 | 5/10 | **6/10** | **8/10** |
| Ops | 3/10 | 6/10 | 6/10 | 7/10 | 8/10 |
| Accuracy | 4/10 | 5/10 | **7–8/10** | 8/10 | 8/10 |
| Data | 1/10 | 5–6/10 | 8/10 | 8/10 | 9/10 |

---

## Spec backlog (author when leaving docs-only phase)

Under `docs/files/` (each with sibling `.md` in same change when code lands):

1. `service/api.py` — FastAPI routes  
2. `service/jobs.py` — queue abstraction  
3. `service/auth.py` — API keys  
4. `service/store.py` — object store + encryption hooks  
5. `service/db.py` — jobs persistence  
6. `service/review_api.py` — review payload / R2 console API  
7. `scripts/calibrate_policy.py` — metrics for flag flip  
8. `scripts/split_gold.py` — document-level splits  

Until then this roadmap + `architecture.md` sequences 6–7 are the design SoT.

---

## Update log

| Date | Change |
|---|---|
| 2026-09-24 | Initial phased roadmap (on-prem → API → SaaS); R1 thin-slice definition; non-goals |
