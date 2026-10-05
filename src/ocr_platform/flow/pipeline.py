"""Deterministic field validation, evidence-preserving classification, and review."""

import fnmatch
import json
import math
import time
import unicodedata
from pathlib import Path

from ocr_platform.benchmark.dataset import digest
from ocr_platform.benchmark.metrics import normalize
from ocr_platform.benchmark.runner import canonical


def load_rules(path: Path) -> dict:
    config = json.loads(path.read_text(encoding="utf-8"))
    if set(config) != {
        "schema_version",
        "draft",
        "ocr_min_confidence",
        "classification_min_confidence",
        "rules",
    }:
        raise ValueError("Unknown or missing flow rule configuration keys")
    if config["schema_version"] != 1 or type(config["draft"]) is not bool:
        raise ValueError("Invalid flow rule version or draft flag")
    for key in ("ocr_min_confidence", "classification_min_confidence"):
        if not probability(config[key]):
            raise ValueError("Flow thresholds must be finite probabilities")
    if not isinstance(config["rules"], list) or not config["rules"]:
        raise ValueError("Flow needs field rules")
    patterns = set()
    for rule in config["rules"]:
        pattern = rule.get("pattern")
        if not isinstance(pattern, str) or not pattern or pattern in patterns:
            raise ValueError("Rule patterns must be unique, non-empty strings")
        patterns.add(pattern)
        kind = rule.get("type")
        keys = {"pattern", "type"}
        if kind == "integer":
            keys |= {"min", "max"}
            if (
                type(rule.get("min")) is not int
                or type(rule.get("max")) is not int
                or rule["min"] > rule["max"]
            ):
                raise ValueError("Invalid integer bounds")
        elif kind == "digits":
            keys |= {"length"}
            if type(rule.get("length")) is not int or not 1 <= rule["length"] <= 100:
                raise ValueError("Invalid digit count")
        elif kind == "code":
            keys |= {"aliases"}
            if (
                not isinstance(rule.get("aliases"), dict)
                or not rule["aliases"]
                or any(
                    not isinstance(k, str) or not isinstance(v, str) or not k or not v
                    for k, v in rule["aliases"].items()
                )
            ):
                raise ValueError("Codes need a non-empty alias mapping")
        elif kind == "category":
            keys |= {"instructions", "categories"}
            if (
                not isinstance(rule.get("instructions"), str)
                or not rule["instructions"]
                or not isinstance(rule.get("categories"), dict)
                or not 2 <= len(rule["categories"]) <= 20
                or "UNKNOWN" not in rule["categories"]
                or any(
                    not isinstance(k, str) or not isinstance(v, str) or not k or not v
                    for k, v in rule["categories"].items()
                )
            ):
                raise ValueError(
                    "Category rule needs instructions and 2-20 choices including UNKNOWN"
                )
        elif kind != "text":
            raise ValueError("Unknown validation rule type")
        if set(rule) != keys:
            raise ValueError("Unknown or missing per-field rule keys")
    return config


def probability(value) -> bool:
    return type(value) in {int, float} and math.isfinite(value) and 0 <= value <= 1


def field_rule(field_id: str, config: dict) -> dict | None:
    matches = [rule for rule in config["rules"] if fnmatch.fnmatchcase(field_id, rule["pattern"])]
    if len(matches) > 1:
        raise ValueError("Overlapping field rules; refine patterns before running")
    return matches[0] if matches else None


def validate_text(text: str, rule: dict | None) -> dict:
    text = normalize(text)
    if not text:
        return {"ok": False, "normalized": None, "reasons": ["EMPTY_OCR"]}
    if len(text) > 1024:
        return {"ok": False, "normalized": None, "reasons": ["TEXT_TOO_LONG"]}
    if text in {'"', '""', "〃", "”", "''", "ditto", "Ditto"}:
        return {"ok": False, "normalized": None, "reasons": ["UNRESOLVED_DITTO"]}
    if rule is None:
        return {"ok": False, "normalized": None, "reasons": ["UNCONFIGURED_FIELD"]}
    numeric = "".join(str(unicodedata.decimal(c)) if c.isdecimal() else c for c in text)
    kind = rule["type"]
    if kind == "integer":
        if not numeric.isascii() or not numeric.isdigit():
            return {"ok": False, "normalized": None, "reasons": ["INVALID_INTEGER"]}
        value = int(numeric)
        if not rule["min"] <= value <= rule["max"]:
            return {"ok": False, "normalized": None, "reasons": ["INTEGER_OUT_OF_RANGE"]}
        return {"ok": True, "normalized": value, "reasons": []}
    if kind == "digits":
        if not numeric.isascii() or not numeric.isdigit() or len(numeric) != rule["length"]:
            return {"ok": False, "normalized": None, "reasons": ["INVALID_DIGIT_SEQUENCE"]}
        return {"ok": True, "normalized": numeric, "reasons": []}
    if kind == "code":
        value = rule["aliases"].get(text)
        if value is None:
            return {"ok": False, "normalized": None, "reasons": ["UNKNOWN_VOCABULARY_CODE"]}
        return {"ok": True, "normalized": value, "reasons": []}
    return {"ok": True, "normalized": text, "reasons": []}


def checked_crop(folder: Path, row: dict) -> bytes:
    path = (folder / row["crop_path"]).resolve()
    if not path.is_relative_to(folder.resolve()):
        raise ValueError("Crop path escapes its run directory")
    content = path.read_bytes()
    if digest(content) != row["crop_sha256"]:
        raise ValueError("Crop evidence failed its hash check")
    if len(row["document_sha256"]) != 64:
        raise ValueError("Missing source document evidence hash")
    return content


