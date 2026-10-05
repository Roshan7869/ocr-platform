# tests/test_training.py

## Role

Check supervision, split and scoring safeguards without training downloads.

## Contracts

Reject unverified prediction targets, cross-split document overlap, synthetic evaluation, mismatched taxonomy and tampered crop evidence. Ground truth never enters inference state. Runtime failures count as incorrect and cannot log private input.

## Infrastructure

unittest/pytest, Pillow; synthetic unit fixtures.

## Depends on

training dataset/classifier and flow rules.

## Tests

Seven unit tests.

## Milestone

Experimental local training and documentation alignment; production gates remain open.

## Status

IMPLEMENTED (not GitNexus VERIFIED).

## Owner

engineering; survey owns independently verified gold labels and codebooks.
