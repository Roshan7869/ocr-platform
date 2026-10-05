# src/ocr_platform/flow/pipeline.py

## Role

Validate field text and produce immutable review decisions.

## Contracts

Draft rules; model final values always null; unknown codes/ditto/uncertain OCR route to review. Hash-addressed resumable runs copy evidence crops. See docs/flow.md and ADR-010.

## Infrastructure

stdlib, benchmark dataset/runner.

## Depends on

adapters; review materialization; CLI.

## Tests

Validation, confidence, failure, non-leakage, resume and evidence tests.

## Milestone

Experimental annotated-crop trial; production extractor remains planned.

## Status

IMPLEMENTED (not GitNexus VERIFIED).

## Owner

engineering; survey owns codebook and verified human corrections.
