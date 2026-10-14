#!/usr/bin/env python3
"""
kaggle_run.py — Survey OCR Pipeline for Kaggle GPU
====================================================
Runs the full pipeline on all Ward-42 PDFs.

Kaggle setup:
  1. Upload this script to a Kaggle notebook (code cell or file)
  2. Ensure the PDF dataset is attached (rk9098/ward42-surveys)
  3. Set Accelerator → GPU T4 x2
  4. Run all cells

Outputs (in /kaggle/working/output/):
  - ocr_results.csv          — human-approved/auto-accepted values only
  - ocr_observations.csv     — OCR observations and review status
  - evidence.db              — full SQLite provenance store
  - documents/               — per-PDF JSON outputs
  - run_manifest.json        — run metadata
"""

from __future__ import annotations

import os, sys, json, time, csv
import subprocess
from pathlib import Path
from datetime import datetime

# ============================================================
# CONFIG
# ============================================================
KAGGLE = True  # set False for local testing

if KAGGLE:
    PDF_ROOT   = Path("/kaggle/input/ward42-surveys")
    WORK_ROOT  = Path("/kaggle/working")
    CODE_ROOT  = Path("/kaggle/input/ocr-platform-code")  # must be added as input
else:
    PDF_ROOT   = Path("/home/roshan/ocr-platform/WARD-42")
    WORK_ROOT  = Path("/home/roshan/ocr-platform/runs")
    CODE_ROOT  = Path("/home/roshan/ocr-platform")

sys.path.insert(0, str(CODE_ROOT / "src"))

TEMPLATE   = CODE_ROOT / "configs" / "ward42_template.json"
OUT_DIR    = WORK_ROOT / "output"
DB_PATH    = OUT_DIR / "evidence.db"
CSV_PATH   = OUT_DIR / "ocr_results.csv"
OBSERVATIONS_CSV_PATH = OUT_DIR / "ocr_observations.csv"
DOCS_DIR   = OUT_DIR / "documents"
MANIFEST   = OUT_DIR / "run_manifest.json"

for d in [OUT_DIR, DOCS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

DPI        = 150  # lower for speed on T4; 200 for quality
HINDI_VLM  = True  # set False to skip MS-SWIFT inference

os.environ["USE_HINDI_VLM"] = "1" if HINDI_VLM else "0"
# Attach the FormLens/HindiOCR-VLM LoRA checkpoint as a Kaggle Dataset and set
# this variable to its local directory. The base GOT model is downloaded once
# into the Kaggle cache or can also be attached as an input dataset.
os.environ.setdefault("HINDI_VLM_BASE_MODEL", "stepfun-ai/GOT-OCR2_0")
os.environ.setdefault("HINDI_VLM_MAX_PIXELS", "401408")  # T4-safe crop resolution
if HINDI_VLM and os.environ.get("HINDI_VLM_ADAPTER_DIR"):
    print(f"[VLM] LoRA adapter: {os.environ['HINDI_VLM_ADAPTER_DIR']}")
if HINDI_VLM:
    adapter_dir = Path(os.environ.get("HINDI_VLM_ADAPTER_DIR", ""))
    if not adapter_dir.is_dir():
        raise RuntimeError(
            "HINDI_VLM=1 requires a mounted FormLens/Hindi-VLM LoRA adapter. "
            "Set HINDI_VLM_ADAPTER_DIR to the adapter directory, or set HINDI_VLM=0 "
            "to run the PaddleOCR-only review pipeline."
        )

# ============================================================
# DEPENDENCY INSTALL
# ============================================================
print("[SETUP] Installing dependencies...")
subprocess.run(
    [sys.executable, "-m", "pip", "install", "-q",
     "pypdfium2", "rapidfuzz", "Pillow", "pandas", "numpy"],
    check=True
)
subprocess.run(
    [sys.executable, "-m", "pip", "install", "-q",
     "paddlepaddle-gpu", "paddleocr",
     "opencv-contrib-python", "transformers", "accelerate"],
    check=True
)
# MS-SWIFT (for Hindi VLM) — may already be cached
if HINDI_VLM:
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", "ms-swift"],
        check=True
    )

print("[SETUP] Dependencies installed.\n")

# ============================================================
# VERIFY GPU
# ============================================================
gpu_check = subprocess.run(["nvidia-smi", "-L"], capture_output=True, text=True)
if gpu_check.returncode == 0:
    print(f"[GPU] {gpu_check.stdout.strip()}\n")
else:
    print("[WARNING] No GPU! This will be very slow.\n")

