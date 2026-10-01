# Accuracy plan — registration, handwriting, dynamic rows, calibration

Addresses the weakest feasibility area. Targets are **gates** for milestone exit, not aspirations. Metrics land in spike/report artifacts and `docs/files` test lists.

**Evidence base (2026-09-24 measurements):**

| Finding | Implication |
|---|---|
| All WARD-42 PDFs: 0-char text layer, 1-bit grayscale image/page | Pure OCR path; native path dormant for this corpus |
| Page width range ~79pt (sample); image width range ~219px | Identity registration misaligns across series |
| Page0 pixel corr: same batch ≈0.48–0.79; cross-batch ≈0.14–0.55; random corpus vs base often **<0.30** (min ≈ −0.01) | Content (fill) dominates pixels; must register **form structure** |
| Ink density stable ≈0.11–0.15 | Same printed template; safe to pursue structure-based affine |
| Horizontal stroke runs p50≈3px on table band | Thin pen/print mix — handwriting is a first-class risk |
| ~344 candidate field evals/doc | Per-field metrics are meaningful even on small N |

---

## 1. Registration

### 1.1 Strategy (locked)

| Phase | Mode | Scope | Gate |
|---|---|---|---|
| **R0** | `identity` + **canonical page-box normalize** (explicit, recorded) | Layout refs / smoke only | Boundary assignment works on 10 refs; non-refs may high-review |
| **R0.5** | **Classical affine** (form rulings, table grid, LEGEND/ANCHOR) + **residual threshold** | All classified fixtures | Residual pass rate + field review rate targets below |
| R3+ | Full enhanced registration (historical R3) | Production refinements | Supersedes R0.5 as needed |

**Forbidden:** silent deskew in R0; accepting fields when registration invalid; claiming corpus readiness on identity alone.

### 1.2 Specs

- `registration.py`: R0 identity contract retained; **R0.5 affine contract added** (transform + residual + fail-closed).
- `coordinates.py`: page normalize helper as **allowed explicit op** (not silent deskew); provenance records op.
- `boundaries.py`: consumes registered page only.

### 1.3 Metrics (R0.5 exit)

| Metric | Target |
|---|---|
| Residual (affine) within threshold on classified fixture set | ≥ **95%** pages pass |
| Field-level review rate due to boundary/registration reasons (dev-gold) | ≤ **15%** (tune after first baseline) |
| Identity-only baseline recorded | Must publish before/after for ADR evidence |

### 1.4 Experiment log

| ID | Experiment | Status |
|---|---|---|
| E1 | Normalize + identity residual on 10 layout refs + 20 random | **Planned** (pre-code measurement) |
| E2 | Form-line / ruling detectability for affine anchors | **Planned** |
| E3 | Handwriting probe on filled text fields | **Planned** (post-spike OCR or crop review) |
| E4 | Dynamic row ink-projection vs manual counts on 10 refs | **Planned** |

Results append here + feed `registration.py` / `table.yaml` specs.

---

## 2. Handwriting

### 2.1 Posture (locked — ADR-004)

1. **Detect:** optional signal `handwriting_suspected` on FIELD crops (stroke heuristics / low print-model confidence / ink density anomaly).
2. **R0/R0.5:** suspected handwriting text fields → **`disposition=review` only**. No print-model auto-accept.
3. **Checkbox / marks:** geometric path in `marks.py` remains primary (not OCR of question text).
4. **Later (R2):** dedicated handwriting rec, fine-tune, or VLM/hybrid — separate ADR before enabling accept.
5. Codes/lists: religion/gender/caste etc. still go through vocabulary — unknown stays unknown.

### 2.2 Specs touched

`engine.py` (signal on observation), `marks.py` (non-interference), `acceptance_policy` + `acceptance_policy_v1.yaml` (hard review if suspected), `review_candidates` (reason present).

### 2.3 Metrics

| Metric | R0.5 target |
|---|---|
| Print-field auto-accept precision (when gate on) | ≥ **97%** on calibration set |
| Handwriting fields accepted without human path | **0** |
| E3 error taxonomy | Documented (substitution classes, field types) |

---

## 3. Dynamic table rows

### 3.1 Algorithm contract (already in specs — metrics added)

