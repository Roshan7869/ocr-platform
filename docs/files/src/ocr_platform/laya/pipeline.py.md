# src/ocr_platform/laya/pipeline.py

## Role
Runs cell-level Laya gates and household QA.

## Contracts
`process_cell()` returns `CellDecision`; prior confidence is explicit and defaults to 0.8 for compatibility.

## Infrastructure
PyTorch on the configured device.

## Depends on
`ocr_platform.laya.layers`, `ocr_platform.laya.config`.

## Tests
`tests/test_laya_layers.py`.

## Milestone
M08 decision orchestration.

## Status
IMPLEMENTED

## Owner
OCR Platform team
