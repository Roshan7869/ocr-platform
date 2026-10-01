# templates/family_survey_v1/table.yaml

## Role

Family-member table algorithm parameters: data region reference (page_2), dynamic row detection settings (min ink / separator cues / pitch defaults), populated-row predicate, blank-row → no-record rule, INTERSECT policy hook (overlap 0.80 from acceptance policy — thresholds not duplicated here), ditto reference policy pointer.

## Contracts

- **Invariants:**
  - Never run independent full-page OCR then reconstruct by text order (design §16).
  - Algorithm shape: rows = FIND_POPULATED_ROWS(data_region); cells = INTERSECT(row.bbox, column.bbox); PROCESS_CELL with column schema (§34).
  - Blank rows below last member produce no `NO_MEMBER` fake records and no empty Member entities.
  - Row identity: `row_key` stable within rendered table/run — not inferred across pages by position alone (design linkage rules); explicit linkage for cross-entity keys.
  - Dynamic detector may fail closed → page review, never invent rows.
  - **Accuracy targets (R0 exit on layout refs — `docs/accuracy-plan.md`):** row recall ≥0.95, row precision ≥0.95, zero fake blank-row records, 100% `row_key` uniqueness; failure reasons `ROW_UNDERSEGMENT` / `ROW_OVERSEGMENT` / `ROW_UNCERTAIN`.
- **Outputs:** algorithm config for `boundaries.py` table path.
- **Forbidden:** acceptance thresholds (live in AcceptancePolicy); OCR model config; hardcoded populated row count.

## Boundary classes

TABLE, TABLE_ROW (runtime-derived rows tagged TABLE_ROW), TABLE_CELL.

## Entity owner

member/education row structure (links entities).

## Infrastructure

- **Python deps:** pyyaml
- **Config/artifacts:** hash in template_manifest; references page_2_boundaries
- **Models/external:** none
- **Env vars:** none

## Depends on

- **Calls:** none (data)
- **Called by:** `worker/template/boundaries.py`

## Tests

- Unit: populated-row predicate on synthetic ink patterns
- Unit: blank trailing region yields zero rows
- Integration: 95–99.pdf varying member counts → row counts match manual annotation
- Integration: row_key uniqueness within run
- Integration: row recall/precision ≥0.95 on 10 layout refs (accuracy-plan gate)

## Milestone

R0

## Status

SPEC

## Owner

engineering (algorithm params) / survey (row detection acceptance on fixtures)
