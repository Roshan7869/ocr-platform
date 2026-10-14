# src/ocr_platform/laya/layers.py

## Role
Implements geometry, candidate, semantic, evidence, and household QA layers.

## Contracts
Inference is deterministic and low-confidence evidence routes to human review.

## Infrastructure
PyTorch with rule-based inference paths.

## Depends on
Torch tensors and configured thresholds.

## Tests
`tests/test_laya_layers.py`.

## Milestone
R0 decision gates.

## Status
IMPLEMENTED

## Owner
OCR Platform team
