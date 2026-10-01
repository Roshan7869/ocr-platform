# Architecture — ocr-platform

System design SoT for R0–R2. Per-file contracts remain authoritative under `docs/files/`; this document owns layer boundaries, data flow, trust boundaries, and deployment views. Decisions: `docs/adr/`.

**Invariant:** `FINAL_VALUE MUST NEVER EXIST WITHOUT PROVENANCE`  
**Template:** `FAMILY_SURVEY_V1` · **Milestones:** R0 → R0.5 → R1 → R2 (see `docs/market-roadmap.md`)

---

## 1. Component map

```text
                    ┌─────────────────────────────────────────────────────────┐
                    │                     TRUST BOUNDARY                     │
  untrusted PDF ───►│  L1 Ingest                                             │
  (PII, attacker)   │  fixtures/loader ─► render/renderer ─► coordinates      │
                    │       │ capability matrix (scanned/native/…)            │
                    └───────┼─────────────────────────────────────────────────┘
                            ▼
                    ┌─────────────────────────────────────────────────────────┐
                    │  L2 Template (hash-rooted package)                     │
                    │  manifest ─► registration (identity | affine R0.5)      │
                    │           ─► boundaries (typed bboxes, INTERSECT cells) │
                    └───────┼─────────────────────────────────────────────────┘
                            ▼
                    ┌─────────────────────────────────────────────────────────┐
                    │  L3 Extract                                            │
                    │  paddle/engine (det+rec) ─► OcrObservation              │
                    │  paddle/marks (checkbox/ditto geometry)                 │
                    │  extraction/normalizer ─► vocabulary ─► acceptance_policy│
                    └───────┼─────────────────────────────────────────────────┘
                            ▼
                    ┌─────────────────────────────────────────────────────────┐
                    │  L4 Validate + Attest                                  │
                    │  validation/rules + cross_field                         │
                    │  state_machine (legal transitions only)                 │
                    │  provenance/hashing + validator (integrity gate)        │
                    └───────┼─────────────────────────────────────────────────┘
                            ▼
                    ┌─────────────────────────────────────────────────────────┐
                    │  L5 Output                                              │
                    │  export/json_export (Household/Member/EducationRecord)  │
                    │  export/review_candidates (uncertain → human)           │
                    │  worker/pipeline (single-process orchestrator R0)       │
                    └─────────────────────────────────────────────────────────┘

  schemas/* = shared types (job, evidence, decision, provenance) — no I/O
  configs/* = runtime.yaml + acceptance_policy_v1.yaml (fingerprinted)
```

| Layer | Responsibility | Must NOT do |
|---|---|---|
| L0 schemas | Types + enum vocabularies | I/O, OCR, policy |
| L1 ingest | Bytes → pixels, classification, coords | Template, OCR |
| L2 template | Geometry + approval + registration | OCR, accept |
| L3 extract | Evidence production + normalize + policy inputs | Accept without policy |
| L4 attest | Rules, transitions, provenance gate | Invent evidence |
| L5 output | Canonical JSON + review file | Bypass validator |

---

## 2. Data flow (R0 happy path)

```text
PDF bytes
  → sha256 → document_content_hash
  → capability classify (scanned|native|mixed|encrypted|corrupt|empty)
  → render (DPI/colorspace from runtime.yaml) → PageArtifact + RenderMetadata
  → load template_manifest (child hashes + approval scope)
  → registration: identity (+ page-box normalize) [R0]; affine residual [R0.5]
  → boundaries: page-space regions + INTERSECT cells + quality signals
  → parallel evidence:
        text path:  paddle det+rec → OcrObservation
        mark path:  marks.py → mark/Region evidence
        native path: NativeTextEvidence (digital PDFs; inactive on pure scans)
  → normalizer (profile by field_types) → raw preserved
  → vocabulary resolve → code|unknown
  → validation rules + cross_field (incl. ditto derived ops)
  → acceptance_policy → disposition + reason_codes + accepted_by
  → provenance validator (hard fail → demote to review/exception)
  → state_machine terminal states
  → json_export + review_candidates
```

**R0 outputs are in-memory + files.** Persistence/queue/API are R1 (`docs/market-roadmap.md`).

---

## 3. Trust boundaries

