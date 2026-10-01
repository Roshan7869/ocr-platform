# SLOs / SLIs — ocr-platform

Service Level Objectives and Service Level Indicators. What we promise, how we measure it, and what happens when we miss.

**Invariant:** `FINAL_VALUE MUST NEVER EXIST WITHOUT PROVENANCE`
**Template:** `FAMILY_SURVEY_V1` · **Milestones:** R0 → R0.5 → R1 → R2

---

## 1. Definitions

| Term | Meaning |
|---|---|
| **SLI** | Service Level Indicator — the measurement itself (e.g., p95 latency) |
| **SLO** | Service Level Objective — the target for an SLI (e.g., p95 < 15s) |
| **Error budget** | The allowed unreliability over a time window (e.g., 0.1% of requests) |
| **Window** | The rolling time period over which the SLO is measured (e.g., 7 days) |

---

## 2. R0 SLOs (local CLI, single-operator)

| SLI | SLO | Measurement | Window | Consequence of miss |
|---|---|---|---|---|
| Extract latency (CPU) | p95 < 120s | `run_ms` from `run.complete` | Per run | Investigate; not user-facing |
| Provenance completeness | 100% on accepted | `provenance_fail_total == 0` | Any run | Stop deployment |
| Determinism | 100% identical | Canonical JSON byte-equal across N=3 | Per commit | Fix before merge |
| Review rate | ≤40% | `disposition_total{review} / fields_evaluated_total` | Per run | Tune thresholds |
| R0 exit gate | All gates green | `ruff` + `pytest` + smoke + provenance | Per PR | No merge |

---

## 3. R0.5 SLOs (affine registration, dev-gold measured)

| SLI | SLO | Measurement | Window | Consequence of miss |
|---|---|---|---|---|
| Affine residual pass rate | ≥95% | Pages with residual < threshold / total pages | Per run | Tune affine anchors |
| Row recall | ≥0.95 | Correct rows / total rows (vs manual) | Per dev-gold set | Tune row detection |
| Row precision | ≥0.95 | Correct rows / detected rows | Per dev-gold set | Tune row detection |
| Handwriting accepted | 0 | `disposition_total{accepted}` where `HANDWRITING_SUSPECTED` | Any run | Stop deployment |
| Review rate (dev-gold) | ≤40% | `disposition_total{review} / fields_evaluated_total` | Per dev-gold run | Tune thresholds |

---

## 4. R1 SLOs (async API, GPU workers)

| SLI | SLO | Measurement | Window | Consequence of miss |
|---|---|---|---|---|
| Extract latency (GPU) | p95 < 15s | `run_ms` from `run.complete` | 7-day rolling | Page on-call |
| Throughput | ≥500 docs/GPU-hour | `docs_processed_total / GPU-hours` | 24h | Investigate bottleneck |
| Availability | 99.5% | Successful jobs / total jobs | 7-day rolling | Page on-call |
| Provenance violations | 0 | `provenance_fail_total` | Any run | Stop deployment |
| Review rate | ≤40% | `disposition_total{review} / fields_evaluated_total` | Per run | Tune thresholds |
| Queue depth | <100 | Jobs in queue | Real-time | Add workers |
| Error rate | <1% | `disposition_total{errored} / docs_processed_total` | 7-day rolling | Investigate |

---

## 5. R2 SLOs (review console, multi-tenant)

| SLI | SLO | Measurement | Window | Consequence of miss |
|---|---|---|---|---|
| Review turnaround | p95 < 24h | Time from review candidate to resolution | 7-day rolling | Add reviewers |
| Correction accuracy | ≥99% | Correct corrections / total corrections | Per batch | Retrain reviewers |
| Multi-tenant isolation | 0 cross-tenant leaks | Audit log review | Any run | Stop deployment |
| Availability | 99.9% | Successful requests / total requests | 7-day rolling | Page on-call |

---

## 6. Error budget policy

| SLO | Error budget | Action at 50% burn | Action at 100% burn |
|---|---|---|---|
| Extract latency (GPU) | 0.5% of requests >15s | Investigate; tune | Freeze deployments |
| Availability | 0.5% failed requests | Investigate; fix | Freeze deployments |
| Provenance violations | 0 | N/A | Stop deployment immediately |
| Review rate | 0% above 40% | Tune thresholds | Freeze deployments |

---

## 7. Measurement points

| SLI | Where measured | How |
|---|---|---|
| Extract latency | `run.complete` event | `run_ms` histogram |
| Provenance completeness | `provenance.fail` event | `provenance_fail_total` counter |
| Review rate | `run.complete` event | `disposition_total{review} / fields_evaluated_total` |
| Throughput | `run.complete` event | `docs_processed_total / GPU-hours` |
| Availability | API gateway | Successful requests / total requests |
| Queue depth | Queue | Jobs in queue (real-time) |
| Error rate | `run.complete` event | `disposition_total{errored} / docs_processed_total` |

---

## 8. Launch criteria

| Milestone | SLO that must hold | Duration | Before next milestone |
|---|---|---|---|
| R0 | All R0 SLOs | 1 week | R0.5 |
| R0.5 | All R0.5 SLOs | 1 week | Calibration |
| Calibration | All R0.5 SLOs + calibration report | 1 week | R1 |
| R1 | All R1 SLOs | 2 weeks | R2 |
| R2 | All R2 SLOs | 2 weeks | GA |

---

## 9. Related documents

- Capacity: `docs/capacity.md`
- Accuracy plan: `docs/accuracy-plan.md`
- Observability: `docs/observability.md`
- Runbook: `docs/runbook.md`
- Market roadmap: `docs/market-roadmap.md`
