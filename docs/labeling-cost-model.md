# Labeling cost model — ocr-platform

Throughput model and cost estimates for gold labeling. Build the model now, validate with real measurements when the labeling tool exists.

**Invariant:** `FINAL_VALUE MUST NEVER EXIST WITHOUT PROVENANCE`
**Template:** `FAMILY_SURVEY_V1` · **Milestones:** R0 → R0.5 → R1 → R2

---

## 1. Model

```
labeling_time = (fields_per_doc × time_per_field) + overhead_per_doc
```

Where:
- `fields_per_doc` = ~344 (from `capacity.md`: ~64 checkbox options + ~10 page-1 text + up to 15×18=270 table cells)
- `time_per_field` = conservative estimate: 10 seconds (includes reading crop, typing value, submitting)
- `overhead_per_doc` = 5 minutes (navigation, verification, saving)

**Per-document time:**
```
(344 fields × 10s) + 300s overhead = 3,440s + 300s = 3,740s ≈ 62 min/doc
```

---

## 2. Stage estimates

| Stage | N docs | Time/doc | Total hours | Notes |
|---|---|---|---|---|
| Smoke | 5-10 | 62 min | 5-10 h | CI green on smoke |
| Dev-gold | 20-30 | 62 min | 21-31 h | Registration/row iteration |
| Calibration | 50-100 | 62 min | 52-103 h | Flag-flip evidence |
| Holdout | 30-50 | 62 min | 31-52 h | Promotion only |
| Full corpus | 1,446 | 62 min | 1,494 h | Deferred |

---

## 3. Validation plan

When the labeling tool exists:
1. Have one labeler label 5 docs
2. Measure actual time/doc
3. Update `time_per_field` and `overhead_per_doc` with measured values
4. Recompute stage estimates
5. If actual time is >2x estimate, investigate: is the tool slow? Are fields ambiguous? Is the labeler trained?

---

## 4. Cost optimization levers

| Lever | Expected effect | Cost | Milestone |
|---|---|---|---|
| **Pre-fill from OCR** | Reduce time_per_field for high-confidence fields | Medium (build pre-fill UI) | R0.5 |
| **Batch labeling** | Reduce overhead_per_doc | Low (tooling) | R0.5 |
| **Double-key only critical fields** | Reduce QA time | Low (process) | R0.5 |
| **Outsource labeling** | Parallelize but adds management overhead | High (cost) | Calibration |
| **Active learning** | Label only uncertain fields first | Medium (tooling) | R2 |

---

## 5. Quality model

| Metric | Target | Measurement |
|---|---|---|
| Labeler error rate | <5% | Double-key 10% subset |
| Inter-annotator agreement | >90% | Cohen's kappa or similar |
| Disagreement resolution | 100% | Adjudication by survey owner |

**Impact on calibration:**
- If labeler error rate is 5%, the 97% precision target for auto-accept is effectively 97% / 0.95 = 102% — impossible.
- Therefore, labeler error rate must be <3% for the 97% precision target to be achievable.
- If labeler error rate is >3%, either:
  - Improve training and tooling to reduce errors, or
  - Adjust the precision target (requires survey owner sign-off)

---

## 6. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Labeling takes longer than estimated | Medium | High | Validate model early with 5-doc pilot |
| Labeler error rate >3% | Medium | High | Improve training, add validation to tool |
| Labeler availability limited | High | Medium | Start labeling early; outsource if needed |
| Field catalog changes during labeling | Low | High | Freeze catalog before labeling starts |

---

## 7. Update log

| Date | Change |
|---|---|
| 2026-09-27 | Initial cost model from capacity.md estimates; validation plan defined |
