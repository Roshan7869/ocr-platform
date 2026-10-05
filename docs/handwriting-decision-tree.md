# Handwriting decision tree — ocr-platform

Decision framework for handwriting posture based on prevalence. Design now, fill in numbers after E3 experiment.

**Invariant:** `FINAL_VALUE MUST NEVER EXIST WITHOUT PROVENANCE`
**Template:** `FAMILY_SURVEY_V1` · **Milestones:** R0 → R0.5 → R1 → R2

---

## 1. Current posture (ADR-004)

- Handwriting suspected on text field → `disposition=review` only
- No print-model auto-accept on pen strokes
- Checkbox marks use geometric path (not OCR)
- Dedicated handwriting rec / fine-tune / VLM is R2+

---

## 2. Decision tree

```
E3 experiment: measure handwriting prevalence on dev-gold
    │
    ├─ <10% of text fields
    │   └─ Proceed with review-only posture
    │       └─ Monitor review rate; if >30%, tune handwriting detection threshold
    │
    ├─ 10-30% of text fields
    │   └─ Build triage path
    │       ├─ High-confidence handwriting → review with "likely correct" hint
    │       └─ Low-confidence handwriting → review with "needs attention" flag
    │       └─ Consider VLM-assisted review (human confirms VLM suggestion)
    │
    └─ >30% of text fields
        └─ Escalate to product
            ├─ Option A: Build VLM-assisted review (faster than manual)
            ├─ Option B: Outsource handwriting transcription
            └─ Option C: Adjust milestone timeline (R2 handwriting path earlier)
```

---

## 3. E3 experiment design

| Aspect | Detail |
|---|---|
| **Goal** | Measure handwriting prevalence on dev-gold |
| **Sample** | 20-30 docs from dev-gold set |
| **Method** | Manual review of all text fields; label as print/hand/uncertain |
| **Output** | Prevalence %, error taxonomy (substitution classes, field types) |
| **Owner** | Survey owner + engineering |
| **Timeline** | After R0.5 affine registration is stable |

---

## 4. Triage path (if 10-30%)

### 4.1 High-confidence handwriting

- OCR confidence >90%
- Handwriting signal is strong
- Reviewer sees: crop + OCR value + "likely correct" hint
- Reviewer action: confirm or correct

### 4.2 Low-confidence handwriting

- OCR confidence <90%
- Handwriting signal is weak
- Reviewer sees: crop + OCR value + "needs attention" flag
- Reviewer action: manual entry

### 4.3 VLM-assisted review (optional)

- A vision model may suggest a transcription. Laya is a text-only decision model:
  in the current experiment it classifies occupation text after OCR, and cannot
  read handwriting from a crop.
- Reviewer sees: crop + VLM suggestion + "confirm or correct" prompt
- Reviewer action: confirm or correct

---

## 5. Economic analysis

| Handwriting % | Review rate impact | Product viability | Action |
|---|---|---|---|
| <10% | <10% | Viable | Proceed |
| 10-30% | 10-30% | Viable with triage | Build triage |
| 30-50% | 30-50% | Marginal | Escalate; consider VLM |
| >50% | >50% | Not viable | Escalate; adjust timeline |

---

## 6. Related documents

- ADR-004: `docs/adr/adr-004-handwriting-posture.md`
- Accuracy plan: `docs/accuracy-plan.md §2`
- Research gaps: `docs/research-gaps.md` (RG-13, RG-14)

---

## 7. Update log

| Date | Change |
|---|---|
| 2026-09-27 | Initial decision tree; E3 experiment design; economic analysis |
