# scripts/prepare_document_trial.py

## Role

Materialize the trial dataset against a local source directory.

## Contracts

Exclusive output write protects labeled datasets. Validate schema and source hashes; remove incomplete output after failure. Region annotations are not transcriptions.

## Infrastructure

stdlib, installed benchmark package.

## Depends on

benchmark dataset; document_trial_regions.json.

## Tests

Executed against two real PDFs; byte-identical document/field metadata verified.

## Milestone

Experimental local document trial.

## Status

IMPLEMENTED (not GitNexus VERIFIED).

## Owner

engineering; survey owns independently verified ground truth.
