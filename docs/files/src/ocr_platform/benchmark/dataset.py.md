# src/ocr_platform/benchmark/dataset.py

## Role

Strict label schema, source containment, and SHA-256 verification.

## Contracts

A labeled text crop requires a unique ID, normalized non-empty box, page, kind, value state, human labeler, and verified expected text. No labels cannot yield an accuracy score. Sources are bounded at 10MB.

Explicit inference mode allows null expected values in answer regions; these
are never scorable ground truth. Default benchmark loading still requires labels.

Outputs are evaluation-only artifacts. See docs/benchmark.md and ADR-009.

## Infrastructure

stdlib. No credentials are committed.

## Depends on

Called by: runner, prepare, cli. Python module imports define direct collaborators.

## Tests

Schema rejection, traversal, hash mismatch, unlabeled inputs. See tests/test_benchmark.py.

## Milestone

R0 evaluation prerequisite, independent of production extraction.

## Status

IMPLEMENTED (not GitNexus VERIFIED).

## Owner

engineering; survey owns human transcription and data classification.
