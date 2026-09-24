# docs/files — per-file responsibility index

One `.md` per planned file. Mirror tree of the repo. Contract: [`TEMPLATE.md`](TEMPLATE.md).

**Status legend:** `SPEC` = authored, code not landed · `IMPLEMENTED` = code exists · `VERIFIED` = GitNexus coverage + role check passed.

**Invariant:** `FINAL_VALUE MUST NEVER EXIST WITHOUT PROVENANCE` · Template: `FAMILY_SURVEY_V1` · Milestone scope: **R0 only**.

## Index (41 targets)

| # | Path | Role (summary) | Entity / notes | Status |
|---|------|----------------|----------------|--------|
| 1 | `src/ocr_platform/schemas/job.py` | DocumentRun, PageArtifact, capability matrix, run identity | document | SPEC |
| 2 | `src/ocr_platform/schemas/evidence.py` | Ocr/Native/Region/Human evidence + EvidenceSet + bbox coord_system | — | SPEC |
| 3 | `src/ocr_platform/schemas/decision.py` | FieldDecision, orthogonal scope/value_state/disposition/reason_codes | maps 8-label states | SPEC |
| 4 | `src/ocr_platform/schemas/provenance.py` | Provenance graph nodes/edges, content hashes | — | SPEC |
| 5 | `src/ocr_platform/worker/pipeline.py` | R0 single-process orchestrator | — | SPEC |
| 6 | `src/ocr_platform/worker/state_machine.py` | Explicit job/page/field transitions | — | SPEC |
| 7 | `src/ocr_platform/worker/render/renderer.py` | Deterministic PDF→page image + metadata | — | SPEC |
| 8 | `src/ocr_platform/worker/render/coordinates.py` | PDF↔image, normalized/pixel, crop-local transforms | — | SPEC |
| 9 | `src/ocr_platform/worker/template/manifest.py` | Load hash-root manifest, approval scopes | — | SPEC |
| 10 | `src/ocr_platform/worker/template/boundaries.py` | Typed bboxes, overlap≥0.80, INTERSECT cells | all classes | SPEC |
| 11 | `src/ocr_platform/worker/template/registration.py` | R0 identity transform; R3 affine stub | LEGEND/ANCHOR | SPEC |
| 12 | `src/ocr_platform/worker/paddle/engine.py` | Paddle det+rec adapter → OcrObservation | — | SPEC |
| 13 | `src/ocr_platform/worker/paddle/models.py` | Pinned model registry (post-spike) | — | SPEC |
| 14 | `src/ocr_platform/worker/paddle/marks.py` | Checkbox/glyph/ditto mark evidence | CHECKBOX_* | SPEC |
| 15 | `src/ocr_platform/worker/extraction/normalizer.py` | Type-specific profiles, raw preserved | — | SPEC |
| 16 | `src/ocr_platform/worker/extraction/vocabulary.py` | H/M religion, gender, caste, resident 1–6… | versioned codes | SPEC |
| 17 | `src/ocr_platform/worker/extraction/acceptance_policy.py` | AcceptancePolicy-v1 evaluator | — | SPEC |
| 18 | `src/ocr_platform/worker/validation/rules.py` | Deterministic per-field checks | — | SPEC |
| 19 | `src/ocr_platform/worker/validation/cross_field.py` | Conditional rules, ditto expansion + provenance op | — | SPEC |
| 20 | `src/ocr_platform/worker/provenance/validator.py` | Portable integrity gate pre-export | — | SPEC |
| 21 | `src/ocr_platform/worker/provenance/hashing.py` | Canonical JSON + sha256 content addressing | — | SPEC |
| 22 | `src/ocr_platform/export/json_export.py` | Household/Member/EducationRecord canonical JSON | entities | SPEC |
| 23 | `src/ocr_platform/export/review_candidates.py` | Review-candidate JSON (crop + reasons) | — | SPEC |
| 24 | `src/ocr_platform/fixtures/loader.py` | Classification/expiry/hash gate for fixtures | — | SPEC |
| 25 | `scripts/run_spike.py` | Compatibility go/no-go matrix | gate | SPEC |
| 26 | `scripts/extract.py` | CLI / Docker ENTRYPOINT | — | SPEC |
| 27 | `scripts/annotate_template.py` | Bbox annotation over WARD-42 95–99.pdf | authoring | SPEC |
| 28 | `configs/runtime.yaml` | DPI, colorspace, coordinate convention, compare policy | fingerprint | SPEC |
| 29 | `configs/acceptance_policy_v1.yaml` | Thresholds, hard reasons, R0 OCR/native gates off | fingerprint | SPEC |
| 30 | `templates/family_survey_v1/template_manifest.json` | Hash root + approval envelope | package root | SPEC |
| 31 | `templates/family_survey_v1/field_catalog.json` | Every field_id + entity + examples | **OWNER: survey** | SPEC |
| 32 | `templates/family_survey_v1/page_1_boundaries.yaml` | Admin + checkbox group bboxes | document+household | SPEC |
| 33 | `templates/family_survey_v1/page_2_boundaries.yaml` | Table + 18 columns + legend | member+education | SPEC |
| 34 | `templates/family_survey_v1/table.yaml` | Dynamic row algorithm params | TABLE_* | SPEC |
| 35 | `templates/family_survey_v1/field_types.yaml` | Type/profile per field_id | — | SPEC |
| 36 | `templates/family_survey_v1/vocabularies.yaml` | Religion/gender/caste/resident/option codebooks | versioned | SPEC |
| 37 | `templates/family_survey_v1/validation_rules.yaml` | Per-field deterministic rules | — | SPEC |
| 38 | `templates/family_survey_v1/cross_field_rules.yaml` | Conditionals + ditto columns + non-inference | — | SPEC |
| 39 | `templates/family_survey_v1/review_triggers.yaml` | Per-field trigger applicability (no thresholds) | — | SPEC |
| 40 | `fixtures/fixture_manifest.json` | Classification gate for all PDFs | **OWNER: survey** (redaction) | SPEC |
| 41 | `docker/Dockerfile` | Pinned reproducible image (post-spike) | — | SPEC |

## Layout references (external, not in 41)

- `~/Documents/WARD-42/1RN-982-WARD NO-42/95.pdf`–`99.pdf`
- `~/Documents/WARD-42/11RN-985-WARD NO-42/95.pdf`–`99.pdf`

Register in `fixtures/fixture_manifest.json` before loader use.

## Loop (Phase 5–6)

```bash
cd /home/roshan/ocr-platform && npx gitnexus analyze   # or node .gitnexus/run.cjs analyze
node .gitnexus/run.cjs status
```

1. Coverage Cypher: `src/**` File nodes ↔ this tree — 0 unpaired  
2. Role: `context(file_path=…)` vs **Depends on**  
3. Infra: `impact(upstream)` — no undeclared importers  
4. Template: every `boundary_class` in YAML ↔ boundaries/marks docs  
5. Flip `Status: VERIFIED` or open fix task  

**New `src/**` or `templates/**` file ⇒ sibling `.md` in the same change.** Test `.md`s author with their test files during implementation.
