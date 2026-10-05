# src/ocr_platform/benchmark/runner.py

## Role

Bounded rendering, crop evidence, journaling, resumption, and engine execution.

## Contracts

The flow caller can explicitly disable label requirements for inference-only
regions. This mode enters run identity; null expected values are never scored.

Verify source hashes before requests; API needs classified inputs and opt-in. Evidence preserves page/box/source/crop hashes. Resume skips completed attempts; explicit retry accumulates usage. One output writer. Predictions never enter production exports.

Outputs are evaluation-only artifacts. See docs/benchmark.md and ADR-009.

## Infrastructure

pypdfium2, pillow; dataset/engine inputs; local output directory. No credentials are committed.

## Depends on

Called by: cli. Python module imports define direct collaborators.

## Tests

Real synthetic-PDF rendering, hash-linked crops, resume, retry, failed billing, upload gates, locks. See tests/test_benchmark.py.

## Milestone

R0 evaluation prerequisite, independent of production extraction.

## Status

IMPLEMENTED (not GitNexus VERIFIED).

## Owner

engineering; survey owns human transcription and data classification.
