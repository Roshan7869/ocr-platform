## Role

Household-level relational QA — validates business rules (head count, father age, wife gender).

## Contracts

- `RelationalQA(db_path)`: validates household business rules after all members are extracted
- `validate(doc_id, run_id, members)`: returns list of QAAnomaly for rule violations

Rules enforced: exactly one head, father >= 18, wife must be female.

## Infrastructure

- `sqlite3` for anomaly persistence

## Depends on

- Standard library only

## Tests

- `tests/test_worker.py`

## Milestone

M08 — Relational QA

## Status

IMPLEMENTED

## Owner

OCR Platform team
