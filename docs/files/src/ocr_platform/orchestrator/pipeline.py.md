## Role

SurveyPipeline — end-to-end orchestrator for PDF/ZIP → structured household data.

## Contracts

- `SurveyPipeline(template_path, db_path, output_dir, laya_config, dpi)`: initializes all modules
- `run(source)`: processes PDF/ZIP/images through M01-M10 pipeline stages
- `_register_and_slice()`: homography-based template alignment + grid slicing
- `_dispatch_ocr()`: tiered OCR dispatch (PaddleOCR → HindiOCR-VLM → IndicOCR)

## Infrastructure

- `cv2` (OpenCV) for image processing and homography
- `numpy` for array operations
- `sqlite3` for evidence persistence

## Depends on

- `ocr_platform.document.loader.DocumentLoader`
- `ocr_platform.laya.pipeline.LayaPipeline`
- `ocr_platform.laya.config.LayaConfig`
- `ocr_platform.worker.*` (arbiter, morphology, normalizer, semantic, provenance, validation)
- `ocr_platform.export.writer.ExportEngine`

## Tests

- `tests/test_orchestrator.py` (integration)

## Milestone

M08 — Pipeline orchestration

## Status

IMPLEMENTED

## Owner

OCR Platform team
