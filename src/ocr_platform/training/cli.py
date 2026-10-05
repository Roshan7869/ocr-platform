"""Validate supervision or fine-tune a local Laya occupation classifier."""

import argparse
import json
from pathlib import Path

from ocr_platform.flow.pipeline import load_rules

from .classifier import train
from .dataset import load_training


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["validate", "train"])
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--rules", type=Path, default=Path("configs/flow_rules_v1.json"))
    parser.add_argument("--pilot", action="store_true")
    parser.add_argument("--model", type=Path, default=Path("models/laya-multilingual"))
    parser.add_argument("--training-source", type=Path)
    parser.add_argument("--out", type=Path, default=Path("runs/fine-tuning/laya"))
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()
    try:
        rules = load_rules(args.rules)
        if args.command == "validate":
            _, result = load_training(args.manifest, rules, pilot=args.pilot)
        else:
            if args.training_source is None:
                raise ValueError(
                    "Training requires --training-source pointing to official Laya source"
                )
            result = train(
                args.manifest,
                args.model,
                args.out,
                rules,
                args.training_source,
                pilot=args.pilot,
                epochs=args.epochs,
                device=args.device,
            )
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, OSError, ImportError, KeyError, TypeError) as exc:
        print(
            json.dumps(
                {
                    "error": type(exc).__name__,
                    "message": str(exc)
                    if isinstance(exc, ValueError)
                    else "Training input or dependency error",
                }
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
