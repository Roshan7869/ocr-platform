# Data plan — fixtures, template content, gold labels, privacy

Owner split: **survey** = field catalog, codebooks, bbox approval, redaction approval · **engineering** = schemas, loader, tooling, labeling pipeline.

**Current state (2026-09-24):** `fixtures/` empty · `templates/family_survey_v1/` empty · 0 gold labels · 1,446 unclassified PDFs outside repo under `~/Documents/WARD-42/`.

---

**2026-10-03 update:** The 1,446 PDFs are now available locally under
`data/WARD-42/WARD-42/`, as a pilot sample of a wider corpus in the lakhs.
They remain unclassified and are not registered production fixtures. The
independent evaluation workflow in `docs/benchmark.md` permits local annotation
and benchmark experiments; API upload requires classified inputs plus explicit
opt-in. No gold answers are inferred from the mere presence of these files.

## 1. Principles

**2026-10-05 local experiment scope:** The user authorized inspecting the local
data and running fine-tuning pilots. These experiments may read unclassified
local PDFs without registering them as production fixtures. Engineering visual
drafts and synthetic prototypes are not human gold, require explicit pilot
mode, and stay local with crop evidence. Model outputs are never training truth.
Production fixture/redaction approvals and independent-label QA remain required.

1. **No pipeline open** of real survey PDFs without manifest classification (`synthetic` \| `approved_redacted`).
2. **No git commit** of real PDFs until classification + path policy allow (`.gitignore` already blocks `*.pdf` except `fixtures/**/*.pdf`).
3. Smoke ≠ gold; promotion claims need holdout (`fixtures/loader.py`, `docs/accuracy-plan.md`).
4. Splits are **document-level**.
5. Template geometry from **annotation**, not prose (`annotate_template.py`).

---

## 2. Fixture classification (C1)

### 2.1 Manifest schema (authoritative fields)

Per entry (also specified in `docs/files/fixtures/fixture_manifest.json.md`):

```json
{
  "fixture_id": "ward42-1rn982-095",
  "path": "fixtures/pdf/ward42/1rn982/095.pdf",
  "content_hash_sha256": "…",
  "classification": "synthetic | approved_redacted",
  "source_owner": "…",
  "redaction_method": "… | null-if-synthetic",
  "redaction_approver": "… | null-if-synthetic",
  "allowed_storage_location": "…",
  "expiry": "ISO-8601",
  "template_version": "FAMILY_SURVEY_V1",
  "split": "train | calibration | test | holdout | null",
  "role": "smoke | gold | layout_ref",
  "ward_batch": "1RN-982 | 11RN-985 | null",
  "notes": "…"
}
```

Top level: `{ "schema_version": 1, "fixtures": [ … ] }`.

Loader rejects: missing fields, unknown classification, expired, hash mismatch, path outside allowed, wildcard-only entries.

### 2.2 Staged registration

| Stage | Docs | Action |
|---|---|---|
| **Now** | 10 layout refs (both batches 95–99) | Schema seed + entries **pending survey classification** (synthetic redraw or approved_redacted + approver) |
| Smoke | 5 | After redaction path; `role=smoke` |
| Dev-gold | 20–30 | `split=train` or `calibration` |
| Bulk 1,446 | — | **Blocked** on redaction capacity + storage policy |

`fixtures/fixture_manifest.json` may ship with `fixtures: []` + schema until survey fills approvals — loader stays fail-closed.

---

## 3. Redaction & PII (gate for real data)

| Data class | Examples | Rule |
|---|---|---|
| Direct identifiers | mobile, head name, full address, enumerator id | Redact or approved_redacted before gold use outside controlled path |
| Structural | ward, zone, checkbox enums | Usually retain |
| Exports | `result.json` | Treat as sensitive; R0 local only; R1 encryption-at-rest + retention (`market-roadmap`) |
| Logs | — | Never log raw field values or full paths with names |
| Crops | review PNGs | Same classification as parent PDF; lifecycle TTL R1 |

**Open:** survey must provide redaction method + approver identity before first `approved_redacted` entry.

---

## 4. Template content package (C2)

Target directory: `templates/family_survey_v1/` (all hash-bound in `template_manifest.json`).

| File | Content owner | Depends on |
|---|---|---|
| `field_catalog.json` | survey primary; eng drafts from form | reading WARD-42 form |
| `field_types.yaml` | eng draft / survey confirm | catalog |
| `vocabularies.yaml` | survey codebook | form legend |
| `validation_rules.yaml` | eng draft / survey confirm | catalog + vocab |
| `cross_field_rules.yaml` | eng draft / survey confirm | catalog |
| `review_triggers.yaml` | eng | policy reason registry |
| `page_1_boundaries.yaml` / `page_2_boundaries.yaml` | eng tool + survey bbox approval | `annotate_template.py` + layout refs |
| `table.yaml` | eng | page_2 table region |
| `template_manifest.json` | eng hash root + survey approval scope | all children hashed |

**Order:** catalog draft → types/vocab/rules → annotate bboxes → hash manifest → `synthetic_baseline_approved` (eng+survey) → only then production claims.

Entity prefixes mandatory: `document.*` `household.*` `member.*` `education.*`.

---

## 5. Gold labeling pipeline (C3)

### 5.1 Label format

- **Same canonical JSON** the exporter will emit (Household / Member / EducationRecord + field values).
- Missing = explicit value_state, never `""`.
- Document-level `gold_manifest.json` links fixture_id → label path + hash + labeler + date.

### 5.2 Stages

| Stage | N | Est. human time | Exit |
|---|---|---|---|
| Smoke | 5–10 | 4–7 h | CI green on smoke |
| Dev-gold | 20–30 | 8–21 h | registration/row iteration |
| Calibration | 50–100 | 20–70 h | flag-flip evidence |
| Holdout | 30–50 | 12–35 h | promotion only |
| Full corpus | 1446 | 578–1012 h | deferred |

### 5.3 QA

- Double-key ≥10% subset; disagreement → adjudicate before metrics.
- Document-level split enforcer script (R1 tooling; plan now).
- Never tune thresholds on holdout.

### 5.4 Roles

| Activity | Who |
|---|---|
| Field-level keying | survey / trained annotators |
| Schema + converter + CI | engineering |
| Spot audit | survey owner |

---

## 6. Layout references (external)

```text
~/Documents/WARD-42/1RN-982-WARD NO-42/95.pdf–99.pdf
~/Documents/WARD-42/11RN-985-WARD NO-42/95.pdf–99.pdf
```

- Register before loader use (`role=layout_ref` proposed).
- Full sibling PDFs in those folders (~1,446 total) remain **unregistered** until C2/C3 need them.

---

## 7. Checklist — data gate (before R0 kernel OCR)

- [ ] Manifest schema + empty or layout-ref entries committed
- [ ] Redaction/approver decision recorded (or synthetic-only start)
- [ ] ≥5 classified PDFs openable by loader
- [ ] Catalog + vocab + types drafts exist
- [ ] Boundary YAMLs annotated for page 1–2 (draft OK)
- [ ] Manifest hashes + `synthetic_baseline_approved`
- [ ] Smoke gold JSON for ≥5 docs (or explicit synthetic fixtures)

---

## 8. Update log

| Date | Change |
|---|---|
| 2026-09-24 | Initial data plan aligned with fixture/loader specs + corpus inventory |
