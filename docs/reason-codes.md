# Reason & exit codes — ocr-platform

Canonical registry for process **exit codes** and decision **reason codes**. Before this file, codes were duplicated by-reference across `schemas/decision.py`, `configs/acceptance_policy_v1.yaml`, `templates/.../review_triggers.yaml`, `worker/state_machine.py`, `scripts/extract.py`, and `docs/accuracy-plan.md`. This is now the single list; those files must align their identifiers to it (no forks, no new codes outside this registry).

**Invariant:** `FINAL_VALUE MUST NEVER EXIST WITHOUT PROVENANCE`
**Template:** `FAMILY_SURVEY_V1` · **Milestones:** R0 → R0.5 → R1 → R2 (see `docs/market-roadmap.md`)

> **Status column:** `tokenized` = the identifier already appears in the specs; `proposed` = the condition is specified in prose (the AcceptancePolicy-v1 14-item hard-review list, `acceptance_policy_v1.yaml.md:12`) but the canonical `UPPER_SNAKE` token is assigned here for the first time. Implementers adopt the `proposed` tokens verbatim.

---

## 1. Process exit codes

### `scripts/extract.py`

| Exit | Meaning | Source |
|---|---|---|
| `0` | Success — accepted + review files written | `scripts/extract.py:12` |
| `2` | Validation / provenance failure | `scripts/extract.py:12` |
| `3` | Spike / model pins missing | `scripts/extract.py:12` |
| `4` | Usage error (bad args) | `scripts/extract.py:12` |

### `scripts/run_spike.py`

| Exit | Meaning | Source |
|---|---|---|
| `0` | Go — compatibility matrix passed | `sequences.md:161` · `run_spike.py.md` |
| `1` | No-go — matrix failed | `sequences.md:161` · `run_spike.py.md` |

> Quantitative go/no-go criteria (determinism tolerance, canonical-JSON compare, min CPU resolution, conditional-go) are defined in `docs/files/scripts/run_spike.py.md` (Wave 1). Exit `0` here means *compatibility*, not auto-accept enablement.

---

## 2. Reason-code registry

All reason codes are multi-label (`reason_codes`); the single `primary_reason` is chosen by the precedence in `configs/acceptance_policy_v1.yaml` (see §4). Every code below either forces `review`, or marks a terminal `errored`/`rejected` state.

### 2.1 Document-level (terminal, before any field decision)

| Code | Fires when | Disposition | Status |
|---|---|---|---|
| `ENCRYPTED_PDF` | PDF is encrypted / unreadable bytes | `errored` | tokenized (`job.py.md:14`) |
| `CORRUPT_PDF` | PDF fails to parse/render | `errored` | tokenized (`job.py.md:14`) |
| `EMPTY_DOCUMENT` | Renders to zero usable pages | `errored` | proposed (`empty` class, `job.py.md:13`) |

### 2.2 Page-level (blocks field acceptance on that page)

| Code | Fires when | Disposition | Status |
|---|---|---|---|
| `PAGE_SET_MISMATCH` | Rendered page set ≠ template expectation / wrong template | `review` | tokenized (`state_machine.py.md:12`) |
| `REGISTRATION_RESIDUAL_HIGH` | Affine residual over threshold or ambiguous anchors (R0.5); LEGEND/ANCHOR sanity fails (R0) | `review` | tokenized (`state_machine.py.md:12`, `sequences.md:62`) |

### 2.3 Field / cell-level — hard-review reasons (AcceptancePolicy-v1)

The 14-item hard-review list from `acceptance_policy_v1.yaml.md:12`, canonicalized:

