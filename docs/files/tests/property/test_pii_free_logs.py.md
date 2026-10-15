# tests/property/test_pii_free_logs.py

## Role
Gate G6: proves no emitted log line contains a known fixture PII value.

## Contracts
Fake PII (name, mobile) flows through the real pipeline path while
`caplog` captures `ocr_platform.observability` records; every record must
carry `run_id` and only PII-safe keys, and must not contain the values.

## Infrastructure
pytest, caplog, unittest.mock, numpy; mocked OCR dispatch and slicing.

## Depends on
`ocr_platform.orchestrator.pipeline.SurveyPipeline` and
`ocr_platform.observability`.

## Tests
This file is the test suite.

## Milestone
R0 exit gate G6.

## Status
IMPLEMENTED

## Owner
OCR Platform team
