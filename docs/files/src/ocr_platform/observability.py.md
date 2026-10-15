# src/ocr_platform/observability.py

## Role
PII-free structured run logging: emits the observability.md section 3
subset (`run.start`, `run.errored`, `field.decision`, `run.complete`) as
one JSON object per log record, every record carrying `run_id`.

## Contracts
Signatures accept PII-safe scalars only (ids, hashes, reason codes,
dispositions, counts, timings) — no `**kwargs` passthrough, so field
values, OCR text, and paths cannot enter a record. Gate G6 asserts this.

## Infrastructure
Python stdlib `logging` and `json`; logger `ocr_platform.observability`.

## Depends on
Called by `ocr_platform.orchestrator.pipeline.SurveyPipeline.run`;
consumes no other module.

## Tests
`tests/property/test_pii_free_logs.py` (G6: injected PII never appears in
any record; records carry `run_id` with safe keys only).

## Milestone
M08 — Pipeline orchestration

## Status
IMPLEMENTED

## Owner
OCR Platform team
