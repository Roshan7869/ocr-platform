"""Bounded, resumable crop evaluation with content-addressed evidence."""

import importlib.metadata
import io
import json
import math
import os
import platform
import time
from pathlib import Path

from .dataset import digest, load_dataset, verified_source
from .engines import EngineError
from .metrics import make_report


def canonical(value: dict) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False).encode("utf-8")


def render_document(path: Path, dpi: int) -> list:
    import pypdfium2

    images = []
    with pypdfium2.PdfDocument(str(path)) as pdf:
        if len(pdf) > 10:
            raise ValueError("Benchmark document exceeds 10-page cap")
        for page in pdf:
            try:
                if page.get_width() * page.get_height() * (dpi / 72) ** 2 > 30_000_000:
                    raise ValueError("Rendered page exceeds 30-megapixel cap")
                bitmap = page.render(scale=dpi / 72)
                try:
                    images.append(bitmap.to_pil().copy())
                finally:
                    bitmap.close()
            finally:
                page.close()
    return images


def crop_bytes(image, bbox: list[float]) -> bytes:
    width, height = image.size
    box = (
        math.floor(bbox[0] * width),
        math.floor(bbox[1] * height),
        math.ceil(bbox[2] * width),
        math.ceil(bbox[3] * height),
    )
    output = io.BytesIO()
    image.crop(box).save(output, format="PNG")
    return output.getvalue()


def run(dataset_path: Path, output: Path, engine, **options) -> dict:
    """One writer per output root; prevent duplicate concurrent API submissions."""
    output.mkdir(parents=True, exist_ok=True)
    lock = output / ".benchmark.lock"
    try:
        stream = lock.open("x", encoding="utf-8")
    except FileExistsError:
        raise ValueError("Benchmark output is locked; stop the other run before retrying") from None
    try:
        with stream:
            stream.write(str(os.getpid()))
        return _run(dataset_path, output, engine, **options)
    finally:
        lock.unlink(missing_ok=True)


