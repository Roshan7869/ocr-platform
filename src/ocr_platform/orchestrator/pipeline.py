"""SurveyPipeline — fully wired orchestrator.

Modules in order:
  M01 DocumentLoader       → load PDF/ZIP/image pages
  M02 TemplateSlicer       → slice using fixed template dividers (no warping)
  M03 TieredOCR            → PaddleOCR hi + en + HindiVLM + IndicOCR
  M04 Morphology           → GeometryProfile for Laya L1 + VLM routing
  M05 Normalizer           → Unicode NFC, digits, phone, income, date, education
  M06 SemanticEngine       → closed-vocab snapping + ditto DAG
  M07 Arbiter              → best candidate selection
  Laya L1-L4               → per-cell Bayesian decision
  Laya L5                  → per-household QA
  M09 EvidenceStore        → SQLite provenance + Bayesian priors
  M10 ExportEngine         → single-document JSON + CSV per PDF
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from itertools import pairwise
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from ocr_platform.document.loader import DocumentLoader
from ocr_platform.export.writer import ExportEngine
from ocr_platform.laya.config import LayaConfig
from ocr_platform.laya.pipeline import LayaPipeline
from ocr_platform.observability import (
    emit_field_decision,
    emit_run_complete,
    emit_run_errored,
    emit_run_start,
)
from ocr_platform.worker.arbiter import Arbiter
from ocr_platform.worker.bayesian import BayesianConfig, BayesianScorer
from ocr_platform.worker.hindi_vlm import HindiVLMEngine
from ocr_platform.worker.morphology import ContourMorphologyEngine
from ocr_platform.worker.normalizer import SpatialNormalizer
from ocr_platform.worker.provenance.store import EvidenceStore
from ocr_platform.worker.semantic import SemanticEngine
from ocr_platform.worker.validation.qa import RelationalQA, parse_int_or_none

# 18 member-table columns (fixed by template)
COL_KEYS = [
    "sr_no",
    "member_name",
    "relation",
    "gender",
    "age",
    "marital_status",
    "marriage_age",
    "religion",
    "caste",
    "caste_category",
    "education",
    "occupation",
    "employment_nature",
    "monthly_income",
    "bank_account",
    "resident_code",
    "migration_nature",
    "remarks",
]

CLOSED_VOCAB_FIELDS = {
    "gender",
    "relation",
    "religion",
    "marital_status",
    "caste_category",
    "resident_code",
    "marriage_age",
    "bank_account",
}

EN_FIELDS = {
    "enumerator_name",
    "enumerator_mobile",
    "head_name",
    "head_mobile",
    "member_name",
    "monthly_income",
    "education",
    "survey_date",
    "occupation",
    "employment_nature",
}


class SurveyPipeline:
    """Fully wired pipeline: PDF/ZIP/images → per-document JSON + CSV.

    Template-constrained: loads fixed dividers from template.json, slices
    rendered pages directly without homography. Bayesian scores accumulate
    across runs in the evidence DB.
    """

    def __init__(
        self,
        template_path: Path | str,
        db_path: Path | str,
        output_dir: Path | str,
        laya_config: LayaConfig | None = None,
        bayesian_config: BayesianConfig | None = None,
        dpi: int = 200,
        use_hindi_vlm: bool = True,
        allow_auto_accept: bool = False,
    ):
        self.template_path = Path(template_path)
        self.db_path = Path(db_path)
        self.output_dir = Path(output_dir)
        self.dpi = dpi
        self.allow_auto_accept = allow_auto_accept

        # Laya pipeline
        self.laya = LayaPipeline(laya_config)

        # Bayesian scorer — loads priors from previous runs on first use
        self.bayesian = BayesianScorer(bayesian_config)

        # Workers
        self.loader = DocumentLoader(dpi=dpi)
        self.morphology = ContourMorphologyEngine()
        self.normalizer = SpatialNormalizer()
        self.semantic = SemanticEngine()
        self.arbiter = Arbiter()
        self.qa = RelationalQA(self.db_path)
        self.store = EvidenceStore(self.db_path)
        self.export = ExportEngine(self.db_path, self.output_dir)

        # OCR engines (lazy init)
        self._paddle = None
        self._paddle_en = None
        self._swift_engine = HindiVLMEngine() if use_hindi_vlm else None
        self._indic = None

        # Load fixed template
        with open(self.template_path) as f:
            tpl = json.load(f)
        self.template = tpl
        self._validate_template_layout(tpl, "root")
        self.tpl_W, self.tpl_H = tpl["page_size"]
        self.row_divs = [int(x) for x in tpl["row_dividers"]]
        self.col_divs_top = [int(x) for x in tpl["column_dividers_top"]]
        self.col_divs_bottom = [int(x) for x in tpl["column_dividers_bottom"]]
        self.header_fields = {k: v for k, v in tpl.get("fields", {}).items()}
        self.member_table_cols = tpl.get("member_table_cols", COL_KEYS)
        self.members_start_row = tpl.get("members_start_row", 9)
        self.header_rows = tpl.get("header_rows", 5)

    # ------------------------------------------------------------------
    # OCR initialization
    # ------------------------------------------------------------------

    def _init_paddle(self):
        if self._paddle is not None:
            return
        try:
            from paddleocr import PaddleOCR

            os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
            # PaddleOCR 3.x: 'hi' for Hindi; falls back to multilingual.
            # enable_mkldnn=False: the default oneDNN path raises
            # NotImplementedError on CPU/paddlepaddle 3.3.1 (spike caveat);
            # this is the supported knob, same PP-OCRv6 models.
            try:
                self._paddle = PaddleOCR(use_angle_cls=False, lang="hi", enable_mkldnn=False)
            except Exception:  # noqa: BLE001 - PaddleOCR lang init raises varied errors; fallback to multilingual
                self._paddle = PaddleOCR(
                    use_angle_cls=False, lang="multilingual", enable_mkldnn=False
                )
            print("  [M03] PaddleOCR hin ready.")
        except Exception as e:  # noqa: BLE001 - optional OCR backend may fail init arbitrarily; pipeline degrades to review-only
            # Memoize an unavailable backend so every crop does not retry
            # model discovery/initialization. The pipeline remains review-only.
            self._paddle = False
            print(f"  [M03] PaddleOCR hin init failed: {e}")

    def _init_paddle_en(self):
        if self._paddle_en is not None:
            return
        try:
            from paddleocr import PaddleOCR

            self._paddle_en = PaddleOCR(use_angle_cls=False, lang="en", enable_mkldnn=False)
            print("  [M03] PaddleOCR en ready.")
        except Exception as e:  # noqa: BLE001 - optional OCR backend may fail init arbitrarily; pipeline degrades to review-only
            self._paddle_en = False
            print(f"  [M03] PaddleOCR en init failed: {e}")

    def _init_indic(self):
        if self._indic is not None:
            return
        try:
            from transformers import AutoModelForVision2Seq, AutoProcessor

            print("  [M03] Loading IndicOCR...")
            p = AutoProcessor.from_pretrained("bodhan-ai/indic-ocr", trust_remote_code=True)
            m = AutoModelForVision2Seq.from_pretrained(
                "bodhan-ai/indic-ocr", trust_remote_code=True
            )
            self._indic = (p, m)
            print("  [M03] IndicOCR ready.")
        except Exception as e:  # noqa: BLE001 - optional HF backend may fail load arbitrarily; pipeline degrades to review-only
            self._indic = False
            print(f"  [M03] IndicOCR unavailable: {e}")

    # ------------------------------------------------------------------
    # OCR dispatch — tiered, morphology-aware
    # ------------------------------------------------------------------

    def _run_paddle(self, crop: np.ndarray, lang: str = "devanagari") -> dict[str, Any] | None:
        self._init_paddle() if lang == "devanagari" else self._init_paddle_en()
        engine = self._paddle if lang == "devanagari" else self._paddle_en
        if not engine:
            return None
        try:
            # Ensure BGR input for PaddleOCR
            if len(crop.shape) == 3 and crop.shape[2] == 3:
                pass  # already BGR from cv2.imdecode
            padded = cv2.copyMakeBorder(
                crop, 15, 15, 15, 15, cv2.BORDER_CONSTANT, value=(255, 255, 255)
            )
            # PaddleOCR 3.x: predict() takes the image only (no det/rec/cls
            # kwargs); returns per-image page dicts with rec_texts/rec_scores.
            results = engine.predict(padded)
            best_txt, best_conf = "", 0.0
            if results:
                for page_result in results:
                    if isinstance(page_result, dict):
                        texts = page_result.get("rec_texts") or []
                        scores = page_result.get("rec_scores") or []
                        for raw_txt, raw_conf in zip(texts, scores):
                            try:
                                txt = str(raw_txt or "").strip()
                                conf = float(raw_conf)
                            except (TypeError, ValueError):
                                continue
                            if txt and conf > best_conf:
                                best_txt, best_conf = txt, conf
                        continue
                    if not page_result:
                        continue
                    for item in page_result:
                        try:
                            if isinstance(item, (list, tuple)) and len(item) >= 2:
                                txt = (
                                    (item[0] or "").strip()
                                    if isinstance(item[0], str)
                                    else str(item[0]).strip()
                                )
                                conf = float(item[1]) if not isinstance(item[1], str) else 0.0
                            else:
                                continue
                            if conf > best_conf:
                                best_txt, best_conf = txt, conf
                        except (TypeError, ValueError):
                            continue
            if best_txt and best_conf > 0.0:
                return {"value": best_txt, "conf": best_conf, "engine": f"paddle_{lang[:2]}"}
        except Exception as e:  # noqa: BLE001 - per-crop OCR may raise varied cv2/engine errors; crop degrades to no-candidate
            print(f"  [M03] PaddleOCR err: {e}")
        return None

    def _run_paddle_en(self, crop: np.ndarray) -> dict[str, Any] | None:
        return self._run_paddle(crop, lang="en")

    def _run_vlm(self, crop: np.ndarray) -> dict[str, Any] | None:
        """Run HindiOCR-VLM via MS-SWIFT (returns None if unavailable)."""
        if self._swift_engine is None or not self._swift_engine.available:
            return None
        return self._swift_engine.ocr(crop)

    def _run_indic(self, crop: np.ndarray) -> dict[str, Any] | None:
        self._init_indic()
        if not self._indic:
            return None
        proc, model = self._indic
        try:
            from PIL import Image

            padded = cv2.copyMakeBorder(
                crop, 15, 15, 15, 15, cv2.BORDER_CONSTANT, value=(255, 255, 255)
            )
            rgb = cv2.cvtColor(padded, cv2.COLOR_BGR2RGB)
            inp = proc(Image.fromarray(rgb), return_tensors="pt")
            ids = model.generate(**inp, max_new_tokens=256)
            txt = proc.batch_decode(ids, skip_special_tokens=True)[0].strip()
            if txt:
                return {"value": txt, "conf": 0.75, "engine": "indic"}
        except Exception as e:  # noqa: BLE001 - per-crop VLM inference may raise varied errors; crop degrades to no-candidate
            print(f"  [M03] IndicOCR err: {e}")
        return None

    def _resolve_ocr(
        self, cell_id: str, field_key: str, candidates: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Deduplicate candidates and attach a deterministic resolved observation."""
        seen: set[str] = set()
        unique: list[dict[str, Any]] = []
        for candidate in candidates:
            key = str(candidate.get("value", "")).strip().lower()
            if key and key not in seen:
                seen.add(key)
                unique.append(candidate)
        best = max(unique, key=lambda candidate: candidate["conf"]) if unique else None
        return {
            "cell_id": cell_id,
            "field_key": field_key,
            "candidates": unique,
            "resolved": best["value"] if best else "",
            "reason": f"best_{best['engine']}" if best else "all_failed",
        }

    def _dispatch_ocr(
        self,
        cell_id: str,
        field_key: str,
        crop: np.ndarray,
        handwriting: bool,
        include_vlm: bool = True,
    ) -> dict[str, Any]:
        """Tiered OCR dispatch: Hindi → English (for Latin fields) → VLM → IndicOCR."""
        candidates: list[dict[str, Any]] = []

        # Tier 1: Hindi OCR (always)
        p = self._run_paddle(crop, lang="devanagari")
        if p:
            candidates.append(p)

        # Tier 2: English OCR for Latin-mixed fields
        if field_key in EN_FIELDS:
            en = self._run_paddle_en(crop)
            if en:
                candidates.append(en)

        # Tier 3: Hindi VLM for handwriting or low-confidence
        if include_vlm and (
            handwriting or not candidates or all(c["conf"] < 0.85 for c in candidates)
        ):
            v = self._run_vlm(crop)
            if v:
                candidates.append(v)

        # Tier 4: IndicOCR last resort
        if candidates and all(c["conf"] < 0.85 for c in candidates):
            ind = self._run_indic(crop)
            if ind:
                candidates.append(ind)

        return self._resolve_ocr(cell_id, field_key, candidates)

    # ------------------------------------------------------------------
    # Template-constrained slicing (no homography warping)
    # ------------------------------------------------------------------

    def _layout_for_page(self, page_index: int) -> dict[str, Any] | None:
        """Return the explicitly configured layout for a page.

        A legacy template describes page zero only. Applying its grid to a
        different form page is data corruption, so unconfigured pages are
        deliberately withheld for review.
        """
        layouts = self.template.get("page_layouts")
        if layouts is None:
            return self.template if page_index == 0 else None
        override = layouts.get(str(page_index)) or layouts.get(page_index)
        if override is None:
            return None
        layout = {key: value for key, value in self.template.items() if key != "page_layouts"}
        layout.update(override)
        self._validate_template_layout(layout, f"page_layouts[{page_index}]")
        return layout

    @staticmethod
    def _validate_template_layout(layout: dict[str, Any], name: str) -> None:
        """Reject layouts that would create invalid or silently clipped crops."""
        try:
            width, height = (int(value) for value in layout["page_size"])
            row_divs = [int(value) for value in layout["row_dividers"]]
            top_divs = [int(value) for value in layout["column_dividers_top"]]
            bottom_divs = [int(value) for value in layout["column_dividers_bottom"]]
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Template {name} is missing a valid grid definition") from exc

        grids = {
            "row_dividers": (row_divs, height),
            "column_dividers_top": (top_divs, width),
            "column_dividers_bottom": (bottom_divs, width),
        }
        for field, (dividers, dimension) in grids.items():
            if len(dividers) < 2:
                raise ValueError(f"Template {name}.{field} needs at least two dividers")
            if dividers[0] != 0 or any(right <= left for left, right in pairwise(dividers)):
                raise ValueError(
                    f"Template {name}.{field} must start at zero and be strictly increasing"
                )
            if dividers[-1] > dimension:
                raise ValueError(
                    f"Template {name}.{field} ends at {dividers[-1]}, beyond page dimension {dimension}"
                )

    def _slice_cells(
        self, img_bgr: np.ndarray, doc_id: str, page_index: int
    ) -> list[dict[str, Any]]:
        """Slice rendered page using template dividers.

        Dividers are in template pixel space (self.tpl_W × self.tpl_H).
        Scale them to the rendered page size if they don't match.
        """
        layout = self._layout_for_page(page_index)
        if layout is None:
            return []
        h_img, w_img = img_bgr.shape[:2]
        template_width, template_height = layout.get("page_size", self.template["page_size"])
        sx = w_img / template_width
        _sy = h_img / template_height

        def scale(val: int) -> int:
            return round(val * sx)

        rois: list[dict[str, Any]] = []
        row_divs = [int(value) for value in layout["row_dividers"]]
        col_divs_top = [int(value) for value in layout["column_dividers_top"]]
        col_divs_bottom = [int(value) for value in layout["column_dividers_bottom"]]
        header_rows = int(layout.get("header_rows", self.header_rows))
        header_fields = layout.get("fields", {})
        member_table_cols = layout.get("member_table_cols", self.member_table_cols)
        n_rows = len(row_divs)

        for ri in range(1, n_rows):
            y1 = scale(row_divs[ri - 1])
            y2 = scale(row_divs[ri])
            if y2 - y1 < 5:
                continue

            # Choose column grid based on whether this is a header or member row
            if ri <= header_rows:
                col_divs = col_divs_top
                is_header = True
            else:
                col_divs = col_divs_bottom
                is_header = False

            for ci in range(1, len(col_divs)):
                x1 = scale(col_divs[ci - 1])
                x2 = scale(col_divs[ci])
                if x2 - x1 < 10:
                    continue

                # Clamp to image bounds
                cx1, cy1 = max(0, x1 + 4), max(0, y1 + 4)
                cx2, cy2 = min(w_img, x2 - 4), min(h_img, y2 - 4)
                if cx2 <= cx1 or cy2 <= cy1:
                    continue

                crop = img_bgr[cy1:cy2, cx1:cx2]
                if crop.size == 0:
                    continue

                sha = hashlib.sha256(cv2.imencode(".png", crop)[1].tobytes()).hexdigest()[:16]

                # Assign field key
                if is_header:
                    # Map header cells using template field config
                    fk = self._map_header_field(ri, ci, header_fields, page_index)
                else:
                    fk = self._map_member_field(ci, member_table_cols)

                rois.append(
                    {
                        "cell_id": f"p{page_index}_r{ri}_c{ci}_{sha}",
                        "page_index": page_index,
                        "row_idx": ri,
                        "col_idx": ci,
                        "field_key": fk,
                        "is_header": is_header,
                        "crop_bgr": crop,
                        "sha256": sha,
                        "box": [cx1, cy1, cx2, cy2],
                        "doc_id": doc_id,
                    }
                )

        return rois

    def _map_header_field(
        self,
        ri: int,
        ci: int,
        fields: dict[str, Any] | None = None,
        page_index: int = 0,
    ) -> str:
        """Map header cell position to field key using template config.

        Template field keys use 0-indexed column positions (col=0 → first data column).
        ci is 1-indexed interior column index (ci=1 → first data column).
        """
        for fk, cfg in (fields if fields is not None else self.header_fields).items():
            configured_page = cfg.get("page")
            # Existing templates use 1-indexed page numbers; accept a zero-
            # indexed value too so per-page layouts do not silently lose
            # their header mappings.
            if configured_page is not None and configured_page not in (page_index, page_index + 1):
                continue
            # row_divs[0] is the top edge; template row=1 → ri=1
            if ri == cfg.get("row", 0) + 1:
                # col=0 → first data column → ci=1
                ci_start = cfg.get("col", 0) + 1
                ci_end = ci_start + cfg.get("col_span", 1)
                if ci_start <= ci < ci_end:
                    return fk
        return f"hdr_r{ri}_c{ci}"

    def _map_member_field(self, ci: int, member_table_cols: list[str] | None = None) -> str:
        """Map member table column index to field key."""
        # column_dividers_bottom has N+1 entries for N columns
        # ci starts at 1 (first interior division)
        idx = ci - 1
        columns = member_table_cols if member_table_cols is not None else self.member_table_cols
        if 0 <= idx < len(columns):
            return columns[idx]
        return f"col_{ci}"

    @staticmethod
    def _collect_cell_output(
        cell: dict[str, Any],
        cell_output: dict[str, Any],
        header_fields: dict[str, dict[str, Any]],
        members_by_row: dict[int, dict[str, Any]],
    ) -> None:
        """Preserve every sliced field, including unreadable/blank cells."""
        if cell["is_header"]:
            header_fields[cell["field_key"]] = cell_output
            return
        row_idx = cell["row_idx"]
        members_by_row.setdefault(row_idx, {"row_idx": row_idx, "fields": {}})
        members_by_row[row_idx]["fields"][cell["field_key"]] = cell_output

    # ------------------------------------------------------------------
    # Full pipeline run
    # ------------------------------------------------------------------

    def run(self, source: Path | str, load_priors: bool = True) -> dict[str, Any]:
        """Run full pipeline on *source* (PDF, ZIP, or image directory).

        Args:
            source: Input path (PDF, ZIP, or image directory).
            load_priors: If True, load Bayesian priors from previous runs in the DB.

        Returns:
            Run summary dict with run_id, stats, output paths.
        """
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        source = Path(source)
        run_wall_start = time.time()
        emit_run_start(run_id=run_id)

        print("=" * 70)
        print(f">>> SURVEY OCR PIPELINE — {run_id}")
        print(f">>> Input: {source}")
        print(f">>> Template: {self.template_path}")
        print("=" * 70)

        # Do not treat previous OCR confidence as supervision. Historical score
        # learning remains disabled until verified corrections feed calibration.
        if load_priors:
            print("  [BAYES] Historical unverified priors disabled; review-first mode")

        # M01: Load documents
        pages = self.loader.load(source)
        if not pages:
            print("No pages loaded. Check input.")
            emit_run_errored(run_id=run_id, reason_code="EMPTY_DOCUMENT")
            return {"run_id": run_id, "error": "no_pages"}

        self.store.start_run(run_id, doc_count=len(pages))
        stats: dict[str, int] = {
            "docs": 0,
            "pages": 0,
            "cells": 0,
            "auto": 0,
            "low_conf": 0,
            "qa_flags": 0,
        }

        household_outputs: list[dict[str, Any]] = []
        all_qa_anomalies: list[dict[str, Any]] = []
        page_errors: list[dict[str, Any]] = []
        _prev_doc_id: str | None = None

        for page in pages:
            doc_id = page.doc_id

            # Reset document-scoped state when moving to a new document.
            if doc_id != _prev_doc_id:
                self.semantic = SemanticEngine()
                self.bayesian.reset()
                _prev_doc_id = doc_id
            print(f"\n--- [{doc_id}] page {page.page_index + 1} ---")

            # Decode page image
            img = cv2.imdecode(np.frombuffer(page.image_bytes, np.uint8), cv2.IMREAD_COLOR)
            if img is None:
                print("  Cannot decode image. Skipping.")
                continue

            # M02: Template-constrained slice (no homography)
            rois = self._slice_cells(img, doc_id, page.page_index)
            if not rois:
                reason = (
                    "unsupported_page_layout"
                    if self._layout_for_page(page.page_index) is None
                    else "no_cells_sliced"
                )
                page_errors.append(
                    {"doc_id": doc_id, "page_index": page.page_index, "reason": reason}
                )
                print(f"  No cells sliced: {reason}.")
                continue

            print(f"  [M02] {len(rois)} cells sliced")

            # Save crops
            crop_dir = self.output_dir / "crops" / doc_id / f"p{page.page_index + 1:02d}"
            crop_dir.mkdir(parents=True, exist_ok=True)
            for r in rois:
                p = crop_dir / f"{r['sha256']}.png"
                cv2.imwrite(str(p), r["crop_bgr"], [cv2.IMWRITE_PNG_COMPRESSION, 3])
                r["crop_path"] = str(p)

            stats["pages"] += 1

            # Group cells by row for household extraction
            members_by_row: dict[int, dict[str, Any]] = {}
            header_fields: dict[str, dict[str, Any]] = {}

            t0 = time.time()

            prepared_cells: list[dict[str, Any]] = []
            vlm_pending: list[dict[str, Any]] = []
            for cell in rois:
                crop = cell["crop_bgr"]
                fk = cell["field_key"]
                cell_id = cell["cell_id"]
                geo = self.morphology.analyze(cell_id, crop, fk)
                # Laya L1 consumes the same morphology result used for OCR
                # routing. Without this, it sees zero-valued placeholder
                # features and can contradict the actual glyph classification.
                cell["geometry"] = geo.model_dump()
                handwriting = geo.glyph_type in ("handwritten", "stroke")
                # First pass stays fast and local; VLM candidates are batched
                # below so the GOT model is not reloaded for each cell.
                ocr_res = self._dispatch_ocr(
                    cell_id, fk, crop, handwriting=handwriting, include_vlm=False
                )
                item = {"cell": cell, "geo": geo, "ocr_res": ocr_res, "handwriting": handwriting}
                prepared_cells.append(item)
                if (
                    handwriting
                    or not ocr_res["candidates"]
                    or all(candidate["conf"] < 0.85 for candidate in ocr_res["candidates"])
                ):
                    vlm_pending.append(item)

            if vlm_pending and self._swift_engine is not None and self._swift_engine.available:
                vlm_results = self._swift_engine.ocr_many(
                    [item["cell"]["crop_bgr"] for item in vlm_pending]
                )
                for item, candidate in zip(vlm_pending, vlm_results):
                    if candidate:
                        item["ocr_res"] = self._resolve_ocr(
                            item["cell"]["cell_id"],
                            item["cell"]["field_key"],
                            item["ocr_res"]["candidates"] + [candidate],
                        )

            for item in prepared_cells:
                cell = item["cell"]
                geo = item["geo"]
                ocr_res = item["ocr_res"]
                fk = cell["field_key"]
                cell_id = cell["cell_id"]
                glyph_type = geo.glyph_type

                if not ocr_res["candidates"]:
                    # Empty cell — store blank
                    self.store.log_cell(
                        run_id=run_id,
                        cell=cell,
                        ocr_res={"candidates": [], "resolved": ""},
                        laya_decision={
                            "composite_score": 0.0,
                            "route": "low_confidence",
                            "requires_human": True,
                            "glyph_type": glyph_type,
                            "p_prior": 0.0,
                            "s_spatial": 1.0,
                            "c_consistency": 1.0,
                            "reason": "no_candidates",
                            "disposition": "review",
                            "final_value": None,
                            "laya_layers": {},
                        },
                        norm_value="",
                        is_ditto=False,
                        inherited_from="",
                        norm_flag="no_candidates",
                    )
                    self._collect_cell_output(
                        cell,
                        {
                            "cell_id": cell_id,
                            "field_key": fk,
                            "observed_value": "",
                            "final_value": None,
                            "disposition": "review",
                            "confidence": 0.0,
                            "composite_score": 0.0,
                            "route": "low_confidence",
                            "glyph_type": glyph_type,
                            "engine": "all_failed",
                            "norm_flag": "no_candidates",
                            "is_ditto": False,
                            "laya": {
                                "L1_glyph_type": glyph_type,
                                "L2_decision": "none",
                                "L3_decision": "none",
                                "L4_route": "low_confidence",
                                "L5": None,
                            },
                        },
                        header_fields,
                        members_by_row,
                    )
                    stats["cells"] += 1
                    stats["low_conf"] += 1
                    continue

                # ─── M05: Normalize ───────────────────────────────────────
                norm_val, norm_flag = self.normalizer.normalize(ocr_res["resolved"], fk)

                # ─── M06: Semantic + ditto ────────────────────────────────
                sem = self.semantic.process(cell_id, fk, norm_val, cell["row_idx"])
                if norm_flag and norm_val:
                    sem["is_ditto"] = False  # protected field: never ditto

                # ─── M07: Arbiter ─────────────────────────────────────────
                arb = self.arbiter.decide(cell_id, fk, ocr_res)
                observed_value = sem["snapped"] if arb.decision != "NULL" else ""

                # ─── Bayesian evidence scoring (after arbiter conf is known) ──
                # No verified calibration has been loaded. Use a neutral
                # multiplier, rather than an invented 0.8 prior that caps
                # even a perfect observation below the acceptance threshold.
                p_prior = 1.0
                bayes = self.bayesian.score(
                    field_key=fk,
                    glyph_type=glyph_type,
                    conf_visual=arb.conf,
                    p_prior=p_prior,
                    s_spatial=1.0,
                    c_consistency=0.85 if sem["is_ditto"] else 1.0,
                )

                # ─── Laya L1-L4: Bayesian cell decision ──────────────────
                laya_cell = self.laya.process_cell(
                    cell=cell,
                    ocr_result=ocr_res,
                    final_value=observed_value,
                    is_ditto=sem["is_ditto"],
                    conf_visual=arb.conf,
                    s_spatial=1.0,
                    c_consistency=0.85 if sem["is_ditto"] else 1.0,
                    field_key=fk,
                    closed_vocab_fields=CLOSED_VOCAB_FIELDS,
                    p_prior=p_prior,
                    bayesian_posterior=bayes["posterior"],
                    bayesian_alpha=bayes["alpha"],
                    prior_n=bayes["prior_n"],
                )

                composite_score = laya_cell.composite_score
                route = laya_cell.route
                requires_human = laya_cell.requires_human
                disposition = (
                    "accepted" if self.allow_auto_accept and not requires_human else "review"
                )
                final_value = observed_value if disposition == "accepted" else None
                emit_field_decision(
                    run_id=run_id,
                    field_id=cell_id,
                    disposition=disposition,
                    primary_reason=route,
                    accepted_by="policy" if disposition == "accepted" else "none",
                )

                # ─── M09: Evidence store ──────────────────────────────────
                self.store.log_cell(
                    run_id=run_id,
                    cell=cell,
                    ocr_res=ocr_res,
                    laya_decision={
                        "composite_score": composite_score,
                        "route": route,
                        "requires_human": requires_human,
                        "glyph_type": glyph_type,
                        "p_prior": p_prior,
                        "s_spatial": 1.0,
                        "c_consistency": 0.85 if sem["is_ditto"] else 1.0,
                        "reason": (
                            f"S={composite_score:.3f} "
                            f"{'≥' if composite_score >= 0.88 else '<'} 0.88 "
                            f"[α={bayes['alpha']:.2f}, "
                            f"prior={bayes['prior_mean']:.3f}, "
                            f"n={bayes['prior_n']}]"
                        ),
                        "disposition": disposition,
                        "final_value": final_value,
                        "laya_layers": {k: v for k, v in laya_cell.laya_layers.items()},
                    },
                    norm_value=observed_value,
                    is_ditto=sem["is_ditto"],
                    inherited_from=sem.get("inherited_from", ""),
                    norm_flag=norm_flag,
                )

                if requires_human:
                    stats["low_conf"] += 1
                else:
                    stats["auto"] += 1
                stats["cells"] += 1

                # Collect into household structure
                cell_output = {
                    "cell_id": cell_id,
                    "field_key": fk,
                    "observed_value": observed_value,
                    "final_value": final_value,
                    "disposition": disposition,
                    "confidence": round(arb.conf, 4),
                    "composite_score": round(composite_score, 4),
                    "route": route,
                    "glyph_type": glyph_type,
                    "engine": ocr_res.get("reason", "unknown"),
                    "norm_flag": norm_flag,
                    "is_ditto": sem["is_ditto"],
                    "laya": {
                        "L1_glyph_type": laya_cell.glyph_type,
                        "L2_decision": laya_cell.candidate_decision,
                        "L3_decision": laya_cell.semantic_decision,
                        "L4_route": laya_cell.route,
                        "L5": None,  # filled at household level
                    },
                }

                # Header fields go into header dict, member fields go into row dict
                self._collect_cell_output(cell, cell_output, header_fields, members_by_row)

            # ─── Laya L5 + M08: Household QA ──────────────────────────
            member_rows = sorted(members_by_row.values(), key=lambda m: m["row_idx"])
            member_list = []
            for m in member_rows:
                row_dict = {"row_idx": m["row_idx"]}
                for fk in self.member_table_cols:
                    if fk in m["fields"]:
                        row_dict[fk] = m["fields"][fk]["observed_value"]
                    else:
                        row_dict[fk] = ""
                # Preserve relation/gender/age for QA.
                # Unreadable ages stay None — never a synthetic 0 — so QA
                # rules skip unknown ages instead of flagging them.
                row_dict["relation"] = row_dict.get("relation", "")
                row_dict["gender"] = row_dict.get("gender", "")
                row_dict["age"] = parse_int_or_none(row_dict.get("age"))
                member_list.append(row_dict)

            # L5 HouseholdQA
            relations = [m.get("relation", "") for m in member_list]
            l5_result = self.laya.process_household(members=member_list, relations=relations)

            # M08 RelationalQA
            qa_anomalies = self.qa.validate(doc_id, run_id, member_list, page.page_index)
            for a in qa_anomalies:
                anomaly_dict = a.to_dict() if hasattr(a, "to_dict") else a.__dict__
                self.store.log_qa_anomaly(anomaly_dict, run_id)
                all_qa_anomalies.append(anomaly_dict)
            stats["qa_flags"] += len(qa_anomalies)

            # Attach L5 results to member rows
            member_decisions = l5_result.get("member_decisions", [])
            for md in member_decisions:
                ri = md.get("row_idx", -1)
                if ri >= 0 and ri < len(member_rows):
                    if "laya" not in member_rows[ri]:
                        member_rows[ri]["laya"] = {}
                    member_rows[ri]["laya"]["L5"] = md

            # Build per-document output (single JSON per PDF)
            household = {
                "doc_id": doc_id,
                "page_index": page.page_index,
                "template_version": "1.0",
                "header": header_fields,
                "members": member_rows,
                "l5_decisions": member_decisions,
                "qa_anomalies": [
                    {
                        "anomaly_id": a.anomaly_id,
                        "page_index": a.page_index,
                        "rule": a.rule,
                        "severity": a.severity,
                        "explanation": a.explanation,
                        "row_idx": a.row_idx,
                    }
                    for a in qa_anomalies
                ],
            }
            household_outputs.append(household)

            elapsed = time.time() - t0
            stats["docs"] += 1
            print(
                f"  ✓ {stats['cells']} cells, {stats['auto']} auto, "
                f"{stats['low_conf']} flagged, {len(qa_anomalies)} QA ({elapsed:.1f}s)"
            )

        # ─── M09: calibration state ─────────────────────────────────
        prior_snapshot = self.bayesian.get_priors_snapshot()
        print("\n  [BAYES] No unverified observations persisted as priors")

        # ─── M10: Export ─────────────────────────────────────────────
        print(f"\n>>> EXPORTING (run: {run_id})")
        self.store.finish_run(run_id)

        # Write single-document JSON per PDF
        json_dir = self.output_dir / "households_json"
        json_dir.mkdir(parents=True, exist_ok=True)
        for hh in household_outputs:
            jp = json_dir / f"{hh['doc_id']}_p{hh['page_index'] + 1:02d}.json"
            jp.write_text(json.dumps(hh, ensure_ascii=False, indent=2), encoding="utf-8")

        # Write long CSV
        csv_path = self.export.export(run_id, COL_KEYS)
        zip_path = self.export.make_zip(run_id)

        emit_run_complete(
            run_id=run_id,
            accepted=stats["auto"],
            review=stats["low_conf"],
            errored=len(page_errors),
            wall_ms=int((time.time() - run_wall_start) * 1000),
        )

        result = {
            "run_id": run_id,
            "stats": stats,
            "bayesian": {
                "priors_saved": len(prior_snapshot),
                "prior_snapshot": prior_snapshot[:5],  # sample for log
            },
            "output": {
                "json_dir": str(json_dir),
                "long_csv": csv_path.get("long_csv") if csv_path else "",
                "wide_csv": csv_path.get("wide_csv") if csv_path else "",
                "review_csv": csv_path.get("review_csv") if csv_path else "",
                "zip": str(zip_path),
            },
            "qa_anomalies": len(all_qa_anomalies),
            "documents": household_outputs,
            "members_extracted": sum(len(document["members"]) for document in household_outputs),
            "page_errors": page_errors,
        }

        print(f"\n{'=' * 70}")
        print(f">>> PIPELINE COMPLETE — {run_id}")
        print(f"    Docs/Pages        : {stats['docs']}/{stats['pages']}")
        print(f"    Total cells       : {stats['cells']}")
        print(f"    Auto-accepted     : {stats['auto']}")
        print(f"    Low-confidence    : {stats['low_conf']}")
        print(f"    QA anomalies      : {stats['qa_flags']}")
        print(f"    Bayesian priors   : {len(prior_snapshot)} fields updated")
        if csv_path:
            for k, v in csv_path.items():
                if v:
                    print(f"    {k}: {v}")
        print(f"    ZIP: {zip_path}")

        return result
