"""SurveyPipeline — end-to-end orchestrator.

Threads all modules through Laya multi-layered decisions:
  M01 DocumentLoader → M02 TemplateAligner → M03 TieredOCR
  → M04 Morphology → M05 Normalizer → M06 Semantic → M07 Arbiter
  → Laya L1-L4 (per cell) → Laya L5 (per household) → M10 Export
"""

from __future__ import annotations

import hashlib
import os
import time
import uuid
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from ocr_platform.document.loader import DocumentLoader, Page
from ocr_platform.export.writer import ExportEngine
from ocr_platform.laya.config import LayaConfig
from ocr_platform.laya.pipeline import CellDecision, LayaPipeline
from ocr_platform.worker.arbiter import Arbiter
from ocr_platform.worker.morphology import ContourMorphologyEngine
from ocr_platform.worker.normalizer import SpatialNormalizer
from ocr_platform.worker.provenance.store import EvidenceStore
from ocr_platform.worker.semantic import SemanticEngine
from ocr_platform.worker.validation.qa import RelationalQA

# Column key order (18 columns)
COL_KEYS = [
    "sr_no", "member_name", "relation", "gender", "age", "marital_status",
    "marriage_age", "religion", "caste", "caste_category", "education",
    "occupation", "employment_nature", "monthly_income", "bank_account",
    "resident_code", "migration_nature", "remarks",
]

CLOSED_VOCAB_FIELDS = {
    "gender", "relation", "religion", "marital_status", "caste_category",
    "resident_code", "marriage_age", "bank_account",
}


