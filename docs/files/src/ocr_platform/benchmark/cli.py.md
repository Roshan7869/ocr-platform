# src/ocr_platform/benchmark/cli.py

## Role

Prepare/validate/run/compare command interface.

## Contracts

Fail before engine setup if no verified labels. Comparison requires identical dataset/render/split/evaluation identity and scale assumptions. Console omits transcriptions. Exit 1 for scorable engine failures; 2 for invalid inputs/setup.

Outputs are evaluation-only artifacts. See docs/benchmark.md and ADR-009.

## Infrastructure

argparse; package modules; optional engine dependencies. No credentials are committed.

## Depends on

Called by: project entry point / python -m. Python module imports define direct collaborators.

## Tests

Incompatible comparison rejection, help/prepare/validate smoke; CLI numeric validation. See tests/test_benchmark.py.

## Milestone

R0 evaluation prerequisite, independent of production extraction.

## Status

IMPLEMENTED (not GitNexus VERIFIED).

## Owner

engineering; survey owns human transcription and data classification.
