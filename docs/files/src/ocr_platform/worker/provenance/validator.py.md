# src/ocr_platform/worker/provenance/validator.py

## Role

Portable (pre-DB) provenance referential integrity validator: walk decision → EvidenceSet → page artifacts → template manifest hash → render/registration records; enforce required evidence type per value state; hash consistency. R0 gate before any accepted/corrected value is exported. Equivalent DB FKs arrive in R1.

## Contracts

- **Invariants:**
  - Every accepted or corrected decision resolves to: ≥1 valid evidence node, immutable page artifact, template manifest, render/registration record (design Provenance graph).
  - Checks: evidence-set membership, page/region refs, content hashes, decision revision links, required evidence type for value state.
  - `present` → text (or policy-required) evidence; `absent`/`unreadable`/`not_applicable` → RegionEvidence; human-corrected → HumanCorrectionEvidence (R2+) can replace OCR claim without faking OCR.
  - Failure ⇒ decision cannot be exported as accepted (pipeline hard-fails to review/exception).
  - Zero tolerance: accepted with incomplete provenance is a bug, not a warning (benchmark gate).
- **Outputs:** `ValidationReport {ok, violations[]}`; used by export + tests.
- **Forbidden:** auto-repairing missing nodes; accepting on warnings only.

## Infrastructure

- **Python deps:** pydantic
- **Config/artifacts:** hash algorithm with `hashing.py`; template hash from manifest
- **Models/external:** none
- **Env vars:** none

## Depends on

- **Calls:** `schemas/provenance.py`, `schemas/evidence.py`, `schemas/decision.py`, `schemas/job.py`, `worker/provenance/hashing.py`, `worker/render/coordinates.py`
- **Called by:** `worker/pipeline.py`, `export/json_export.py`, `export/review_candidates.py`

## Tests

- Unit: each violation class triggers (missing page, bad hash, wrong evidence type, orphan evidence)
- Unit: happy path minimum graph passes
- Integration: R0 portable provenance validation for **every** output; zero incomplete accepted (gate test)

## Milestone

R0

## Status

SPEC

## Owner

engineering
