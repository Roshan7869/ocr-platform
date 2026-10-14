# src/ocr_platform/worker/bayesian.py

## Role
Maintains field/glyph priors and computes evidence posteriors.

## Contracts
Scores are bounded and serializable; scoring never accepts values automatically.

## Infrastructure
Python dataclasses and numeric calculations.

## Depends on
Evidence-store prior records when persistence is enabled.

## Tests
Bayesian scoring tests.

## Milestone
M07 evidence scoring.

## Status
IMPLEMENTED

## Owner
OCR Platform team
