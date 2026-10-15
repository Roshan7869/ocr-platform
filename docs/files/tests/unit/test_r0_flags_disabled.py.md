# tests/unit/test_r0_flags_disabled.py

## Role
Gate G3: proves R0 flags disabled force review regardless of confidence.

## Contracts
With `allow_auto_accept=False`, every cell disposition is `review` with
`final_value None` across confidences 0.50–0.99; the suite also pins the
sensitive direction (`allow_auto_accept=True` + high confidence accepts).

## Infrastructure
pytest, unittest.mock, numpy; real Laya/arbiter/bayesian path with mocked
OCR dispatch and slicing.

## Depends on
`ocr_platform.orchestrator.pipeline.SurveyPipeline`.

## Tests
This file is the test suite.

## Milestone
R0 exit gate G3.

## Status
IMPLEMENTED

## Owner
OCR Platform team
