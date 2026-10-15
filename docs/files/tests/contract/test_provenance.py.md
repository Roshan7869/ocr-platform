# tests/contract/test_provenance.py

## Role

Unit and gate tests for the R0 provenance layer: canonical JSON hashing, typed evidence nodes and sets, coordinate-system algebra, run identity, provenance node/graph structure, the decision status vocabulary, FAMILY_SURVEY_V1 label mapping, and the portable referential-integrity validator. This is the enforcement point for the "no accepted value without complete provenance" benchmark gate.

## Contracts

Detects regressions that would let an unprovenanced or mislabelled value be accepted. Specifically guards:

- Canonical JSON is key-order independent, compact, UTF-8, and rejects non-finite floats, `bytes`, and colliding stringified keys; signed zero cannot fork a hash.
- Content hashes are plain sha256 hex digests; IDs are content-addressed; tampered payloads fail verification.
- Every bbox carries an explicit `coordinate_system`; page-space boxes stay in the unit box; `crop_local_*` is tagged and rejected as page space.
- PDF bottom-left → image top-left flips y and rebases to the media-box top edge; `normalize_page_box` is pure.
- `run_id = (document_content_hash, configuration_fingerprint)` is stable for identical bytes+config and unchanged by retries.
- Provenance nodes are immutable, content-addressed, cycle-free, and every edge endpoint resolves (no missing intermediates).
- `value_state` and `disposition` are orthogonal enums; `AUTO_ACCEPTED`/`NORMALIZED_ACCEPTED` are not enum values; missing is not `""`.
- Region-required value states (`absent`, `unreadable`, `not_applicable`) must carry `RegionEvidence`.
- Validator emits each violation class (missing intermediate, bad hash, wrong evidence type, orphan evidence) and the happy path passes.

## Infrastructure

pytest and pydantic. Synthetic fixtures only — no real corpus, no network, no GPU, no credentials.

## Depends on

`ocr_platform.schemas.decision`, `ocr_platform.schemas.evidence`, `ocr_platform.schemas.job`, `ocr_platform.schemas.provenance`, `ocr_platform.worker.provenance.hashing`, `ocr_platform.worker.provenance.validator`, `ocr_platform.worker.render.coordinates`.

## Tests

This file is the test suite: 124 tests across `TestCanonicalJson`, `TestBBox`, `TestEvidenceNodes`, `TestEvidenceSet`, `TestCoordinates`, `TestRunIdentity`, `TestCapabilityMatrix`, `TestProvenanceNodes`, `TestProvenanceGraph`, `TestDecisionVocabulary`, `TestSurveyLabelMapping`, `TestValidatorHappyPath`, `TestValidatorViolations`, `TestProvenanceGate`, `TestEndToEndProvenance`.

## Milestone

R0 provenance gate.

## Status

IMPLEMENTED

## Owner

engineering
