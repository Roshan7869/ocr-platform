# Local fine-tuning experiments

Laya is a text classifier. This implementation fine-tunes its decision head for
the draft occupation categories, retaining the pretrained encoder. It does not
train from scratch, fine-tune PaddleOCR, or make handwriting readable.

The raw corpus contains 1,446 PDFs / 2,892 scanned pages and no text layer.
These files are useful source images, not supervised labels. User-authorized
visual inspection produced a small draft pilot; it is not independently verified
gold. Both pilot candidates failed the exploratory comparison and remain local.

## Prepare supervision

Use an identified annotator to transcribe legible occupation text and select its
category from the versioned survey codebook. Do not infer from names, income,
gender, religion or neighboring family members. Preserve literal text and
exclude ambiguous readings until adjudicated. Engineering visual drafts must be
marked engineering_visual; invented teaching examples are engineering_synthetic,
never human_verified. Synthetic prototypes are train-only.

A manifest contains schema_version=1, task=occupation_classification,
rules_sha256 (the SHA-256 of canonical rule JSON), and records. Each record needs
id, split (train/validation/holdout), document_sha256, field_id, literal text,
category, label_source and annotator. Real records also need evidence with
document_sha256, page, bbox, crop_sha256 and crop_path relative to the manifest.
See src/ocr_platform/training/dataset.py for the executable checks.

Group all fields from the same document hash into one split. Reused or draft
pilot holdouts cannot support independent accuracy claims. Establish fresh,
independently labeled documents for final comparison. The data plan calls for
20–30 development documents, 50–100 calibration documents and 30–50 holdout
documents; cover the relevant field kinds and occupation classes and double-key
at least 10%. Those production acceptance gates remain unchanged.

## Validate and train locally

Install the flow dependencies from docs/flow.md. The released Laya wheel omits
its training module, so provide the official source checkout explicitly:

```powershell
git clone https://github.com/NandhaKishorM/laya.git runs/laya-training-source
git -C runs/laya-training-source checkout 8a6e1328cce2460a0e5aa348ad465bb1b5821cd2
.venv/Scripts/python.exe -m ocr_platform.training.cli validate --manifest runs/training/manifest.json --pilot
.venv/Scripts/python.exe -m ocr_platform.training.cli train --manifest runs/training/manifest.json --pilot --training-source runs/laya-training-source --model models/laya-multilingual --out runs/fine-tuning/candidate-trial --epochs 10
```

Use --pilot only for draft/engineering supervision. Verified-label experiments
still require approved codebooks and the same split/evidence checks. Inference
and training load local artifacts offline; model publication is not implemented.
The output directory must be new.

Training uses frozen-encoder adaptation, soft cross-entropy, randomized option
order, micro-batches of two and gradient accumulation of two. Validation is
separate from training; temperature fitting on very small validation sets is
insufficient, so reports do not claim calibrated confidence. Report identities
include checkpoint, training-data and training-source fingerprints. Holdout
scores count failed model calls as incorrect.

The output contains candidate/ (weights, encoder config, tokenizer and Laya
config) plus report.json. Pass that directory explicitly with --laya-model-dir
only for local comparisons; the default flow checkpoint is unchanged.
No candidate can enable automatic acceptance.

## Current outcome and next data work

Read [the actual pilot report](test-results/fine-tuning-pilot-2026-10-05.md).
Two pilots completed but did not improve the tiny evaluation set. More epochs
alone did not solve it; collect richer, balanced, independently checked labels
before another efficacy claim.

PaddleOCR fine-tuning needs separate crop/image–transcription targets,
language-compatible recognition training configuration, and an isolated training
environment. Category labels cannot train OCR. OCR remains the bottleneck when
the occupation text is empty, misread or low-confidence; improved text
classification would not repair those cases.

References: [official Laya fine-tuning guide](https://github.com/NandhaKishorM/laya/blob/main/docs/finetune.md),
[official training implementation](https://github.com/NandhaKishorM/laya/blob/8a6e1328cce2460a0e5aa348ad465bb1b5821cd2/laya/train.py).
