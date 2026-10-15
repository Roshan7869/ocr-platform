"""Training data gates and scoring without model downloads or optimization."""

import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from PIL import Image

from ocr_platform.benchmark.dataset import digest
from ocr_platform.benchmark.runner import canonical
from ocr_platform.flow.pipeline import load_rules
from ocr_platform.training.classifier import evaluate
from ocr_platform.training.dataset import load_training, training_rows


class TrainingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.rules = load_rules(Path("configs/flow_rules_v1.json"))
        stream = io.BytesIO()
        Image.new("RGB", (40, 20), "white").save(stream, format="PNG")
        image = stream.getvalue()
        (self.root / "crop.png").write_bytes(image)
        self.data = {
            "schema_version": 1,
            "task": "occupation_classification",
            "rules_sha256": digest(canonical(self.rules)),
            "records": [],
        }
        for split in ("train", "validation", "holdout"):
            sha = digest(split.encode())
            self.data["records"].append(
                {
                    "id": split,
                    "split": split,
                    "document_sha256": sha,
                    "field_id": "member.row1.occupation",
                    "text": "teacher",
                    "category": "SALARIED",
                    "label_source": "engineering_visual",
                    "annotator": "unit-test",
                    "evidence": {
                        "crop_path": "crop.png",
                        "crop_sha256": digest(image),
                        "document_sha256": sha,
                        "page": 1,
                        "bbox": [0, 0, 1, 1],
                    },
                }
            )

    def tearDown(self):
        self.temp.cleanup()

    def save(self, data=None):
        path = self.root / "manifest.json"
        path.write_bytes(canonical(data or self.data))
        return path

    def test_raw_scans_and_draft_labels_are_not_gold(self):
        with self.assertRaises(ValueError):
            load_training(self.save(), self.rules)
        data = copy.deepcopy(self.data)
        data["records"] = []
        with self.assertRaisesRegex(ValueError, "raw PDFs"):
            load_training(self.save(data), self.rules, pilot=True)

    def test_pilot_split_counts_and_label_sources(self):
        _, summary = load_training(self.save(), self.rules, pilot=True)
        self.assertEqual(summary["documents_by_split"], {"train": 1, "validation": 1, "holdout": 1})
        self.assertTrue(summary["pilot_only"])

    def test_document_overlap_rejected(self):
        data = copy.deepcopy(self.data)
        data["records"][1]["document_sha256"] = data["records"][0]["document_sha256"]
        with self.assertRaisesRegex(ValueError, "leakage"):
            load_training(self.save(data), self.rules, pilot=True)

    def test_predictions_cannot_be_labels_and_targets_not_inputs(self):
        data = copy.deepcopy(self.data)
        data["records"][0]["label_source"] = "model_prediction"
        with self.assertRaises(ValueError):
            load_training(self.save(data), self.rules, pilot=True)
        row = training_rows(self.data["records"][:1], self.rules)[0]
        self.assertEqual(set(row["state"]), {"field_id", "ocr_text"})
        self.assertNotIn("gold", row["state"])
        self.assertEqual(row["gold"]["category"]["probabilities"]["SALARIED"], 1.0)

    def test_codebook_changes_and_tampered_evidence_rejected(self):
        rules = copy.deepcopy(self.rules)
        rules["ocr_min_confidence"] = 0.6
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            load_training(self.save(), rules, pilot=True)
        (self.root / "crop.png").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "hash"):
            load_training(self.save(), self.rules, pilot=True)

    def test_synthetic_holdout_rejected(self):
        data = copy.deepcopy(self.data)
        data["records"][2]["label_source"] = "engineering_synthetic"
        with self.assertRaisesRegex(ValueError, "evaluation"):
            load_training(self.save(data), self.rules, pilot=True)

    def test_scoring_counts_failures_without_logging_text(self):
        backend = Mock()
        backend.classify.side_effect = [{"category": "SALARIED"}, RuntimeError("private text")]
        result = evaluate(backend, self.data["records"][:2], self.rules)
        self.assertEqual(result["accuracy"], 0.5)
        self.assertEqual(result["failures"], 1)
        self.assertNotIn("private text", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
