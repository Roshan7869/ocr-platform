# src/ocr_platform/export/review_candidates.py

## Role

Export uncertain/exception results as review-candidate JSON for human inspection (R0 file export only — no assignment, correction, adjudication, or production access controls until R2). Reviewer sees crop + raw + candidates + confidences + boundary signals + exception type.

## Contracts

- **Invariants:**
  - Candidate record shape (design/FAMILY_SURVEY_V1 §39): document_id, page, field_id, row_id, column_id, bbox (+coordinate_system), raw_ocr/raw_mark, candidates[], ocr_confidence, boundary_confidence (separate fields), exception_type, crop_uri (or crop bytes ref), template_version.
  - Exception types align with decision reason codes / FAMILY_SURVEY_V1 labels mapped per `decision.md`.
  - Includes checkbox multi-mark, boundary, unknown vocab, invalid numeric, unresolved ditto, cross-field, wrong-template cases.
  - Never places candidate into accepted export path.
  - Privacy: R0 fixtures only (synthetic/approved-redacted); crop paths local; crops inherit parent classification; R1+ TTL + encryption (`docs/market-roadmap.md`).
  - Handwriting / registration / row segmentation reasons included when those signals fire (accuracy-plan taxonomies).
- **Outputs:** review-candidate JSON array/file.
- **Forbidden:** silent drop of secondary reason codes; accepted values in this file.

## Infrastructure

- **Python deps:** stdlib json via hashing canonical writer
- **Config/artifacts:** policy review triggers; crop artifact storage (local dir R0)
- **Models/external:** none
- **Env vars:** review output path

## Depends on

- **Calls:** `schemas/decision.py`, `schemas/evidence.py`, `worker/template/boundaries.py`, `worker/provenance/validator.py` (still provenance-complete for the *decision*, even if disposition=review)
- **Called by:** `worker/pipeline.py`, `scripts/extract.py`

## Tests

- Unit: every hard review reason can produce a candidate record
- Unit: multi reason_codes preserved (not only primary)
- Unit: crop reference present for boundary/ambiguous cases
- Integration: R0 review-candidate rate measured on smoke fixtures; no accepted leakage into review file

## Milestone

R0 (export only); R2 adds workflow

## Status

SPEC

## Owner

engineering
