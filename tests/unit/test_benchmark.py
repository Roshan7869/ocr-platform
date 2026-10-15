"""Benchmark correctness, integrity, billing, and resume regression tests."""

import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pypdf import PdfWriter

from ocr_platform.benchmark.cli import compare
from ocr_platform.benchmark.dataset import digest, validate_dataset, verified_source
from ocr_platform.benchmark.engines import EngineError, GoogleDocumentAI, Tesseract
from ocr_platform.benchmark.metrics import make_report, normalize, summarize
from ocr_platform.benchmark.prepare import prepare, select_sources
from ocr_platform.benchmark.runner import run


class FakeEngine:
    api = False

    def __init__(self, fail=False):
        self.identity = {"engine": "test-only"}
        self.calls = 0
        self.fail = fail

    def recognize(self, image):
        self.calls += 1
        if self.fail:
            raise EngineError("test_failure")
        return {"text": "42", "confidence": None, "attempts": 1, "billable_units": 0}


def metric_row(expected="42", text="42", status="ok", **values):
    return {
        "expected": expected,
        "text": text,
        "status": status,
        "scorable": True,
        "seconds": 2.0,
        "attempts": 1,
        "billable_units": 0,
        "kind": "handwriting",
        "split": "holdout",
        **values,
    }


class BenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "source.pdf"
        writer = PdfWriter()
        writer.add_blank_page(width=200, height=200)
        with self.source.open("wb") as stream:
            writer.write(stream)
        self.dataset = {
            "schema_version": 1,
            "source_root": str(self.root),
            "documents": [
                {
                    "id": "doc1",
                    "path": "source.pdf",
                    "sha256": digest(self.source.read_bytes()),
                    "page_count": 1,
                    "classification": "synthetic",
                    "split": "holdout",
                    "fields": [
                        {
                            "id": "document.ward",
                            "page": 0,
                            "bbox": [0.1, 0.1, 0.3, 0.3],
                            "kind": "handwriting",
                            "state": "present",
                            "expected": "42",
                            "labeler": "tester",
                        }
                    ],
                }
            ],
        }
        self.dataset_path = self.root / "dataset.json"
        self.save_dataset()

    def tearDown(self):
        self.temp.cleanup()

    def save_dataset(self):
        self.dataset_path.write_text(json.dumps(self.dataset), encoding="utf-8")

    def test_failures_count_against_accuracy(self):
        stats = summarize([metric_row(), metric_row(status="failed")])
        self.assertEqual(stats["exact_match"], 0.5)
        self.assertEqual(stats["observed_correction_or_failure_rate"], 0.5)
        self.assertEqual(stats["failed_fields"], 1)

    def test_blank_false_positive_and_unicode(self):
        stats = summarize(
            [metric_row(expected="", text="invented"), metric_row(expected="", text="")]
        )
        self.assertEqual(stats["blank_false_positive_rate"], 0.5)
        self.assertEqual(stats["exact_match"], 0.5)
        self.assertEqual(normalize("  क  42\n"), "क 42")
        self.assertNotEqual(normalize("M"), normalize("m"))

    def test_no_labels_cannot_produce_perfect_score(self):
        self.dataset["documents"][0]["fields"] = []
        with self.assertRaises(ValueError):
            validate_dataset(self.dataset)
        self.assertIsNone(summarize([])["exact_match"])

    def test_unreadable_labels_excluded(self):
        stats = summarize([metric_row(expected=None, scorable=False)])
        self.assertEqual(stats["labeled_fields"], 0)
        self.assertIsNone(stats["exact_match"])

    def test_path_traversal_hash_and_duplicate_field_rejected(self):
        wrong = copy.deepcopy(self.dataset)
        wrong["documents"][0]["path"] = "../outside.pdf"
        with self.assertRaises(ValueError):
            validate_dataset(wrong)
        wrong = copy.deepcopy(self.dataset)
        wrong["documents"][0]["fields"] *= 2
        with self.assertRaises(ValueError):
            validate_dataset(wrong)
        self.source.write_bytes(b"changed")
        with self.assertRaises(ValueError):
            verified_source(self.dataset, self.dataset["documents"][0])

    def test_bad_boxes_and_labels_rejected(self):
        for box in ([0, 0, float("nan"), 1], [0.8, 0, 0.2, 1], [0, 0, 2, 1]):
            wrong = copy.deepcopy(self.dataset)
            wrong["documents"][0]["fields"][0]["bbox"] = box
            with self.assertRaises(ValueError):
                validate_dataset(wrong)
        wrong = copy.deepcopy(self.dataset)
        wrong["documents"][0]["fields"][0]["labeler"] = ""
        with self.assertRaises(ValueError):
            validate_dataset(wrong)

    def test_resume_does_not_call_engine_again_and_records_evidence(self):
        engine = FakeEngine()
        first = run(self.dataset_path, self.root / "results", engine)
        run(self.dataset_path, self.root / "results", engine)
        self.assertEqual(engine.calls, 1)
        self.assertEqual(first["overall"]["exact_match"], 1)
        row = json.loads((Path(first["report_path"]).parent / "predictions.jsonl").read_text())
        crop = Path(first["report_path"]).parent / row["crop_path"]
        self.assertEqual(digest(crop.read_bytes()), row["crop_sha256"])
        self.assertEqual(row["document_sha256"], self.dataset["documents"][0]["sha256"])

    def test_retry_is_explicit_and_accumulates_attempts(self):
        engine = FakeEngine(fail=True)
        run(self.dataset_path, self.root / "results", engine)
        run(self.dataset_path, self.root / "results", engine)
        self.assertEqual(engine.calls, 1)
        engine.fail = False
        result = run(self.dataset_path, self.root / "results", engine, retry_failed=True)
        self.assertEqual(engine.calls, 2)
        self.assertEqual(result["overall"]["attempts"], 2)
        self.assertEqual(result["overall"]["exact_match"], 1)

    def test_concurrent_runs_and_changed_evidence_rejected(self):
        output = self.root / "results"
        output.mkdir()
        lock = output / ".benchmark.lock"
        lock.write_text("other-process")
        engine = FakeEngine()
        with self.assertRaises(ValueError):
            run(self.dataset_path, output, engine)
        lock.unlink()
        first = run(self.dataset_path, output, engine)
        folder = Path(first["report_path"]).parent
        next((folder / "crops").glob("*.png")).write_bytes(b"tampered")
        with self.assertRaises(ValueError):
            run(self.dataset_path, output, engine)
        self.assertEqual(engine.calls, 1)

    def test_api_gates_before_first_call(self):
        engine = FakeEngine()
        engine.api = True
        with self.assertRaises(ValueError):
            run(self.dataset_path, self.root / "results", engine)
        self.dataset["documents"][0]["classification"] = "unclassified"
        self.save_dataset()
        with self.assertRaises(ValueError):
            run(self.dataset_path, self.root / "results", engine, allow_api_upload=True)
        self.assertEqual(engine.calls, 0)

    def test_failed_api_requests_count_billable_units(self):
        engine = FakeEngine(fail=True)
        engine.api = True
        result = run(self.dataset_path, self.root / "results", engine, allow_api_upload=True)
        self.assertEqual(result["overall"]["billable_input_units"], 1)

    def test_scale_projection_uses_fields_not_document_count(self):
        report = make_report(
            [metric_row(billable_units=1)],
            corpus_documents=100_000,
            fields_per_document=100,
            unit_price=2,
            hourly_compute_cost=None,
            review_seconds_per_field=30,
            review_hourly_cost=None,
            currency="INR",
        )
        self.assertEqual(report["projection"]["api_cost"], 20_000)
        self.assertAlmostEqual(
            report["projection"]["serial_inference_hours"], 10_000_000 * 2 / 3600
        )
        self.assertIsNone(report["projection"]["compute_cost"])

    def test_scale_includes_failed_request_time_and_units(self):
        report = make_report(
            [
                metric_row(billable_units=1),
                metric_row(status="failed", seconds=60, billable_units=2, attempts=2),
            ],
            corpus_documents=1000,
            fields_per_document=1,
            unit_price=10,
            hourly_compute_cost=None,
            review_seconds_per_field=30,
            review_hourly_cost=None,
            currency="INR",
        )
        self.assertEqual(report["projection"]["api_cost"], 15)
        self.assertAlmostEqual(report["projection"]["serial_inference_hours"], 1000 * 31 / 3600)

    def test_compare_rejects_different_sample(self):
        engine = FakeEngine()
        result = run(self.dataset_path, self.root / "results", engine)
        path = Path(result["report_path"])
        altered = json.loads(path.read_text())
        altered["identity"]["dataset_sha256"] = "different"
        other = self.root / "other.json"
        other.write_text(json.dumps(altered))
        with self.assertRaises(ValueError):
            compare([path, other])

    def test_sampling_is_reproducible_balanced_and_no_overwrite(self):
        source_root = self.root / "corpus"
        for batch in ("batch-a", "batch-b"):
            folder = source_root / batch
            folder.mkdir(parents=True)
            for i in range(6):
                (folder / f"{i}.pdf").write_bytes(self.source.read_bytes())
        selected = select_sources(source_root, 6, 42)
        self.assertEqual(selected, select_sources(source_root, 6, 42))
        self.assertEqual(sum(p.parent.name == "batch-a" for p in selected), 3)
        prepared = prepare(source_root, self.root / "sample", 6, 42)
        html = Path(prepared["labeler"]).read_text(encoding="utf-8")
        self.assertNotIn("/*BENCHMARK_DATA*/", html)
        self.assertIn("data:image/png;base64,", html)
        with self.assertRaises(ValueError):
            prepare(source_root, self.root / "sample", 6, 42)

    def test_google_request_and_sanitized_error(self):
        processor = "projects/p/locations/us/processors/p1/processorVersions/v1"
        with patch.dict("os.environ", {"GOOGLE_ACCESS_TOKEN": "test-secret"}):
            engine = GoogleDocumentAI(processor, 10)
        response = io.BytesIO(json.dumps({"document": {"text": "42"}}).encode())
        with patch("urllib.request.urlopen", return_value=response) as request:
            result = engine.recognize(b"image")
            sent = request.call_args.args[0]
            self.assertEqual(json.loads(sent.data)["rawDocument"]["mimeType"], "image/png")
            self.assertEqual(result["text"], "42")
        import urllib.error

        error = urllib.error.HTTPError(engine.url, 429, "PII test-secret", None, None)
        with (
            patch("urllib.request.urlopen", side_effect=error),
            self.assertRaisesRegex(EngineError, "^google_http_429$"),
        ):
            engine.recognize(b"image")

    def test_tesseract_preserves_unicode_and_unscaled_confidence(self):
        with patch("shutil.which", return_value="tesseract"), patch("subprocess.run") as command:
            command.return_value.stdout = "tesseract 5.0"
            command.side_effect = [
                type("Result", (), {"stdout": "tesseract 5.0"})(),
                type("Result", (), {"stdout": "List:\nhin\neng\n"})(),
                type("Result", (), {"stdout": "text\tconf\nक\t80\n42\t90\n"})(),
            ]
            result = Tesseract("tesseract", "hin+eng", 10).recognize(b"image")
            self.assertEqual(result["text"], "क 42")
            self.assertEqual(result["confidence"], 0.8)


if __name__ == "__main__":
    unittest.main()
