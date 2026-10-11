## Role

Closed-vocabulary snapping via RapidFuzz — maps OCR text to known Hindi field values.

## Contracts

- `SemanticEngine.process(cell_id, field_key, text, row_idx)`: snaps raw OCR text to closed-vocab value, detects ditto propagation

## Infrastructure

- `rapidfuzz` for fuzzy string matching

## Depends on

- `rapidfuzz.fuzz`, `rapidfuzz.process` (external)

## Tests

- `tests/test_worker.py`

## Milestone

M06 — Semantic snapping

## Status

IMPLEMENTED

## Owner

OCR Platform team
