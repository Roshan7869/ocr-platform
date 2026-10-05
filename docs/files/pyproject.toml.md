# pyproject.toml

## Role

Package build, benchmark/flow CLI entry points, and isolated dependency extras.

## Contracts

Production Paddle pins remain deferred to the spike. Optional benchmark installs rendering; benchmark-local installs inference libraries, not model weights. Wheel includes benchmark HTML resources.

The optional flow extra adds experimental PaddleOCR/PaddlePaddle/Laya dependencies;
it does not download checkpoints. The dev extra includes numpy for adapter tests.
The ocr-train entry point validates supervision or runs local classifier pilots;
the official Laya training source must be provided separately.

Outputs are evaluation-only artifacts. See docs/benchmark.md and ADR-009.

## Infrastructure

hatchling, project/dev/benchmark extras. No credentials are committed.

## Depends on

Called by: pip / uv build-install. Python module imports define direct collaborators.

## Tests

Editable install, CLI availability, lint/tests. See tests/test_benchmark.py.

## Milestone

R0 evaluation prerequisite, independent of production extraction.

## Status

IMPLEMENTED (not GitNexus VERIFIED).

## Owner

engineering; survey owns human transcription and data classification.
