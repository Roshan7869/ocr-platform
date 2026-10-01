# fixtures/fixture_manifest.json

## Role

Classification gate for all fixtures: one JSON entry per PDF (synthetic / approved_redacted, owner, redaction method + approver, allowed storage location, expiry, content hash, template version, split, role smoke|gold). Consumed by `src/ocr_platform/fixtures/loader.py`; unclassified/expired files never enter the pipeline.

## Contracts

- **Invariants:**
  - Required fields per design Gold Data protocol: classification, source owner, redaction method, redaction approver, allowed storage location, expiry, content hash, template version.
  - Optional: `split` (train|calibration|test|holdout) with document-level separation; `role` (smoke|gold); `ward_batch` note for WARD-42 1RN-982 vs 11RN-985.
  - Content hash must match file bytes (sha256 via hashing.py).
  - Smoke set (e.g. 5 docs) labeled smoke — never used alone for promotion claims.
  - Real survey PDFs from `~/Documents/WARD-42/...` require approved_redacted (or synthetic) entry **before** loader opens them; not stored in git until classification + path policy allow.
  - Expiry ISO-8601; loader rejects past expiry.
- **Outputs:** manifest JSON (`schema_version`, `fixtures[]`); seed may ship with empty `fixtures` until survey classification — loader stays fail-closed. Field list aligned with `docs/data-plan.md` §2.
- **Forbidden:** wildcard globs without per-file entries; classification `unknown` accepted by loader; committing real PDF bytes without path policy.

## Infrastructure

- **Python deps:** stdlib json
- **Config/artifacts:** this file; PDFs at declared paths
- **Models/external:** none
- **Env vars:** optional OCR_FIXTURE_ROOT (loader)

## Depends on

- **Calls:** none (data); hash algorithm alignment with worker/provenance/hashing.py
- **Called by:** `src/ocr_platform/fixtures/loader.py`, CI, tests

## Tests

- Unit: schema requires all design fields
- Unit: loader rejects missing manifest entry for a discovered PDF
- Integration: WARD-42 batches registered or loader blocks them
- Integration: expired fixture rejected; hash mismatch rejected

## Milestone

R0

## Status

SPEC

## Owner

survey (redaction/approval for real data) / engineering (schema + loader contract)
