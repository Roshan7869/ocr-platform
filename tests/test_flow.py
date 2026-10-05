"""Flow integration and review invariants, using simulated engines."""

import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from ocr_platform.benchmark.dataset import load_dataset
from ocr_platform.flow.adapters import LayaClassifier, PaddleRecognizer
from ocr_platform.flow.cli import DemoClassifier, DemoRecognizer, demo, recognize
from ocr_platform.flow.pipeline import classify_run, decide, load_rules, validate_text
from ocr_platform.flow.review import correct


class FlowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.config = load_rules(Path("configs/flow_rules_v1.json"))
        self.row = {
            "field_id": "member.row1.occupation",
            "text": "दर्जी",
            "status": "ok",
            "confidence": 0.95,
        }

    def tearDown(self):
        self.temp.cleanup()

    def test_valid_classification_is_only_a_review_suggestion(self):
        result = decide(self.row, self.config, DemoClassifier())
        self.assertEqual(result["raw_text"], "दर्जी")
        self.assertEqual(result["classification"]["category"], "SELF_EMPLOYED")
        self.assertEqual(result["disposition"], "review")
        self.assertIsNone(result["final_value"])
        self.assertIsNone(result["final_category"])

    def test_numeric_codes_and_ditto_fail_closed(self):
        age = {"type": "integer", "min": 0, "max": 130}
        self.assertEqual(validate_text("३०", age)["normalized"], 30)
        self.assertFalse(validate_text("999", age)["ok"])
        self.assertFalse(validate_text("3O", age)["ok"])
        code = {"type": "code", "aliases": {"M": "male"}}
        self.assertFalse(validate_text("m", code)["ok"])
        self.assertIn("DITTO_UNRESOLVED", validate_text('"', code)["reasons"])

    def test_uncertain_ocr_never_reaches_classifier(self):
        classifier = DemoClassifier()
        with patch.object(classifier, "classify") as backend:
            for confidence in (0.1, None, float("nan")):
                result = decide({**self.row, "confidence": confidence}, self.config, classifier)
                self.assertIsNone(result["classification"])
            backend.assert_not_called()

    def test_docs_reason_codes_and_value_state(self):
        registry = Path("docs/reason-codes.md").read_text(encoding="utf-8")
        for row in [
            {**self.row, "kind": "handwriting", "confidence": 0.1},
            {**self.row, "field_id": "member.row1.gender", "text": "X"},
            {**self.row, "field_id": "member.row1.age", "text": "999"},
            {**self.row, "text": '"'},
        ]:
            result = decide(row, self.config, DemoClassifier())
            for reason in result["reason_codes"]:
                self.assertIn(f"`{reason}`", registry)
            if not result["validation"]["ok"]:
                self.assertEqual(result["value_state"], "unknown")
        result = decide(
            {**self.row, "kind": "handwriting", "confidence": 0.1}, self.config, DemoClassifier()
        )
        self.assertIn("HANDWRITING_SUSPECTED", result["reason_codes"])
        self.assertIn("OCR_CONFIDENCE_LOW", result["reason_codes"])

    def test_unknown_low_confidence_and_failure_routes(self):
        classifier = DemoClassifier()
        for response, reason in [
            ({"category": "UNKNOWN", "confidence": 0.9}, "UNKNOWN_CATEGORY"),
            ({"category": "OTHER", "confidence": 0.2}, "LOW_CLASSIFICATION_CONFIDENCE"),
            ({"category": "INVENTED", "confidence": 0.9}, "INVALID_CLASSIFIER_RESPONSE"),
            ({"category": "OTHER", "confidence": float("nan")}, "INVALID_CLASSIFIER_RESPONSE"),
        ]:
            with patch.object(classifier, "classify", return_value=response):
                self.assertIn(reason, decide(self.row, self.config, classifier)["reason_codes"])
        with patch.object(classifier, "classify", side_effect=RuntimeError("PII secret")):
            result = decide(self.row, self.config, classifier)
            self.assertIn("CLASSIFIER_FAILED", result["reason_codes"])
            self.assertNotIn("PII", json.dumps(result))

    def test_labels_not_sent_to_classifier(self):
        classifier = DemoClassifier()
        with patch.object(classifier, "classify", wraps=classifier.classify) as backend:
            decide({**self.row, "expected": "GROUND_TRUTH_DO_NOT_LEAK"}, self.config, classifier)
            self.assertNotIn("GROUND_TRUTH", repr(backend.call_args))

    def test_demo_complete_flow_human_revision_and_resume(self):
        summary = demo(self.root, self.config)
        self.assertTrue(summary["demo_only"])
        self.assertEqual(summary["fields"], 4)
        self.assertEqual(summary["accepted"], 0)
        folder = Path(summary["output"])
        rows = [json.loads(line) for line in (folder / "decisions.jsonl").read_text().splitlines()]
        age = next(d for d in rows if d["record"]["field_id"].endswith("age"))
        self.assertIn("INTEGER_OUT_OF_RANGE", age["record"]["reason_codes"])
        before = (folder / "decisions.jsonl").read_bytes()
        revision = correct(folder, age["decision_id"], "30", "tester")
        self.assertEqual(revision["disposition"], "accepted")
        correct(folder, age["decision_id"], "31", "tester")
        history = [
            json.loads(line) for line in (folder / "human_revisions.jsonl").read_text().splitlines()
        ]
        self.assertEqual(history[1]["record"]["previous_revision_id"], history[0]["revision_id"])
        self.assertEqual(history[0]["record"]["final_value"], 30)
        effective = json.loads((folder / "result.json").read_text())
        corrected = next(d for d in effective["fields"] if d["decision_id"] == age["decision_id"])
        self.assertEqual(corrected["human_revision"]["record"]["final_value"], 31)
        self.assertEqual(json.loads((folder / "summary.json").read_text())["accepted"], 1)
        self.assertEqual((folder / "decisions.jsonl").read_bytes(), before)
        ocr = next((self.root / "ocr").iterdir())
        classifier = DemoClassifier()
        with patch.object(classifier, "classify") as backend:
            classify_run(ocr, self.root / "flow", self.config, classifier)
            backend.assert_not_called()
        self.assertEqual(json.loads((folder / "summary.json").read_text())["review"], 3)

    def test_human_category_requires_explicit_known_choice(self):
        summary = demo(self.root, self.config)
        folder = Path(summary["output"])
        first = json.loads((folder / "decisions.jsonl").read_text().splitlines()[0])
        with self.assertRaises(ValueError):
            correct(folder, first["decision_id"], "tailor", "tester")
        with self.assertRaises(ValueError):
            correct(folder, first["decision_id"], "tailor", "tester", "UNKNOWN")
        result = correct(folder, first["decision_id"], "tailor", "tester", "SELF_EMPLOYED")
        self.assertEqual(result["disposition"], "accepted")

    def test_human_absence_and_unreadable_keep_null_values(self):
        summary = demo(self.root, self.config)
        folder = Path(summary["output"])
        rows = [json.loads(line) for line in (folder / "decisions.jsonl").read_text().splitlines()]
        name = next(d for d in rows if d["record"]["field_id"].endswith("name"))
        correct(folder, name["decision_id"], "", "tester", state="absent")
        result = correct(folder, name["decision_id"], "", "tester", state="unreadable")
        self.assertEqual(result["disposition"], "review")
        revisions = [
            json.loads(line) for line in (folder / "human_revisions.jsonl").read_text().splitlines()
        ]
        self.assertTrue(all(r["record"]["final_value"] is None for r in revisions))

    def test_tampered_crop_blocks_classification_and_review(self):
        summary = demo(self.root, self.config)
        folder = Path(summary["output"])
        first = json.loads((folder / "decisions.jsonl").read_text().splitlines()[0])
        (folder / first["record"]["evidence"]["crop_path"]).write_bytes(b"tampered")
        with self.assertRaises(ValueError):
            correct(folder, first["decision_id"], "tailor", "tester", "SELF_EMPLOYED")

    def test_inference_regions_are_not_ground_truth(self):
        demo(self.root, self.config)
        path = self.root / "demo-input" / "dataset.json"
        data = json.loads(path.read_text())
        for document in data["documents"]:
            document["fields"][0]["expected"] = None
        path.write_text(json.dumps(data))
        load_dataset(path, require_labels=False, allow_unlabeled=True)
        with self.assertRaises(ValueError):
            load_dataset(path)
        result = recognize(
            path, self.root / "unlabeled-ocr", DemoRecognizer(), require_labels=False
        )
        report = json.loads(Path(result["report_path"]).read_text(encoding="utf-8"))
        self.assertEqual(report["coverage"]["documents_without_scorable_text"], 4)
        self.assertEqual(report["overall"]["completed_inference_fields"], 4)
        self.assertEqual(report["overall"]["labeled_fields"], 0)
        self.assertIsNone(report["overall"]["exact_match"])

    def test_rule_config_rejects_unsafe_threshold_and_unknown_keys(self):
        for key, value in [("ocr_min_confidence", float("nan")), ("auto_accept", True)]:
            config = copy.deepcopy(self.config)
            config[key] = value
            path = self.root / "invalid.json"
            path.write_text(json.dumps(config))
            with self.assertRaises(ValueError):
                load_rules(path)

    def test_paddle_adapts_crop_and_result_without_detected_box_claim(self):
        import numpy as np

        adapter = PaddleRecognizer.__new__(PaddleRecognizer)
        adapter.model = type(
            "Model",
            (),
            {
                "predict": lambda self, **kw: iter(
                    [
                        {"res": {"rec_text": "३०", "rec_score": np.float32(0.9)}},
                    ]
                )
            },
        )()
        image = Image.new("RGB", (50, 20), "white")
        stream = io.BytesIO()
        image.save(stream, format="PNG")
        result = adapter.recognize(stream.getvalue())
        self.assertEqual(result["text"], "३०")
        self.assertNotIn("detected_box", result)

    def test_laya_adapter_uses_only_text_and_rule_options(self):
        adapter = LayaClassifier.__new__(LayaClassifier)
        from unittest.mock import Mock

        adapter.agent = Mock()
        adapter.agent.predict.return_value = {
            "answers": {
                "category": {
                    "choice": "SELF_EMPLOYED",
                    "confidence": 0.9,
                }
            }
        }
        rule = next(r for r in self.config["rules"] if r["type"] == "category")
        result = adapter.classify("दर्जी", "member.row1.occupation", rule)
        state, questions = adapter.agent.predict.call_args.args
        self.assertEqual(state, {"field_id": "member.row1.occupation", "ocr_text": "दर्जी"})
        self.assertEqual(questions["category"]["type"], "choice")
        self.assertEqual(result["category"], "SELF_EMPLOYED")

    def test_laya_loader_uses_offline_checkpoint_and_legacy_eager_flags(self):
        import sys
        from unittest.mock import Mock

        checkpoint = self.root / "laya"
        (checkpoint / "tokenizer").mkdir(parents=True)
        (checkpoint / "encoder").mkdir()
        (checkpoint / "rl_agent_config.json").write_text("{}")
        (checkpoint / "model.safetensors").write_bytes(b"mock-weights")
        with self.assertRaisesRegex(ValueError, "encoder/config.json"):
            LayaClassifier(checkpoint)
        (checkpoint / "encoder/config.json").write_text("{}")
        module = Mock()
        with (
            patch.dict(sys.modules, {"laya": module}),
            patch("ocr_platform.flow.adapters.importlib.metadata.version", return_value="0.3.26"),
        ):
            LayaClassifier(checkpoint)
        module.load.assert_called_once_with(
            str(checkpoint.resolve()), device="cpu", fast=False, compile=False
        )


if __name__ == "__main__":
    unittest.main()
