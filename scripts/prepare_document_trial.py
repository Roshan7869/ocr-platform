"""Materialize unverified crop regions for a reproducible local document trial."""

import argparse
import json
from pathlib import Path

from ocr_platform.benchmark.dataset import load_dataset, verified_source


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("data/WARD-42/WARD-42"))
    parser.add_argument("--regions", type=Path, default=Path("configs/document_trial_regions.json"))
    parser.add_argument("--out", type=Path, default=Path("runs/document-trial/dataset.json"))
    args = parser.parse_args()
    data = json.loads(args.regions.read_text(encoding="utf-8"))
    data["source_root"] = str(args.source.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    # Write exclusively so an existing labeled dataset cannot be overwritten.
    with args.out.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
    try:
        dataset = load_dataset(args.out, require_labels=False, allow_unlabeled=True)
        for document in dataset["documents"]:
            verified_source(dataset, document)
    except Exception:
        args.out.unlink(missing_ok=True)
        raise
    print(json.dumps({"documents": len(data["documents"]), "dataset": str(args.out.resolve())}))


if __name__ == "__main__":
    main()
