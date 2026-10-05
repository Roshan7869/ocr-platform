"""Replaceable crop recognizers. No engine makes an acceptance decision."""

import base64
import csv
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
from pathlib import Path


class EngineError(RuntimeError):
    """Sanitized failure without payloads, credentials, or extracted values."""


class Tesseract:
    name = "tesseract"
    api = False

    def __init__(self, executable: str, languages: str, timeout: float):
        resolved = shutil.which(executable)
        if resolved is None:
            raise ValueError("Tesseract executable unavailable; install it or set --tesseract-path")
        self.executable = resolved
        self.languages = languages
        self.timeout = timeout
        version = subprocess.run(
            [resolved, "--version"], capture_output=True, text=True, timeout=timeout, check=True
        ).stdout.splitlines()[0]
        available = subprocess.run(
            [resolved, "--list-langs"], capture_output=True, text=True, timeout=timeout, check=True
        ).stdout.splitlines()
        if not set(languages.split("+")).issubset(set(available)):
            raise ValueError("Requested Tesseract languages are not installed")
        self.identity = {
            "engine": self.name,
            "version": version,
            "languages": languages,
            "psm": 7,
            "timeout_seconds": timeout,
        }

    def recognize(self, image: bytes) -> dict:
        with tempfile.TemporaryDirectory(prefix="ocr-benchmark-") as folder:
            path = Path(folder) / "crop.png"
            path.write_bytes(image)
            try:
                result = subprocess.run(
                    [
                        self.executable,
                        str(path),
                        "stdout",
                        "-l",
                        self.languages,
                        "--psm",
                        "7",
                        "tsv",
                    ],
                    capture_output=True,
                    encoding="utf-8",
                    timeout=self.timeout,
                    check=True,
                )
            except subprocess.TimeoutExpired as exc:
                raise EngineError("tesseract_timeout") from exc
            except subprocess.CalledProcessError as exc:
                raise EngineError("tesseract_failed") from exc
        words = list(csv.DictReader(io.StringIO(result.stdout), delimiter="\t"))
        words = [row for row in words if row.get("text", "").strip()]
        confidence = [float(row["conf"]) / 100 for row in words if float(row["conf"]) >= 0]
        return {
            "text": " ".join(row["text"] for row in words),
            "confidence": min(confidence) if confidence else None,
            "attempts": 1,
            "billable_units": 0,
        }


class GoogleDocumentAI:
    name = "google-document-ai"
    api = True

    def __init__(self, processor: str, timeout: float):
        match = re.fullmatch(
            r"projects/([A-Za-z0-9_-]+)/locations/([a-z0-9-]+)/processors/([A-Za-z0-9_-]+)"
            r"/processorVersions/([A-Za-z0-9_-]+)",
            processor,
        )
        if not match:
            raise ValueError(
                "Use a pinned projects/.../locations/.../processors/.../processorVersions/... resource"
            )
        token = os.environ.get("GOOGLE_ACCESS_TOKEN")
        if not token:
            raise ValueError("Set GOOGLE_ACCESS_TOKEN to a short-lived OAuth access token")
        self._token = token
        self.timeout = timeout
        location = match.group(2)
        self.url = f"https://{location}-documentai.googleapis.com/v1/{processor}:process"
        self.identity = {
            "engine": self.name,
            "processor_version": processor,
            "timeout_seconds": timeout,
        }

    def recognize(self, image: bytes) -> dict:
        body = json.dumps(
            {
                "rawDocument": {
                    "content": base64.b64encode(image).decode("ascii"),
                    "mimeType": "image/png",
                }
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            self.url,
            data=body,
            method="POST",
            headers={"Authorization": f"Bearer {self._token}", "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                result = json.load(response)
        except urllib.error.HTTPError as exc:
            # Do not retry automatically: duplicate submissions can incur duplicate charges.
            raise EngineError(f"google_http_{exc.code}") from None
        except (urllib.error.URLError, TimeoutError):
            raise EngineError("google_network_failure") from None
        except (ValueError, KeyError):
            raise EngineError("google_invalid_response") from None
        document = result.get("document", {})
        if not isinstance(document.get("text"), str):
            raise EngineError("google_missing_document_text")
        confidence = [
            token["layout"]["confidence"]
            for page in document.get("pages", [])
            for token in page.get("tokens", [])
            if "confidence" in token.get("layout", {})
        ]
        return {
            "text": document["text"],
            "confidence": min(confidence) if confidence else None,
            "attempts": 1,
            "billable_units": 1,
        }


class LocalVisionModel:
    name = "local-vlm"
    api = False
    prompt = (
        "Transcribe only the text visible in this cropped survey answer. "
        "Preserve Hindi and English, digits, punctuation, and ditto symbols. "
        "Do not translate, infer, expand abbreviations, or explain. "
        "Return an empty string if there is no text. Return only the transcription."
    )

    def __init__(self, model_id: str, revision: str, device: str, max_tokens: int):
        if not model_id or not re.fullmatch(r"[0-9a-f]{40}", revision):
            raise ValueError("Local VLM requires --model-id and a 40-character commit --revision")
        try:
            import torch
            import transformers
            from transformers import AutoModelForImageTextToText, AutoProcessor
        except ImportError as exc:
            raise ValueError(
                "Install the benchmark-local extra in a GPU-capable environment"
            ) from exc
        # Local cache only: downloading large weights is a separate explicit setup step.
        self.processor = AutoProcessor.from_pretrained(
            model_id,
            revision=revision,
            local_files_only=True,
            trust_remote_code=False,
        )
        self.model = AutoModelForImageTextToText.from_pretrained(
            model_id,
            revision=revision,
            local_files_only=True,
            trust_remote_code=False,
            device_map=device,
        ).eval()
        self.max_tokens = max_tokens
        self.identity = {
            "engine": self.name,
            "model_id": model_id,
            "revision": revision,
            "transformers": transformers.__version__,
            "torch": torch.__version__,
            "device": device,
            "prompt_sha256": hashlib.sha256(self.prompt.encode("utf-8")).hexdigest(),
            "max_tokens": max_tokens,
        }

    def recognize(self, image: bytes) -> dict:
        import torch
        from PIL import Image

        crop = Image.open(io.BytesIO(image)).convert("RGB")
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": crop},
                    {"type": "text", "text": self.prompt},
                ],
            }
        ]
        inputs = self.processor.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        ).to(self.model.device)
        with torch.inference_mode():
            output = self.model.generate(
                **inputs,
                max_new_tokens=self.max_tokens,
                do_sample=False,
            )
        generated = output[:, inputs["input_ids"].shape[1] :]
        text = self.processor.batch_decode(generated, skip_special_tokens=True)[0]
        if generated.shape[1] >= self.max_tokens:
            raise EngineError("local_generation_limit")
        return {"text": text, "confidence": None, "attempts": 1, "billable_units": 0}
