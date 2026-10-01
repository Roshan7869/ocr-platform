# Annotation workflow — ocr-platform

Human-in-the-loop process for template boundary annotation. Defines who annotates, how QA works, and how approved boundaries get into the template package.

**Invariant:** `FINAL_VALUE MUST NEVER EXIST WITHOUT PROVENANCE`
**Template:** `FAMILY_SURVEY_V1` · **Milestones:** R0 → R0.5 → R1 → R2

---

## 1. Roles

| Role | Who | Responsibility |
|---|---|---|
| **Annotator** | Survey staff or trained contractor | Draw bboxes on rendered pages |
| **Reviewer** | Survey owner or senior annotator | QA annotator work; resolve ambiguities |
| **Approver** | Survey owner | Final sign-off; approves hash into manifest |
| **Engineer** | Engineering | Build tool, enforce format, integrate into template package |

---

## 2. Tool interface

### 2.1 Input

- Rendered page image (from `scripts/annotate_template.py` or web UI)
- Page identifier (page_1 or page_2)
- Existing boundaries (if re-annotating)

### 2.2 Interaction

| Action | Description |
|---|---|
| **Draw bbox** | Click and drag to create a rectangle |
| **Edit bbox** | Click to select; drag corners to resize |
| **Delete bbox** | Select and press Delete |
| **Assign class** | Select bbox → choose class from dropdown (FIELD, CHECKBOX_OPTION, etc.) |
| **Assign field_id** | Select bbox → enter field_id from catalog |
| **Zoom** | Scroll to zoom; drag to pan |
| **Save** | Export to YAML |

### 2.3 Output

- YAML file matching `page_1_boundaries.yaml` / `page_2_boundaries.yaml` schema
- Each entry: `field_id`, `boundary_class`, `bbox` (normalized coordinates), `page_index`

---

## 3. Annotation guidelines

### 3.1 bbox rules

| Rule | Description |
|---|---|
| **Tight fit** | bbox should tightly enclose the field region |
| **Include label** | For checkbox options, include the label text if it's part of the region |
| **Exclude neighboring fields** | bbox should not overlap adjacent field regions |
| **Consistent class** | Same field type gets same boundary_class across pages |

### 3.2 Edge cases

| Case | Resolution |
|---|---|
| Field spans two pages | Annotate on both pages; note in `notes` field |
| bbox is unclear | Annotator flags for reviewer; reviewer decides |
| Field is conditional (e.g., "other" text) | Annotate only if it appears on the form |
| Table rows | Annotate row boundaries, not individual cells |

### 3.3 Quality standards

| Standard | Target |
|---|---|
| bbox accuracy | ±2 pixels at 200 DPI |
| Class accuracy | 100% (reviewer verifies) |
| field_id accuracy | 100% (reviewer verifies) |
| Completion | 100% of fields annotated |

---

## 4. QA process

### 4.1 Review workflow

1. Annotator completes a page
2. Reviewer checks:
   - All fields have bboxes
   - bboxes are tight and accurate
   - Classes are correct
   - field_ids match catalog
3. Reviewer flags issues → annotator fixes
4. Reviewer approves page

### 4.2 Spot check

- Reviewer spot-checks 10% of approved pages
- If error rate >5%, full re-review required
- Errors are logged and fed back to annotator training

### 4.3 Inter-annotator agreement (optional)

- For critical fields, have two annotators annotate independently
- Measure agreement (e.g., IoU >0.80)
- Disagreements resolved by reviewer

---

## 5. Approval flow

```text
Annotator completes page
    → Reviewer QA
        → Reviewer approves
            → Approver sign-off
                → Engineer hashes into template_manifest.json
                    → Template package is synthetic_baseline_approved
```

---

## 6. Estimated time

| Task | Time per page | Notes |
|---|---|---|
| Annotate page 1 | 2-4 hours | ~64 checkbox options + ~10 text fields |
| Annotate page 2 | 3-6 hours | ~270 table cells + legend |
| Review page 1 | 1-2 hours | |
| Review page 2 | 2-3 hours | |
| Spot check | 0.5 hours | |
| **Total per page** | **3.5-10.5 hours** | |
| **Total for 2 pages** | **7-21 hours** | |

---

## 7. Integration into template package

1. Engineer receives approved YAMLs
2. Engineer validates against `field_catalog.json` (every field_id has a boundary)
3. Engineer checks for overlaps and gaps
4. Engineer hashes YAMLs into `template_manifest.json`
5. Engineer sets `approval_scope: synthetic_baseline_approved`
6. Template package is ready for R0 extraction

---

## 8. Update log

| Date | Change |
|---|---|
| 2026-09-27 | Initial annotation workflow spec |
