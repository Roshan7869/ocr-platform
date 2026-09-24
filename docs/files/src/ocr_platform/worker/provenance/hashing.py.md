# src/ocr_platform/worker/provenance/hashing.py

## Role

Canonical JSON serialization and content-addressed hashing shared by provenance nodes, template child files, configuration fingerprint, and R0 reproducibility comparisons.

## Contracts

- **Invariants:**
  - Canonical JSON: sorted keys, fixed number formatting, UTF-8, documented hash algorithm (sha256) (design R0 reproducibility).
  - Same semantic object → same hash independent of dict insertion order.
  - Artifact byte equality where runtime guarantees it; numerical tolerance policy only where GPU/image encoding requires — tolerance rules documented here and applied by tests, not by loosening hashes of JSON.
  - Template manifest child hashes use this module (manifest.py must not roll its own).
- **Outputs:** `canonical_json(obj) -> bytes`, `content_hash(bytes|obj) -> sha256hex`, optional `stable_number` helpers.
- **Forbidden:** JSON encoders that drop non-finite floats silently without policy; per-call ad-hoc separators.

## Infrastructure

- **Python deps:** stdlib json, hashlib
- **Config/artifacts:** algorithm id string versioned for fingerprint
- **Models/external:** none
- **Env vars:** none

## Depends on

- **Calls:** none (leaf)
- **Called by:** `worker/provenance/validator.py`, `worker/template/manifest.py`, `schemas/provenance.py`, `export/json_export.py`, fingerprint in pipeline

## Tests

- Unit: key order independence; golden hash vectors checked in
- Unit: float formatting stability cases
- Integration: R0 canonical JSON comparison across two runs

## Milestone

R0

## Status

SPEC

## Owner

engineering
