# src/ocr_platform/benchmark/prepare.py

## Role

Deterministic batch/size-balanced sample and offline labeling artifact.

## Contracts

2-100 documents; 10MB/10-page source limits; no overwrite of existing label artifacts. Source hash and disjoint document holdout are recorded before labels. Real PDFs start unclassified; expected answers are never generated.

Outputs are evaluation-only artifacts. See docs/benchmark.md and ADR-009.

## Infrastructure

pypdf, pypdfium2, pillow; labeler.html template. No credentials are committed.

## Depends on

Called by: cli. Python module imports define direct collaborators.

## Tests

Balanced reproducible sample, real render, embedded images, overwrite refusal. See tests/test_benchmark.py.

## Milestone

R0 evaluation prerequisite, independent of production extraction.

## Status

IMPLEMENTED (not GitNexus VERIFIED).

## Owner

engineering; survey owns human transcription and data classification.
