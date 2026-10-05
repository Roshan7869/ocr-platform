# src/ocr_platform/training/classifier.py

## Role

Fine-tune an existing Laya decision head locally and compare checkpoints.

## Contracts

Freeze pretrained encoder; use official training source and soft CE. Validation records are separated before training/calibration. Holdout is excluded from optimization. Outputs are local candidates/reports; no production promotion or auto-accept. Draft/reused pilot evaluations are exploratory.

## Infrastructure

torch, transformers, safetensors, local checkpoints, explicit official Laya source checkout. HF_HUB_OFFLINE and TRANSFORMERS_OFFLINE; no uploads.

## Depends on

training dataset; LayaClassifier; official laya.train and calibrate.

## Tests

Real two-epoch and ten-epoch pilots; failure-aware category scoring tests.

## Milestone

Experimental local training and documentation alignment; production gates remain open.

## Status

IMPLEMENTED (not GitNexus VERIFIED).

## Owner

engineering; survey owns independently verified gold labels and codebooks.