```text
rows    = FIND_POPULATED_ROWS(data_region)   # ink projection / separators / pitch
cells   = INTERSECT(row.bbox, column.bbox)
records = PROCESS_CELL only for populated rows; blank tail → no Member
fail    → page review (never invent rows)
```

### 3.2 Metrics (R0 exit on layout refs)

| Metric | Target |
|---|---|
| Row **recall** vs manual annotation (10 layout refs) | ≥ **0.95** |
| Row **precision** | ≥ **0.95** |
| Blank trailing rows → fake records | **0** |
| row_key uniqueness within run | 100% |

Over/under-segmentation taxonomy: `ROW_UNDERSEGMENT`, `ROW_OVERSEGMENT`, `ROW_UNCERTAIN` → review reasons (canonical registry: `docs/reason-codes.md §2.4`).

---

## 4. Calibration & auto-accept

### 4.1 Flags

R0 (`configs/acceptance_policy_v1.yaml`):

- `ocr_auto_accept_enabled: false`
- `native_auto_accept_enabled: false`

Flip only via **versioned policy change** + fingerprint bump after calibration evidence.

### 4.2 Calibration gate (required before flip)

| Requirement | Detail |
|---|---|
| Gold N | ≥ **50** field-level labeled documents (prefer 100), document-level split |
| Holdout | ≥ **30** docs never used for threshold tuning |
| Metric | Field-level **precision** on auto-accepted values ≥ **97%** (proposed — **survey-owner sign-off pending**, tracked in `docs/research-gaps.md`) |
| Review rate | ≤ ceiling agreed on dev-gold (start: **≤40%** fields, lower over time) |
| Provenance | 100% completeness on accepted (already hard gate) |
| Record | Calibration report path stored; policy version bumped |

**No spike-only flip.** Spike proves *compatibility*; calibration proves *accuracy*.

### 4.3 Calibration report (schema)

The report recorded at flip time (`configs/acceptance_policy_v1.yaml` version bump references its hash). Normative shape:

```json
{
  "report_version": "1",
  "generated_at": "<ISO-8601>",
  "policy_version_under_test": "AcceptancePolicy-v1",
  "configuration_fingerprint": "<hash>",
  "gold_set": { "labeled_docs": 100, "holdout_docs": 30, "split_by": "document" },
  "metrics": {
    "auto_accept_precision": 0.0,        // must be >= 0.97 (pending survey-owner sign-off) to flip
    "review_rate": 0.0,                   // must be <= agreed dev-gold ceiling (start <= 0.40)
    "provenance_completeness_on_accepted": 1.0   // hard gate: exactly 1.0
  },
  "per_field_type": [ { "field_type": "<id>", "precision": 0.0, "n": 0 } ],
  "sign_off": { "survey_owner": "<name|PENDING>", "engineering": "<name>", "date": "<ISO-8601>" },
  "decision": "flip|hold"                 // flip requires all thresholds met AND survey_owner != PENDING
}
```

Flip is rejected in tests without this report + `sign_off.survey_owner` set (ADR-005; `acceptance_policy_v1.yaml.md:39`).

---

## 5. Gold-set sizes (from data-plan)

| Stage | N | Accuracy use |
|---|---|---|
| Smoke | 5–10 | Regression, not promotion |
| Dev-gold | 20–30 | Iterate registration/rows |
| Calibration | 50–100 | Thresholds / flag flip |
| Holdout | 30–50 | Promotion claims only |

Full 1,446-doc gold is **out of scope** until product requires it.

---

## 6. Milestone accuracy gates (summary)

| Exit | Gate |
|---|---|
| R0 | Smoke extract works; provenance 100% on accepted; E1–E4 baselines recorded; no auto-accept claim |
| R0.5 | Affine residual ≥95% pass; row metrics met; handwriting review-only enforced; dev-gold review-rate baseline published |
| Flag flip | Calibration precision/review gates + policy version bump |
| Market slice (R1) | Numbers above + capacity spike latency on target GPU |

---

## 7. Update log

| Date | Change |
|---|---|
| 2026-09-24 | Initial plan from corpus measurements + locked decisions (identity→R0.5 affine, handwriting review-only, calibration before accept) |
| 2026-09-27 | Added calibration-report schema (§4.3); flagged 97% precision as survey-owner-sign-off-pending (→ `research-gaps.md`); linked row reasons to `reason-codes.md` |
