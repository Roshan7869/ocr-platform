"""Run the experimental PaddleOCR -> validation -> Laya -> review flow."""

import argparse
import json
import os
from pathlib import Path

from ocr_platform.benchmark.cli import positive
from ocr_platform.benchmark.dataset import digest, load_dataset
from ocr_platform.benchmark.runner import run as recognize

from .adapters import LayaClassifier, PaddleRecognizer
from .pipeline import classify_run, load_rules
from .review import correct


class DemoRecognizer:
    """Explicitly simulated outputs for wiring checks, never real OCR accuracy."""

    api = False

    def __init__(self):
        self.identity = {"engine": "SIMULATED_DEMO_OCR", "not_accuracy_evidence": True}
        self.index = 0

    def recognize(self, image: bytes) -> dict:
        text = ["tailor", "999", '"', ""][self.index]
        self.index += 1
        return {"text": text, "confidence": 0.95, "attempts": 1, "billable_units": 0}


class DemoClassifier:
    identity = None

    def __init__(self):
        self.identity = {"engine": "SIMULATED_DEMO_CLASSIFIER", "not_accuracy_evidence": True}

    def classify(self, text: str, field_id: str, rule: dict) -> dict:
        return {"category": "SELF_EMPLOYED", "confidence": 0.9}


def demo(output: Path, config: dict) -> dict:
    from PIL import Image, ImageDraw

    source = output / "demo-input"
    source.mkdir(parents=True, exist_ok=True)
    dataset = {"schema_version": 1, "source_root": str(source.resolve()), "documents": []}
    for i, (field_id, text) in enumerate(
        [
            ("member.row1.occupation", "tailor"),
            ("member.row1.age", "999"),
            ("member.row1.religion", '"'),
            ("member.row1.name", ""),
        ]
    ):
        page = Image.new("RGB", (600, 180), "white")
        ImageDraw.Draw(page).text((40, 60), text, fill="black")
        pdf = source / f"synthetic-{i}.pdf"
        page.save(pdf, format="PDF", resolution=100)
        dataset["documents"].append(
            {
                "id": f"demo-{i}",
                "path": pdf.name,
                "sha256": digest(pdf.read_bytes()),
                "page_count": 1,
                "classification": "synthetic",
                "split": "development",
                "fields": [
                    {
                        "id": field_id,
                        "page": 0,
                        "bbox": [0, 0, 1, 1],
                        "kind": "print",
                        "state": "present" if text else "absent",
                        "expected": text,
                        "labeler": "synthetic-demo-generator",
                    }
                ],
            }
        )
        page.close()
    dataset_path = source / "dataset.json"
    dataset_path.write_text(json.dumps(dataset), encoding="utf-8")
    result = recognize(dataset_path, output / "ocr", DemoRecognizer())
    summary = classify_run(
        Path(result["report_path"]).parent, output / "flow", config, DemoClassifier()
    )
    summary["demo_only"] = True
    return summary


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    execute = commands.add_parser("run", help="Recognize annotated regions, validate, and classify")
    execute.add_argument("--dataset", type=Path, required=True)
    execute.add_argument("--rules", type=Path, default=Path("configs/flow_rules_v1.json"))
    execute.add_argument("--paddle-model-dir", type=Path, required=True)
    execute.add_argument("--paddle-model-name", default="devanagari_PP-OCRv5_mobile_rec")
    execute.add_argument("--laya-model-dir", type=Path, required=True)
    execute.add_argument("--paddle-device", default="cpu")
    execute.add_argument("--laya-device", default="cpu")
    execute.add_argument("--dpi", type=positive, default=200)
    execute.add_argument("--max-fields", type=positive, default=500)
    execute.add_argument("--out", type=Path, default=Path("runs/flow"))
    trial = commands.add_parser("demo", help="Simulated wiring smoke test; does not load models")
    trial.add_argument("--out", type=Path, default=Path("runs/flow-demo"))
    trial.add_argument("--rules", type=Path, default=Path("configs/flow_rules_v1.json"))
    review = commands.add_parser("review", help="Append a verified human correction")
    review.add_argument("--run", type=Path, required=True)
    review.add_argument("--decision-id", required=True)
    review.add_argument("--value", required=True)
    review.add_argument("--reviewer", required=True)
    review.add_argument("--category")
    review.add_argument("--state", choices=["present", "absent", "unreadable"], default="present")
    return root


def main() -> int:
    arguments = parser().parse_args()
    try:
        if arguments.command == "demo":
            result = demo(arguments.out, load_rules(arguments.rules))
        elif arguments.command == "review":
            result = correct(
                arguments.run,
                arguments.decision_id,
                arguments.value,
                arguments.reviewer,
                arguments.category,
                arguments.state,
            )
        else:
            if not 72 <= arguments.dpi <= 300:
                raise ValueError("Flow DPI must be between 72 and 300")
            config = load_rules(arguments.rules)
            dataset = load_dataset(arguments.dataset, require_labels=False, allow_unlabeled=True)
            total = sum(f["kind"] != "mark" for d in dataset["documents"] for f in d["fields"])
            if not 0 < total <= arguments.max_fields:
                raise ValueError("Add answer boxes before running, or raise --max-fields")
            # Download/setup is separate; loading must use local artifacts only.
            os.environ["HF_HUB_OFFLINE"] = "1"
            os.environ["TRANSFORMERS_OFFLINE"] = "1"
            recognizer = PaddleRecognizer(
                arguments.paddle_model_dir, arguments.paddle_model_name, arguments.paddle_device
            )
            classifier = LayaClassifier(arguments.laya_model_dir, arguments.laya_device)
            ocr_result = recognize(
                arguments.dataset,
                arguments.out / "ocr",
                recognizer,
                dpi=arguments.dpi,
                limit=arguments.max_fields,
                require_labels=False,
            )
            result = classify_run(
                Path(ocr_result["report_path"]).parent,
                arguments.out / "classified",
                config,
                classifier,
            )
        print(json.dumps(result, indent=2))
        return int(result.get("classifier_failures", 0) + result.get("ocr_failures", 0) > 0)
    except (ValueError, TypeError, OSError, KeyError, ImportError) as exc:
        print(
            json.dumps(
                {
                    "error": type(exc).__name__,
                    "message": str(exc)
                    if isinstance(exc, (ValueError, TypeError))
                    else "Input or dependency error",
                }
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
