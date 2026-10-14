# src/ocr_platform/export/writer.py

## Role
Exports evidence as long CSV, wide CSV, household JSON, and ZIP.

## Contracts
`ExportEngine.export()` returns output paths and returns no output for an empty run.

## Infrastructure
SQLite, pandas, JSON, CSV, and ZIP.

## Depends on
Evidence-store schema from `worker.provenance.store`.

## Tests
Export integration tests.

## Milestone
M10 export.

## Status
IMPLEMENTED

## Owner
OCR Platform team
