## Role

HindiOCR-VLM inference wrapper. Bridges MS-SWIFT GOT-OCR2.0 + HindiOCR-VLM LoRA adapter into the pipeline's `_run_vlm()` interface.

## Contracts

- `HindiVLMEngine()`: constructor — lazy-init, no GPU needed at import
- `engine.ocr(crop_bgr)`: run inference on a cell crop → returns `{"value", "conf": 0.80, "engine": "hindiocr_vlm"}` or `None`
- `engine.available`: bool — True only if ms-swift installed + adapter found
- `engine.status()`: dict — returns available, adapter_dir, model_id, base_model for diagnostics
- Adapter resolution order: `HINDI_VLM_ADAPTER_DIR` env var → HuggingFace cache (`models--shaoncvit--HindiOCR-VLM`) → unavailable

## Infrastructure

- MS-SWIFT CLI (`swift infer`) via subprocess
- GOT-OCR2_0 base model (`-ai/GOT-OCR2_0`)
- LoRA adapter (`shaoncvit/HindiOCR-VLM`)
- 30s timeout per inference call

## Depends on

- `ms-swift` (optional, graceful fallback)
- `huggingface_hub` (for cache detection)
- `cv2`, `numpy` (crop I/O)

## Tests

- `tests/test_laya_layers.py` (via pipeline integration)

## Milestone

M03 — OCR dispatch (VLM tier)

## Status

IMPLEMENTED

## Owner

OCR Platform team
