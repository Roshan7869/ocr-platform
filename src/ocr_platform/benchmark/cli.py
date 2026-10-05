"""Command line entry point for preparing, running, and comparing benchmarks."""

import argparse
import json
import math
import time
from pathlib import Path

from .dataset import load_dataset
from .engines import GoogleDocumentAI, LocalVisionModel, Tesseract
from .prepare import prepare
from .runner import run


def positive(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("Must be positive")
    return number


def nonnegative(value: str) -> float:
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise argparse.ArgumentTypeError("Must be finite and nonnegative")
    return number


def compare(paths: list[Path]) -> dict:
    reports = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    if len(reports) < 2:
        raise ValueError("Compare at least two reports")
    for key in ("dataset_sha256", "dpi", "pdfium", "python", "split", "runner_version"):
        if len({report["identity"][key] for report in reports}) != 1:
            raise ValueError(f"Reports do not use the same {key}")
    if any(
        report["identity"]["rendering_packages"] != reports[0]["identity"]["rendering_packages"]
        for report in reports
    ):
        raise ValueError("Reports do not use the same rendering packages")
    # Engine-specific prices naturally differ; require the same corpus/review assumptions.
    for key in (
        "corpus_documents",
        "text_fields_per_document",
        "currency",
        "review_seconds_per_field",
        "review_hourly_cost",
    ):
        if len({report["scale_assumptions"][key] for report in reports}) != 1:
            raise ValueError(f"Reports do not use the same {key}")
    return {
        "scope": reports[0]["scope"],
        "engines": [
            {
                "engine": report["identity"]["engine"],
                "overall": report["overall"],
                "by_split_and_kind": report["by_split_and_kind"],
                "projection": report["projection"],
            }
            for report in reports
        ],
        "decision": "No automatic winner: assess holdout accuracy, failures, cost, and correction effort.",
    }


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    sample = commands.add_parser("prepare", help="Create a sample and offline labeling page")
    sample.add_argument("--source", type=Path, required=True)
    sample.add_argument("--out", type=Path, required=True)
    sample.add_argument("--count", type=positive, default=24)
    sample.add_argument("--seed", type=int, default=42)
    validate = commands.add_parser("validate", help="Validate human labels and source hashes")
    validate.add_argument("dataset", type=Path)
    execute = commands.add_parser("run", help="Evaluate one engine on verified crop labels")
    execute.add_argument("--dataset", type=Path, required=True)
    execute.add_argument("--out", type=Path, default=Path("runs/benchmark/results"))
    execute.add_argument(
        "--engine", choices=["tesseract", "google-document-ai", "local-vlm"], required=True
    )
    execute.add_argument("--dpi", type=positive, default=200)
    execute.add_argument("--split", choices=["all", "development", "holdout"], default="all")
    execute.add_argument("--max-fields", type=positive, default=500)
    execute.add_argument("--timeout", type=positive, default=60)
    execute.add_argument("--retry-failed", action="store_true")
    execute.add_argument("--allow-api-upload", action="store_true")
    execute.add_argument("--tesseract-path", default="tesseract")
    execute.add_argument("--languages", default="hin+eng")
    execute.add_argument("--processor-version", default="")
    execute.add_argument("--model-id", default="")
    execute.add_argument("--revision", default="")
    execute.add_argument("--device", default="auto")
    execute.add_argument("--max-tokens", type=positive, default=128)
    execute.add_argument("--corpus-documents", type=positive, default=100_000)
    execute.add_argument("--fields-per-document", type=positive, default=100)
    execute.add_argument("--price-per-1000-input-units", type=nonnegative)
    execute.add_argument("--hourly-compute-cost", type=nonnegative)
    execute.add_argument("--review-seconds-per-field", type=nonnegative, default=30)
    execute.add_argument("--review-hourly-cost", type=nonnegative)
    execute.add_argument("--currency", default="INR")
    comparison = commands.add_parser("compare", help="Compare reports from the same sample")
    comparison.add_argument("reports", type=Path, nargs="+")
    return root


def main() -> int:
    arguments = parser().parse_args()
    try:
        if arguments.command == "prepare":
            result = prepare(arguments.source, arguments.out, arguments.count, arguments.seed)
        elif arguments.command == "validate":
            from .dataset import verified_source

            dataset = load_dataset(arguments.dataset)
            for document in dataset["documents"]:
                verified_source(dataset, document)
            result = {
                "valid": True,
                "documents": len(dataset["documents"]),
                "fields": sum(len(d["fields"]) for d in dataset["documents"]),
            }
        elif arguments.command == "compare":
            result = compare(arguments.reports)
        else:
            if not 72 <= arguments.dpi <= 300:
                raise ValueError("Benchmark DPI must be between 72 and 300")
            # Fail before expensive model initialization when no labels exist.
            load_dataset(arguments.dataset)
            start = time.perf_counter()
            if arguments.engine == "tesseract":
                engine = Tesseract(arguments.tesseract_path, arguments.languages, arguments.timeout)
            elif arguments.engine == "google-document-ai":
                if not arguments.allow_api_upload:
                    raise ValueError("API uploads require explicit --allow-api-upload")
                engine = GoogleDocumentAI(arguments.processor_version, arguments.timeout)
            else:
                engine = LocalVisionModel(
                    arguments.model_id, arguments.revision, arguments.device, arguments.max_tokens
                )
            setup_seconds = time.perf_counter() - start
            result = run(
                arguments.dataset,
                arguments.out,
                engine,
                dpi=arguments.dpi,
                split=arguments.split,
                limit=arguments.max_fields,
                allow_api_upload=arguments.allow_api_upload,
                retry_failed=arguments.retry_failed,
                corpus_documents=arguments.corpus_documents,
                fields_per_document=arguments.fields_per_document,
                unit_price=arguments.price_per_1000_input_units,
                hourly_compute_cost=arguments.hourly_compute_cost,
                review_seconds_per_field=arguments.review_seconds_per_field,
                review_hourly_cost=arguments.review_hourly_cost,
                currency=arguments.currency,
            )
            report_path = Path(result["report_path"])
            report = json.loads(report_path.read_text(encoding="utf-8"))
            report["engine_setup_seconds_this_invocation"] = setup_seconds
            report_path.write_text(
                json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        # Console summaries exclude source paths containing personal names and extracted values.
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return int(arguments.command == "run" and result["overall"]["failed_fields"] > 0)
    except (ValueError, TypeError, OSError, KeyError, ImportError) as exc:
        # Avoid printing file contents or API/model exception payloads.
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
