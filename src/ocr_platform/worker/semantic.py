"""Semantic Engine — closed-vocabulary projection + ditto DAG.

Snaps noisy OCR text to canonical Hindi values using RapidFuzz.
Propagates ditto marks vertically within the same column.
"""

from __future__ import annotations

import re
from typing import Any

from rapidfuzz import fuzz, process

NULL_RE = re.compile(r"^[\-_—~=−‒]+\.?$")
# Ditto: quote marks, commas, pipes, double-slash, dash-only
# Intentionally excludes "11" and "ll" — those are real education values
DITTO_RE = re.compile(r'^(?:["“”]{1,3}|,,|\.\.|\|\||//|II|ii)$')
STROKE_RE = re.compile(r"^[\|lI1!/\\।]$")
SNAP_THRESH = 78

CLOSED_VOCAB: dict[str, dict[str, str]] = {
    "gender": {
        "पुरुष": "पुरुष", "पु": "पुरुष", "M": "पुरुष", "महिला": "महिला",
        "स्त्री": "महिला", "म": "महिला", "F": "महिला", "अन्य": "अन्य", "T": "अन्य",
    },
    "relation": {
        "स्वयं": "स्वयं", "स्वय": "स्वयं", "मुखिया": "स्वयं", "HEAD": "स्वयं",
        "SELF": "स्वयं", "पति": "पति", "पत्नी": "पत्नी", "बेटा": "बेटा",
        "बेटी": "बेटी", "पुत्र": "पुत्र", "पुत्री": "पुत्री", "पोता": "पोता",
        "पोती": "पोती", "पिता": "पिता", "माता": "माता", "भाई": "भाई",
        "बहन": "बहन", "बहू": "बहू", "पुत्रवधू": "बहू",
    },
    "religion": {
        "हिन्दू": "हिन्दू", "हिं": "हिन्दू", "मुस्लिम": "मुस्लिम",
        "सिख": "सिख", "ईसाई": "ईसाई", "जैन": "जैन", "पार्सी": "पार्सी",
        "बौद्ध": "बौद्ध", "अन्य": "अन्य",
    },
    "marital_status": {
        "अविवाहित": "अविवाहित", "कुंवारी": "अविवाहित", "कुंवारे": "अविवाहित",
        "विवाहित": "विवाहित", "विधवा": "विधवा", "विधवे": "विधवा",
        "अलग": "अलग", "अन्य": "अन्य",
    },
    "caste_category": {
        "सामान्य": "सामान्य", "अनुसूचित जाति": "अनुसूचित जाति",
        "अनुसूचित जनजाति": "अनुसूचित जनजाति", "पिछड़ा वर्ग": "पिछड़ा वर्ग",
        "OBC": "पिछड़ा वर्ग", "SC": "अनुसूचित जाति", "ST": "अनुसूचित जनजाति",
        "GEN": "सामान्य",
    },
    "resident_code": {
        "1": "1", "स्थायी": "1", "2": "2", "आस्थायी": "2",
        "3": "3", "अन्य": "3", "4": "4",
    },
    "housing_type": {
        "पका मकान": "पका मकान", "पका": "पका मकान", "अपका मकान": "अपका मकान",
        "अपका": "अपका मकान", "कच्चा मकान": "कच्चा मकान", "कच्चा": "कच्चा मकान",
        "झोपड़ी": "झोपड़ी", "others": "अन्य",
    },
    "ownership": {
        "स्वयं का": "स्वयं का", "निजी": "स्वयं का", "किराये पर": "किराये पर",
        "किरायेदार": "किराये पर", "सरकारी आवास": "सरकारी आवास", "अन्य": "अन्य",
    },
    "marriage_age": {
        "18": "18", "21": "21",
    },
    "bank_account": {
        "हां": "हां", "नहीं": "नहीं", "Y": "हां", "N": "नहीं",
        "1": "हां", "0": "नहीं",
    },
}


class DittoDAG:
    """Vertical ditto propagation within a column."""

    def __init__(self):
        self.col_state: dict[str, str] = {}
        self.dag: list[dict[str, Any]] = []

    def process(self, row_idx: int, field_key: str, raw: str) -> dict[str, Any]:
        # Explicit empty bypass: blank cells resolve to "" without touching
        # fuzzy matching or ditto/stroke regexes, so "" can never snap to "1"
        # or inherit an ancestor value.
        if not (raw or "").strip():
            node: dict[str, Any] = {
                "row_idx": row_idx,
                "field_key": field_key,
                "raw": raw,
                "snapped": "",
                "is_ditto": False,
                "inherited_from": None,
            }
            self.dag.append(node)
            return node
        snapped = self._snap(field_key, raw)
        is_ditto = bool(DITTO_RE.match(raw.strip()))
        inherited = None
        if is_ditto and field_key in self.col_state and self.col_state[field_key]:
            snapped = self.col_state[field_key]
            inherited = self._last_verified(field_key)
        # Always update col_state with current confirmed value
        if snapped:
            self.col_state[field_key] = snapped
        node: dict[str, Any] = {
            "row_idx": row_idx,
            "field_key": field_key,
            "raw": raw,
            "snapped": snapped,
            "is_ditto": is_ditto,
            "inherited_from": inherited,
        }
        self.dag.append(node)
        return node

    def _snap(self, fk: str, text: str) -> str:
        if fk not in CLOSED_VOCAB:
            return text
        if STROKE_RE.match(text.strip()) and fk == "resident_code":
            return "1"
        res = process.extractOne(text, list(CLOSED_VOCAB[fk].keys()), scorer=fuzz.ratio)
        if res and res[1] >= SNAP_THRESH:
            return CLOSED_VOCAB[fk][res[0]]
        return text

    def _last_verified(self, fk: str) -> str | None:
        for n in reversed(self.dag):
            if n["field_key"] == fk and not n["is_ditto"] and n["snapped"]:
                return str(n["row_idx"])
        return None


class SemanticEngine:
    """Wraps DittoDAG for per-cell processing."""

    def __init__(self):
        self.dag = DittoDAG()

    def process(self, cell_id: str, fk: str, raw: str, row_idx: int) -> dict[str, Any]:
        n = self.dag.process(row_idx, fk, raw)
        return {
            "cell_id": cell_id,
            "field_key": fk,
            "raw": raw,
            "snapped": n["snapped"],
            "is_ditto": n["is_ditto"],
            "inherited_from": n["inherited_from"],
        }
