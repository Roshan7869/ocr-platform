# Runbook — ocr-platform

Alert-to-action mapping for operational response. When something fires, this doc tells you what to check and what to do.

**Invariant:** `FINAL_VALUE MUST NEVER EXIST WITHOUT PROVENANCE`
**Template:** `FAMILY_SURVEY_V1` · **Milestones:** R0 → R0.5 → R1 → R2

---

## 1. Alert-to-action table

| Signal | Likely cause | Check | Action |
|---|---|---|---|
| `provenance.fail` | Hash mismatch or missing evidence | `validator_reason` field in log | Re-run with same config. If persists, check template hashes in `template_manifest.json` |
| `REGISTRATION_RESIDUAL_HIGH` | Scan quality or template mismatch | `residual` value in `page.registered` event | If residual > threshold on all pages, check template version. If only some pages, check scan quality |
| `ENCRYPTED_PDF` | Expected for unredacted fixtures | `fixture_manifest` classification | Verify classification is correct. If misclassified, update manifest |
| `CORRUPT_PDF` | PDF parse failure | `document_content_hash` | Verify file integrity. If hash matches manifest, check rasterizer version |
| `EMPTY_DOCUMENT` | Zero usable pages | `run.classify` event | Check if PDF is actually empty or if classifier is mis-firing |
| `PAGE_SET_MISMATCH` | Wrong template or page count | `page.registered` events | Verify template version matches fixture. Check if PDF has unexpected page count |
| `UNKNOWN_VOCABULARY_CODE` | Value not in vocabulary | `field.decision` event | Check if vocabulary is missing codes. If so, update `vocabularies.yaml` |
| `HANDWRITING_SUSPECTED` | Handwriting detected on text field | `field.review` event | Expected behavior. Route to review queue |
| `ROW_UNDERSEGMENT` / `ROW_OVERSEGMENT` | Row detection failure | `field.review` event | Check if table geometry is correct. May need boundary adjustment |
| `DITTO_UNRESOLVED` | Unresolved "same-as-above" mark | `field.review` event | Check if ditto column is correctly identified in `cross_field_rules.yaml` |
| Queue depth growing | Worker capacity or poison pill | `run.complete` events | Check if workers are stuck. If poison pill, quarantine job |
| `provenance_fail_total > 0` | Provenance violation | `provenance.fail` events | Stop deployment. Investigate before any further processing |

---

## 2. Top 5 failure modes

### 2.1 Provenance violation

**Symptom:** `provenance.fail` event with `validator_reason` field.

**Diagnostic:**
1. Check `validator_reason` for specific failure type
2. If `missing_evidence`: check if evidence nodes were created
3. If `hash_mismatch`: check if template or config changed without fingerprint bump
4. If `wrong_evidence_type`: check if value_state matches evidence type

**Resolution:**
- Re-run with same config: `python scripts/extract.py --fixture <id> --out runs/retry`
- If persists, check template hashes: `python scripts/verify_template.py`
- If config changed, bump fingerprint in `runtime.yaml`

**Escalation:** If provenance violation affects accepted values, stop deployment immediately.

### 2.2 Registration failure

**Symptom:** `REGISTRATION_RESIDUAL_HIGH` on multiple pages.

**Diagnostic:**
1. Check `residual` value in `page.registered` event
2. If residual > 0.1 (10% of page width), check scan quality
3. If residual varies wildly, check if template version matches fixture
4. If all pages fail, check if affine anchors are correctly defined

**Resolution:**
- If scan quality: re-scan or adjust DPI in `runtime.yaml`
- If template mismatch: update `template_version` in fixture manifest
- If affine anchors: adjust anchor regions in `page_1_boundaries.yaml` / `page_2_boundaries.yaml`

**Escalation:** If >50% of pages fail registration, halt batch processing.

### 2.3 Handwriting review explosion

**Symptom:** Review rate >40% due to `HANDWRITING_SUSPECTED`.

**Diagnostic:**
1. Check `review_reason_total{HANDWRITING_SUSPECTED}` metric
2. If >30% of text fields, handwriting is prevalent
3. Check if handwriting signal is over-firing (false positives)

**Resolution:**
- If false positives: tune handwriting detection threshold in `engine.py`
- If true positives: route to review queue; consider VLM-assisted review (R2)
- If >50%: escalate to product; may need to adjust milestone timeline

**Escalation:** If review rate exceeds 50%, escalate to survey owner for guidance.

### 2.4 Queue backlog

**Symptom:** Queue depth growing faster than processing rate.

**Diagnostic:**
1. Check `docs_processed_total` vs `pages_rendered_total` ratio
2. If ratio is low, workers are stuck or slow
3. Check `run_ms` histogram for latency regression
4. Check if poison pill job is blocking queue

**Resolution:**
- If stuck workers: restart workers
- If poison pill: quarantine job, investigate root cause
- If latency regression: check for dependency drift or resource contention
- If capacity: add workers (horizontal scale)

**Escalation:** If queue depth >1000, escalate to infra.

### 2.5 Config drift

**Symptom:** Results change without code changes.

**Diagnostic:**
1. Check `configuration_fingerprint` in `run.start` event
2. If fingerprint changed, config was modified
3. Check `runtime.yaml` and `acceptance_policy_v1.yaml` for changes
4. Check if model pins changed in `models.py`

**Resolution:**
- If intentional: document change in update log
- If unintentional: revert config, bump fingerprint, re-run
- If model pins: re-run spike matrix to verify compatibility

**Escalation:** If config drift affects accepted values, stop deployment.

---

## 3. Escalation path

| Issue | First responder | Escalate to | When |
|---|---|---|---|
| Provenance violation | On-call eng | Engineering lead | Immediately |
| Registration failure | On-call eng | Template owner | If >50% pages fail |
| Handwriting explosion | On-call eng | Survey owner | If review rate >50% |
| Queue backlog | On-call eng | Infra | If depth >1000 |
| Config drift | On-call eng | Engineering lead | If accepted values affected |
| Template mismatch | On-call eng | Survey owner | If template version unknown |

---

## 4. Operational metrics

| Metric | Warning | Critical | Action |
|---|---|---|---|
| `provenance_fail_total` | >0 | >0 | Stop deployment |
| `disposition_total{review} / fields_evaluated_total` | >30% | >50% | Tune thresholds or escalate |
| `run_ms` p95 | >30s | >60s | Investigate latency regression |
| Queue depth | >100 | >1000 | Add workers or investigate |
| `REGISTRATION_RESIDUAL_HIGH` rate | >5% | >20% | Check template or scan quality |

---

## 5. Related documents

- Observability: `docs/observability.md`
- Reason codes: `docs/reason-codes.md`
- Accuracy plan: `docs/accuracy-plan.md`
- Capacity: `docs/capacity.md`
- Threat model: `docs/threat-model.md`
