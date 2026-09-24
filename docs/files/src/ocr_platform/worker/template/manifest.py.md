# src/ocr_platform/worker/template/manifest.py

## Role

Load, validate, and resolve the `FAMILY_SURVEY_V1` template package: read `template_manifest.json` hash root, verify child YAML content hashes, enforce approval scope (`synthetic_baseline_approved` | `production_approved`), expose immutable resolved template to the pipeline. Production resolves an approved alias to one immutable manifest hash.

## Contracts

- **Invariants:**
  - Manifest contains: canonical field/table definitions (via children), content hash, coordinate convention, render parameters, author, reviewer, approval scope/status, benchmark artifact ID, compatibility version, deprecation state (design Template lifecycle).
  - Child files (`page_1_boundaries.yaml`, `page_2_boundaries.yaml`, `table.yaml`, `field_types.yaml`, `vocabularies.yaml`, `validation_rules.yaml`, `cross_field_rules.yaml`, `review_triggers.yaml`, `field_catalog.json`) hash-verified against manifest.
  - R0 runs only with `synthetic_baseline_approved` scope; production requires full gate.
  - Every run stores exact manifest hash, not mutable name.
  - Activation/rollback are explicit operations (R5; R0 loads current approved).
- **Outputs:** `ResolvedTemplate` (immutable).
- **Forbidden:** editing YAML in place without new manifest hash; accepting unhashed children.

## Infrastructure

- **Python deps:** pyyaml, pydantic, hashlib (via provenance/hashing)
- **Config/artifacts:** entire `templates/family_survey_v1/` package
- **Models/external:** none
- **Env vars:** none

## Depends on

- **Calls:** `worker/provenance/hashing.py`, `schemas/job.py` (template hash into fingerprint)
- **Called by:** `worker/pipeline.py`, `worker/template/boundaries.py`, `worker/template/registration.py`, `export/json_export.py`

## Tests

- Unit: child hash mismatch rejects load
- Unit: approval scope enforced (production path refuses synthetic-only in R0 tests via fixture)
- Unit: unknown/deprecated template rejected
- Integration: identity-transform boundary assignment against approved manifest
- Integration: template mismatch fixture → review, not accept

## Milestone

R0

## Status

SPEC

## Owner

engineering (loader) / survey (manifest content approval)
