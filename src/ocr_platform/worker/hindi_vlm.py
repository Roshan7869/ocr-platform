"""HindiOCR-VLM inference wrapper.

Bridges MS-SWIFT GOT-OCR2.0 + HindiOCR-VLM LoRA into the pipeline's
_run_vlm() interface. Gracefully degrades when MS-SWIFT or GPU is missing.

Usage:
    from ocr_platform.worker.hindi_vlm import HindiVLMEngine
    engine = HindiVLMEngine()          # lazy-init, no GPU needed at import
    result = engine.ocr(crop_bgr)      # returns {"value", "conf", "engine"} or None
"""

from __future__ import annotations

import os
import tempfile
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import cv2
import numpy as np


_MODEL_ID = "shaoncvit/HindiOCR-VLM"
_BASE_MODEL = "-ai/GOT-OCR2_0"
_ADAPTER_DIR = os.environ.get("HINDI_VLM_ADAPTER_DIR", "")
_USE_SWIFT = os.environ.get("USE_HINDI_VLM", "1") == "1"


class HindiVLMEngine:
    """Thin wrapper around MS-SWIFT inference for HindiOCR-VLM.

    Falls back to None if MS-SWIFT is not installed or no adapter is available.
    """

    def __init__(self):
        self._available = False
        self._adapter_dir = ""
        self._temp_jsonl: str | None = None

        if not _USE_SWIFT:
            return

        # Check if ms-swift is installed
        try:
            import ms_swift  # noqa: F401
        except ImportError:
            return

        # Resolve adapter directory
        adapter = _ADAPTER_DIR
        if not adapter:
            # Try HuggingFace cache
            cache_base = Path.home() / ".cache" / "huggingface" / "hub"
            candidate = cache_base / f"models--{_MODEL_ID.replace('/', '--')}"
            if candidate.exists():
                # Find the snapshot with adapter weights
                for snap in (candidate / "snapshots").iterdir() if (candidate / "snapshots").exists() else []:
                    if (snap / "adapter_config.json").exists():
                        adapter = str(snap)
                        break

        if not adapter or not Path(adapter).exists():
            return

        self._adapter_dir = adapter
        self._available = True

    @property
    def available(self) -> bool:
        return self._available

    def ocr(self, crop_bgr: np.ndarray) -> dict[str, Any] | None:
        """Run HindiOCR-VLM on a cell crop.

        Returns dict with value/conf/engine or None on failure.
        """
        if not self._available:
            return None

        try:
            # Write crop to temp file
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            cv2.imwrite(tmp.name, crop_bgr)
            tmp.close()

            # Write JSONL input for swift infer
            jsonl_path = self._write_input_jsonl(tmp.name)
            out_dir = tempfile.mkdtemp()

            cmd = [
                sys.executable, "-m", "swift", "infer",
                "--adapters", self._adapter_dir,
                "--stream", "false",
                "--temperature", "0",
                "--val_dataset", jsonl_path,
                "--max_new_tokens", "256",
                "--output_dir", out_dir,
            ]

            env = os.environ.copy()
            env["CUDA_VISIBLE_DEVICES"] = os.environ.get("CUDA_VISIBLE_DEVICES", "0")

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30, env=env
            )
            if result.returncode != 0:
                return None

            # Parse output JSONL
            pred = self._parse_output(out_dir)
            if pred:
                return {
                    "value": pred,
                    "conf": 0.80,
                    "engine": "hindiocr_vlm",
                }
        except Exception:
            pass
        finally:
            try:
                os.unlink(tmp.name)
            except Exception:
                pass

        return None

    def _write_input_jsonl(self, image_path: str) -> str:
        """Write a single-image JSONL for swift infer."""
        fd, path = tempfile.mkstemp(suffix=".jsonl")
        with os.fdopen(fd, "w") as f:
            json.dump({
                "query": "OCR this handwritten Hindi form field. Output only the text.",
                "images": [image_path],
            }, f, ensure_ascii=False)
            f.write("\n")
        return path

    def _parse_output(self, out_dir: str) -> str | None:
        """Find and parse the infer_result JSONL."""
        out_path = Path(out_dir)
        for jf in out_path.rglob("infer_result*.jsonl"):
            try:
                with open(jf) as f:
                    for line in f:
                        data = json.loads(line.strip())
                        resp = data.get("response", "").strip()
                        if resp:
                            return resp
            except Exception:
                continue
        return None

    def status(self) -> dict[str, Any]:
        """Return engine status for diagnostics."""
        return {
            "available": self._available,
            "adapter_dir": self._adapter_dir,
            "model_id": _MODEL_ID,
            "base_model": _BASE_MODEL,
        }
