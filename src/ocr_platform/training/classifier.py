"""Fine-tune Laya's decision head locally and compare an untouched pilot holdout."""

import gc
import os
import sys
from dataclasses import asdict
from pathlib import Path

from ocr_platform.benchmark.dataset import digest
from ocr_platform.benchmark.runner import canonical
from ocr_platform.flow.adapters import LayaClassifier
from ocr_platform.flow.pipeline import field_rule

from .dataset import load_training, training_rows


def evaluate(classifier, records: list[dict], rules: dict) -> dict:
    correct, failures, by_class = 0, 0, {}
    for row in records:
        label = row["category"]
        bucket = by_class.setdefault(label, {"examples": 0, "correct": 0})
        bucket["examples"] += 1
        try:
            result = classifier.classify(
                row["text"], row["field_id"], field_rule(row["field_id"], rules)
            )
            match = result["category"] == label
            correct += match
            bucket["correct"] += match
        except Exception:  # noqa: BLE001 -- model exceptions can contain private inputs
            failures += 1
    return {
        "examples": len(records),
        "correct": correct,
        "failures": failures,
        "accuracy": correct / len(records) if records else None,
        "macro_recall": sum(v["correct"] / v["examples"] for v in by_class.values()) / len(by_class)
        if by_class
        else None,
        "by_category": by_class,
    }


def train(
    manifest: Path,
    model: Path,
    output: Path,
    rules: dict,
    source: Path,
    *,
    pilot: bool = False,
    epochs: int = 2,
    device: str = "cpu",
) -> dict:
    data, summary = load_training(manifest, rules, pilot=pilot)
    if not 1 <= epochs <= 20:
        raise ValueError("Training epochs must be between 1 and 20")
    source = source.resolve()
    module = source / "laya" / "train.py"
    if not module.is_file():
        raise ValueError("Provide an official Laya source checkout containing laya/train.py")
    # Source wheels omit the training module; use an explicitly supplied checkout.
    sys.path.insert(0, str(source))
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    import torch
    from laya.calibrate import fit_temperature_map
    from laya.train import (
        TrainConfig,
        calibration_records,
        items_from_rows,
        load_checkpoint,
        save_checkpoint,
        train_model,
    )

    output.mkdir(parents=True, exist_ok=False)
    records = data["records"]
    training = [r for r in records if r["split"] == "train"]
    validation = [r for r in records if r["split"] == "validation"]
    holdout = [r for r in records if r["split"] == "holdout"]
    train_config = TrainConfig(
        epochs=epochs,
        micro_batch=2,
        grad_accum=2,
        loss="soft-ce",
        freeze_encoder=True,
        shuffle_options=("choice",),
        seed=42,
        calib_frac=0,
        amp=False,
        gradient_checkpointing=False,
        log_every=5,
    )
    baseline = LayaClassifier(model, device=device)
    base_identity = baseline.identity
    # Validation only before training; holdout is evaluated once after checkpoint creation.
    baseline_validation = evaluate(baseline, validation, rules)
    del baseline
    gc.collect()
    network, tokenizer, config = load_checkpoint(str(model.resolve()))
    max_len, head_len = config["max_len"], config["head_max_len"]
    items, skipped = items_from_rows(tokenizer, training_rows(training, rules), max_len, head_len)
    if skipped or len(items) != len(training):
        raise ValueError("Training tokenizer skipped or changed labeled records")
    calibration, skipped = items_from_rows(
        tokenizer, training_rows(validation, rules), max_len, head_len
    )
    if skipped or len(calibration) != len(validation):
        raise ValueError("Validation tokenizer skipped labeled records")
    losses = train_model(
        network, tokenizer, items, train_config, torch.device(device), max_len, head_len
    )
    fitted = fit_temperature_map(
        calibration_records(
            network, tokenizer, calibration, torch.device(device), max_len, head_len
        )
    )
    candidate = output / "candidate"
    config = dict(config, fine_tuned=True, temperature=fitted["temperature"])
    config.pop("temperature_by_options", None)
    if fitted["temperature_by_options"]:
        config["temperature_by_options"] = fitted["temperature_by_options"]
    config["training"] = {
        "scope": "pilot" if pilot else "verified-label-experiment",
        "loss": "soft-ce",
        "freeze_encoder": True,
        "epochs": epochs,
        "manifest_sha256": summary["manifest_sha256"],
    }
    save_checkpoint(network, tokenizer, config, str(candidate))
    del network, tokenizer
    gc.collect()
    baseline = LayaClassifier(model, device=device)
    baseline_holdout = evaluate(baseline, holdout, rules)
    del baseline
    gc.collect()
    adapted = LayaClassifier(candidate, device=device)
    report = {
        "schema_version": 1,
        "scope": "classification on supplied transcriptions; not OCR",
        "dataset": summary,
        "base_checkpoint": base_identity,
        "candidate_checkpoint": adapted.identity,
        "training_source_sha256": digest(
            canonical(
                {
                    p.relative_to(source).as_posix(): digest(p.read_bytes())
                    for p in sorted((source / "laya").rglob("*.py"))
                }
            )
        ),
        "epoch_loss": losses,
        "training_config": asdict(train_config),
        "baseline_validation": baseline_validation,
        "candidate_validation": evaluate(adapted, validation, rules),
        "baseline_holdout": baseline_holdout,
        "candidate_holdout": evaluate(adapted, holdout, rules),
        "temperature_fit_attempted": len(validation) >= 10,
        "confidence_calibrated": False,
        "human_verified_holdout": all(r["label_source"] == "human_verified" for r in holdout),
        "independent_gold_holdout": False,
        "production_promotion": False,
        "auto_accept_enabled": False,
        "limitations": [
            "Draft labels require independent verification."
            if pilot
            else "Production calibration/sign-off remain required.",
            "A small pilot does not establish corpus accuracy.",
            "Transcription errors and page extraction are not evaluated.",
        ],
    }
    (output / "report.json").write_bytes(canonical(report))
    return report
