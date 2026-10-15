"""Iteration runner — automated Bayesian learning loop.

Runs the pipeline multiple times on the same input(s), accumulating
evidence across iterations. After each run, field priors are sharper.
After N iterations, produces a final summary of convergence.

Usage:
    python -m ocr_platform.orchestrator.iterations \\
        --input /data/ward42_pdfs/ \\
        --template configs/ward42_template.json \\
        --iterations 5 \\
        --output runs/iterations/
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from ocr_platform.laya.config import LayaConfig
from ocr_platform.orchestrator.pipeline import SurveyPipeline
from ocr_platform.worker.bayesian import BayesianConfig


def run_iterations(
    input_path: Path,
    template_path: Path,
    output_dir: Path,
    iterations: int = 5,
    device: str = "cpu",
    dpi: int = 200,
    db_path: Path | None = None,
) -> dict:
    """Run N iterations of the pipeline with Bayesian learning.

    Args:
        input_path: PDF/ZIP/image directory to process.
        template_path: Fixed template JSON.
        output_dir: Root output directory (each iteration gets a sub-dir).
        iterations: Number of pipeline runs.
        device: CPU or CUDA device string.
        dpi: Rendering DPI for PDF pages.
        db_path: Shared SQLite DB for cross-iteration priors.

    Returns:
        Summary dict with per-iteration stats and convergence info.
    """
    input_path = Path(input_path)
    template_path = Path(template_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if db_path is None:
        db_path = output_dir / "evidence.db"

    laya_cfg = LayaConfig(device=device)
    bayes_cfg = BayesianConfig(decay=0.1, alpha_min=0.2, prior_default=0.5)

    iteration_results: list[dict] = []
    start_total = time.time()

    for i in range(1, iterations + 1):
        iter_dir = output_dir / f"iter_{i:03d}"
        iter_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n{'=' * 70}")
        print(f">>> ITERATION {i}/{iterations}")
        print(f">>> Output: {iter_dir}")
        print(f"{'=' * 70}")

        t0 = time.time()

        pipeline = SurveyPipeline(
            template_path=template_path,
            db_path=db_path,
            output_dir=iter_dir,
            laya_config=laya_cfg,
            bayesian_config=bayes_cfg,
            dpi=dpi,
            use_hindi_vlm=True,
        )

        result = pipeline.run(input_path, load_priors=(i > 1))
        elapsed = time.time() - t0

        iter_summary = {
            "iteration": i,
            "run_id": result.get("run_id", ""),
            "elapsed_seconds": round(elapsed, 2),
            "stats": result.get("stats", {}),
            "bayesian_priors": result.get("bayesian", {}).get("priors_saved", 0),
            "qa_anomalies": result.get("qa_anomalies", 0),
            "output": result.get("output", {}),
        }
        iteration_results.append(iter_summary)

        print(f"\n  Iteration {i} complete: {elapsed:.1f}s")
        if "error" in result:
            print(f"  WARNING: {result['error']}")

    total_elapsed = time.time() - start_total

    # Convergence summary
    auto_rates = [
        r["stats"].get("auto", 0) / max(r["stats"].get("cells", 1), 1) for r in iteration_results
    ]
    prior_counts = [r["bayesian_priors"] for r in iteration_results]

    summary = {
        "iterations": iterations,
        "total_elapsed_seconds": round(total_elapsed, 2),
        "input": str(input_path),
        "template": str(template_path),
        "db": str(db_path),
        "per_iteration": iteration_results,
        "convergence": {
            "auto_accept_rates": [round(r, 4) for r in auto_rates],
            "prior_field_counts": prior_counts,
            "trend": "improving"
            if len(auto_rates) >= 2 and auto_rates[-1] > auto_rates[0]
            else "stable"
            if len(auto_rates) >= 2 and abs(auto_rates[-1] - auto_rates[0]) < 0.05
            else "degrading",
        },
    }

    summary_path = output_dir / "iteration_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{'=' * 70}")
    print(f">>> ALL {iterations} ITERATIONS COMPLETE ({total_elapsed:.1f}s)")
    print(f">>> Summary: {summary_path}")
    print(f">>> Auto-accept trend: {[f'{r:.1%}' for r in auto_rates]}")
    print(f">>> Prior fields: {prior_counts}")
    print(f">>> Convergence: {summary['convergence']['trend']}")
    print(f"{'=' * 70}")

    return summary


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Run N iterations of the Survey OCR pipeline with Bayesian learning.",
    )
    p.add_argument("--input", type=Path, required=True, help="PDF/ZIP/image directory")
    p.add_argument("--template", type=Path, default=Path("configs/ward42_template.json"))
    p.add_argument("--output", type=Path, default=Path("runs/iterations"))
    p.add_argument("--iterations", type=int, default=5, help="Number of runs (default: 5)")
    p.add_argument("--dpi", type=int, default=200)
    p.add_argument("--device", default="cpu")
    p.add_argument("--db", type=Path, default=None)
    return p


def main() -> int:
    args = parser().parse_args()
    try:
        run_iterations(
            input_path=args.input,
            template_path=args.template,
            output_dir=args.output,
            iterations=args.iterations,
            device=args.device,
            dpi=args.dpi,
            db_path=args.db,
        )
        return 0
    except (ValueError, OSError, ImportError) as exc:
        print(f"Error: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
