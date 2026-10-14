# Kaggle T4 execution

This project has two GPU paths:

1. `kaggle_run.py` renders pages, slices fields, records provenance, and
   exports CSV/JSON/ZIP outputs.
2. `worker/hindi_vlm.py` uses a FormLens/HindiOCR-VLM LoRA adapter through
   the `swift infer` CLI for handwriting crops.

FormLens is a GOT-OCR2.0 LoRA adaptation for handwritten form digitization.
This repository uses it as the handwriting crop recognizer inside the
provenance-first template pipeline, preserving field identity and evidence.

## Kaggle setup

Attach the survey PDFs, this repository, and a FormLens or HindiOCR-VLM LoRA
checkpoint containing `adapter_config.json` and adapter weights. Enable one
NVIDIA T4 GPU, then set:

```python
import os
os.environ["USE_HINDI_VLM"] = "1"
os.environ["HINDI_VLM_ADAPTER_DIR"] = "/kaggle/input/hindi-vlm-lora"
os.environ["HINDI_VLM_BASE_MODEL"] = "stepfun-ai/GOT-OCR2_0"
os.environ["HINDI_VLM_MAX_PIXELS"] = "401408"
```

Install without replacing Kaggle's CUDA-enabled PyTorch:

```bash
pip install -q pypdfium2 paddleocr paddlepaddle-gpu opencv-contrib-python \
  rapidfuzz transformers accelerate ms-swift pandas pillow numpy
```

Run:

```bash
python kaggle_run.py
```

The runner uses MS-SWIFT's `transformers` inference backend, passes the GOT
base model plus LoRA adapter, and bounds visual pixels to reduce T4 OOM risk.
For repeatable offline runs, attach the base model as a Kaggle dataset and set
`HINDI_VLM_BASE_MODEL` to its local path.

Outputs are written below `/kaggle/working/output/`: `evidence.db`, exported
CSV/JSON files, ZIP archives, and `run_manifest.json`. Model failures remain
review candidates and are never silently accepted.
