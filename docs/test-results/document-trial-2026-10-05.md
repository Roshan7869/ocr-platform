# Local document trial — 2026-10-05

Real local model inference on two WARD-42 PDFs, one from each batch. These are
development examples chosen for a wiring trial, not a representative accuracy set.
No survey answers, names, crop images, PDFs or model weights are published here.

## Scope and outcome

| Item | Result |
|---|---:|
| PDFs / source pages | 2 / 4 |
| Visually selected handwriting crops | 20 |
| Separately identified printed legend controls | 3 |
| OCR calls completed / runtime failures | 23 / 0 |
| Laya category calls completed / runtime failures | 3 / 0 |
| Handwritten occupations reaching Laya | 0 of 5 |
| Review candidates / automatically accepted | 23 / 0 |
| Verified transcription or category labels | 0 |

The handwriting trial covers five names, five ages, five gender codes and five
occupations. The printed controls come from the employment legend and are **not
filled survey answers**. All five handwritten occupations failed the OCR gate
(low confidence or empty output), so they were not sent to Laya. This is intended.

Visual spot checks found numeric misreads, including 48 read as 98 and 24 read
as 2. The latter OCR confidence was approximately 0.934. Laya assigned OTHER to
all three printed employment controls; two had confidence above 0.94. This
does not establish useful occupation accuracy. Keep final values null until a
reviewer verifies them; collect independent labels before tuning either model.

Exact-match accuracy and character error rate are null because there is no
independent ground truth. OCR inference for 23 crops totaled approximately
0.927 seconds; rendering totaled 0.279 seconds. These exclude checkpoint loading,
Laya inference, human review and full-form segmentation and are not a throughput
promise for the corpus in lakhs.

## Runtime and reproducibility

Windows CPU, Python 3.12.14; PaddleOCR 3.7.0, PaddlePaddle 3.3.1, PaddleX 3.7.2,
Laya 0.3.26, Torch 2.14.1, Transformers 5.18.0, numpy 2.3.5. Relevant constraints
are recorded in `configs/flow_trial_constraints.txt`.

OCR: official `devanagari_PP-OCRv5_mobile_rec` inference weights,
checkpoint fingerprint `8736cf9d2703949f9d4630549f7d632bb7e2d14603e24cdf4c8f05fa74b5a5e1`.
Classifier: `convaiinnovations/laya-multilingual`, publisher revision
`e4e9ddf21a7b1903b7acffd8814ad4307bf63a67`, with weights, tokenizer and
`encoder/config.json` stored locally. Model directories are ignored by Git.

The published Laya wheel omits its optional backend-dispatch package. The adapter
now uses the supported `fast=False, compile=False` API to select eager inference.
Offline setup must include the encoder configuration; this is checked before
loading. Paddle's source-check flag is set before importing its toolkit.

```powershell
.venv/Scripts/python.exe scripts/prepare_document_trial.py --out runs/document-trial/dataset.json
.venv/Scripts/python.exe -m ocr_platform.flow.cli run --dataset runs/document-trial/dataset.json --paddle-model-dir models/devanagari_PP-OCRv5_mobile_rec_infer --laya-model-dir models/laya-multilingual --out runs/document-trial/results
```

The preparation script refuses to overwrite an existing dataset. Source files
must match the hashes in `configs/document_trial_regions.json`. Trial results
stay under ignored `runs/`; the source files stay under ignored `data/`.

Automated regression checks cover model-output routing, normalization, failure
sanitization, checkpoint loading, evidence hashes, resume behavior and immutable
human corrections. See `tests/test_flow.py` and `tests/test_benchmark.py`.
All 31 tests pass; Ruff lint and formatting checks pass.
