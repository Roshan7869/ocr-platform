# src/ocr_platform/training/dataset.py

## Role

Validate supervised occupation records and document-separated splits.

## Contracts

Raw scans and model predictions are not targets. Draft labels/codebooks require explicit pilot mode; synthetic prototypes are training-only. Real labels require matching crop hashes. Fingerprint the taxonomy/rules and exclude gold from model input.

## Infrastructure

stdlib; benchmark hashes/evidence checks.

## Depends on

flow field rules; training classifier/CLI.

## Tests

Leakage, missing targets, taxonomy changes, evidence tampering and label-source tests.

## Milestone

Experimental local training and documentation alignment; production gates remain open.

## Status

IMPLEMENTED (not GitNexus VERIFIED).

## Owner

engineering; survey owns independently verified gold labels and codebooks.
