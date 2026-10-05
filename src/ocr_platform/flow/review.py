"""Append human corrections as immutable, evidence-linked revisions."""

import json
from datetime import UTC, datetime
from pathlib import Path

from ocr_platform.benchmark.dataset import digest
from ocr_platform.benchmark.runner import canonical

from .pipeline import checked_crop, field_rule, validate_text


def refresh_review_view(folder: Path) -> dict:
    """Rebuild effective results from immutable model decisions and human revisions.

    The caller holds the flow writer lock.
    """
    results = {}
    for line in (folder / "decisions.jsonl").read_text(encoding="utf-8").splitlines():
        decision = json.loads(line)
        if digest(canonical(decision["record"])) != decision["decision_id"]:
            raise ValueError("Original decision failed integrity checks")
        if decision["record"]["run_id"] != folder.name or decision["decision_id"] in results:
            raise ValueError("Duplicate or foreign original decision")
        checked_crop(folder, decision["record"]["evidence"])
        results[decision["decision_id"]] = {**decision, "human_revision": None}
    previous = None
    journal = folder / "human_revisions.jsonl"
    if journal.exists():
        for line in journal.read_text(encoding="utf-8").splitlines():
            revision = json.loads(line)
            record = revision["record"]
            if (
                digest(canonical(record)) != revision["revision_id"]
                or record["previous_revision_id"] != previous
                or record["run_id"] != folder.name
                or record["decision_id"] not in results
            ):
                raise ValueError("Human revision journal failed integrity checks")
            original = results[record["decision_id"]]
            if record["evidence"] != original["record"]["evidence"]:
                raise ValueError("Human revision evidence differs from original")
            original["human_revision"] = revision
            previous = revision["revision_id"]
    effective = list(results.values())
    pending = [
        d for d in effective if (d["human_revision"] or d)["record"]["disposition"] == "review"
    ]
    (folder / "result.json").write_bytes(canonical({"run_id": folder.name, "fields": effective}))
    (folder / "review_candidates.json").write_bytes(
        canonical({"run_id": folder.name, "candidates": pending})
    )
    summary = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
    summary.update(review=len(pending), accepted=len(effective) - len(pending))
    (folder / "summary.json").write_bytes(canonical(summary))
    return summary


def correct(
    folder: Path,
    decision_id: str,
    value: str,
    reviewer: str,
    category: str | None = None,
    state: str = "present",
) -> dict:
    if not reviewer.strip():
        raise ValueError("A human reviewer identity is required")
    identity = json.loads((folder / "identity.json").read_text(encoding="utf-8"))
    if digest(canonical(identity)) != folder.name:
        raise ValueError("Flow identity failed its hash check")
    decisions = [
        json.loads(line)
        for line in (folder / "decisions.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    selected = [d for d in decisions if d["decision_id"] == decision_id]
    if len(selected) != 1 or digest(canonical(selected[0]["record"])) != decision_id:
        raise ValueError("Missing or changed original decision")
    record = selected[0]["record"]
    checked_crop(folder, record["evidence"])
    rule = field_rule(record["field_id"], identity["rules"])
    if state not in {"present", "absent", "unreadable"}:
        raise ValueError("Unknown human value state")
    if state != "present":
        if value or category is not None:
            raise ValueError("Absent/unreadable corrections need an empty value and no category")
        validation = {"ok": True, "normalized": None}
    else:
        validation = validate_text(value, rule)
        if not validation["ok"]:
            raise ValueError("Correction fails field validation; keep the decision in review")
    if state == "present" and rule["type"] == "category":
        if category not in rule["categories"] or category == "UNKNOWN":
            raise ValueError("A known category must be selected explicitly by the human reviewer")
    elif category is not None:
        raise ValueError("This field does not use category classification")
    lock = folder / ".flow.lock"
    try:
        stream = lock.open("x", encoding="utf-8")
    except FileExistsError:
        raise ValueError("Flow output has an active writer") from None
    try:
        stream.close()
        refresh_review_view(folder)
        journal = folder / "human_revisions.jsonl"
        previous = None
        if journal.exists():
            for line in journal.read_text(encoding="utf-8").splitlines():
                revision = json.loads(line)
                if (
                    digest(canonical(revision["record"])) != revision["revision_id"]
                    or revision["record"]["previous_revision_id"] != previous
                ):
                    raise ValueError("Human revision journal failed integrity checks")
                previous = revision["revision_id"]
        revision_record = {
            "decision_id": decision_id,
            "run_id": folder.name,
            "previous_revision_id": previous,
            "reviewer": reviewer.strip(),
            "reviewed_at": datetime.now(UTC).isoformat(),
            "source": "human_correction",
            "corrected_text": value,
            "final_value": validation["normalized"],
            "final_category": category,
            "value_state": state,
            "disposition": "review" if state == "unreadable" else "accepted",
            "evidence": record["evidence"],
        }
        revision = {"revision_id": digest(canonical(revision_record)), "record": revision_record}
        with journal.open("a", encoding="utf-8") as stream:
            stream.write(canonical(revision).decode("utf-8") + "\n")
        refresh_review_view(folder)
        return {
            "revision_id": revision["revision_id"],
            "decision_id": decision_id,
            "disposition": revision_record["disposition"],
            "source": "human_correction",
        }
    finally:
        lock.unlink(missing_ok=True)
