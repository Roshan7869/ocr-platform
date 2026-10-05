# Benchmark before choosing an OCR engine

The 1,446 local WARD-42 PDFs are a pilot sample of a corpus in the lakhs. The
benchmark compares Tesseract, Google Document AI, and an existing local vision
model on **identical human-labeled answer crops**. It is not the production
extractor: answer boxes bypass registration, table segmentation, and field mapping.

## Setup and label

Use Python 3.11 or newer. On Linux substitute `.venv/bin/python`.

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev,benchmark]"
.venv/Scripts/python -m ocr_platform.benchmark.cli prepare `
  --source data/WARD-42/WARD-42 --out runs/benchmark/sample-v1 --count 24 --seed 42
```

Open `runs/benchmark/sample-v1/label.html`. This self-contained local page makes
no network requests. The seed dataset contains **no ground truth**. Draw a box
around one answer line, excluding its printed question, and enter exactly what
is written. Include Hindi/English handwriting, digits, codes, ditto symbols, blank
answers, and difficult scans. Use field IDs such as `member.row1.age`. Preserve
spelling, punctuation, and ditto symbols; do not infer intended answers. Each
field needs a human labeler ID. Mark unreadable answers without inventing text.

Export `dataset.json` to the sample directory, replacing the seed file. Browsers
may add a numbered filename, so explicitly choose the file passed to the runner.
The page retains labels in memory only: export regularly and import the saved
dataset to resume. Independent human spot checks remain necessary.

```powershell
.venv/Scripts/python -m ocr_platform.benchmark.cli validate runs/benchmark/sample-v1/dataset.json
```

The sample is balanced across batches and file-size thirds. Size is a diversity
proxy, not a scan-quality measurement. Document-level holdout splits are assigned
before labeling. Never train, tune prompts, or tune thresholds on holdout.
Balanced results are not population-weighted. Expand to other wards, writers,
scan defects, and form variants before corpus-wide claims.

## Run Tesseract

Install Tesseract and the `hin`/`eng` traineddata files. The runner checks the
executable, version, and languages. PSM 7 assumes a single answer line.

```powershell
.venv/Scripts/python -m ocr_platform.benchmark.cli run `
  --dataset runs/benchmark/sample-v1/dataset.json --engine tesseract `
  --tesseract-path "C:/Program Files/Tesseract-OCR/tesseract.exe" `
  --corpus-documents 300000 --fields-per-document 100
```

## Run Google Document AI

Choose an Enterprise Document OCR processor version supporting the languages
being tested; advertised language support does not establish handwriting accuracy.
Set `GOOGLE_ACCESS_TOKEN` outside the repo to a short-lived OAuth token. Do not
put credentials in datasets or reports. Use a pinned processor version resource.

Preparation leaves real scans `unclassified`. The API runner requires explicit
`--allow-api-upload` and inputs classified `synthetic` or `approved_redacted`.
Only set those classifications when true. Prepare redacted PDFs as a new sample
so hashes/previews match the approved bytes. Do not redact the target answer and
then claim to have benchmarked it; use approved material preserving that task or
an approved synthetic substitute. Raw unclassified uploads are blocked.

```powershell
.venv/Scripts/python -m ocr_platform.benchmark.cli run `
  --dataset runs/benchmark/redacted-sample/dataset.json --engine google-document-ai `
  --processor-version "projects/PROJECT/locations/us/processors/PROCESSOR/processorVersions/VERSION" `
  --allow-api-upload --corpus-documents 300000 --fields-per-document 100 `
  --price-per-1000-input-units YOUR_RATE --currency INR
