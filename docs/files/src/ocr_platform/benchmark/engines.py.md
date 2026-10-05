# src/ocr_platform/benchmark/engines.py

## Role

Tesseract, Google Document AI, and existing local vision crop recognizers.

## Contracts

Recognizers produce raw transcription and uncalibrated confidence, never acceptance. Google requires pinned processor version and token; errors omit payloads. Local models require cached weights and a commit revision, with remote code disabled.

Outputs are evaluation-only artifacts. See docs/benchmark.md and ADR-009.

## Infrastructure

stdlib; Tesseract binary/hin+eng data; optional torch/transformers/accelerate; GOOGLE_ACCESS_TOKEN for Google. No credentials are committed.

## Depends on

Called by: runner, cli. Python module imports define direct collaborators.

## Tests

Mocked TSV Unicode/confidence and REST payload/errors; real engine accuracy requires labeled corpus. See tests/test_benchmark.py.

## Milestone

R0 evaluation prerequisite, independent of production extraction.

## Status

IMPLEMENTED (not GitNexus VERIFIED).

## Owner

engineering; survey owns human transcription and data classification.

