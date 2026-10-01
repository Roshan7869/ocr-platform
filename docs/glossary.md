# Glossary — ocr-platform

Single definition source-of-truth for cross-cutting terms used across the specs. When a term is *owned* by a specific file (its authoritative shape lives there), the **Owner** column points at it; this glossary only gives the one-line meaning so readers stop re-deriving it per doc.

**Invariant:** `FINAL_VALUE MUST NEVER EXIST WITHOUT PROVENANCE`
**Template:** `FAMILY_SURVEY_V1` · **Milestones:** R0 → R0.5 → R1 → R2 (see `docs/market-roadmap.md`)

> Convention: `UPPER_SNAKE` tokens are codes — their firing conditions and dispositions live in `docs/reason-codes.md`, not here.

---

## 1. Run identity & fingerprinting

| Term | Meaning | Owner |
|---|---|---|
| **run_id (tuple)** | Immutable run identity `= (document_content_hash, configuration_fingerprint)`. One run per (bytes, config); retries reuse it. | `schemas/job.py` |
| **document_content_hash** | `sha256(exact_uploaded_pdf_bytes)` in R0/R1. Identifies the input, not the run. | `schemas/job.py` |
| **configuration_fingerprint** | Hash over runtime config + policy version + template hashes + model pins. Second half of the run_id tuple. | `schemas/job.py` + `configs/*` |
| **document_semantic_fingerprint** | Optional distinct field for semantic dedupe; **never** replaces run identity. | `schemas/job.py` |
| **retry** | A re-attempt recorded as a separate record under the same run_id — never a new run. | `schemas/job.py` |

---

## 2. Capability classification (PageClass)

| Term | Meaning | Owner |
|---|---|---|
| **capability matrix** | Per-page classification into one of the classes below; drives which evidence paths run. | `schemas/job.py` |
| **scanned_only / native_only / mixed** | Page has raster only / digital text layer only / both. | `schemas/job.py` |
| **encrypted / corrupt / empty** | Terminal document conditions → `disposition=errored` before any field decision (`ENCRYPTED_PDF` / `CORRUPT_PDF`). | `schemas/job.py` |
| **page-set mismatch** | Rendered page set doesn't match the template's expected pages (`PAGE_SET_MISMATCH`). | `state_machine.py` |

---

## 3. Template geometry & registration

| Term | Meaning | Owner |
|---|---|---|
| **boundary classes** | Typed region kinds: `FIELD` · `CHECKBOX_OPTION` · `CHECKBOX_GROUP` · `TABLE` · `TABLE_ROW` · `TABLE_CELL` · `LEGEND` · `ANCHOR`. | `template_manifest.json` |
| **LEGEND** | A region carrying the form's code legend (e.g. resident_status codes 1–6); used for identity sanity and hard cross-checks. | `templates/family_survey_v1/*` |
| **ANCHOR** | A stable structural region used for identity sanity (R0) and as an affine anchor (R0.5+). | `worker/template/registration.py` |
| **registration mode: identity** | R0 default: explicit identity transform + recorded canonical page-box **normalize** (not silent deskew) + LEGEND/ANCHOR sanity. | `worker/template/registration.py` |
| **registration mode: affine** | R0.5: classical affine from form structure (rulings, table grid, anchors), fail-closed on high residual. | `worker/template/registration.py` |
| **residual** | Post-registration geometric error in **normalized page-space units** (0-1 range, where 1.0 = full page width). Above the R0.5 threshold (or ambiguous anchors) ⇒ page review (`REGISTRATION_RESIDUAL_HIGH`). | `worker/template/registration.py` |
| **affine (DoF)** | Affine transform with **6 degrees of freedom** (translation x/y, rotation, scale x/y, shear). R0.5 uses classical affine from form structure (rulings, table grid, anchors). | `worker/template/registration.py` |
| **page-box normalize** | Explicit transform that maps the PDF's native page box to a canonical frame (e.g., letter-size equivalent). Recorded in provenance as an explicit op — never silent. Distinct from deskew. | `worker/render/coordinates.py` |
| **canonical page-box normalize** | The specific normalize op used in R0: maps variable page boxes (~79pt width range) to a canonical size before identity registration. Recorded in provenance. | `worker/render/coordinates.py` |
| **INTERSECT cell** | A table cell bbox computed as `INTERSECT(row_bbox, col_bbox)` — never guessed. | `worker/template/boundaries.py` |
| **overlap_ratio** | Text-box → field-region assignment metric. Formula: `intersection_area(text_box, field_region) / area(text_box)`. Provisional threshold `>= 0.80` (benchmarked before production). | `worker/extraction/acceptance_policy.py` |
| **coordinate_system** | Explicit frame stamped on every bbox (`image_top_left_normalized` for page-space); crop-local coords stored separately, never mixed. | `worker/render/coordinates.py` |

---

## 4. Evidence

| Term | Meaning | Owner |
|---|---|---|
| **EvidenceSet** | The set of immutable, content-addressed evidence nodes a decision resolves through. A final value is unwritable unless its `source_set` resolves through a valid EvidenceSet. | `schemas/evidence.py` |
| **OcrObservation** | OCR evidence node: det+rec model versions, raw OCR confidence, render/preprocess metadata, field/row/col IDs. | `schemas/evidence.py` |
| **NativeTextEvidence** | `SourceEvidence` from a digital PDF text layer — not an OCR observation. | `schemas/evidence.py` |
| **RegionEvidence** | Proof of an empty / unreadable / not_applicable region; required to store those value states. | `schemas/evidence.py` |
| **HumanCorrectionEvidence** | Human-correction evidence node (later milestones / R2 review console). | `schemas/evidence.py` |
| **ditto** | A "same-as-above" mark in a table column; resolved by a recorded derived operation, never silently. Unresolved ⇒ review (`DITTO_UNRESOLVED`). | `worker/validation/cross_field.py` |

