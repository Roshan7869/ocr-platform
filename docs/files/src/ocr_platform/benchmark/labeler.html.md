# src/ocr_platform/benchmark/labeler.html

## Role

Offline human answer-box annotation and JSON export/import.

## Contracts

Answer-region-only mode exports null expected text for inference. A human box
does not imply a verified transcription. Existing readable label mode still
requires independently verified text.

Normalized image-top-left coordinates; labeler identity; no network requests. State/type distinguish text, marks, blanks, and unreadable. Import must match source hashes, paths, splits, and page counts. In-memory changes require export.

Outputs are evaluation-only artifacts. See docs/benchmark.md and ADR-009.

## Infrastructure

modern browser; generated embedded images/dataset. No credentials are committed.

## Depends on

Called by: prepare. Python module imports define direct collaborators.

## Tests

Browser smoke: box drawing, saving, deletion, classification, export/resume; prepared HTML payload replacement. See tests/test_benchmark.py.

## Milestone

R0 evaluation prerequisite, independent of production extraction.

## Status

IMPLEMENTED (not GitNexus VERIFIED).

## Owner

engineering; survey owns human transcription and data classification.
