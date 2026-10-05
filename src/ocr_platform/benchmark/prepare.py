"""Deterministic batch/size-stratified sample and offline annotation page."""

import base64
import io
import json
import random
from collections import defaultdict
from pathlib import Path

from pypdf import PdfReader

from .dataset import digest, validate_dataset
from .runner import render_document


def select_sources(root: Path, count: int, seed: int) -> list[Path]:
    batches = defaultdict(list)
    for source in sorted(root.rglob("*.pdf")):
        batches[str(source.parent.relative_to(root))].append(source)
    if not batches or count > sum(len(files) for files in batches.values()):
        raise ValueError("Sample size exceeds available PDFs, or no PDFs found")
    rng = random.Random(seed)
    strata = []
    for files in batches.values():
        ordered = sorted(files, key=lambda f: (f.stat().st_size, f.name))
        # File size is only a cheap diversity proxy, never a scan-quality score.
        for index in range(3):
            bucket = ordered[len(ordered) * index // 3 : len(ordered) * (index + 1) // 3]
            rng.shuffle(bucket)
            if bucket:
                strata.append(bucket)
    selected = []
    while len(selected) < count:
        for bucket in strata:
            if bucket and len(selected) < count:
                selected.append(bucket.pop())
    return selected


def prepare(root: Path, output: Path, count: int, seed: int) -> dict:
    if not 2 <= count <= 100:
        raise ValueError("Prepare sample size must be between 2 and 100")
    if (output / "dataset.json").exists() or (output / "label.html").exists():
        raise ValueError("Output already contains a dataset; choose a new directory")
    root = root.resolve()
    selected = select_sources(root, count, seed)
    by_batch = defaultdict(list)
    for source in selected:
        by_batch[source.parent].append(source)
    split_rng = random.Random(seed + 1)
    holdout = set()
    for batch in by_batch.values():
        holdout.update(split_rng.sample(batch, max(1, len(batch) // 3)))
    dataset = {
        "schema_version": 1,
        "source_root": str(root),
        "documents": [],
        "sampling": {
            "seed": seed,
            "method": "balanced batch / file-size thirds",
            "available_documents": sum(1 for _ in root.rglob("*.pdf")),
            "note": "Balanced sample is not corpus-frequency weighted.",
        },
    }
    images = {}
    for source in selected:
        if source.stat().st_size > 10_000_000:
            raise ValueError("Sample PDF exceeds 10MB benchmark input cap")
        relative = source.relative_to(root).as_posix()
        sha = digest(source.read_bytes())
        reader = PdfReader(source)
        if reader.is_encrypted or not 1 <= len(reader.pages) <= 10:
            raise ValueError("Sample PDF is encrypted or outside the 1-10 page cap")
        doc_id = digest(relative.encode("utf-8"))[:16]
        document = {
            "id": doc_id,
            "path": relative,
            "sha256": sha,
            "batch": source.parent.relative_to(root).as_posix(),
            "classification": "unclassified",
            "page_count": len(reader.pages),
            "split": "holdout" if source in holdout else "development",
            "fields": [],
        }
        dataset["documents"].append(document)
        images[doc_id] = []
        for page in render_document(source, 110):
            buffer = io.BytesIO()
            page.save(buffer, format="PNG")
            images[doc_id].append(
                "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")
            )
            page.close()
    validate_dataset(dataset, require_labels=False)
    output.mkdir(parents=True, exist_ok=True)
    template = Path(__file__).with_name("labeler.html").read_text(encoding="utf-8")
    payload = json.dumps({"dataset": dataset, "images": images}, ensure_ascii=False)
    html = template.replace("/*BENCHMARK_DATA*/", payload.replace("<", "\\u003c"))
    (output / "dataset.json").write_text(
        json.dumps(dataset, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output / "label.html").write_text(html, encoding="utf-8")
    return {
        "documents": count,
        "labeler": str((output / "label.html").resolve()),
        "dataset": str((output / "dataset.json").resolve()),
    }
