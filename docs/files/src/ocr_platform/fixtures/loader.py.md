# src/ocr_platform/fixtures/loader.py

## Role

Fixture discovery and classification gate: read `fixtures/fixture_manifest.json`, reject unclassified/expired fixtures, yield PDFs + expected metadata to the pipeline. Enforces synthetic / approved_redacted policy before any file is opened by the extractor.

## Contracts

- **Invariants:**
  - Every fixture manifest entry: classification (`synthetic` | `approved_redacted`), source owner, redaction method, redaction approver, allowed storage location, expiry, content hash, template version (design Gold Data protocol).
  - CI and loader **reject** unclassified or expired fixtures — no silent default to synthetic.
  - Content hash verified on load (detect moved/tampered files).
  - Layout reference PDFs under `~/Documents/WARD-42/...` must be registered here (or copied under classified paths) before pipeline use; not committed until classified.
  - A five-document set is smoke-test only — loader labels `smoke` vs `gold` split; promotion paths refuse smoke-only (design).
  - Document-level split metadata for gold (never page-level leakage) when `split` present.
- **Outputs:** iterator of validated fixture refs (path, hash, classification, split, template version).
- **Forbidden:** loading PDFs outside the manifest; mutating fixtures.

## Infrastructure

- **Python deps:** stdlib pathlib, hashlib, json/yaml
- **Config/artifacts:** `fixtures/fixture_manifest.json`
- **Models/external:** fixture PDFs (paths may be absolute outside repo for R0)
- **Env vars:** optional `OCR_FIXTURE_ROOT` override

## Depends on

- **Calls:** `worker/provenance/hashing.py` (hash verify)
- **Called by:** `worker/pipeline.py`, `scripts/extract.py`, tests

## Tests

- Unit: unclassified/expired/hash-mismatch rejected
- Unit: smoke vs gold labels enforced
- Integration: R0 scanned/native/mixed/encrypted/corrupt/empty/page-set fixtures via loader
- Integration: WARD-42 95–99 registered as approved_redacted (or synthetic) with hashes

## Milestone

R0

## Status

SPEC

## Owner

engineering (loader) / survey (redaction approval for real scans)
