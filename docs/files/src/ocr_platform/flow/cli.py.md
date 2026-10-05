# src/ocr_platform/flow/cli.py

## Role

Expose run, demo and human review commands.

## Contracts

Run uses local checkpoints and annotated regions. Demo explicitly simulated. No auto-accept or full-page extraction. Field cap bounds trials. See docs/flow.md and ADR-010.

## Infrastructure

argparse; optional flow extra.

## Depends on

benchmark runner/dataset; flow adapters/pipeline/review.

## Tests

Synthetic end-to-end smoke and CLI help.

## Milestone

Experimental annotated-crop trial; production extractor remains planned.

## Status

IMPLEMENTED (not GitNexus VERIFIED).

## Owner

engineering; survey owns codebook and verified human corrections.

