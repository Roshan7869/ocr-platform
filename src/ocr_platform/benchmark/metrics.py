"""Recognition metrics and explicitly conditional scale/cost projections."""

import unicodedata
from collections import defaultdict


def normalize(text: str) -> str:
    # Preserve case, digits, punctuation, and language; normalize only Unicode/whitespace.
    return " ".join(unicodedata.normalize("NFC", text).split())


def distance(left: str, right: str) -> int:
    previous = list(range(len(right) + 1))
    for i, a in enumerate(left, 1):
        current = [i]
        for j, b in enumerate(right, 1):
            current.append(min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (a != b)))
        previous = current
    return previous[-1]


def summarize(rows: list[dict]) -> dict:
    eligible = [r for r in rows if r["scorable"]]
    successful = [r for r in eligible if r["status"] == "ok"]
    correct = sum(normalize(r["expected"]) == normalize(r["text"]) for r in successful)
    edits = sum(distance(normalize(r["expected"]), normalize(r["text"])) for r in successful)
    characters = sum(len(normalize(r["expected"])) for r in successful)
    nonblank = [r for r in successful if normalize(r["expected"])]
    blank = [r for r in successful if not normalize(r["expected"])]
    return {
        "completed_inference_fields": sum(r["status"] == "ok" for r in rows),
        "failed_inference_fields": sum(r["status"] != "ok" for r in rows),
        "labeled_fields": len(eligible),
        "successful_fields": len(successful),
        "failed_fields": len(eligible) - len(successful),
        "exact_match": correct / len(eligible) if eligible else None,
        "observed_correction_or_failure_rate": (1 - correct / len(eligible) if eligible else None),
        "character_error_rate_successful_fields": edits / characters if characters else None,
        "character_error_rate_nonblank_successful_fields": (
            sum(distance(normalize(r["expected"]), normalize(r["text"])) for r in nonblank)
            / sum(len(normalize(r["expected"])) for r in nonblank)
            if nonblank
            else None
        ),
        "blank_false_positive_rate": (
            sum(bool(normalize(r["text"])) for r in blank) / len(blank) if blank else None
        ),
        "inference_seconds": sum(r["seconds"] for r in rows),
        "billable_input_units": sum(r["billable_units"] for r in rows),
        "attempts": sum(r["attempts"] for r in rows),
    }


def make_report(
    rows: list[dict],
    *,
    corpus_documents: int,
    fields_per_document: int,
    unit_price: float | None,
    hourly_compute_cost: float | None,
    review_seconds_per_field: float,
    review_hourly_cost: float | None,
    currency: str,
) -> dict:
    overall = summarize(rows)
    groups = defaultdict(list)
    for row in rows:
        groups[f"{row['split']}/{row['kind']}"].append(row)
    # Failed attempts also consume time and may incur charges. Divide by evaluated
    # fields rather than successes; human correction handles failures, not assumed
    # unlimited retries until recognition succeeds.
    seconds_per_field = overall["inference_seconds"] / len(rows) if rows else None
    projected_fields = corpus_documents * fields_per_document
    projected_hours = (
        projected_fields * seconds_per_field / 3600 if seconds_per_field is not None else None
    )
    api_units_per_field = overall["billable_input_units"] / len(rows) if rows else None
    rate = overall["observed_correction_or_failure_rate"]
    review_hours = (
        projected_fields * rate * review_seconds_per_field / 3600 if rate is not None else None
    )
    return {
        "schema_version": 1,
        "scope": "oracle-region recognition; not end-to-end extraction or auto-accept calibration",
        "overall": overall,
        "by_split_and_kind": {key: summarize(value) for key, value in sorted(groups.items())},
        "scale_assumptions": {
            "corpus_documents": corpus_documents,
            "text_fields_per_document": fields_per_document,
            "currency": currency,
            "price_per_1000_input_units": unit_price,
            "hourly_compute_cost": hourly_compute_cost,
            "review_seconds_per_field": review_seconds_per_field,
            "review_hourly_cost": review_hourly_cost,
        },
        "projection": {
            "serial_inference_hours": projected_hours,
            "api_cost": (
                projected_fields * api_units_per_field * unit_price / 1000
                if unit_price is not None and api_units_per_field is not None
                else None
            ),
            "compute_cost": (
                projected_hours * hourly_compute_cost
                if projected_hours is not None and hourly_compute_cost is not None
                else None
            ),
            "correction_hours": review_hours,
            "correction_cost": (
                review_hours * review_hourly_cost
                if review_hours is not None and review_hourly_cost is not None
                else None
            ),
        },
        "limitations": [
            "Human-selected answer boxes bypass registration, field assignment, and row detection.",
            "Marks and unreadable ground truth are excluded from text scores.",
            "Correction rate is observed disagreement, not a calibrated production review rate.",
            "Crop API mode sends one image per field, not one PDF per document.",
            "Projections assume representative labels and serial throughput; no SLA is implied.",
            "API failures may still incur charges; attempted request units are counted conservatively.",
            "Model loading and rendering time are recorded separately from inference projections.",
        ],
    }
