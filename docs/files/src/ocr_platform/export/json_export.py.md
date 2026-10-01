# src/ocr_platform/export/json_export.py

## Role

Serialize run outputs to canonical JSON: `Household`, `Member`, `EducationRecord` entities with `FieldDecision` objects, provenance bundle, run metadata (template hash, policy version, model pins, configuration fingerprint). R0 primary artifact — no Postgres (R1).

## Contracts

- **Invariants:**
  - Entity shape per design: Household / Member / EducationRecord with required keys (`document_run_id`, `household_key`, `member_key`, `row_key`, linkage rules).
  - Field IDs entity-qualified: `household.*`, `member.*`, `education.*`, `document.*` for pure admin.
  - Every exported accepted/corrected value passed `provenance/validator.py` first; failure blocks export.
  - Canonical JSON via `hashing.py` (sorted keys, UTF-8, documented numbers).
  - Missing values are value_state + decision, never `""`.
  - Education cells map to `EducationRecord` entity owner (not flattened into member) when catalog says so; same-row linkage explicit via `row_key`/provenance, not cross-page guess.
  - Includes expected-output example shape from field catalog when present.
  - **PII posture:** exports may contain names, mobiles, addresses — R0 writes local classified paths only; R1+ requires encryption-at-rest + retention hooks (`docs/market-roadmap.md` privacy); never log raw field values.
- **Outputs:** JSON file(s) / bytes for a run.
- **Forbidden:** writing accepted values with validation report failure; inventing catalog fields not in `field_catalog.json`; emitting accepted values without redaction policy when mode requires it (R1+).

## Infrastructure

- **Python deps:** stdlib json (via hashing canonical writer)
- **Config/artifacts:** `field_catalog.json`, template manifest hash, policy version
- **Models/external:** none
- **Env vars:** output path via CLI

## Depends on

- **Calls:** all `schemas/*`, `worker/provenance/validator.py`, `worker/provenance/hashing.py`, `worker/template/manifest.py`
- **Called by:** `worker/pipeline.py`, `scripts/extract.py`

## Tests

- Unit: entity/field_id shape matches catalog + design examples
- Unit: unvalidated accepted value cannot serialize
- Integration: R0 schema validation for every output; canonical JSON golden
- Integration: provenance completeness 100% on exported accepted fields

## Milestone

R0

## Status

SPEC

## Owner

engineering