def decide(row: dict, config: dict, classifier) -> dict:
    reasons = ["AUTO_ACCEPT_DISABLED"]
    if config["draft"]:
        reasons.append("DRAFT_RULES")
    validation = validate_text(row["text"], field_rule(row["field_id"], config))
    reasons.extend(validation["reasons"])
    if row["status"] != "ok":
        reasons.append("OCR_FAILED")
    score = row.get("confidence")
    if not probability(score):
        reasons.append("OCR_CONFIDENCE_UNAVAILABLE")
    elif score < config["ocr_min_confidence"]:
        reasons.append("LOW_OCR_CONFIDENCE")
    classification = None
    rule = field_rule(row["field_id"], config)
    if validation["ok"] and row["status"] == "ok" and rule["type"] == "category":
        if "LOW_OCR_CONFIDENCE" in reasons or "OCR_CONFIDENCE_UNAVAILABLE" in reasons:
            reasons.append("CLASSIFICATION_SKIPPED_UNCERTAIN_OCR")
        else:
            try:
                classification = classifier.classify(row["text"], row["field_id"], rule)
                category = classification.get("category")
                confidence = classification.get("confidence")
                if category not in rule["categories"] or not probability(confidence):
                    classification = None
                    reasons.append("INVALID_CLASSIFIER_RESPONSE")
                else:
                    classification = {"category": category, "confidence": confidence}
                    if category == "UNKNOWN":
                        reasons.append("UNKNOWN_CATEGORY")
                    elif confidence < config["classification_min_confidence"]:
                        reasons.append("LOW_CLASSIFICATION_CONFIDENCE")
            except Exception:  # noqa: BLE001 -- model errors may contain input PII
                classification = None
                reasons.append("CLASSIFIER_FAILED")
    return {
        "raw_text": row["text"],
        "ocr_confidence": score,
        "value_state": "present" if row["text"].strip() else "unknown",
        "validation": validation,
        "classification": classification,
        "disposition": "review",
        "final_value": None,
        "final_category": None,
        "reason_codes": reasons,
        "classifier_seconds": None,
    }


def classify_run(ocr_folder: Path, output: Path, config: dict, classifier) -> dict:
    ocr_identity = json.loads((ocr_folder / "identity.json").read_text(encoding="utf-8"))
    if digest(canonical(ocr_identity)) != ocr_folder.name:
        raise ValueError("OCR run identity failed its hash check")
    latest = {}
    for line in (ocr_folder / "predictions.jsonl").read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        latest[(row["document_id"], row["field_id"])] = row
    if not latest:
        raise ValueError("OCR run has no answer-region predictions")
    # Complete evidence preflight before any classifier invocation.
    crops = {key: checked_crop(ocr_folder, row) for key, row in latest.items()}
    identity = {
        "flow_version": 1,
        "ocr_identity": ocr_identity,
        "ocr_predictions_sha256": digest(canonical({str(k): v for k, v in latest.items()})),
        "rules": config,
        "classifier": classifier.identity,
    }
    run_id = digest(canonical(identity))
    folder = output / run_id
    folder.mkdir(parents=True, exist_ok=True)
    lock = folder / ".flow.lock"
    try:
        stream = lock.open("x", encoding="utf-8")
    except FileExistsError:
        raise ValueError("Flow output has an active writer") from None
    try:
        stream.close()
        (folder / "identity.json").write_bytes(canonical(identity))
        journal = folder / "decisions.jsonl"
        existing = {}
        if journal.exists():
            for line in journal.read_text(encoding="utf-8").splitlines():
                decision = json.loads(line)
                if decision["decision_id"] != digest(canonical(decision["record"])):
                    raise ValueError("Cached decision was changed")
                existing[(decision["record"]["document_id"], decision["record"]["field_id"])] = (
                    decision
                )
        decisions = []
        crop_folder = folder / "crops"
        crop_folder.mkdir(exist_ok=True)
        for key, row in latest.items():
            (crop_folder / f"{row['crop_sha256']}.png").write_bytes(crops[key])
            if key in existing:
                decisions.append(existing[key])
                continue
            start = time.perf_counter()
            record = decide(row, config, classifier)
            record["classifier_seconds"] = time.perf_counter() - start
            record.update(
                {
                    "run_id": run_id,
                    "document_id": row["document_id"],
                    "field_id": row["field_id"],
                    "split": row["split"],
                    "evidence": {
                        "document_sha256": row["document_sha256"],
                        "page": row["page"],
                        "bbox": row["bbox"],
                        "crop_sha256": row["crop_sha256"],
                        "crop_path": f"crops/{row['crop_sha256']}.png",
                    },
                }
            )
            decision = {"decision_id": digest(canonical(record)), "record": record}
            with journal.open("a", encoding="utf-8") as stream:
                stream.write(canonical(decision).decode("utf-8") + "\n")
            decisions.append(decision)
        (folder / "review_candidates.json").write_bytes(
            canonical({"run_id": run_id, "candidates": decisions})
        )
        summary = {
            "run_id": run_id,
            "fields": len(decisions),
            "review": len(decisions),
            "accepted": 0,
            "classified": sum(d["record"]["classification"] is not None for d in decisions),
            "classifier_failures": sum(
                "CLASSIFIER_FAILED" in d["record"]["reason_codes"] for d in decisions
            ),
            "ocr_failures": sum("OCR_FAILED" in d["record"]["reason_codes"] for d in decisions),
            "output": str(folder.resolve()),
            "scope": "experimental annotated-crop flow; production auto-accept disabled",
        }
        (folder / "summary.json").write_bytes(canonical(summary))
        from .review import refresh_review_view

        return refresh_review_view(folder)
    finally:
        lock.unlink(missing_ok=True)
