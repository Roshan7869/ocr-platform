"""Validate draft classifier supervision and document-separated splits."""

import json
from collections import Counter
from pathlib import Path

from ocr_platform.benchmark.dataset import digest
from ocr_platform.benchmark.runner import canonical
from ocr_platform.flow.pipeline import checked_crop, field_rule


def load_training(path: Path, rules: dict, *, pilot: bool = False) -> tuple[dict, dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or data.get("task") != "occupation_classification":
        raise ValueError("Unsupported training manifest")
    if data.get("rules_sha256") != digest(canonical(rules)):
        raise ValueError("Training targets do not match the rule/codebook fingerprint")
    if rules["draft"] and not pilot:
        raise ValueError("Draft codebooks require explicit pilot mode")
    if not isinstance(data.get("records"), list) or not data["records"]:
        raise ValueError("No supervised examples; raw PDFs are not training labels")
    ids, splits, counts, sources, targets = set(), {}, Counter(), Counter(), Counter()
    for row in data["records"]:
        if not isinstance(row, dict):
            raise TypeError("Training records must be objects")
        key = row.get("id")
        if not isinstance(key, str) or not key or key in ids:
            raise ValueError("Training record IDs must be unique")
        ids.add(key)
        split = row.get("split")
        if split not in {"train", "validation", "holdout"}:
            raise ValueError("Unknown training split")
        source = row.get("document_sha256", "")
        if len(source) != 64 or any(c not in "0123456789abcdef" for c in source):
            raise ValueError("Each record needs a document/group hash")
        if source in splits and splits[source] != split:
            raise ValueError("Document leakage across training/validation/holdout")
        splits[source] = split
        label_source = row.get("label_source")
        if label_source not in {"human_verified", "engineering_visual", "engineering_synthetic"}:
            raise ValueError("Model predictions and unlabeled crops cannot be training targets")
        if label_source != "human_verified" and not pilot:
            raise ValueError("Draft supervision requires pilot mode")
        if label_source == "engineering_synthetic" and split != "train":
            raise ValueError("Synthetic prototypes cannot be evaluation cases")
        if not isinstance(row.get("annotator"), str) or not row["annotator"].strip():
            raise ValueError("Training labels need an identified annotator")
        text = row.get("text")
        if not isinstance(text, str) or not text.strip() or len(text) > 1024:
            raise ValueError("Training requires a literal occupation transcription")
        rule = field_rule(row["field_id"], rules)
        if (
            rule is None
            or rule["type"] != "category"
            or row.get("category") not in rule["categories"]
        ):
            raise ValueError("Training category is outside the versioned codebook")
        if label_source != "engineering_synthetic":
            evidence = row.get("evidence")
            if not isinstance(evidence, dict) or evidence.get("document_sha256") != source:
                raise ValueError("Visual/human labels require matching crop evidence")
            checked_crop(path.parent, evidence)
        counts[split] += 1
        sources[label_source] += 1
        if split == "train":
            targets[row["category"]] += 1
    if any(counts[s] == 0 for s in ("train", "validation", "holdout")):
        raise ValueError("Separate train, validation and holdout records are required")
    summary = {
        "examples_by_split": dict(counts),
        "documents_by_split": {s: sum(v == s for v in splits.values()) for s in counts},
        "label_sources": dict(sources),
        "training_categories": dict(targets),
        "pilot_only": pilot,
        "manifest_sha256": digest(path.read_bytes()),
    }
    return data, summary


def training_rows(records: list[dict], rules: dict) -> list[dict]:
    """Match the exact inference state/questions; targets stay outside model input."""
    rows = []
    for record in records:
        rule = field_rule(record["field_id"], rules)
        rows.append(
            {
                "state": {"field_id": record["field_id"], "ocr_text": record["text"]},
                "questions": {
                    "category": {
                        "type": "choice",
                        "instructions": rule["instructions"],
                        "criteria": rule["categories"],
                    }
                },
                "gold": {
                    "category": {
                        "probabilities": {
                            key: float(key == record["category"]) for key in rule["categories"]
                        }
                    }
                },
            }
        )
    return rows