---

## 5. Decision vocabulary (orthogonal status)

These four axes are **kept separate** — never collapsed into one overloaded status enum.

| Term | Meaning | Owner |
|---|---|---|
| **scope** | Which level a decision applies to: document / page / field / cell. | `schemas/decision.py` |
| **value_state** | State of the value itself: `present` · `absent` · `unknown` · `unreadable` · `not_applicable`. Missing ≠ `""`. | `schemas/decision.py` |
| **disposition** | Outcome: `accepted` · `review` · `rejected` · `errored`. | `schemas/decision.py` |
| **reason_codes** | Multi-label set explaining a disposition (see `docs/reason-codes.md`). | `schemas/decision.py` |
| **primary_reason** | The single reason chosen by documented precedence from the multi-label set. | `schemas/decision.py` + `configs/acceptance_policy_v1.yaml` |
| **accepted_by** | What accepted a value: `policy` (auto) vs normalized/human — distinguishes `AUTO_ACCEPTED` from `NORMALIZED_ACCEPTED` (both store `disposition=accepted`). | `schemas/decision.py` |
| **acceptance_policy_version** | Version string (`AcceptancePolicy-v1`) stamped on every accepted decision. | `configs/acceptance_policy_v1.yaml` |
| **DecisionRevision** | Append-only correction record; corrections never overwrite a prior decision (R2 fills human path). | `schemas/decision.py` |
| **BOUNDARY_EXPAND** | A *proposal action*, never a field disposition. | `schemas/decision.py` |

---

## 6. Acceptance, calibration & gates

| Term | Meaning | Owner |
|---|---|---|
| **AcceptancePolicy-v1** | Versioned artifact of thresholds, the hard-review reason list, and global gates. Immutable once used in a run. | `configs/acceptance_policy_v1.yaml` |
| **auto-accept flags** | `ocr_auto_accept_enabled` / `native_auto_accept_enabled` — **false** in R0 until spike-go + calibration report flip them (config change + fingerprint bump). | `configs/acceptance_policy_v1.yaml` |
| **calibration gate** | Separate accuracy gate (ADR-005) that must pass on a labeled gold set before auto-accept can be enabled. Distinct from the compatibility spike. | `docs/accuracy-plan.md` |
| **fail-closed** | Default posture: uncertainty routes to review, never to silent accept. | ADR-005 |
| **hard-review reason** | A reason that forces `disposition=review` regardless of confidence. | `configs/acceptance_policy_v1.yaml` |

---

## 7. Provenance & lifecycle

| Term | Meaning | Owner |
|---|---|---|
| **FINAL_VALUE rule** | The platform invariant: no final value may exist without a provenance chain back to evidence. | `docs/architecture.md` |
| **provenance validator** | Zero-tolerance integrity gate; a hard fail demotes a decision to review/exception. | `worker/provenance/validator.py` |
| **canonical JSON** | Deterministic serialization (sorted keys, fixed number formatting, UTF-8) used for hashing and cross-run comparison. | `worker/provenance/hashing.py` |
| **state_machine** | Explicit legal job/page/field transitions; illegal transitions raise (no silent no-op). | `worker/state_machine.py` |

---

## 8. Data governance & approval scopes

| Term | Meaning | Owner |
|---|---|---|
| **approval scope** | Template package trust level gating what a run may claim: `synthetic_baseline_approved` (R0 runs) vs `production_approved` (needs benchmark + regression + security + human sign-off). | `templates/family_survey_v1/template_manifest.json` |
| **classification (fixtures)** | A PDF's data-governance label: `synthetic` \| `approved_redacted`; the loader is fail-closed on anything else. | `fixtures/fixture_manifest.json` · `docs/data-plan.md` |
| **--allow-unclassified** | Explicit opt-in flag to run a raw/unclassified path; marks the run `user_input`. R0 default-deny for production-like files. | `scripts/extract.py` |
| **layout reference** | A classified fixture used to measure registration/row accuracy (the WARD-42 95–99 batches). | `docs/data-plan.md` |
| **gold labels** | Human-labeled field values used to calibrate/validate accuracy; none exist yet. | `docs/accuracy-plan.md` |

---

## 9. Spike & tooling

| Term | Meaning | Owner |
|---|---|---|
| **compatibility spike** | Dated go/no-go run that pins Python/PaddleOCR/PaddlePaddle/CUDA + det/rec model revisions **before** R0 extraction. Proves *compatibility*, not accuracy. | `scripts/run_spike.py` |
| **model pins** | Exact model revisions+checksums recorded only after the spike matrix passes — no unpinned `latest` at runtime. | `worker/paddle/models.py` |
| **RACE strategy** | Runtime-artifact-vs-baked deployment choice for models/container, decided by the spike. | `scripts/run_spike.py` · `docker/Dockerfile` |

---

## Related documents

- Reason & exit codes: `docs/reason-codes.md`
- Architecture: `docs/architecture.md`
- Accuracy gates: `docs/accuracy-plan.md`
- Data governance: `docs/data-plan.md`
- Capacity: `docs/capacity.md`
- ADRs: `docs/adr/`
- Per-file index: `docs/files/README.md`
