# src/ocr_platform/schemas/job.py

## Role

Pydantic models for run identity and lifecycle: `DocumentRun`, `PageArtifact`, `RenderMetadata`, and job-level capability classification (`scanned_only` | `native_only` | `mixed` | `encrypted` | `corrupt` | `empty`). Owns the run-identity tuple and configuration fingerprint shape — no I/O, no OCR, no policy decisions.

## Contracts

- **Invariants:**
  - `run_id = (document_content_hash, configuration_fingerprint)` is immutable per run (design: Important Technical Decisions).
  - `document_content_hash = sha256(exact_uploaded_pdf_bytes)` in R0/R1; page metadata stored separately; optional `document_semantic_fingerprint` is a distinct field, never replaces run identity.
  - Retry attempts are separate records under one run; they never mint a new run_id.
  - Page class follows the capability matrix (scanned / native / mixed / encrypted / corrupt / empty / page-set mismatch).
  - Encrypted/corrupt → document `disposition=errored` with `ENCRYPTED_PDF` / `CORRUPT_PDF` before any field decision exists.
- **Outputs:** `DocumentRun`, `PageArtifact`, `PageClass`, `ConfigurationFingerprint` types.
- **Forbidden:** persistence writes; boundary geometry; acceptance decisions.

## Infrastructure

- **Python deps:** pydantic>=2.7
- **Config/artifacts:** none (fingerprint fields defined here, filled by caller)
- **Models/external:** none
- **Env vars:** none

## Depends on

- **Calls:** `schemas/provenance.py` (page artifact provenance node IDs)
- **Called by:** `worker/pipeline.py`, `worker/state_machine.py`, `export/json_export.py`, `worker/provenance/validator.py`

## Tests

- Unit: run_id stability for identical bytes+config; different config → different run
- Unit: retry does not change run_id
- Unit: capability matrix classification for each page class (encrypted, corrupt, empty, mismatch)
- Integration: R0 encrypted/corrupt/empty files → document disposition errored, zero field decisions

## Milestone

R0

## Status

IMPLEMENTED

## Owner

engineering
