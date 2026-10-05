# Fine-tuning feasibility and pilot — 2026-10-05

The data directory was inspected again: 1,446 two-page PDFs, 2,892 pages,
1,326 documents in 1RN-982 and 120 in 11RN-985. No PDF text layer and no parse
errors were found. This remains the local sample of a wider corpus in lakhs.

Ten filled forms (95–99 in both batches) were visually inspected for occupation
content. Repeated daily-wage entries, a legible private-employment entry, dashes,
English/Hindi handwriting and ambiguous cells were observed. These are feasible
source images for supervised labeling; the directory contains no independent
transcription/category gold set. Fixed boxes do not solve variation in layout,
dynamic rows, handwritten strokes or ditto semantics.

## Actual training

Two real Laya head-adaptation runs completed locally: two epochs and ten epochs.
The encoder was frozen; soft cross-entropy and option-order augmentation trained
the existing decision head. The official source revision was
8a6e1328cce2460a0e5aa348ad465bb1b5821cd2. Source inference/training identified
itself as Laya 0.3.27; the original document trial used the released 0.3.26 wheel.

Supervision: eight visually transcribed draft survey entries from eight PDFs and
twelve synthetic teaching prototypes for the six draft categories. Of twenty
records, fifteen were training, two validation and three exploratory evaluation.
The real source-document hashes were kept disjoint across splits; synthetic
groups were train-only. Labels were explicitly engineering_visual or
engineering_synthetic, not human_verified. No survey answers or images are
included in this published report.

| Check | Base | Two-epoch candidate | Ten-epoch candidate |
|---|---:|---:|---:|
| Validation correct / cases | 0 / 2 | 0 / 2 | 0 / 2 |
| Exploratory comparison correct / cases | 0 / 3 | 0 / 3 | 0 / 3 |
| Model call failures | 0 | 0 | 0 |
| Production promotion | no | no | no |

The comparison contains only daily-wage and salaried examples and was reused
across pilot runs. It is **not an independent gold holdout or a six-class accuracy
estimate**. No improvement was demonstrated. The ten-epoch training loss fell
from approximately 3.84 to 1.91, but that did not translate into correct
evaluation answers; lower training loss is not sufficient evidence to deploy.

Ten-epoch candidate fingerprint:
9023a5235c9b0d888c1484e38f9ff82c20f127c4b16c6f994f50ab9367353c9d.
Local artifacts are under runs/fine-tuning/laya-pilot-v1 and laya-pilot-v2.
Weights, inputs, crops and raw transcriptions are excluded from Git.
The default checkpoint and review-only posture are unchanged.

## Interpretation

The scans are usable for annotation and a future supervised OCR/classifier
dataset. Their presence does not provide correct training targets automatically.
This small, class-limited frozen-encoder pilot is insufficient for useful
occupation adaptation. It does not prove Laya can never improve; it does prove
these particular candidates should not replace the baseline.

PaddleOCR was not fine-tuned. Real handwriting recognition requires separately
verified image–transcription pairs and recognition training/evaluation. Names,
digits, mixed scripts, blank/ditto cases and occupation words need separate
coverage. Independent review of the draft taxonomy is also required before
treating these six categories as the survey codebook.

Next data work follows docs/data-plan.md and docs/accuracy-plan.md: development
labeling across 20–30 documents, separate calibration and 30–50 fresh holdout
documents, balanced relevant field/category coverage and at least 10% double QA.
All model-produced values continue to require human review.

Implementation verification: 41 tests pass, including training-data leakage,
target provenance, failed-call scoring and documentation-contract gates.
Ruff lint and formatting pass. The real v2 crop recheck retained all 23 fields
in review, including explicit reasons for the 20 declared handwriting fields.