# ============================================================
# DISCOVER PDFs
# ============================================================
pdfs = sorted(PDF_ROOT.rglob("*.pdf"))
print(f"[PDFs] Found {len(pdfs)} PDFs in {PDF_ROOT}")
for p in pdfs[:5]:
    print(f"       {p.relative_to(PDF_ROOT)}")
if len(pdfs) > 5:
    print(f"       ... and {len(pdfs) - 5} more")
print()

# ============================================================
# RUN PIPELINE
# ============================================================
from ocr_platform.orchestrator.pipeline import SurveyPipeline

FIELDNAMES = [
    "doc_id", "page_index", "row_idx", "sr_no", "member_name", "relation", "gender", "age",
    "marital_status", "religion", "caste", "caste_category", "education", "occupation",
    "monthly_income", "bank_account", "resident_code", "migration_nature", "remarks",
]


def result_rows(result: dict) -> tuple[list[dict], list[dict]]:
    """Flatten page-aware pipeline results into canonical and review-safe CSV rows."""
    accepted_rows: list[dict] = []
    observation_rows: list[dict] = []
    for document in result.get("documents", []):
        for member in document.get("members", []):
            row = {
                "doc_id": document["doc_id"],
                "page_index": document["page_index"],
                "row_idx": member["row_idx"],
            }
            observation = dict(row)
            row_is_accepted = True
            for field in FIELDNAMES[3:]:
                field_result = member.get("fields", {}).get(field, {})
                disposition = field_result.get("disposition", "review")
                observed = field_result.get("observed_value", "")
                final_value = field_result.get("final_value", "")
                row[field] = final_value if disposition == "accepted" and final_value is not None else ""
                observation[field] = observed
                observation[f"{field}__disposition"] = disposition
                observation[f"{field}__confidence"] = field_result.get("confidence", "")
                row_is_accepted = row_is_accepted and disposition == "accepted"
            observation_rows.append(observation)
            if row_is_accepted:
                accepted_rows.append(row)
    return accepted_rows, observation_rows

pipeline = SurveyPipeline(
    template_path=str(TEMPLATE),
    db_path=str(DB_PATH),
    output_dir=str(DOCS_DIR),
    dpi=DPI,
    use_hindi_vlm=HINDI_VLM,
)

results = []
observations = []
t0 = time.time()
errors = []

for i, pdf_path in enumerate(pdfs):
    doc_id = pdf_path.stem
    print(f"\n{'='*60}")
    print(f"[{i+1}/{len(pdfs)}] {doc_id}")
    print(f"{'='*60}")

    try:
        result = pipeline.run(pdf_path)

        accepted_rows, observed_rows = result_rows(result)
        results.extend(accepted_rows)
        observations.extend(observed_rows)

        print(f"  ✓ Members: {result.get('members_extracted', 0)} | "
              f"Anomalies: {len(result.get('qa_anomalies', []))}")

    except Exception as e:
        print(f"  ✗ ERROR: {e}")
        errors.append({"doc_id": doc_id, "error": str(e)})

elapsed = time.time() - t0
print(f"\n{'='*60}")
print(f"COMPLETE: {len(pdfs) - len(errors)}/{len(pdfs)} PDFs in {elapsed:.1f}s ({elapsed/60:.1f}min)")
print(f"Errors: {len(errors)}")
print(f"Total members extracted: {len(results)}")
print(f"{'='*60}")

# ============================================================
# WRITE CSV
# ============================================================
with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(results)

print(f"\n[CSV] {CSV_PATH} ({len(results)} rows)")
observation_fieldnames = FIELDNAMES + [
    f"{field}__{suffix}" for field in FIELDNAMES[3:] for suffix in ("disposition", "confidence")
]
with open(OBSERVATIONS_CSV_PATH, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=observation_fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(observations)
print(f"[CSV] {OBSERVATIONS_CSV_PATH} ({len(observations)} rows; review-safe observations)")

# ============================================================
# WRITE MANIFEST
# ============================================================
manifest = {
    "run_id": f"kaggle_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
    "timestamp": datetime.utcnow().isoformat() + "Z",
    "total_pdfs": len(pdfs),
    "successful": len(pdfs) - len(errors),
    "errors": len(errors),
    "total_members": len(observations),
    "accepted_members": len(results),
    "elapsed_seconds": round(elapsed, 1),
    "elapsed_minutes": round(elapsed/60, 1),
    "dpi": DPI,
    "hindi_vlm": HINDI_VLM,
    "pdf_root": str(PDF_ROOT),
    "error_list": errors,
}

with open(MANIFEST, "w") as f:
    json.dump(manifest, f, indent=2, default=str)

print(f"[MANIFEST] {MANIFEST}")
print("\nDone! Download output folder from Kaggle.")
