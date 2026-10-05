# src/ocr_platform/benchmark/metrics.py

## Role

Failure-aware recognition scores and conditional scale/cost projections.

## Contracts

Inference completion/failure counts cover all rows separately from verified-label
score denominators; unlabeled inputs never produce accuracy scores.

Exact-match denominator includes failed labeled text fields. Marks/unreadable truth are excluded. Unknown rates are null; costs count input crops, not documents. Observed disagreement is not calibrated review workload.

Outputs are evaluation-only artifacts. See docs/benchmark.md and ADR-009.

## Infrastructure

stdlib. No credentials are committed.

## Depends on

Called by: runner. Python module imports define direct collaborators.

## Tests

Blank false positives, failures, Unicode, absent prices, lakh-scale arithmetic. See tests/test_benchmark.py.

## Milestone

R0 evaluation prerequisite, independent of production extraction.

## Status

IMPLEMENTED (not GitNexus VERIFIED).

## Owner

engineering; survey owns human transcription and data classification.