| Code | Fires when | Disposition | Status |
|---|---|---|---|
| `OCR_CONFIDENCE_LOW` | Raw OCR confidence below cutoff | `review` | proposed |
| `MULTIPLE_CANDIDATES` | More than one plausible value candidate | `review` | proposed |
| `OCR_UNSTABLE` | Unstable / non-reproducible OCR output | `review` | proposed |
| `BOUNDARY_CROSS` | Detected box crosses a region boundary | `review` | proposed |
| `BOUNDARY_TOUCH` | Detected box touches a region edge | `review` | proposed |
| `BOUNDARY_OVERLAP` | Ambiguous multi-region overlap (`overlap_ratio` under threshold) | `review` | proposed |
| `OUT_OF_BOUNDARY` | Value falls outside its assigned region | `review` | tokenized (`decision.py.md:23`) |
| `INVALID_NUMERIC` | Numeric field fails validation | `review` | proposed |
| `CONFLICTING_MARKS` | Contradictory checkbox/mark evidence | `review` | proposed |
| `MULTI_SINGLE_SELECT` | Multiple marks in a single-select group | `review` | proposed |
| `UNKNOWN_SYMBOL` | Unrecognized mark symbol | `review` | proposed |
| `UNKNOWN_VOCABULARY_CODE` | Value not in the field's vocabulary → `value_state=unknown` | `review` | tokenized (`decision.py.md:26`) |
| `DITTO_UNRESOLVED` | "Same-as-above" mark not resolvable to a value | `review` | proposed |
| `CROSS_FIELD_CONFLICT` | Cross-field rule violated | `review` | proposed |
| `WRONG_TEMPLATE` | Field context indicates a different template | `review` | proposed |
| `HANDWRITING_SUSPECTED` | Handwriting detected on a text field (ADR-004) → force review | `review` | tokenized (`acceptance_policy_v1.yaml.md:14`) |

### 2.3.1 Gate-emitted (provenance hard gate)

Emitted by `worker/provenance/validator.py` when an accepted value fails the
portable referential-integrity gate. The decision is demoted to `review` and its
`final_value` dropped; evidence is retained, never deleted.

| Code | Fires when | Disposition | Status |
|---|---|---|---|
| `PROVENANCE_INCOMPLETE` | Accepted/corrected decision fails the provenance gate (missing evidence node, wrong evidence type for the value state, missing page artifact, unverified node hash, broken revision link, missing registration) | `review` | tokenized (`validator.py`) |

### 2.4 Row-level (dynamic table, R0 exit on layout refs)

| Code | Fires when | Disposition | Status |
|---|---|---|---|
| `ROW_UNDERSEGMENT` | Two logical rows merged into one | `review` | tokenized (`accuracy-plan.md:101`) |
| `ROW_OVERSEGMENT` | One logical row split into several | `review` | tokenized (`accuracy-plan.md:101`) |
| `ROW_UNCERTAIN` | Row boundary/count not confidently determined | `review` | tokenized (`accuracy-plan.md:101`) |

---

### Experimental crop/classifier additions (2026-10-05)

The experimental flow uses the canonical `OCR_CONFIDENCE_LOW`, `DITTO_UNRESOLVED`,
`INVALID_NUMERIC`, `UNKNOWN_VOCABULARY_CODE` and `HANDWRITING_SUSPECTED` tokens.
The following additional tokens are registered for experimental review routing;
they do not enable production acceptance or replace AcceptancePolicy-v1.

| Code | Condition |
|---|---|
| `AUTO_ACCEPT_DISABLED` | Every model observation remains in review |
| `DRAFT_RULES` | Survey codebook/rules are still draft |
| `EMPTY_OCR` | Recognition returned no usable text; absence is not inferred |
| `TEXT_TOO_LONG` | Input exceeds the experiment's field-text cap |
| `UNCONFIGURED_FIELD` | No matching experimental field rule |
| `INVALID_INTEGER` | Integer syntax failed; accompanies INVALID_NUMERIC |
| `INTEGER_OUT_OF_RANGE` | Integer bound failed; accompanies INVALID_NUMERIC |
| `INVALID_DIGIT_SEQUENCE` | Digit syntax/length failed; accompanies INVALID_NUMERIC |
| `OCR_FAILED` | Recognition backend failed |
| `OCR_CONFIDENCE_UNAVAILABLE` | Missing or invalid recognition confidence |
| `CLASSIFICATION_SKIPPED_UNCERTAIN_OCR` | OCR gate blocked the category model |
| `INVALID_CLASSIFIER_RESPONSE` | Invalid category or confidence |
| `UNKNOWN_CATEGORY` | Category model returned UNKNOWN |
| `LOW_CLASSIFICATION_CONFIDENCE` | Category confidence below the draft routing cutoff |
| `CLASSIFIER_FAILED` | Category inference failed |

