# src/ocr_platform/flow/adapters.py

## Role

Load local Paddle recognition and Laya category checkpoints.

## Contracts

Require Laya's weights and local encoder configuration. Select eager inference
using legacy fast/compile flags to avoid the released wheel's missing backend
module. Set Paddle's source-check flag before toolkit import.

Checkpoint hashes and versions identify inference. Paddle consumes BGR crops; Laya sees OCR text and allowed categories only. Local artifacts required; no verified labels sent. See docs/flow.md and ADR-010.

## Infrastructure

Pillow, numpy, optional PaddleOCR/PaddlePaddle/Laya.

## Depends on

benchmark engines; CLI; local checkpoints.

## Tests

Mock adapter contract tests, including numpy confidence.

## Milestone

Experimental annotated-crop trial; production extractor remains planned.

## Status

IMPLEMENTED (not GitNexus VERIFIED).

## Owner

engineering; survey owns codebook and verified human corrections.
