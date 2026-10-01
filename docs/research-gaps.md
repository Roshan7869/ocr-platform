# Research gaps — ocr-platform

Consolidated register of genuine **unknowns** — questions that need a spike, experiment, measurement, or external sign-off before a decision can be locked. This is the single backlog of open questions; individual docs (spike, `accuracy-plan` E1–E4, ADRs) own the *work*, this file owns the *tracking* so nothing stays implicitly "TBD".

**Invariant:** `FINAL_VALUE MUST NEVER EXIST WITHOUT PROVENANCE`
**Template:** `FAMILY_SURVEY_V1` · **Milestones:** R0 → R0.5 → R1 → R2 (see `docs/market-roadmap.md`)

> **Blocking column:** `R0` = must close before R0 extraction ships · `flip` = blocks the calibration flag-flip (auto-accept) · `R0.5`/`R1`/`R2+` = blocks that milestone. Closing a gap = record the answer in the **Resolved by** artifact and flip Status to `closed` with a date.

---

## 1. Compatibility spike (the single largest R0 gate)

| ID | Open question | Resolved by | Blocking | Cite |
|---|---|---|---|---|
| RG-01 | Exact Python / PaddleOCR / PaddlePaddle / CUDA + det/rec model revisions & checksums | `scripts/run_spike.py` go/no-go matrix | R0 | `run_spike.py.md:5` |
| RG-02 | v3 vs v5 rec model — which one? | spike C5 tie-break | R0 | `models.py.md:13`, `engine.py.md:11` |
| RG-03 | Python 3.11 target vs host 3.12.3 reconciliation | spike C4 | R0 | `capacity.md:15` |
| RG-04 | Models downloaded at runtime vs baked (RACE strategy) | spike C8 | R0 | `Dockerfile.md:24`, `run_spike.py.md:5` |
| RG-05 | Rasterizer pin — pypdfium2 stays or amended? | spike C6 (ADR-001 review) | R0 | `adr-001:5` |

## 2. Pre-code accuracy baselines (E1–E4)

| ID | Open question | Resolved by | Blocking | Cite |
|---|---|---|---|---|
| RG-06 | Normalize + identity residual on 10 refs + 20 random | Experiment E1 | R0 | `accuracy-plan.md:48` |
| RG-07 | Form-line / ruling detectability for affine anchors | Experiment E2 | R0.5 | `accuracy-plan.md:49` |
| RG-08 | Dynamic row ink-projection vs manual counts (10 refs) | Experiment E4 | R0 | `accuracy-plan.md:51` |
| RG-09 | Dynamic row-count detection (no hardcoded pitch) | E4 + `annotate_template.py` | R0 | `annotate_template.py.md:16` |
| RG-10 | Geometry reconciliation across refs 95–99 (union/approved layout) | annotate pass, recorded | R0 | `annotate_template.py.md:13` |

## 3. Registration threshold (R0.5)

| ID | Open question | Resolved by | Blocking | Cite |
|---|---|---|---|---|
| RG-11 | Affine residual threshold value (the "≥95% pages pass" cutoff) | E2 anchor feasibility → `registration.py` | R0.5 | `accuracy-plan.md:40`, `registration.py.md:15` |
| RG-12 | `overlap_ratio >= 0.80` — confirm or retune empirically | benchmark before production | R0.5 | `acceptance_policy.py.md:14`, `boundaries.py.md:11` |

## 4. Handwriting

| ID | Open question | Resolved by | Blocking | Cite |
|---|---|---|---|---|
| RG-13 | Handwriting accuracy on this corpus (probe) | Experiment E3 | R0 baseline → R0.5 posture | `accuracy-plan.md:50`, `adr-004:9` |
| RG-14 | Dedicated handwriting rec / fine-tune / VLM path | new ADR + calibration evidence | R2+ | `adr-004:16`, `accuracy-plan.md:64` |

## 5. Calibration & flag-flip (accuracy, not compatibility)

| ID | Open question | Resolved by | Blocking | Cite |
|---|---|---|---|---|
| RG-15 | 97% auto-accept precision — **survey-owner sign-off** | calibration report §4.3 + sign-off | flip | `accuracy-plan.md:122`, `adr-005:16` |
| RG-16 | Gold set (≥50–100 labeled, ≥30 holdout) does not exist yet | data collection + labeling | flip | `accuracy-plan.md:120-121` |
| RG-17 | Dev-gold review-rate ceiling (start ≤40%, lower over time) | first dev-gold baseline | flip | `accuracy-plan.md:123` |

## 6. Data governance

| ID | Open question | Resolved by | Blocking | Cite |
|---|---|---|---|---|
| RG-18 | Redaction method + approver identity (explicit **Open**) | survey owner decision | R0 (first `approved_redacted`) | `data-plan.md:71` |
| RG-19 | `role=layout_ref` label — finalize (currently proposed) | fixture manifest registration | R0 | `data-plan.md:138` |
| RG-20 | Template package `synthetic_baseline_approved` sign-off | eng + survey approval | R0 | `template_manifest.json.md:12`, `data-plan.md:91` |
| RG-21 | Bulk 1,446-doc redaction + storage policy | redaction capacity + lifecycle | R2+ (deferred) | `data-plan.md:56`, `data-plan.md:113` |

## 7. Later-milestone (stated, not yet designed)

| ID | Open question | Resolved by | Blocking | Cite |
|---|---|---|---|---|
| RG-22 | Async API / job store / object storage specs | `docs/files/service/*` when impl starts | R1 | `market-roadmap.md:63`, `:148-159` |
| RG-23 | Queue design + multi-tenant fair-share | R1 queue design | R1/R2 | `capacity.md:97`, `market-roadmap.md:75` |
| RG-24 | Template alias→immutable-hash + activation/rollback | R5 | R5 | `manifest.py.md:14`, `template_manifest.json.md:14` |
| RG-25 | Online threshold learning (Laya) | R4/R5 | R4+ | `adr-005:30`, `vocabulary.py.md:14` |
| RG-26 | Model quantization — never evaluated | perf spike (see `capacity.md` register) | R1 (perf) | *(no doc; gap noted)* |
| RG-27 | I/O cost — excluded from throughput estimate, unmeasured | perf spike | R1 (perf) | `capacity.md:35` |

---

## How to close a gap

1. Do the work in the **Resolved by** artifact (spike matrix, experiment log, calibration report, ADR, sign-off).
2. Record the concrete answer *there* (numbers, pins, decisions) — not here.
3. Flip the row's Status to `closed (YYYY-MM-DD → <artifact>)` in the update log below.
4. If the answer changes a locked decision, open/append an ADR.

## Update log

| Date | Change |
|---|---|
| 2026-09-27 | Initial register consolidated from spec audit (spike, E1–E4, calibration, data governance, deferred milestones); added RG-26 quantization + RG-27 I/O perf gaps |

---

## Related documents

- Spike criteria: `docs/files/scripts/run_spike.py.md`
- Accuracy gates + experiments: `docs/accuracy-plan.md`
- Perf levers: `docs/capacity.md` (Optimization Lever Register)
- Data governance: `docs/data-plan.md`
- Decisions: `docs/adr/`
- Glossary: `docs/glossary.md`
