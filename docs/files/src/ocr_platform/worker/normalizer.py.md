## Role

Text normalization: Unicode NFC, Devanagari digit transliteration, lookalike correction, phone stripping.

## Contracts

- `SpatialNormalizer.normalize(text, field_key)`: normalizes OCR text for a given field

## Infrastructure

- Standard library only (`re`, `unicodedata`)

## Depends on

- Standard library only

## Tests

- `tests/test_worker.py`

## Milestone

M05 — Normalizer

## Status

IMPLEMENTED

## Owner

OCR Platform team