Flow v1 artifacts used LOW_OCR_CONFIDENCE and UNRESOLVED_DITTO. Flow v2 emits
the canonical tokens above, records declared handwriting explicitly, and attaches
`coordinate_system=image_top_left_normalized` to new evidence. Existing immutable
artifacts are not rewritten. Experimental CLIs use exit 0 for completed runs,
1 for backend failures, and 2 for invalid inputs/dependencies; these are separate
from the planned production extract.py exit-code contract.

## 3. Not reason codes (do not confuse)

These tokens appear in the specs but are **not** dispositions or reason codes:

| Token | What it actually is | Owner |
|---|---|---|
| `AUTO_ACCEPTED` / `NORMALIZED_ACCEPTED` | Both store `disposition=accepted`; distinguished by `accepted_by` + `acceptance_policy_version` | `schemas/decision.py` |
| `BOUNDARY_EXPAND` | A proposal *action*, never a field disposition | `schemas/decision.py` |
| `value_state` values (`present`/`absent`/`unknown`/`unreadable`/`not_applicable`) | The value-state axis, orthogonal to disposition | `schemas/decision.py` |

---

## 4. Precedence (`primary_reason`)

When several reason codes fire, exactly one is chosen as `primary_reason`. Precedence order is owned by `configs/acceptance_policy_v1.yaml` (this registry supplies the vocabulary, the policy supplies the ordering). General precedence, most-severe first:

1. Document-terminal (`ENCRYPTED_PDF`, `CORRUPT_PDF`, `EMPTY_DOCUMENT`)
2. Page-blocking (`PAGE_SET_MISMATCH`, `REGISTRATION_RESIDUAL_HIGH`)
3. Structural boundary (`WRONG_TEMPLATE`, `OUT_OF_BOUNDARY`, `BOUNDARY_*`)
4. Evidence quality (`OCR_UNSTABLE`, `OCR_CONFIDENCE_LOW`, `HANDWRITING_SUSPECTED`)
5. Value semantics (`UNKNOWN_VOCABULARY_CODE`, `INVALID_NUMERIC`, `MULTIPLE_CANDIDATES`, mark/ditto/cross-field)

> The concrete numeric ordering is pinned in the policy artifact; keep it in one place to avoid a fork.

---

## 5. Recovery & retry semantics

- **Retry ≠ new run.** A retry is a separate record under the same `run_id`; it never mints a new run_id (`job.py.md:12`).
- **Errored is terminal for the document, not the batch.** `ENCRYPTED_PDF` / `CORRUPT_PDF` / `EMPTY_DOCUMENT` end that document with zero field decisions; the CLI still writes files and reports counts.
- **Review is recoverable via the human path.** A `review` disposition is resolved by a `DecisionRevision` (R2 review console) — corrections append, never overwrite.
- **Provenance hard-fail demotes, never deletes.** A failed provenance validation demotes the decision to review/exception (`architecture.md:80`); the evidence and the failure reason are retained.
- **No silent transitions.** Illegal lifecycle transitions raise in `state_machine.py`; there is no implicit skip to `accepted`.

---

## Related documents

- Term definitions: `docs/glossary.md`
- Policy thresholds & precedence: `configs/acceptance_policy_v1.yaml` (spec: `docs/files/configs/acceptance_policy_v1.yaml.md`)
- Decision schema: `docs/files/src/ocr_platform/schemas/decision.py.md`
- Spike go/no-go: `docs/files/scripts/run_spike.py.md`
- Accuracy gates (row + calibration): `docs/accuracy-plan.md`
- Fail-closed rationale: `docs/adr/adr-005-fail-closed-calibration.md`
