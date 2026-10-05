"""Local Paddle recognition and Laya classification adapters."""

import hashlib
import importlib.metadata
import io
import math
import os
from numbers import Real
from pathlib import Path

from PIL import Image

from ocr_platform.benchmark.engines import EngineError


def checkpoint_hash(path: Path) -> str:
    if not path.is_dir():
        raise ValueError("Model checkpoint directory does not exist")
    entries = []
    for file in sorted(path.rglob("*")):
        if not file.is_file():
            continue
        sha = hashlib.sha256()
        with file.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                sha.update(chunk)
        entries.append(file.relative_to(path).as_posix() + ":" + sha.hexdigest())
    if not entries:
        raise ValueError("Model checkpoint directory is empty")
    return hashlib.sha256("\n".join(entries).encode("utf-8")).hexdigest()


class PaddleRecognizer:
    """Recognition-only crop adapter; the human box is not a detected text box."""

    api = False
    name = "paddle-recognition"

    def __init__(self, model_dir: Path, model_name: str, device: str = "cpu"):
        fingerprint = checkpoint_hash(model_dir)
        os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
        try:
            from paddleocr import TextRecognition
        except ImportError as exc:
            raise ValueError("Install the flow extra before loading PaddleOCR") from exc
        self.model = TextRecognition(
            model_name=model_name, model_dir=str(model_dir.resolve()), device=device
        )
        self.identity = {
            "engine": self.name,
            "model_name": model_name,
            "checkpoint_sha256": fingerprint,
            "device": device,
            "paddleocr": importlib.metadata.version("paddleocr"),
            "paddlepaddle": importlib.metadata.version("paddlepaddle"),
            "scope": "human-region recognition only",
        }

    def recognize(self, image: bytes) -> dict:
        import numpy as np

        crop = Image.open(io.BytesIO(image)).convert("RGB")
        # Paddle's numpy image convention is BGR, not PIL RGB.
        pixels = np.asarray(crop)[:, :, ::-1].copy()
        outputs = list(self.model.predict(input=pixels, batch_size=1))
        if len(outputs) != 1:
            raise EngineError("paddle_invalid_result_count")
        result = outputs[0]
        # Paddle Result is dict-like. Support the documented .json wrapper as well.
        if not isinstance(result, dict):
            result = result.json
        result = result.get("res", result)
        text, score = result.get("rec_text"), result.get("rec_score")
        if not isinstance(text, str) or isinstance(score, bool) or not isinstance(score, Real):
            raise EngineError("paddle_invalid_result")
        score = float(score)
        if not math.isfinite(score) or not 0 <= score <= 1:
            raise EngineError("paddle_invalid_confidence")
        return {"text": text, "confidence": score, "attempts": 1, "billable_units": 0}


class LayaClassifier:
    def __init__(self, model_dir: Path, device: str = "cpu"):
        if not (model_dir / "rl_agent_config.json").is_file():
            raise ValueError("Laya directory needs rl_agent_config.json")
        if not (model_dir / "tokenizer").is_dir():
            raise ValueError("Laya directory needs its local tokenizer subdirectory")
        if not (model_dir / "encoder" / "config.json").is_file():
            raise ValueError("Laya directory needs encoder/config.json for offline model loading")
        if not (model_dir / "model.safetensors").is_file():
            raise ValueError("Laya directory needs model.safetensors")
        # No inference-time downloads; prepare a complete checkpoint separately.
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        try:
            import laya
        except ImportError as exc:
            raise ValueError("Install the flow extra before loading Laya") from exc
        # Released wheels omit laya.backends; the legacy flags select eager
        # inference without importing that optional backend-dispatch package.
        self.agent = laya.load(str(model_dir.resolve()), device=device, fast=False, compile=False)
        self.identity = {
            "engine": "laya",
            "checkpoint_sha256": checkpoint_hash(model_dir),
            "laya": importlib.metadata.version("laya"),
            "device": device,
        }

    def classify(self, text: str, field_id: str, rule: dict) -> dict:
        questions = {
            "category": {
                "type": "choice",
                "instructions": rule["instructions"],
                "criteria": rule["categories"],
            }
        }
        # Never pass verified labels or unrelated household attributes to the classifier.
        response = self.agent.predict({"field_id": field_id, "ocr_text": text}, questions)
        answer = response["answers"]["category"]
        return {
            "category": answer.get("choice"),
            "confidence": answer.get("confidence"),
            "probabilities": answer.get("probabilities"),
        }
