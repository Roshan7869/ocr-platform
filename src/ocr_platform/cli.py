"""CLI entry point: ocr-survey."""

from __future__ import annotations

import argparse
from pathlib import Path

from ocr_platform.laya.config import LayaConfig
from ocr_platform.orchestrator.pipeline import SurveyPipeline


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ocr-survey",
        description="WARD-42 Survey OCR Platform — PDF/ZIP → structured household data",
    )
    sub = p.add_subparsers(dest="command", required=True)

    run_cmd = sub.add_parser("run", help="Run full pipeline on PDF/ZIP/image directory")
    run_cmd.add_argument("--input", type=Path, required=True, help="PDF, ZIP, or image directory")
    run_cmd.add_argument("--template", type=Path, default=Path("configs/ward42_template.json"))
    run_cmd.add_argument(
        "--laya-model", type=Path, default=None, help="Optional Laya checkpoint dir"
    )
    run_cmd.add_argument("--output", type=Path, default=Path("runs/survey"))
    run_cmd.add_argument("--dpi", type=int, default=200)
    run_cmd.add_argument("--device", type=str, default="cpu")
    run_cmd.add_argument("--db", type=Path, default=None)

    demo_cmd = sub.add_parser("demo", help="Run synthetic demo")
    demo_cmd.add_argument("--output", type=Path, default=Path("runs/demo"))
    demo_cmd.add_argument("--template", type=Path, default=Path("configs/ward42_template.json"))
    demo_cmd.add_argument("--device", type=str, default="cpu")
    return p


def main() -> int:
    args = parser().parse_args()
    if args.command == "demo":
        _run_demo(args)
    else:
        _run_pipeline(args)
    return 0


def _run_pipeline(args):
    db_path = args.db or args.output / "evidence.db"
    laya_config = LayaConfig(device=args.device)
    pipeline = SurveyPipeline(
        template_path=args.template,
        db_path=db_path,
        output_dir=args.output,
        laya_config=laya_config,
        dpi=args.dpi,
    )
    result = pipeline.run(args.input)
    if result.get("error"):
        print(f"Error: {result['error']}")
        return 2
    return 0


def _run_demo(args):
    """Generate a synthetic form and run the pipeline."""
    from PIL import Image, ImageDraw

    demo_dir = args.output
    demo_dir.mkdir(parents=True, exist_ok=True)
    src = demo_dir / "demo_input"
    src.mkdir(exist_ok=True)

    # Create synthetic form image
    img = Image.new("RGB", (1240, 1754), "white")
    draw = ImageDraw.Draw(img)
    draw.text((130, 100), "WARD-42 HOUSEHOLD SURVEY — DEMO", fill="black")
    draw.text((130, 130), "Ward: 42 | Area: Demo", fill="black")
    # Header row
    for i, key in enumerate(["सी.न.", "नाम", "संबंध", "लिंग", "उम्र", "वैवाहिक", "आय"]):
        x = 130 + i * 90
        draw.rectangle([x, 180, x + 85, 205], fill="lightgray")
        draw.text((x + 5, 185), key, fill="black")
    # One member row
    member_data = ["1", "राम कुमार", "स्वयं", "पुरुष", "35", "विवाहित", "25000"]
    for i, val in enumerate(member_data):
        x = 130 + i * 90
        draw.text((x + 5, 220), val, fill="black")

    form_path = src / "demo_ward42.png"
    img.save(form_path, "PNG")
    print(f"Demo form saved: {form_path}")

    db_path = demo_dir / "evidence.db"
    laya_config = LayaConfig(device=args.device)
    pipeline = SurveyPipeline(
        template_path=args.template,
        db_path=db_path,
        output_dir=demo_dir,
        laya_config=laya_config,
        dpi=200,
    )
    result = pipeline.run(form_path)
    print(f"Demo complete: {result['run_id']}")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