```

Replace `YOUR_RATE` with the actual numeric processor rate in the chosen currency.
This mode sends **one PNG input per field**, not one PDF per document. It isolates
recognition fairly, but may be substantially more expensive than full-page API
processing. A production API decision needs a second full-page extraction and
cost benchmark. No default provider price is asserted.

## Run an existing local vision model

Choose a multilingual model compatible with Transformers'
`AutoModelForImageTextToText` and multimodal chat templates. Verify Hindi/English
capability, licensing, and hardware needs. No model is selected as a winner or
trained by this tool.

```powershell
.venv/Scripts/python -m pip install -e ".[benchmark,benchmark-local]"
.venv/Scripts/python -m ocr_platform.benchmark.cli run `
  --dataset runs/benchmark/sample-v1/dataset.json --engine local-vlm `
  --model-id ORGANIZATION/MODEL --revision FULL_40_CHARACTER_COMMIT `
  --device auto --corpus-documents 300000 --fields-per-document 100
```

Download weights separately into the Hugging Face cache, pinned to the exact
40-character commit revision. The adapter uses cached weights only, disables
remote custom code, and uses greedy decoding. It records model/runtime versions
and the transcription prompt hash. A later fine-tuned checkpoint can use the
same interface and evaluation protocol.

## Read reports and compare

Each run prints its `report.json` path. Resume reuses journaled predictions;
`--retry-failed` explicitly retries failed fields and accumulates attempt counts,
elapsed time, and conservative API input-unit estimates. There are no automatic
API retries. A crash after submission but before journaling can still cause a
duplicate charge: exactly-once delivery is not claimed.

```powershell
.venv/Scripts/python -m ocr_platform.benchmark.cli compare `
  runs/benchmark/results/RUN_A/report.json runs/benchmark/results/RUN_B/report.json
```

Comparison requires the same dataset, renderer, DPI, split, and evaluation
version. Engine-specific prices may differ. Assess holdout accuracy, handwriting
accuracy, false text on blank answers, failures, time, and correction effort.
Failures remain in the exact-match denominator. CER on successful calls must be
read alongside those failures. Marks and unreadable ground truth are excluded
from text scores. Confidence is uncalibrated and never enables auto-accept.

`--corpus-documents` defaults to 100000. `--fields-per-document` defaults to 100
as an explicit planning assumption; set both to the real workload. Optional
`--hourly-compute-cost`, `--review-hourly-cost`, `--review-seconds-per-field`, and
`--price-per-1000-input-units` support cost scenarios. Unknown prices remain null.
The observed correction/failure rate is **not a production review rate**.
Serial throughput projections exclude model setup/rendering, recorded separately,
and do not imply parallel scaling or an SLA.

If recognition is adequate, next evaluate whole-form registration, populated rows,
ticks, and field assignment. If handwriting remains the main error, collect
verified crop/transcription pairs and fine-tune a suitable pretrained model.
Keep holdout untouched and separate writers/batches where feasible. Many raw
PDFs alone do not constitute a supervised training set.

## Limits and verification

This bounded pilot caps preparation at 100 documents, PDFs at 10MB/10 pages,
rendering at 30 megapixels per page, and runs at 500 fields unless explicitly
raised. It is not a distributed queue for lakhs of forms. Parallel production
workers, storage lifecycle, full-page batching, and SLAs remain separate work.
One writer is allowed per output directory. After an abnormal process termination,
remove `.benchmark.lock` only after confirming no active writer uses it.

Source PDFs, previews, labels, and crops may contain personal data. `data/` and
`runs/` are ignored, including the ZIP. Hash-linked benchmark evidence provides
traceability, not signed authenticity or production approval.

```powershell
.venv/Scripts/python -m pytest -q
.venv/Scripts/python -m ruff check .
.venv/Scripts/python -m ruff format --check .
```

Tests use synthetic PDFs and mocked recognizers, exercising real rendering,
evidence integrity, resume, explicit retries, upload gates, adapter request shapes,
failure-aware scoring, and lakh-scale arithmetic. They do not establish real OCR
accuracy or provider availability.

Primary adapter references:
[Tesseract CLI](https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html),
[Google processing requests](https://docs.cloud.google.com/document-ai/docs/send-request),
[Transformers multimodal generation](https://huggingface.co/docs/transformers/tasks/image_text_to_text).
