# tests/unit/test_fixture_loader.py

## Role

Fail-closed unit tests for the fixtures loader (`src/ocr_platform/fixtures/loader.py`, Gate G2).

## Contracts

No models, no network, no real PII. Builds temp manifests + byte artifacts under `tmp_path` only; never writes to `fixtures/`. One read-only test loads the real `smoke-001` manifest entry through the gates.

## Infrastructure

pytest; stdlib hashlib/json only.

## Depends on

Called by: pytest / unittest discover. Python module imports define direct collaborators.

## Tests

Valid synthetic entry loads with verified hash; tampered bytes → FixtureHashMismatchError; unknown id → UnknownFixtureError; unclassified entry → FixtureClassificationError; expired entry → FixtureExpiredError; real smoke-001 passes all gates. See tests/unit/test_fixture_loader.py.

## Milestone

R0

## Status

IMPLEMENTED (not GitNexus VERIFIED).

## Owner

engineering
