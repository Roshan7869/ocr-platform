# src/ocr_platform/training/cli.py

## Role

Expose training-manifest validation and local classifier fine-tuning.

## Contracts

Require manifest, matching codebook, explicit pilot flag for draft supervision and explicit source checkout. Refuse to overwrite an output directory. Aggregate console output only; private inputs and weights remain under ignored runs/models.

## Infrastructure

argparse; existing flow dependencies; local source/checkpoint paths.

## Depends on

training dataset/classifier; flow load_rules.

## Tests

CLI validation, manifest guards and local training pilot.

## Milestone

Experimental local training and documentation alignment; production gates remain open.

## Status

IMPLEMENTED (not GitNexus VERIFIED).

## Owner

engineering; survey owns independently verified gold labels and codebooks.
