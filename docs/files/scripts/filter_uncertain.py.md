## Role

Post-extraction filter: classifies WARD-42 extracted fields into clean / uncertain / blank states, builds review queue.

## Contracts

- Input: JSON array of records (pdf_id, page_1{...}, page_2_members[{...}])
- Output: `filtered.json` (every field classified), `review_queue.csv`, `summary.json`
- Uncertainty sources: trailing '?', flag annotations, uncertain array, blank/null
- Derived checks: head_name mismatch, duplicate mobile, gender/relation mismatch, name containing relation words, future date, constant-field recovery

## Infrastructure

- Standard library only (csv, json, re, unicodedata, collections)

## Depends on

- Standard library only

## Tests

- None (standalone script)

## Milestone

M08 — Post-processing

## Status

IMPLEMENTED

## Owner

OCR Platform team