def _run(
    dataset_path: Path,
    output: Path,
    engine,
    *,
    dpi: int = 200,
    allow_api_upload: bool = False,
    split: str = "all",
    retry_failed: bool = False,
    limit: int = 500,
    corpus_documents: int = 100_000,
    fields_per_document: int = 100,
    unit_price: float | None = None,
    hourly_compute_cost: float | None = None,
    review_seconds_per_field: float = 30,
    review_hourly_cost: float | None = None,
    currency: str = "INR",
    require_labels: bool = True,
) -> dict:
    dataset = load_dataset(
        dataset_path, require_labels=require_labels, allow_unlabeled=not require_labels
    )
    selected = [d for d in dataset["documents"] if split == "all" or d["split"] == split]
    # Marks are a different task. Keep unreadable crops for qualitative review only.
    total = sum(sum(f["kind"] != "mark" for f in d["fields"]) for d in selected)
    if not 0 < total <= limit:
        raise ValueError("No selected text fields, or field count exceeds --max-fields")
    if engine.api and not allow_api_upload:
        raise ValueError("API uploads require explicit --allow-api-upload")
    if engine.api and any(
        d["classification"] not in {"synthetic", "approved_redacted"}
        for d in selected
        if any(f["kind"] != "mark" for f in d["fields"])
    ):
        raise ValueError("API inputs must be classified synthetic or approved_redacted")
    # Verify every selected source before the first potentially billable request.
    sources = {d["id"]: verified_source(dataset, d) for d in selected}
    import pypdfium2

    identity = {
        "dataset_sha256": digest(canonical(dataset)),
        "engine": engine.identity,
        "dpi": dpi,
        "python": platform.python_version(),
        "pdfium": str(pypdfium2.PDFIUM_INFO),
        "rendering_packages": {
            name: importlib.metadata.version(name) for name in ("pypdfium2", "pillow")
        },
        "runner_version": 2,
        "require_labels": require_labels,
        "split": split,
    }
    run_id = digest(canonical(identity))
    folder = output / run_id
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "identity.json").write_bytes(canonical(identity))
    predictions = folder / "predictions.jsonl"
    cached = {}
    if predictions.exists():
        for line in predictions.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            cached[(row["document_id"], row["field_id"])] = row
    rows = []
    render_seconds = 0.0
    for document in selected:
        fields = [f for f in document["fields"] if f["kind"] != "mark"]
        if not fields:
            continue
        needed = [
            f
            for f in fields
            if (document["id"], f["id"]) not in cached
            or (retry_failed and cached[(document["id"], f["id"])]["status"] != "ok")
        ]
        pages = []
        if needed:
            start = time.perf_counter()
            pages = render_document(sources[document["id"]], dpi)
            if len(pages) != document["page_count"]:
                raise ValueError("Dataset page count does not match source")
            render_seconds += time.perf_counter() - start
        for field in fields:
            key = (document["id"], field["id"])
            prior = cached.get(key)
            if prior:
                if (
                    prior["document_sha256"] != document["sha256"]
                    or prior["bbox"] != field["bbox"]
                    or prior["page"] != field["page"]
                    or prior["expected"] != field["expected"]
                    or prior["kind"] != field["kind"]
                    or prior["state"] != field["state"]
                    or prior["split"] != document["split"]
                ):
                    raise ValueError("Cached prediction does not match evaluation dataset")
                crop_path = (folder / prior["crop_path"]).resolve()
                if (
                    not crop_path.is_relative_to(folder.resolve())
                    or digest(crop_path.read_bytes()) != prior["crop_sha256"]
                ):
                    raise ValueError("Cached crop evidence is missing or changed")
            if prior and not (retry_failed and prior["status"] != "ok"):
                rows.append(prior)
                continue
            image = crop_bytes(pages[field["page"]], field["bbox"])
            crop_hash = digest(image)
            crop_folder = folder / "crops"
            crop_folder.mkdir(exist_ok=True)
            (crop_folder / f"{crop_hash}.png").write_bytes(image)
            start = time.perf_counter()
            status, error = "ok", None
            try:
                prediction = engine.recognize(image)
            except EngineError as exc:
                status, error = "failed", str(exc)
                prediction = {
                    "text": "",
                    "confidence": None,
                    "attempts": 1,
                    "billable_units": int(engine.api),
                }
            except Exception:  # noqa: BLE001 -- backend messages can contain PII; score sanitized failures
                # Backend exceptions can contain PII or request payloads. Record a
                # sanitized failure and continue so failures remain in the denominator.
                status, error = "failed", "engine_runtime_failure"
                prediction = {
                    "text": "",
                    "confidence": None,
                    "attempts": 1,
                    "billable_units": int(engine.api),
                }
            seconds = time.perf_counter() - start
            row = {
                "document_id": document["id"],
                "field_id": field["id"],
                "document_sha256": document["sha256"],
                "page": field["page"],
                "bbox": field["bbox"],
                "crop_sha256": crop_hash,
                "crop_path": f"crops/{crop_hash}.png",
                "kind": field["kind"],
                "state": field["state"],
                "split": document["split"],
                "expected": field["expected"],
                "scorable": field["state"] != "unreadable" and field["expected"] is not None,
                "status": status,
                "error": error,
                **prediction,
                "seconds": seconds + (prior["seconds"] if prior else 0),
                "attempts": prediction["attempts"] + (prior["attempts"] if prior else 0),
                "billable_units": prediction["billable_units"]
                + (prior["billable_units"] if prior else 0),
            }
            # Flush each attempt for safe restart. A crash during an API call can still bill;
            # exactly-once delivery cannot be guaranteed without provider idempotency.
            with predictions.open("a", encoding="utf-8") as stream:
                stream.write(canonical(row).decode("utf-8") + "\n")
            rows.append(row)
        for page in pages:
            page.close()
    report = make_report(
        rows,
        corpus_documents=corpus_documents,
        fields_per_document=fields_per_document,
        unit_price=unit_price,
        hourly_compute_cost=hourly_compute_cost,
        review_seconds_per_field=review_seconds_per_field,
        review_hourly_cost=review_hourly_cost,
        currency=currency,
    )
    report.update(
        {
            "run_id": run_id,
            "identity": identity,
            "render_seconds_this_invocation": render_seconds,
            "excluded_mark_fields": sum(
                sum(f["kind"] == "mark" for f in d["fields"]) for d in selected
            ),
            "coverage": {
                "selected_documents": len(selected),
                "documents_with_text_labels": len(
                    {r["document_id"] for r in rows if r["scorable"]}
                ),
                "documents_without_scorable_text": sum(
                    not any(
                        f["kind"] != "mark"
                        and f["state"] != "unreadable"
                        and f["expected"] is not None
                        for f in d["fields"]
                    )
                    for d in selected
                ),
            },
        }
    )
    (folder / "report.json").write_bytes(canonical(report))
    return {
        "run_id": run_id,
        "report_path": str((folder / "report.json").resolve()),
        "overall": report["overall"],
    }
