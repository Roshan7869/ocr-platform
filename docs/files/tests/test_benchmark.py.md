# tests/test_benchmark.py

## Role

Regression tests for evaluation correctness and safe resumption.

## Contracts

Synthetic source PDFs and mocked engines only; test scores are not real-corpus accuracy evidence.

Outputs are evaluation-only artifacts. See docs/benchmark.md and ADR-009.

## Infrastructure

unittest; pypdf, pypdfium2, pillow; pytest runner optional. No credentials are committed.

## Depends on

Called by: pytest / unittest discover. Python module imports define direct collaborators.

## Tests

Failure-aware scores, evidence/corpus integrity, API gates/contracts, retry accounting, sample stratification. See tests/test_benchmark.py.

## Milestone

R0 evaluation prerequisite, independent of production extraction.

## Status

IMPLEMENTED (not GitNexus VERIFIED).

## Owner

engineering; survey owns human transcription and data classification.
