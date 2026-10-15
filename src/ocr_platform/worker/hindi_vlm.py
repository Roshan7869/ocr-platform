"""HindiOCR-VLM inference wrapper.

Bridges MS-SWIFT GOT-OCR2.0 + HindiOCR-VLM LoRA into the pipeline's
_run_vlm() interface. Gracefully degrades when MS-SWIFT or GPU is missing.

Usage:
    from ocr_platform.worker.hindi_vlm import HindiVLMEngine
    engine = HindiVLMEngine()          # lazy-init, no GPU needed at import
    result = engine.ocr(crop_bgr)      # returns {"value", "conf", "engine"} or None
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

import cv2
import numpy as np

_MODEL_ID = os.environ.get("HINDI_VLM_MODEL_ID", "shaoncvit/HindiOCR-VLM")
# FormLens and HindiOCR-VLM are LoRA adapters trained from GOT-OCR2.0.
_BASE_MODEL = os.environ.get("HINDI_VLM_BASE_MODEL", "-ai/GOT-OCR2_0")
_ADAPTER_DIR = os.environ.get(
    "HINDI_VLM_ADAPTER_DIR",
    os.environ.get("FORM_LENS_ADAPTER_DIR", ""),
)
_USE_SWIFT = os.environ.get("USE_HINDI_VLM", "1") == "1"
_MAX_PIXELS = os.environ.get("HINDI_VLM_MAX_PIXELS", "401408")
_BATCH_SIZE = int(os.environ.get("HINDI_VLM_BATCH_SIZE", "8"))


class HindiVLMEngine:
    """Thin wrapper around MS-SWIFT inference for HindiOCR-VLM.

    Falls back to None if MS-SWIFT is not installed or no adapter is available.
    Uses in-process swift.infer() call (no subprocess spawn).
    """

    def __init__(self):
        self._available = False
        self._adapter_dir = ""
        self._failure: str | None = None
        self._swift_infer = None  # cached swift.infer callable

        if not _USE_SWIFT:
            return

        # The pip distribution is named ms-swift; its Python module/CLI is swift.
        try:
            import swift

            self._swift_infer = swift.infer
        except ImportError:
            self._failure = "swift_not_installed"
            return

        # Resolve adapter directory
        adapter = _ADAPTER_DIR
        if not adapter:
            # Try HuggingFace cache
            cache_base = Path.home() / ".cache" / "huggingface" / "hub"
            candidate = cache_base / f"models--{_MODEL_ID.replace('/', '--')}"
            if candidate.exists():
                # Find the snapshot with adapter weights
                for snap in (
                    (candidate / "snapshots").iterdir()
                    if (candidate / "snapshots").exists()
                    else []
                ):
                    if (snap / "adapter_config.json").exists():
                        adapter = str(snap)
                        break

        if not adapter or not Path(adapter).exists():
            self._failure = "lora_adapter_not_found"
            return

        self._adapter_dir = adapter
        self._available = True

    @property
    def available(self) -> bool:
        return self._available

    def ocr(self, crop_bgr: np.ndarray) -> dict[str, Any] | None:
        """Run one crop through the batch path for backward compatibility."""
        return self.ocr_many([crop_bgr])[0]

    def ocr_many(self, crops_bgr: list[np.ndarray]) -> list[dict[str, Any] | None]:
        """Run a batch of crops through MS-SWIFT inference.

        Uses in-process swift.infer() (no subprocess). Results preserve input
        order; missing model results become ``None`` and remain review candidates.
        """
        empty = [None] * len(crops_bgr)
        if not crops_bgr:
            return empty
        if not self._available:
            return empty
        if self._failure:
            return empty
        if self._swift_infer is None:
            return empty

        try:
            with tempfile.TemporaryDirectory(prefix="ocr-platform-swift-") as work_dir:
                work = Path(work_dir)
                image_paths = []
                for index, crop_bgr in enumerate(crops_bgr):
                    path = work / f"crop_{index:04d}.png"
                    if not cv2.imwrite(str(path), crop_bgr):
                        return empty
                    image_paths.append(str(path))
                jsonl_path = self._write_input_jsonl(image_paths, work / "input.jsonl")
                result_path = work / "infer_result.jsonl"

                # Call swift.infer() as a Python function — no subprocess.
                # Each call still loads the model into VRAM, but we avoid
                # Python process spawn overhead and get better error handling.
                try:
                    self._swift_infer(
                        model=_BASE_MODEL,
                        adapters=self._adapter_dir,
                        infer_backend="transformers",
                        stream=False,
                        temperature=0,
                        val_dataset=str(jsonl_path),
                        max_new_tokens=256,
                        max_batch_size=_BATCH_SIZE,
                        result_path=str(result_path),
                        output_dir=str(work / "output"),
                    )
                except Exception as e:  # noqa: BLE001 - VLM backend raises varied runtime errors; failure degrades to review-only
                    self._failure = f"swift_infer_exception: {e}"
                    return empty

                predictions = self._parse_outputs(work, len(crops_bgr))
                return [
                    {"value": value, "conf": 0.80, "engine": "hindiocr_vlm"} if value else None
                    for value in predictions
                ]
        except Exception as e:  # noqa: BLE001 - VLM batch tempdir covers varied I/O/model errors; failure degrades to review-only
            self._failure = f"swift_infer_exception: {e}"
            return empty

    def _write_input_jsonl(self, image_paths: list[str], path: Path) -> Path:
        """Write one multimodal JSONL record per crop for batch inference."""
        with path.open("w", encoding="utf-8") as stream:
            for image_path in image_paths:
                json.dump(
                    {
                        "messages": [
                            {
                                "role": "user",
                                "content": "<image>OCR this handwritten Hindi form field. Output only the text.",
                            }
                        ],
                        "images": [image_path],
                    },
                    stream,
                    ensure_ascii=False,
                )
                stream.write("\n")
        return path

    def _parse_outputs(self, out_dir: Path, expected: int) -> list[str | None]:
        """Find ordered MS-SWIFT inference results, padding missing responses."""
        values: list[str] = []
        for jf in sorted(out_dir.rglob("infer_result*.jsonl")):
            try:
                with jf.open(encoding="utf-8") as stream:
                    for line in stream:
                        data = json.loads(line.strip())
                        resp = data.get("response", "").strip()
                        if resp:
                            values.append(resp)
            except Exception:  # noqa: BLE001, S112 - corrupt/missing VLM result files are skipped; no logging surface in this module
                continue
        return (values + [None] * expected)[:expected]

    def status(self) -> dict[str, Any]:
        """Return engine status for diagnostics."""
        return {
            "available": self._available,
            "adapter_dir": self._adapter_dir,
            "model_id": _MODEL_ID,
            "base_model": _BASE_MODEL,
            "batch_size": _BATCH_SIZE,
            "failure": self._failure,
            "inference_mode": "in_process" if self._swift_infer else "unavailable",
        }
