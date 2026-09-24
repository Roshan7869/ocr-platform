# src/ocr_platform/schemas/provenance.py

## Role

Provenance graph node types and edges: `DocumentRun → PageArtifact → TemplateManifest → RegistrationTransform → CropArtifact → EvidenceSet → {OcrObservation, NativeTextEvidence, RegionEvidence, …} → DecisionRevision`. Owns immutable node IDs, content hashes, versions, and graph serialization shape used by the portable validator and JSON export.

## Contracts

- **Invariants:**
  - Provenance is a directed graph, not a single source rectangle.
  - Every node: immutable ID, content hash, version, creation time.
  - Artifacts content-addressed and immutable.
  - Derived/cross-field values record operation ID, input hash, output hash, rule version, template version.
  - Every run stores exact template manifest **hash**, not only a mutable name.
- **Outputs:** node dataclasses/pydantic models, edge types, graph JSON shape.
- **Forbidden:** mutable nodes; cycles; nodes without content hash.

## Infrastructure

- **Python deps:** pydantic>=2.7
- **Config/artifacts:** hash algorithm documented with `worker/provenance/hashing.py` (canonical JSON rules)
- **Models/external:** none
- **Env vars:** none

## Depends on

- **Calls:** `schemas/evidence.py` (evidence node envelope), `schemas/job.py` (DocumentRun/PageArtifact)
- **Called by:** `worker/provenance/validator.py`, `worker/provenance/hashing.py`, `export/json_export.py`, `schemas/decision.py`

## Tests

- Unit: minimum graph path constructible for a synthetic accepted field
- Unit: missing intermediate node detected by structure helpers
- Integration: R0 portable provenance validation for every output
- Integration: zero accepted values with incomplete provenance (benchmark gate shape)

## Milestone

R0

## Status

SPEC

## Owner

engineering
