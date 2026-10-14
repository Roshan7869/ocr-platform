# src/ocr_platform/cli.py

## Role
CLI for full survey extraction and synthetic demo.

## Contracts
Provides `ocr-survey run` and `ocr-survey demo` with configurable input, template, output, database, DPI, and device.

## Infrastructure
argparse, Pillow, and SurveyPipeline.

## Depends on
`ocr_platform.orchestrator.pipeline`, `ocr_platform.laya.config`.

## Tests
CLI demo smoke and orchestrator integration tests.

## Milestone
R0 executable entry point.

## Status
IMPLEMENTED

## Owner
OCR Platform team
