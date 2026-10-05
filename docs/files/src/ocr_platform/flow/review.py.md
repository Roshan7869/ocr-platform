# src/ocr_platform/flow/review.py

## Role

Append human revisions and materialize effective results and review queue.

## Contracts

Original decisions immutable. Human values pass rules, explicit categories required, blank/unreadable distinct. Hash-checked crop evidence and chained revisions. Caller lock for view refresh. See docs/flow.md and ADR-010.

## Infrastructure

stdlib.

## Depends on

pipeline validation; benchmark canonical hashes.

## Tests

Correction history, queue updates, tampered evidence and resume tests.

## Milestone

Experimental annotated-crop trial; production extractor remains planned.

## Status

IMPLEMENTED (not GitNexus VERIFIED).

## Owner

engineering; survey owns codebook and verified human corrections.

