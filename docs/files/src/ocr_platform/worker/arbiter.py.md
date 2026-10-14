# src/ocr_platform/worker/arbiter.py

## Role
Selects the highest-confidence OCR candidate deterministically.

## Contracts
Empty candidates become NULL; selected values retain engine and confidence metadata.

## Infrastructure
Python standard library.

## Depends on
OCR candidate dictionaries.

## Tests
Arbiter unit tests.

## Milestone
M07 candidate arbitration.

## Status
IMPLEMENTED

## Owner
OCR Platform team
