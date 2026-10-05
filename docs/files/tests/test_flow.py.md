# tests/test_flow.py

## Role

Verify experimental flow invariants without model downloads.

## Contracts

Synthetic PDFs and mocked engines do not measure real OCR accuracy. See docs/flow.md and ADR-010.

## Infrastructure

unittest/pytest, Pillow, numpy.

## Depends on

flow modules and benchmark dataset.

## Tests

31 combined benchmark and flow tests.

## Milestone

Experimental annotated-crop trial; production extractor remains planned.

## Status

IMPLEMENTED (not GitNexus VERIFIED).

## Owner

engineering; survey owns codebook and verified human corrections.
