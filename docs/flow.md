# Experimental PaddleOCR → validation → Laya → human review

This CLI tests human-selected answer crops from survey PDFs. It does not yet locate table rows, register templates, detect answer boxes, process checkboxes, or extract complete households automatically. It can use real local model checkpoints; the demo uses simulated responses. Two local Laya classifier-head training pilots have now completed without measured improvement; see [fine-tuning results](test-results/fine-tuning-pilot-2026-10-05.md). PaddleOCR remains unfine-tuned.

PaddleOCR reads the crop. Deterministic checks validate age, digits, exact codes, blank answers and ditto marks. Laya suggests a category for occupation text only. Every model decision starts in human review with null final values. A human correction supplies the accepted value and category, linked to the original crop and decision.

## Try the wiring now

From the repository root in PowerShell:

```powershell
.venv/Scripts/python.exe -m ocr_platform.flow.cli demo --out runs/flow-demo
```

The four synthetic examples exercise occupation classification, an invalid age, an unresolved ditto and an empty answer. This proves integration, not Hindi handwriting accuracy. The command prints its output folder.

In that folder, inspect `summary.json`, `review_candidates.json`, `result.json`, and the PNGs under `crops/`. Model observations remain in `decisions.jsonl`. Human edits append to `human_revisions.jsonl`; `result.json` pairs each original decision with its latest human revision. Read the revision when present to obtain the effective final value. Unreadable revisions remain in the review queue.

## Set up the real models

```powershell
uv pip install --python .venv/Scripts/python.exe -e ".[dev,benchmark,flow]" -c configs/flow_trial_constraints.txt
```

The flow extra installs PaddleOCR (the OCR toolkit), PaddlePaddle (its execution framework), and Laya. CPU is the default; GPU runtime compatibility needs a separate environment check. These are experiment dependency ranges, not production pins. Model files are not included and inference does not download them.

Prepare a local Paddle inference-model directory compatible with `TextRecognition`, including its configuration and inference weights. The default name is `devanagari_PP-OCRv5_mobile_rec`. A Laya directory must include `rl_agent_config.json`, `model.safetensors`, a local `tokenizer/` directory and `encoder/config.json`. Use a checkpoint supported by the installed Laya package. Checkpoint contents and package versions enter each run identity. The adapter selects eager inference with `fast=False, compile=False` because the released wheel omits the optional backend-dispatch package.

The tested multilingual checkpoint can be prepared separately while online:

```python
from huggingface_hub import snapshot_download

snapshot_download(
    "convaiinnovations/laya-multilingual",
    revision="e4e9ddf21a7b1903b7acffd8814ad4307bf63a67",
    local_dir="models/laya-multilingual",
    allow_patterns=["rl_agent_config.json", "model.safetensors", "tokenizer/*", "encoder/*"],
)
```

See the [actual document trial report](test-results/document-trial-2026-10-05.md)
for outcomes and reproducible crop-region inputs. Real inference completed, but
the trial found recognition and classification errors; independent labels and
task-specific evaluation are still needed.

Sources: [Paddle TextRecognition documentation](https://www.paddleocr.ai/main/en/version3.x/module_usage/text_recognition.html), [Laya repository and checkpoint setup](https://github.com/NandhaKishorM/laya).

## Prepare a small real-scan trial

Use the benchmark labeling page (see [benchmark guide](benchmark.md)) to draw tight boxes around individual answer text. Select “Answer region only” if there is no independently verified transcription; this exports `expected: null`. Verified labels are needed to measure accuracy and remain hidden from the classifier. Use field IDs such as `member.row1.occupation`, `member.row1.age`, `member.row1.name`, or `document.ward`. Download the edited dataset JSON before running.

Example with local checkpoint paths:

```powershell
.venv/Scripts/python.exe -m ocr_platform.flow.cli run --dataset runs/benchmark/trial/dataset.json --paddle-model-dir models/paddle/devanagari-rec --laya-model-dir models/laya --out runs/flow-trial
```

The maximum is 500 text fields per trial by default; use `--max-fields` to change it deliberately. Marks are excluded. Recognition uses the human crop, not a detected text-box claim. Mixed Hindi/English, handwriting and multiline answers need empirical checks; printed Devanagari support does not establish handwritten accuracy. Keep this trial small before planning for lakhs of documents.

`configs/flow_rules_v1.json` contains **draft** occupation categories and illustrative confidence thresholds. Replace these with the survey codebook before judging category accuracy. Scores are uncalibrated; high confidence never triggers automatic acceptance. Unknown fields, uncertain OCR, invalid values, unknown categories and model errors stay in review.

## Record a human correction

Copy a decision ID from the review candidates, inspect its crop, then:

```powershell
.venv/Scripts/python.exe -m ocr_platform.flow.cli review --run runs/flow-trial/classified/RUN_ID --decision-id DECISION_ID --value "30" --reviewer "reviewer-1"
```

For occupation supply the exact human-selected category, for example `--category SELF_EMPLOYED`. To record a verified blank use `--state absent --value ""`; to preserve an unreadable answer use `--state unreadable --value ""`. The latter stays unresolved. Corrections preserve original OCR and model suggestions, verify crop hashes, append a chained revision and rebuild the effective results and pending queue. Reruns reuse completed model decisions.

## What to measure next

Measure transcription exact match and character error rate on independently labeled holdout crops through the benchmark report. Measure occupation category accuracy separately against a human codebook label; this CLI does not yet calculate that metric. Record latency, OCR failures and review workload before extrapolating to the full corpus. Training is a later step: export verified corrections, build document-separated training/validation/holdout splits, and compare fine-tuned checkpoints against these baselines. No corpus-wide throughput or accuracy claim follows from the demo.
