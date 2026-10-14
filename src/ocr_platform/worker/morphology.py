"""Contour Morphology Engine — classifies cell glyphs.

Produces geometry profile used by Laya Layer 1 (GeometryGate).
"""

from __future__ import annotations

import re

import cv2
import numpy as np

from pydantic import BaseModel

NULL_RE = re.compile(r"^[\-_—~=−‒]+\.?$")
DITTO_RE = re.compile(r'^(?:["“”]{1,3}|,,|\.\.|\|\||//|11|ll|II|ii)$')
STROKE_RE = re.compile(r"^[\|lI1!/\\।]$")


class GeometryProfile(BaseModel):
    cell_id: str
    glyph_type: str
    ink_density: float
    contour_count: int
    is_checkbox: bool
    is_code1_stroke: bool


class ContourMorphologyEngine:
    """Analyze cell geometry for Laya Layer 1."""

    def analyze(self, cell_id: str, crop_bgr: np.ndarray, field_key: str = "") -> GeometryProfile:
        gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
        _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        ink = float(np.sum(bw > 0)) / bw.size
        if ink < 0.005:
            return GeometryProfile(
                cell_id=cell_id, glyph_type="empty",
                ink_density=ink, contour_count=0, is_checkbox=False, is_code1_stroke=False,
            )
        cnts, _ = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        h, w = crop_bgr.shape[:2]
        ar = w / max(1, h)
        is_cb = any(
            0.7 < ar < 1.3
            and cv2.contourArea(c) > 50
            and len(cv2.approxPolyDP(c, 0.02 * cv2.arcLength(c, True), True)) == 4
            for c in cnts
        )
        is_c1 = "resident_code" in field_key and ink < 0.03 and len(cnts) <= 2
        glyph = "stroke" if is_cb or is_c1 else "printed" if len(cnts) > 5 else "handwritten"
        return GeometryProfile(
            cell_id=cell_id, glyph_type=glyph, ink_density=ink,
            contour_count=len(cnts), is_checkbox=is_cb, is_code1_stroke=is_c1,
        )
