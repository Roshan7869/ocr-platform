# templates/family_survey_v1/template_manifest.json

## Role

Hash root and approval envelope for the FAMILY_SURVEY_V1 template package: content hashes of all child YAML/JSON files, coordinate convention, render parameters, author, reviewer, approval scope (`synthetic_baseline_approved` | `production_approved`), approval status, benchmark artifact ID, compatibility version, deprecation state, template version string `FAMILY_SURVEY_V1`.

## Contracts

- **Invariants:**
  - Design Template lifecycle fields all present (design L245–249).
  - Child hash list exhaustive — manifest load fails if any child missing/extra unmatched (except README-level docs).
  - R0 runs require `synthetic_baseline_approved`; `production_approved` requires benchmark + regression + security gate + human approval (enforced by loader/manifest.py, recorded here).
  - Every pipeline run stores **this file's content hash**, not the name alone.
  - Alias resolution to one immutable hash is R5; R0 may have single implicit alias.
- **Outputs:** validated manifest object.
- **Forbidden:** pointing at children with wrong hashes; approval status without reviewer fields.

## Boundary classes

Document-level: declares coordinate_system + region type inventory (FIELD, CHECKBOX_OPTION, CHECKBOX_GROUP, TABLE, TABLE_ROW, TABLE_CELL, LEGEND, ANCHOR).

## Entity owner

n/a (package root). Child fields must use `document.*` / `household.*` / `member.*` / `education.*`.

## Infrastructure

- **Python deps:** stdlib json + hashlib via provenance/hashing
- **Config/artifacts:** all sibling files in `templates/family_survey_v1/`
- **Models/external:** none
- **Env vars:** none

## Depends on

- **Calls:** `worker/provenance/hashing.py`
- **Called by:** `worker/template/manifest.py`

## Tests

- Unit: golden hash of children matches manifest
- Unit: scope/status fields validated
- Integration: pipeline fingerprint includes manifest hash
- Integration: WARD-42 annotation output binds into this package before `synthetic_baseline_approved`

## Milestone

R0

## Status

SPEC

## Owner

survey (content approval) / engineering (schema + hashing)
