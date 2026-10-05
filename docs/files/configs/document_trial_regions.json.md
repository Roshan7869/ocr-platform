# configs/document_trial_regions.json

## Role

Reproduce visually selected trial crop boxes without publishing answer content.

## Contracts

Two source PDFs verified by hashes, 20 handwriting regions and 3 printed legend controls. All expected values null; development only. No gold labels or corpus-accuracy claim.

## Infrastructure

JSON, benchmark schema.

## Depends on

prepare_document_trial.py; survey files provided locally.

## Tests

Strict dataset validation and local source-hash verification.

## Milestone

Experimental local document trial.

## Status

IMPLEMENTED (not GitNexus VERIFIED).

## Owner

engineering; survey owns independently verified ground truth.

