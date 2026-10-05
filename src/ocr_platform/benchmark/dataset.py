"""Strict evaluation dataset and input integrity checks."""

import hashlib
import json
import math
from pathlib import Path


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_dataset(path: Path, *, require_labels: bool = True, allow_unlabeled: bool = False) -> dict:
    dataset = json.loads(path.read_text(encoding="utf-8"))
    validate_dataset(dataset, require_labels=require_labels, allow_unlabeled=allow_unlabeled)
    return dataset


def validate_dataset(
    dataset: dict, *, require_labels: bool = True, allow_unlabeled: bool = False
) -> None:
    if not isinstance(dataset, dict):
        raise TypeError("Dataset must be an object")
    if (
        dataset.get("schema_version") != 1
        or not isinstance(dataset.get("documents"), list)
        or not dataset["documents"]
    ):
        raise ValueError("Dataset needs schema_version=1 and non-empty documents")
    if not isinstance(dataset.get("source_root"), str):
        raise TypeError("Dataset needs a source_root")
    if not Path(dataset["source_root"]).is_absolute():
        raise ValueError("source_root must be absolute")
    root = Path(dataset["source_root"]).resolve()
    document_ids = set()
    labeled_count = 0
    for document in dataset["documents"]:
        if not isinstance(document, dict):
            raise TypeError("Document must be an object")
        if not isinstance(document.get("fields"), list):
            raise TypeError("Document fields must be a list")
        if not isinstance(document.get("path"), str) or not document["path"]:
            raise TypeError("Document path must be a non-empty string")
        doc_id = document["id"]
        if not isinstance(doc_id, str) or not doc_id or doc_id in document_ids:
            raise ValueError("Document IDs must be non-empty and unique")
        document_ids.add(doc_id)
        source = (root / document["path"]).resolve()
        if not source.is_relative_to(root):
            raise ValueError("Source path escapes source_root")
        if document.get("classification") not in {"unclassified", "synthetic", "approved_redacted"}:
            raise ValueError("Unknown document classification")
        if document.get("split") not in {"development", "holdout"}:
            raise ValueError("Unknown document split")
        page_count = document.get("page_count")
        if type(page_count) is not int or page_count < 1:
            raise ValueError("Invalid page count")
        sha = document.get("sha256", "")
        if len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha):
            raise ValueError("Invalid document SHA-256")
        field_ids = set()
        for field in document.get("fields", []):
            if not isinstance(field, dict):
                raise TypeError("Field must be an object")
            key = field.get("id")
            if not isinstance(key, str) or not key or key in field_ids:
                raise ValueError("Field IDs must be non-empty and unique within a document")
            field_ids.add(key)
            page = field.get("page")
            if type(page) is not int or not 0 <= page < page_count:
                raise ValueError("Invalid field page index")
            box = field.get("bbox")
            if (
                not isinstance(box, list)
                or len(box) != 4
                or any(type(x) not in {int, float} or not math.isfinite(x) for x in box)
                or not 0 <= box[0] < box[2] <= 1
                or not 0 <= box[1] < box[3] <= 1
            ):
                raise ValueError("Bbox must be [left,top,right,bottom] normalized to [0,1]")
            if field.get("kind") not in {"handwriting", "print", "mark"}:
                raise ValueError("Unknown field kind")
            if field.get("state") not in {"present", "absent", "unreadable"}:
                raise ValueError("Unknown field state")
            expected = field.get("expected")
            if field["state"] == "unreadable":
                if expected is not None:
                    raise ValueError("Unreadable fields must have null expected")
            elif allow_unlabeled and expected is None:
                pass  # Inference-only answer region; never scored as verified truth.
            elif not isinstance(expected, str):
                raise ValueError("Readable fields require a verified string expected")
            elif field["state"] == "present" and not expected.strip():
                raise ValueError("Present fields cannot have blank expected")
            elif field["state"] == "absent" and expected != "":
                raise ValueError("Absent fields must have empty expected")
            if not isinstance(field.get("labeler"), str) or not field["labeler"].strip():
                raise ValueError("Each field needs a human labeler")
            if field["kind"] != "mark" and field["state"] != "unreadable" and expected is not None:
                labeled_count += 1
    if require_labels and not labeled_count:
        raise ValueError("No scorable text labels. Label answer regions before running engines")


def verified_source(dataset: dict, document: dict) -> Path:
    root = Path(dataset["source_root"]).resolve()
    source = (root / document["path"]).resolve()
    if not source.is_relative_to(root) or source.stat().st_size > 10_000_000:
        raise ValueError("Source path or 10MB input cap check failed")
    if digest(source.read_bytes()) != document["sha256"]:
        raise ValueError("Source integrity check failed")
    return source