| Boundary | Crossing | Control |
|---|---|---|
| External PDF → loader | untrusted bytes, PII | `fixture_manifest` classification (synthetic \| approved_redacted), content hash, expiry; raw path requires `--allow-unclassified` |
| Loader → pipeline | classified path only | hash verify; no wildcards |
| Pipeline → export | decisions | provenance validator zero-tolerance on accepted |
| Export → disk/network | PII fields (name, mobile, address) | R0 local paths only; R1 encryption-at-rest + redaction mode (see `json_export` / `review_candidates` specs + market-roadmap privacy) |
| Template package → runtime | config | hash root; approval scope gates (`synthetic_baseline_approved` vs `production_approved`) |
| Policy flags | auto-accept | `ocr_auto_accept_enabled` / `native_auto_accept_enabled` default false until calibration evidence (`docs/accuracy-plan.md`) |

**Non-goals R0:** multi-tenant auth, secrets in image, network calls from validation (master lists are fixture files).

---

## 4. Deployment views

### 4.1 Local dev / spike (current machine class)

- CPU-only laptop class (measured: 2c/4t ~2.3GHz i5, 15GB RAM, no GPU).
- Render ~0.4–1.5s / 2 pages; OCR via Paddle **mobile** models CPU — OK for spike + single-doc smoke; **not** production SLA.
- `python scripts/extract.py --fixture <id> --out runs/`.

### 4.2 On-prem container (R0.5–R1 product form)

```text
docker build -f docker/Dockerfile --target cpu-runtime .
docker run -v fixtures:/data -v out:/out image --fixture smoke-001 --out /out
```

- Non-root; configs + templates baked; PDFs mounted (not baked).
- GPU variant: `--target gpu-runtime` (CUDA base + pinned paddle) — post-spike pins (`docs/adr/adr-003`).

### 4.3 Cloud GPU workers (R1 async API — production OCR)

```text
Client ─► API (auth, tenant) ─► object store (PDF) ─► job queue
                │                                         │
                │              ┌──────────────────────────┘
                ▼              ▼
           status/result ◄─ GPU worker pool (extract container)
                │              │
                ▼              ▼
           review UI (R2)   provenance-valid JSON + crops
```

- Local CPU = dev/spike only; capacity model: `docs/capacity.md`.
- Horizontal scale = more workers; one run_id per (document hash, config fingerprint) — retries do not mint new runs (`schemas/job.py`).

---

## 5. Milestone boundaries (what ships when)

| Milestone | In scope | Out of scope |
|---|---|---|
| **R0** | Single-process extract on classified fixtures; identity registration; provenance complete; auto-accept **off**; CLI + JSON files | API, DB, review workflow, affine, calibrated accept |
| **R0.5** | Affine registration + residual; handwriting posture; dynamic-row metrics met; smoke/dev-gold accuracy measured | SaaS, multi-tenant |
| **R1** | Async extraction API (thin slice), job store, object storage, GPU image, privacy hooks, calibration gate to flip accept flags | Full review console, billing |
| **R2** | Review console + human correction provenance, multi-tenant isolation, retention, SLOs | Marketplace templates (R5) |

---

## 6. Cross-cutting concerns

| Concern | Where owned |
|---|---|
| Coordinate algebra | `worker/render/coordinates.py` only |
| Content addressing | `worker/provenance/hashing.py` only |
| Accept/review thresholds | `configs/acceptance_policy_v1.yaml` + evaluator |
| Per-field trigger applicability | `templates/.../review_triggers.yaml` |
| Field catalog / vocab SoT | `templates/family_survey_v1/*` (survey-owned content) |
| Model pins | `worker/paddle/models.py` after `scripts/run_spike.py` |
| Capacity / cost | `docs/capacity.md` |
| Accuracy gates | `docs/accuracy-plan.md` |
| Data governance | `docs/data-plan.md` |
| Test strategy / fail-closed gates | `docs/testing-plan.md` |
| Observability / audit (provenance = audit trail) | `docs/observability.md` + ADR-007 |
| Security / threat model | `docs/threat-model.md` |
| Error / review / exit codes | `docs/reason-codes.md` |
| Terminology | `docs/glossary.md` |
| Open questions (spike / experiment / sign-off) | `docs/research-gaps.md` |
| Revenue path | `docs/market-roadmap.md` |

---

## 7. Related documents

- Sequences: `docs/sequences.md`
- Capacity: `docs/capacity.md`
- Accuracy: `docs/accuracy-plan.md`
- Data: `docs/data-plan.md`
- Testing: `docs/testing-plan.md`
- Observability: `docs/observability.md`
- Threat model: `docs/threat-model.md`
- Reason codes: `docs/reason-codes.md`
- Glossary: `docs/glossary.md`
- Research gaps: `docs/research-gaps.md`
- Market: `docs/market-roadmap.md`
- ADRs: `docs/adr/`
- Per-file index: `docs/files/README.md`
