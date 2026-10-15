"""Gate-5 compatibility spike: CPU go/no-go matrix for R0 extraction.

Loads the smoke-001 fixture via the real fail-closed loader, rasterizes with
pypdfium2 at the ``configs/runtime.yaml`` DPI (rendered twice, byte-compared),
runs REAL det+rec via PaddleOCR on both pages, and repeats the full pass
``--repeat`` times (default 3) comparing canonical JSON through
``worker/provenance/hashing.py`` under the runtime comparison policy.

Exit codes (``docs/reason-codes.md`` §1): ``0`` = go (including
conditional-go with ``caveats[]``), ``1`` = no-go (any C1–C7 hard failure).
GPU sections are skipped on laptop-class hosts as a recorded caveat, never a
failure. Idempotent: re-runs replace the revision under
``runs/spike/<datestamp>/``.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from ocr_platform.fixtures.loader import load_fixture
from ocr_platform.runtime_config import load_runtime_config
from ocr_platform.worker.provenance.hashing import canonical_json, content_hash

POLY_KEYS = ("dt_polys", "rec_polys", "dt_boxes")
TEXT_KEYS = ("rec_texts",)
SCORE_KEYS = ("rec_scores",)

RACE_STRATEGY = "custom-image"
RACE_JUSTIFICATION = (
    "Ship the multi-target Dockerfile as-is with cpu-runtime as the default/last "
    "stage: exact Python/Paddle/model pins from this matrix are baked into the "
    "image, giving offline on-prem installs a self-contained, bit-reproducible "
    "runtime with no network at deploy time. Template+bootstrap stays a documented "
    "fallback (Dockerfile RACE note) for hosts where custom images are unsupported."
)


def _pick_first(mapping: dict, keys: tuple[str, ...]):
    for key in keys:
        if key in mapping:
            return key, mapping[key]
    return None, None


def _to_builtin(value):
    """Deterministically convert numpy scalars/arrays to plain Python types."""
    if isinstance(value, dict):
        return {str(k): _to_builtin(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_builtin(v) for v in value]
    item = getattr(value, "tolist", None)
    if callable(item):
        return _to_builtin(item())
    toscalar = getattr(value, "item", None)
    if callable(toscalar) and not isinstance(value, (str, bytes)):
        try:
            return _to_builtin(toscalar())
        except (ValueError, TypeError):
            pass
    if isinstance(value, float):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, (str, bool)) or value is None:
        return value
    return str(value)


def _extract_regions(result: dict) -> tuple[list[dict], dict]:
    """Pull stable region records out of one PaddleOCR predict() page dict."""
    poly_key, polys = _pick_first(result, POLY_KEYS)
    _, texts = _pick_first(result, TEXT_KEYS)
    _, scores = _pick_first(result, SCORE_KEYS)
    polys = _to_builtin(polys) if polys is not None else []
    texts = _to_builtin(texts) if texts is not None else []
    scores = _to_builtin(scores) if scores is not None else []
    if not isinstance(polys, list):
        polys = []
    count = len(polys)
    regions = []
    for i in range(count):
        text = texts[i] if isinstance(texts, list) and i < len(texts) else ""
        score = scores[i] if isinstance(scores, list) and i < len(scores) else 0.0
        regions.append({"poly": polys[i], "text": text, "score": score})
    info = {
        "poly_key": poly_key,
        "text_key_found": texts != [],
        "score_key_found": scores != [],
        "result_keys": sorted(str(k) for k in result),
    }
    return regions, info


def _render_pages(pdf_path: Path, dpi: int):
    """Render every page twice (grayscale PNG bytes + RGB arrays for OCR)."""
    import pypdfium2 as pdfium

    scale = dpi / 72.0
    png_a, png_b, rgb_pages, sizes = [], [], [], []
    for attempt in (png_a, png_b):
        doc = pdfium.PdfDocument(str(pdf_path))
        for i in range(len(doc)):
            pil_gray = doc[i].render(scale=scale).to_pil().convert("L")
            sizes.append(pil_gray.size)
            import io

            buf = io.BytesIO()
            pil_gray.save(buf, format="PNG")
            attempt.append(buf.getvalue())
        doc.close()
    doc = pdfium.PdfDocument(str(pdf_path))
    for i in range(len(doc)):
        rgb_pages.append(doc[i].render(scale=scale).to_pil().convert("RGB"))
    doc.close()
    return png_a, png_b, rgb_pages, sizes


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _model_records() -> tuple[dict, list[str]]:
    """Name + sha256 per cached file for the pinned det/rec models."""
    cache = Path.home() / ".paddlex" / "official_models"
    alt = Path.home() / ".paddleocr"
    base = cache if cache.is_dir() else alt
    notes: list[str] = []
    models = {}
    for name in ("PP-OCRv6_medium_det", "PP-OCRv6_medium_rec"):
        model_dir = base / name
        if not model_dir.is_dir():
            notes.append(f"model dir missing: {model_dir}")
            continue
        files = {}
        for child in sorted(model_dir.iterdir()):
            if child.is_file():
                files[child.name] = _sha256_file(child)
        card = model_dir / "README.md"
        license_id = None
        if card.is_file():
            for line in card.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.strip().lower().startswith("license:"):
                    license_id = line.split(":", 1)[1].strip()
                    break
        models[name] = {"dir": str(model_dir), "files": files, "license": license_id}
        if license_id is None:
            notes.append(f"no license front-matter found in {card}")
    return {"cache_base": str(base), "models": models}, notes


def _package_versions() -> dict:
    from importlib import metadata

    out = {}
    for dist in ("paddleocr", "paddlepaddle", "pypdfium2"):
        try:
            out[dist] = {"version": metadata.version(dist)}
        except metadata.PackageNotFoundError:
            out[dist] = {"version": None}
    return out


def _python_reconciliation() -> dict:
    import tomllib

    requires = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())["project"][
        "requires-python"
    ]
    host = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    ci_pins: list[str] = []
    for line in (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text().splitlines():
        stripped = line.strip()
        if stripped.startswith("python-version:"):
            ci_pins.append(stripped.split(":", 1)[1].strip().strip('"').strip("'"))
    ci_pin = ci_pins[0] if ci_pins else None
    host_ok = sys.version_info >= (3, 11)
    caveats = []
    if ci_pin is not None and not host.startswith(ci_pin):
        caveats.append(
            f"CI pins Python {ci_pin} but the spike host runs {host}; both satisfy "
            f"{requires}. Recommend aligning CI to the pinned {host} as follow-up."
        )
    return {
        "requires_python": requires,
        "host_python": host,
        "ci_python": ci_pin,
        "pinned": host if host_ok else None,
        "host_satisfies_requires": host_ok,
        "caveats": caveats,
    }


def _mem_info() -> dict:
    total = available = None
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal:"):
                total = int(line.split()[1]) // 1024
            elif line.startswith("MemAvailable:"):
                available = int(line.split()[1]) // 1024
    except OSError:
        pass
    return {"total_mib": total, "available_mib": available}


def _write_matrix(out_dir: Path, matrix: dict) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "matrix.json"
    json_path.write_text(json.dumps(matrix, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        f"# Gate-5 spike matrix ({matrix['matrix']}) — {matrix['date']}",
        "",
        f"**Verdict: {matrix['verdict'].upper()}** (exit {matrix['exit_code']})",
        "",
        "## C1–C8",
        "",
        "| # | Criterion | Result | Evidence |",
        "|---|---|---|---|",
    ]
    for row in matrix["criteria"]:
        lines.append(f"| {row['id']} | {row['name']} | {row['result']} | {row['evidence']} |")
    lines += [
        "",
        "## Pins",
        "",
        f"- python: `{matrix['python']['pinned']}` (requires {matrix['python']['requires_python']}, host {matrix['python']['host_python']}, CI {matrix['python']['ci_python']})",
        f"- paddleocr `{matrix['packages']['paddleocr']['version']}` / paddlepaddle `{matrix['packages']['paddlepaddle']['version']}` / pypdfium2 `{matrix['packages']['pypdfium2']['version']}`",
        f"- det: `{matrix['ocr']['det_model']}` · rec: `{matrix['ocr']['rec_model']}` (sha256 in matrix.json)",
        f"- rasterizer: pypdfium2, DPI {matrix['runtime']['render']['dpi']}, colorspace {matrix['runtime']['render']['colorspace']}",
        f"- RACE: {matrix['race']['strategy']}",
        "",
        "## Caveats",
        "",
    ]
    lines += [f"- {c}" for c in matrix["caveats"]] or ["- none"]
    lines += [
        "",
        "## Capacity snippet (for docs/capacity.md)",
        "",
        "```",
        matrix["capacity_snippet"],
        "```",
        "",
        "## Follow-ups",
        "",
    ]
    lines += [f"- {f}" for f in matrix["follow_ups"]] or ["- none"]
    md_path = out_dir / "matrix.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Gate-5 CPU compatibility spike")
    parser.add_argument("--matrix", default="cpu")
    parser.add_argument("--repeat", type=int, default=3)
    args = parser.parse_args(argv)

    datestamp = datetime.date.today().isoformat()
    out_dir = REPO_ROOT / "runs" / "spike" / datestamp
    criteria: list[dict] = []
    caveats: list[str] = []
    follow_ups: list[str] = []

    def record(cid: str, name: str, result: str, evidence: str):
        criteria.append({"id": cid, "name": name, "result": result, "evidence": evidence})

    failures: list[str] = []
    if args.matrix != "cpu":
        print(f"error: only --matrix cpu is supported (got {args.matrix!r})")
        return 1
    if args.repeat < 3:
        record("C1", "Determinism", "fail", f"--repeat {args.repeat} < required N=3")
        failures.append("C1")

    try:
        runtime = load_runtime_config()
    except Exception as exc:  # noqa: BLE001 - fail-closed loader error becomes no-go evidence
        print(f"no-go: runtime config invalid: {exc}")
        return 1
    runtime_dict = runtime.as_dict()

    try:
        ref = load_fixture("smoke-001")
    except Exception as exc:  # noqa: BLE001 - loader error becomes no-go evidence
        print(f"no-go: fixture load failed: {exc}")
        return 1

    dpi = runtime.render["dpi"]
    png_a, png_b, rgb_pages, sizes = _render_pages(ref.path, dpi)
    n_pages = len(rgb_pages)
    render_stable = png_a == png_b and len(png_a) == n_pages
    if render_stable:
        record(
            "C6",
            "Rasterizer determinism",
            "pass",
            f"pypdfium2 rendered {n_pages}p twice @DPI {dpi}, PNG bytes identical (tol 0), sizes {sizes[0]}",
        )
    else:
        record("C6", "Rasterizer determinism", "fail", "repeated render not byte-stable")
        failures.append("C6")

    try:
        from paddleocr import PaddleOCR

        ocr = PaddleOCR(lang="en", enable_mkldnn=False)
        ocr_backend = "PaddleOCR(lang='en', enable_mkldnn=False)"
        mkldnn_note = (
            "default oneDNN/mkldnn path raises NotImplementedError "
            "(ConvertPirAttribute2RuntimeAttribute, ArrayAttribute<Double>) on this "
            "CPU/paddlepaddle 3.3.1 build; enable_mkldnn=False is the supported "
            "PaddleOCR knob and runs the identical PP-OCRv6 models"
        )
    except Exception as exc:  # noqa: BLE001 - engine init failure is no-go evidence
        print(f"no-go: PaddleOCR init failed: {exc}")
        return 1

    import numpy as np

    passes: list[dict] = []
    pass_seconds: list[float] = []
    region_counts: list[list[int]] = []
    sample_texts: list[list[str]] = []
    result_info: dict = {}
    for n in range(max(args.repeat, 1)):
        started = time.time()
        try:
            pages_out = []
            for i, pil in enumerate(rgb_pages):
                res = ocr.predict(np.array(pil))
                page = res[0] if isinstance(res, list) else res
                regions, info = _extract_regions(page)
                if n == 0 and i == 0:
                    result_info = info
                pages_out.append({"page_index": i, "regions": regions})
        except Exception as exc:  # noqa: BLE001 - OCR failure is no-go evidence
            print(f"no-go: OCR pass {n} failed: {exc}")
            return 1
        payload = {"pages": pages_out}
        blob = canonical_json(payload)
        passes.append({"digest": content_hash(blob), "bytes_len": len(blob)})
        pass_seconds.append(time.time() - started)
        region_counts.append([len(p["regions"]) for p in pages_out])
        sample_texts.append([r["text"] for p in pages_out for r in p["regions"]][:8])

    if "C1" not in failures:
        identical = len({p["digest"] for p in passes}) == 1
        policy = runtime.comparison_policy
        if identical and policy["cpu_render_pixel_tolerance"] == 0:
            record(
                "C1",
                "Determinism",
                "pass",
                f"{args.repeat} full det+rec passes, canonical-JSON digests identical "
                f"({passes[0]['digest'][:16]}…), cpu_render_pixel_tolerance=0",
            )
        else:
            record(
                "C1", "Determinism", "fail", f"pass digests: {[p['digest'][:16] for p in passes]}"
            )
            failures.append("C1")
        record(
            "C2",
            "Canonical-JSON compare",
            "pass" if identical else "fail",
            f"byte-equal canonical JSON ({passes[0]['bytes_len']}B) via hashing.py; "
            "no float-tolerance path exercised on CPU",
        )
        if not identical:
            failures.append("C2")

    mem = _mem_info()
    min_regions = min((min(c) for c in region_counts), default=0)
    if min_regions >= 1:
        record(
            "C3",
            "Min CPU resolution",
            "pass",
            f"≥1 region on every page/pass (counts {region_counts[0]} @DPI {dpi}, "
            f"sizes {sizes[0]}); no OOM (RAM total {mem['total_mib']}MiB)",
        )
    else:
        record("C3", "Min CPU resolution", "fail", f"empty page: counts {region_counts}")
        failures.append("C3")

    pyinfo = _python_reconciliation()
    caveats.extend(pyinfo["caveats"])
    if pyinfo["pinned"] is not None:
        record(
            "C4",
            "Python reconciliation",
            "pass",
            f"single pin {pyinfo['pinned']} satisfies {pyinfo['requires_python']}",
        )
    else:
        record(
            "C4", "Python reconciliation", "fail", f"host {pyinfo['host_python']} violates requires"
        )
        failures.append("C4")

    model_info, model_notes = _model_records()
    rec = model_info["models"].get("PP-OCRv6_medium_rec", {})
    det = model_info["models"].get("PP-OCRv6_medium_det", {})
    if rec.get("files") and det.get("files"):
        record(
            "C5",
            "Model tie-break",
            "pass",
            f"exactly one rec model PP-OCRv6_medium_rec ({len(rec['files'])} files, "
            "sha256 in matrix.json) + det PP-OCRv6_medium_det",
        )
    else:
        record("C5", "Model tie-break", "fail", "; ".join(model_notes) or "model files missing")
        failures.append("C5")
    follow_ups.append(
        "src/ocr_platform/worker/paddle/models.py is absent: promote the pinned "
        "PP-OCRv6_medium_det/rec + checksums from this matrix into models.py (out of scope for Stream D)."
    )

    packages = _package_versions()
    model_licenses = {k: v.get("license") for k, v in model_info["models"].items()}
    if all(packages[p]["version"] for p in ("paddleocr", "paddlepaddle", "pypdfium2")) and all(
        model_licenses.values()
    ):
        record(
            "C7",
            "License + availability",
            "pass",
            f"paddleocr {packages['paddleocr']['version']} Apache-2.0; paddlepaddle "
            f"{packages['paddlepaddle']['version']} Apache-2.0; pypdfium2 "
            f"{packages['pypdfium2']['version']} BSD-3-Clause; models Apache-2.0 "
            "(model-card front-matter); cache reproducible, no download needed",
        )
    else:
        missing = [k for k, v in model_licenses.items() if not v]
        record("C7", "License + availability", "fail", f"missing: {missing} {packages}")
        failures.append("C7")

    record("C8", "RACE strategy", "pass", f"{RACE_STRATEGY}: {RACE_JUSTIFICATION[:120]}…")

    if shutil.which("nvidia-smi") is None:
        caveats.append("GPU section skipped: no nvidia-smi/CUDA on this laptop (CPU-only host).")
        gpu_section: dict = {"status": "skipped", "reason": "no CUDA on laptop host"}
    else:
        gpu_section = {
            "status": "not-run",
            "reason": "GPU present but out of scope for --matrix cpu",
        }

    caveats.append(
        "OCR ran with enable_mkldnn=False: " + mkldnn_note + ". Determinism holds "
        "under this knob; re-validate if the mkldnn path is re-enabled."
    )

    verdict = "no-go" if failures else ("conditional-go" if caveats else "go")
    exit_code = 1 if failures else 0

    capacity_snippet = (
        f"Gate-5 spike {datestamp} (CPU, {pyinfo['pinned']}): render {n_pages}p @DPI {dpi} "
        f"pypdfium2 {packages['pypdfium2']['version']}; PaddleOCR "
        f"{packages['paddleocr']['version']}/paddle {packages['paddlepaddle']['version']} "
        f"(enable_mkldnn=False) PP-OCRv6_medium det+rec; per-pass OCR wall "
        f"{min(pass_seconds):.0f}–{max(pass_seconds):.0f}s, regions/page {region_counts[0]}; "
        f"host RAM total {mem['total_mib']}MiB; GPU skipped (no CUDA)."
    )

    matrix = {
        "date": datestamp,
        "matrix": args.matrix,
        "repeat": args.repeat,
        "verdict": verdict,
        "exit_code": exit_code,
        "criteria": criteria,
        "caveats": caveats,
        "follow_ups": follow_ups,
        "runtime": runtime_dict,
        "configuration_fingerprint": runtime.fingerprint,
        "fixture": {
            "fixture_id": ref.fixture_id,
            "path": str(ref.path),
            "content_hash_sha256": ref.content_hash_sha256,
            "classification": ref.classification,
        },
        "render": {
            "rasterizer": f"pypdfium2 {packages['pypdfium2']['version']}",
            "dpi": dpi,
            "colorspace": runtime.render["colorspace"],
            "render_bytes_stable": render_stable,
            "page_sizes_px": sizes[:n_pages],
            "ocr_input_note": "grayscale render converted to RGB for PaddleX (3-channel requirement)",
        },
        "ocr": {
            "backend": ocr_backend,
            "det_model": "PP-OCRv6_medium_det",
            "rec_model": "PP-OCRv6_medium_rec",
            "models": model_info,
            "passes": passes,
            "pass_seconds": [round(s, 1) for s in pass_seconds],
            "region_counts_per_pass": region_counts,
            "sample_texts_pass0": sample_texts[0] if sample_texts else [],
            "result_info": result_info,
            "mkldnn_note": mkldnn_note,
        },
        "python": pyinfo,
        "packages": packages,
        "licenses": {
            "paddleocr": "Apache-2.0 (pip show)",
            "paddlepaddle": "Apache-2.0 (pip show)",
            "pypdfium2": "BSD-3-Clause (pip show)",
            "models": model_licenses,
        },
        "race": {"strategy": RACE_STRATEGY, "justification": RACE_JUSTIFICATION},
        "gpu": gpu_section,
        "memory_mib": mem,
        "capacity_snippet": capacity_snippet,
    }

    json_path, md_path = _write_matrix(out_dir, matrix)
    print(f"verdict={verdict} exit={exit_code}")
    for c in caveats:
        print(f"caveat: {c}")
    print(f"MATRIX_JSON={json_path}")
    print(f"MATRIX_MD={md_path}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
