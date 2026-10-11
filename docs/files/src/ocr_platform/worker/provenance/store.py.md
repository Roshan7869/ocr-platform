## Role

SQLite-backed evidence store for pipeline provenance.

## Contracts

- `EvidenceStore(db_path)`: initializes WAL-mode SQLite with 4 tables (run_meta, evidence_log, laya_decisions, qa_anomalies)
- `start_run()`, `finish_run()`: run lifecycle
- `log_cell()`: records per-cell evidence chain
- `log_qa_anomaly()`: records QA anomalies
- `get_run_summary()`, `get_evidence()`, `get_qa_anomalies()`: read methods

## Infrastructure

- `sqlite3` (stdlib, WAL mode)

## Depends on

- Standard library only

## Tests

- `tests/test_worker.py`

## Milestone

M09 — Provenance store

## Status

IMPLEMENTED

## Owner

OCR Platform team