class SurveyPipeline:
    """Full pipeline: PDF/ZIP/images → per-household JSON + CSV."""

    def __init__(
        self,
        template_path: Path | str,
        db_path: Path | str,
        output_dir: Path | str,
        laya_config: LayaConfig | None = None,
        dpi: int = 200,
    ):
        self.template_path = Path(template_path)
        self.db_path = Path(db_path)
        self.output_dir = Path(output_dir)
        self.dpi = dpi

        # Laya pipeline
        self.laya = LayaPipeline(laya_config)

        # Workers
        self.loader = DocumentLoader(dpi=dpi)
        self.morphology = ContourMorphologyEngine()
        self.normalizer = SpatialNormalizer()
        self.semantic = SemanticEngine()
        self.arbiter = Arbiter()
        self.qa = RelationalQA(self.db_path)
        self.store = EvidenceStore(self.db_path)
        self.export = ExportEngine(self.db_path, self.output_dir)

        # OCR engines (lazy init — loaded once per run)
        self._paddle = None
        self._hindi_vlm = None
        self._indic = None

        # Load template
        import json
        with open(self.template_path) as f:
            tpl = json.load(f)
        self.W, self.H = tpl["page_size"]
        self.anchors = np.array(tpl["global_anchors"], dtype=np.float32)
        self.col_t = np.array(tpl["column_dividers_top"], dtype=np.float32)
        self.col_b = np.array(tpl["column_dividers_bottom"], dtype=np.float32)
        self.rows = np.array(tpl.get("row_divs", tpl.get("row_dividers", [])), dtype=np.float32)

        # Validate template has enough dividers for COL_KEYS
        n_cols = len(self.col_t) - 1
        if n_cols < len(COL_KEYS):
            raise ValueError(
                f"Template has {n_cols} columns but COL_KEYS has {len(COL_KEYS)} fields. "
                f"Fix column_dividers in {self.template_path}"
            )

    # ------------------------------------------------------------------
    # OCR initialization (called once)
    # ------------------------------------------------------------------

    def _init_paddle(self):
        if self._paddle is not None:
            return
        try:
            from paddleocr import PaddleOCR
            os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
            self._paddle = PaddleOCR(use_angle_cls=False, lang="devanagari", show_log=False)
            print("  [M03] PaddleOCR hin ready.")
        except Exception as e:
            print(f"  [M03] PaddleOCR init failed: {e}")

    def _init_vlm(self):
        if self._hindi_vlm is not None:
            return
        try:
            from transformers import AutoProcessor, AutoModelForVision2Seq
            print("  [M03] Loading HindiOCR-VLM...")
            p = AutoProcessor.from_pretrained("HindiOCR-VLM/HindiOCR-VLM", trust_remote_code=True)
            m = AutoModelForVision2Seq.from_pretrained("HindiOCR-VLM/HindiOCR-VLM", trust_remote_code=True)
            self._hindi_vlm = (p, m)
            print("  [M03] HindiOCR-VLM ready.")
        except Exception as e:
            print(f"  [M03] HindiOCR-VLM load failed: {e}")

    def _init_indic(self):
        if self._indic is not None:
            return
        try:
            from transformers import AutoProcessor, AutoModelForVision2Seq
            print("  [M03] Loading IndicOCR (bodhan-ai/indic-ocr)...")
            p = AutoProcessor.from_pretrained("bodhan-ai/indic-ocr", trust_remote_code=True)
            m = AutoModelForVision2Seq.from_pretrained("bodhan-ai/indic-ocr", trust_remote_code=True)
            self._indic = (p, m)
            print("  [M03] IndicOCR ready.")
        except Exception as e:
            print(f"  [M03] IndicOCR load failed: {e}")

    # ------------------------------------------------------------------
    # OCR dispatch
    # ------------------------------------------------------------------

    def _run_paddle(self, crop: np.ndarray) -> dict[str, Any] | None:
        self._init_paddle()
        if self._paddle is None:
            return None
        try:
            padded = cv2.copyMakeBorder(crop, 15, 15, 15, 15, cv2.BORDER_CONSTANT, value=(255, 255, 255))
            results = self._paddle.ocr(padded, cls=False, rec=True, det=False)
            if results and results[0]:
                txt, conf = results[0][0][1]
                return {"value": txt, "conf": float(conf), "engine": "paddle"}
        except Exception as e:
            print(f"  [M03] PaddleOCR err: {e}")
        return None

    def _run_vlm(self, crop: np.ndarray) -> dict[str, Any] | None:
        self._init_vlm()
        if self._hindi_vlm is None:
            return None
        proc, model = self._hindi_vlm
        try:
            from PIL import Image
            padded = cv2.copyMakeBorder(crop, 15, 15, 15, 15, cv2.BORDER_CONSTANT, value=(255, 255, 255))
            rgb = cv2.cvtColor(padded, cv2.COLOR_BGR2RGB)
            inp = proc(Image.fromarray(rgb), text="OCR this Hindi form field. Output only text.", return_tensors="pt")
            ids = model.generate(**inp, max_new_tokens=128)
            txt = proc.batch_decode(ids, skip_special_tokens=True)[0].strip()
            return {"value": txt, "conf": 0.80, "engine": "hindi_vlm"}
        except Exception as e:
            print(f"  [M03] HindiOCR-VLM err: {e}")
        return None

    def _run_indic(self, crop: np.ndarray) -> dict[str, Any] | None:
        self._init_indic()
        if self._indic is None:
            return None
        proc, model = self._indic
        try:
            from PIL import Image
            padded = cv2.copyMakeBorder(crop, 15, 15, 15, 15, cv2.BORDER_CONSTANT, value=(255, 255, 255))
            rgb = cv2.cvtColor(padded, cv2.COLOR_BGR2RGB)
            inp = proc(Image.fromarray(rgb), return_tensors="pt")
            ids = model.generate(**inp, max_new_tokens=256)
            txt = proc.batch_decode(ids, skip_special_tokens=True)[0].strip()
            return {"value": txt, "conf": 0.75, "engine": "indic"}
        except Exception as e:
            print(f"  [M03] IndicOCR err: {e}")
        return None

    def _dispatch_ocr(self, cell_id: str, field_key: str, crop: np.ndarray, handwriting: bool) -> dict[str, Any]:
        """Tiered OCR dispatch — models initialized once per run."""
        candidates = []
        p = self._run_paddle(crop)
        if p:
            candidates.append({"value": p["value"], "conf": p["conf"], "engine": p["engine"]})
        if handwriting or (p and p["conf"] < 0.85):
            v = self._run_vlm(crop)
            if v:
                candidates.append({"value": v["value"], "conf": v["conf"], "engine": v["engine"]})
        if candidates and all(c["conf"] < 0.85 for c in candidates):
            ind = self._run_indic(crop)
            if ind:
                candidates.append({"value": ind["value"], "conf": ind["conf"], "engine": ind["engine"]})
        # Deduplicate
        seen: set[str] = set()
        unique: list[dict[str, Any]] = []
        for c in candidates:
            k = c["value"].strip().lower()
            if k and k not in seen:
                seen.add(k)
                unique.append(c)
        best = max(unique, key=lambda c: c["conf"]) if unique else None
        return {
            "cell_id": cell_id,
            "field_key": field_key,
            "candidates": unique,
            "resolved": best["value"] if best else "",
            "reason": f"best_{best['engine']}" if best else "all_failed",
        }

    # ------------------------------------------------------------------
    # Template alignment + grid slicing
    # ------------------------------------------------------------------

    def _register_and_slice(self, img_bgr: np.ndarray, page_sha256: str, run_id: str, out_dir: Path, doc_id: str) -> list[dict] | None:
        """Warp to canonical template and slice into cell ROIs."""
        # Find corners via convex hull
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        bw = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY_INV, 11, 2)
        cnts, _ = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not cnts:
            print("  [M02] No printed content found.")
            return None
        hull = cv2.convexHull(np.vstack([c.reshape(-1, 2) for c in cnts]))
        quad = cv2.approxPolyDP(hull, 0.02 * cv2.arcLength(hull, True), True)
        if len(quad) != 4:
            x, y, w, h = cv2.boundingRect(hull)
            quad = np.array([[[x, y]], [[x + w, y]], [[x + w, y + h]], [[x, y + h]]], dtype=np.float32)
        pts = quad.reshape(4, 2).astype(np.float32)
        sy = pts[np.argsort(pts[:, 1])]
        top, bot = sy[:2], sy[2:]
        corners = np.array([
            top[np.argmin(top[:, 0])], top[np.argmax(top[:, 0])],
            bot[np.argmax(bot[:, 0])], bot[np.argmin(bot[:, 0])],
        ], dtype=np.float32)

        H, st = cv2.findHomography(corners, self.anchors, cv2.RANSAC, 3.0)
        if H is None or int(np.sum(st)) < 3:
            print(f"  [M02] Alignment failed ({int(np.sum(st))}/4 corners matched).")
            return None
        warped = cv2.warpPerspective(img_bgr, H, (self.W, self.H), cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        conf = float(np.sum(st)) / 4.0

        # Slice cells
        rois: list[dict[str, Any]] = []
        n_rows = len(self.rows)
        for ri in range(1, n_rows):
            y1, y2 = int(self.rows[ri - 1]), int(self.rows[ri])
            dri = ri - 1
            frac = (y1 - self.rows[0]) / max(1, self.rows[-1] - self.rows[0])
            n_cols = len(self.col_t) - 1
            for ci in range(n_cols):
                x1 = int(self.col_t[ci] + frac * (self.col_b[ci] - self.col_t[ci]))
                x2 = int(self.col_t[ci + 1] + frac * (self.col_b[ci + 1] - self.col_b[ci]))
                cx1, cy1 = max(0, x1 + 6), max(0, y1 + 6)
                cx2, cy2 = min(self.W, x2 - 6), min(self.H, y2 - 6)
                if cx2 <= cx1 or cy2 <= cy1:
                    continue
                crop = warped[cy1:cy2, cx1:cx2]
                sha = hashlib.sha256(cv2.imencode(".png", crop)[1].tobytes()).hexdigest()[:16]
                fk = COL_KEYS[ci] if ci < len(COL_KEYS) else f"col_{ci}"
                rois.append({
                    "cell_id": f"{dri}_{ci}_{sha}",
                    "row_idx": dri,
                    "col_idx": ci,
                    "field_key": fk,
                    "crop_bgr": crop,
                    "sha256": sha,
                    "box": [cx1, cy1, cx2, cy2],
                    "doc_id": doc_id,
                })
        return rois

    # ------------------------------------------------------------------
    # Full pipeline
    # ------------------------------------------------------------------

    def run(self, source: Path | str) -> dict[str, Any]:
        """Run the full pipeline on *source* (PDF, ZIP, or image directory)."""
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        source = Path(source)
        print("=" * 70)
        print(f">>> SURVEY OCR PIPELINE — {run_id}")
        print(f">>> Input: {source}")
        print("=" * 70)

        # M01: Load documents
        pages = self.loader.load(source)
        if not pages:
            print("No pages loaded. Check input.")
            return {"run_id": run_id, "error": "no_pages"}

        self.store.start_run(run_id, doc_count=len(pages))
        stats: dict[str, int] = {"docs": 0, "cells": 0, "auto": 0, "low_conf": 0, "qa_flags": 0}

        for page in pages:
            doc_id = page.doc_id
            print(f"\n--- {doc_id} (page {page.page_index + 1}) ---")
            t0 = time.time()

            # M02: Template-align + slice
            img = cv2.imdecode(np.frombuffer(page.image_bytes, np.uint8), cv2.IMREAD_COLOR)
            if img is None:
                print("  Cannot decode image. Skipping.")
                continue
            rois = self._register_and_slice(img, page.sha256, run_id, self.output_dir / "crops", doc_id)
            if not rois:
                print("  Alignment failed. Check template.")
                continue

            # Save crops
            crop_dir = self.output_dir / "crops" / doc_id
            crop_dir.mkdir(parents=True, exist_ok=True)
            for r in rois:
                p = crop_dir / f"{r['sha256']}.png"
                cv2.imwrite(str(p), r["crop_bgr"], [cv2.IMWRITE_PNG_COMPRESSION, 3])
                r["crop_path"] = str(p)

            doc_members: list[dict[str, Any]] = []

            for cell in rois:
                crop = cv2.imread(cell["crop_path"])
                if crop is None:
                    continue
                fk = cell["field_key"]

                # M04: Morphology (also used by Laya L1)
                geo = self.morphology.analyze(cell["cell_id"], crop, fk)

                # M03: OCR dispatch
                ocr_res = self._dispatch_ocr(cell["cell_id"], fk, crop, handwriting=(geo.glyph_type == "handwritten"))
                if not ocr_res["candidates"]:
                    continue

                # M05: Normalize
                norm = self.normalizer.normalize(ocr_res["resolved"], fk)

                # M06: Semantic + ditto
                sem = self.semantic.process(cell["cell_id"], fk, norm, cell["row_idx"])

                # M07: Arbiter
                arb = self.arbiter.decide(cell["cell_id"], fk, ocr_res)

                final_val = arb.value if arb.decision != "NULL" else ""

                # Laya layers L1-L4 (per cell)
                laya_decision = self.laya.process_cell(
                    cell=cell,
                    ocr_result=ocr_res,
                    final_value=final_val,
                    is_ditto=sem["is_ditto"],
                    conf_visual=arb.conf,
                    s_spatial=1.0,
                    c_consistency=0.85 if sem["is_ditto"] else 1.0,
                    field_key=fk,
                    closed_vocab_fields=CLOSED_VOCAB_FIELDS,
                )

                # M09 + evidence store (using Laya's composite score)
                self.store.log_cell(
                    run_id=run_id, cell=cell, ocr_res=ocr_res,
                    arb_decision=arb.to_dict(),
                    laya_decision={
                        "composite_score": laya_decision.composite_score,
                        "route": laya_decision.route,
                        "requires_human": laya_decision.requires_human,
                        "glyph_type": laya_decision.glyph_type,
                        "p_prior": 1.0 if fk in {"member_name", "head_name", "remarks", "caste", "occupation", "education", "employment_nature", "monthly_income"} else 0.8,
                        "s_spatial": 1.0,
                        "c_consistency": 0.85 if sem["is_ditto"] else 1.0,
                        "reason": f"S={laya_decision.composite_score} {'>=' if laya_decision.composite_score >= 0.88 else '<'} 0.88",
                        "laya_layers": {k: v for k, v in laya_decision.laya_layers.items()},
                    },
                    norm_value=final_val,
                    is_ditto=sem["is_ditto"],
                    inherited_from=sem.get("inherited_from", ""),
                )

                if laya_decision.requires_human:
                    stats["low_conf"] += 1
                else:
                    stats["auto"] += 1
                stats["cells"] += 1

                doc_members.append({
                    "doc_id": doc_id, "row_idx": cell["row_idx"],
                    "field_key": fk, "value": final_val,
                    "S": laya_decision.composite_score,
                    "route": laya_decision.route,
                    "relation": final_val if fk == "relation" else "",
                    "gender": final_val if fk == "gender" else "",
                    "age": final_val if fk == "age" else "",
                })

            # M08: Relational QA (per household)
            if doc_members:
                members_by_row: dict[int, dict[str, Any]] = {}
                for m in doc_members:
                    ri = m["row_idx"]
                    if ri not in members_by_row:
                        members_by_row[ri] = {"doc_id": doc_id, "row_idx": ri}
                    members_by_row[ri][m["field_key"]] = m["value"]
                    # Preserve relation/gender/age for QA
                    if m["field_key"] == "relation":
                        members_by_row[ri]["relation"] = m["value"]
                    if m["field_key"] == "gender":
                        members_by_row[ri]["gender"] = m["value"]
                    if m["field_key"] == "age":
                        try:
                            members_by_row[ri]["age"] = int(m["value"])
                        except (TypeError, ValueError):
                            members_by_row[ri]["age"] = 0

                member_list = list(members_by_row.values())
                anoms = self.qa.validate(doc_id, run_id, member_list)
                for a in anoms:
                    self.store.log_qa_anomaly(a.to_dict() if hasattr(a, "to_dict") else a.__dict__, run_id)
                stats["qa_flags"] += len(anoms)

                # Laya L5: HouseholdQA
                relations = [m.get("relation", "") for m in member_list]
                l5 = self.laya.process_household(members=member_list, relations=relations)

            elapsed = time.time() - t0
            stats["docs"] += 1
            print(f"  ✓ {stats['cells']} cells, {stats['auto']} auto, {stats['low_conf']} flagged ({elapsed:.1f}s)")

        # M10: Export
        print(f"\n>>> EXPORTING (run: {run_id})")
        result = self.export.export(run_id, COL_KEYS)
        if result:
            zip_path = self.export.make_zip(run_id)
            result["zip"] = str(zip_path)

        self.store.finish_run(run_id)

        print(f"\n{'=' * 70}")
        print(f">>> PIPELINE COMPLETE")
        print(f"    Docs processed   : {stats['docs']}")
        print(f"    Total cells      : {stats['cells']}")
        print(f"    Auto-accepted    : {stats['auto']}")
        print(f"    Low-confidence   : {stats['low_conf']}")
        print(f"    QA anomalies     : {stats['qa_flags']}")
        if result:
            print(f"\nOutput:")
            for k, v in result.items():
                if v:
                    print(f"  {k}: {v}")

        return {"run_id": run_id, "stats": stats, "output": result}
