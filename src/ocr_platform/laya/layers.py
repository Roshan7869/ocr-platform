"""Laya multi-layered decision classifier for Survey OCR.

Each layer is a PyTorch nn.Module that takes the previous module's output
and produces a structured decision with confidence. Layers can be used
in two modes:
  - **Inference (default):** deterministic rule-based fallback (untrained)
  - **Training:** enable with layer.train() → PyTorch head used

Trained checkpoints can replace the rule-based logic end-to-end.
"""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Any


# ---------------------------------------------------------------------------
# Shared classification head (small MLP)
# ---------------------------------------------------------------------------

class ClassificationHead(nn.Module):
    """Reusable MLP head: Linear → ReLU → Dropout → Linear → classes."""

    def __init__(self, in_dim: int, hidden: int, out_classes: int, dropout: float = 0.1):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden, out_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


# ---------------------------------------------------------------------------
# Feature helper
# ---------------------------------------------------------------------------

def _to_tensor(value: Any, device: torch.device) -> torch.Tensor:
    if isinstance(value, torch.Tensor):
        return value.to(device=device, dtype=torch.float32)
    if isinstance(value, (list, tuple)):
        return torch.tensor(value, device=device, dtype=torch.float32)
    if isinstance(value, (int, float)):
        return torch.tensor([value], device=device, dtype=torch.float32)
    raise TypeError(f"Cannot convert {type(value)} to tensor")


# ---------------------------------------------------------------------------
# L1 — GeometryGate
# ---------------------------------------------------------------------------

class GeometryGateLayer(nn.Module):
    """Morphology features → glyph_type decision.

    Inference mode: rule-based (no training required).
    Training mode: PyTorch MLP head.
    """

    LABELS = ["empty", "stroke", "printed", "handwritten"]

    def __init__(self, hidden: int = 32, dropout: float = 0.1):
        super().__init__()
        self.head = ClassificationHead(4, hidden, 4, dropout)
        self.eval()  # Default to inference (rule-based) mode

    def _rule_based(self, ink_density: float, contour_count: int,
                    is_checkbox: bool, is_code1: bool) -> dict:
        if ink_density < 0.005:
            return {"glyph_type": "empty", "confidence": 0.95, "mode": "rule"}
        if is_code1 and ink_density < 0.03 and contour_count <= 2:
            return {"glyph_type": "stroke", "confidence": 0.90, "mode": "rule"}
        if is_checkbox:
            return {"glyph_type": "stroke", "confidence": 0.85, "mode": "rule"}
        if contour_count > 5:
            return {"glyph_type": "printed", "confidence": 0.80, "mode": "rule"}
        return {"glyph_type": "handwritten", "confidence": 0.75, "mode": "rule"}

    def forward(self, ink_density: float, contour_count: int,
                is_checkbox: bool, is_code1: bool) -> dict:
        if not self.training:
            return self._rule_based(ink_density, contour_count, is_checkbox, is_code1)
        # Training mode: use PyTorch head
        dev = self.head.net[0].weight.device
        x = torch.stack([
            _to_tensor(ink_density, dev),
            _to_tensor(min(contour_count / 20.0, 1.0), dev),
            _to_tensor(float(is_checkbox), dev),
            _to_tensor(float(is_code1), dev),
        ], dim=-1).unsqueeze(0)
        logits = self.head(x)
        probs = F.softmax(logits, dim=-1)
        pred_idx = int(torch.argmax(probs, dim=-1).item())
        return {
            "glyph_type": self.LABELS[pred_idx],
            "confidence": float(probs.max().item()),
            "probs": probs.detach().cpu().tolist()[0],
            "mode": "model",
        }


# ---------------------------------------------------------------------------
# L2 — CandidateSelector
# ---------------------------------------------------------------------------

class CandidateSelectorLayer(nn.Module):
    """OCR candidates + geometry → best engine + escalation flag.

    Inference mode: rule-based (high-conf single candidate → accept, else escalate).
    Training mode: PyTorch MLP head.
    """

    LABELS = ["escalate", "accept"]

    def __init__(self, hidden: int = 48, dropout: float = 0.1):
        super().__init__()
        self.head = ClassificationHead(24, hidden, 2, dropout)
        self.eval()

    def _rule_based(self, candidates: list[dict], glyph_type: str) -> dict:
        if not candidates:
            return {"decision": "accept", "escalate": False, "confidence": 0.5, "mode": "rule"}
        best = max(candidates, key=lambda c: c.get("conf", 0.0))
        if glyph_type == "handwritten":
            return {"decision": "escalate", "escalate": True, "confidence": 0.75, "mode": "rule"}
        if len(candidates) == 1 and best["conf"] >= 0.85:
            return {"decision": "accept", "escalate": False, "confidence": best["conf"], "mode": "rule"}
        if best["conf"] < 0.85:
            return {"decision": "escalate", "escalate": True, "confidence": 0.70, "mode": "rule"}
        return {"decision": "accept", "escalate": False, "confidence": best["conf"], "mode": "rule"}

    def forward(self, candidates: list[dict], glyph_type: str) -> dict:
        if not self.training:
            return self._rule_based(candidates, glyph_type)
        dev = self.head.net[0].weight.device
        feats = []
        for c in candidates[:6]:
            conf = float(c.get("conf", 0.0))
            glyph_score = 1.0 if glyph_type in ("printed", "handwritten") else 0.0
            engine_id = {"paddle": 0.0, "hindi_vlm": 0.5, "indic": 1.0}.get(c.get("engine", ""), 0.0)
            vocab_match = 1.0 if c.get("value", "").strip() else 0.0
            feats.extend([conf, glyph_score, engine_id, vocab_match])
        while len(feats) < 24:
            feats.append(0.0)
        x = _to_tensor(feats[:24], dev).unsqueeze(0)
        logits = self.head(x)
        probs = F.softmax(logits, dim=-1)
        pred_idx = int(torch.argmax(probs, dim=-1).item())
        return {
            "decision": self.LABELS[pred_idx],
            "escalate": pred_idx == 0,
            "confidence": float(probs.max().item()),
            "probs": probs.detach().cpu().tolist()[0],
            "mode": "model",
        }


# ---------------------------------------------------------------------------
# L3 — SemanticValidator
# ---------------------------------------------------------------------------

class SemanticValidatorLayer(nn.Module):
    """Snapped value + vocab match → confidence in the snap.

    Inference mode: rule-based (vocab match = high conf, open field = lower).
    Training mode: PyTorch MLP head.
    """

    LABELS = ["low_confidence", "high_confidence"]

    def __init__(self, hidden: int = 32, dropout: float = 0.1):
        super().__init__()
        self.head = ClassificationHead(3, hidden, 2, dropout)
        self.eval()

    def _rule_based(self, raw: str, snapped: str, field_key: str, closed_vocab_fields: set) -> dict:
        vocab_match = 1.0 if field_key in closed_vocab_fields and snapped != raw else 0.0
        if not snapped:
            return {"decision": "low_confidence", "confidence": 0.2, "vocab_match": vocab_match, "mode": "rule"}
        if field_key in closed_vocab_fields and snapped != raw:
            return {"decision": "high_confidence", "confidence": 0.90, "vocab_match": vocab_match, "mode": "rule"}
        if raw == snapped:
            return {"decision": "high_confidence", "confidence": 0.85, "vocab_match": vocab_match, "mode": "rule"}
        try:
            from rapidfuzz import fuzz
            score = fuzz.ratio(raw, snapped) / 100.0
        except ImportError:
            score = 0.5
        if score >= 0.78:
            return {"decision": "high_confidence", "confidence": 0.80, "vocab_match": vocab_match, "mode": "rule"}
        return {"decision": "low_confidence", "confidence": score, "vocab_match": vocab_match, "mode": "rule"}

    def forward(self, raw: str, snapped: str, field_key: str, closed_vocab_fields: set) -> dict:
        if not self.training:
            return self._rule_based(raw, snapped, field_key, closed_vocab_fields)
        dev = self.head.net[0].weight.device
        vocab_match = 1.0 if field_key in closed_vocab_fields and snapped != raw else 0.0
        try:
            from rapidfuzz import fuzz
            fuzzy_score = min(1.0, fuzz.ratio(raw, snapped) / 100.0)
        except ImportError:
            fuzzy_score = 1.0 if raw == snapped else 0.0
        text_len = min(1.0, len(snapped.strip()) / 50.0)
        x = _to_tensor([vocab_match, fuzzy_score, text_len], dev).unsqueeze(0)
        logits = self.head(x)
        probs = F.softmax(logits, dim=-1)
        pred_idx = int(torch.argmax(probs, dim=-1).item())
        return {
            "decision": self.LABELS[pred_idx],
            "confidence": float(probs.max().item()),
            "vocab_match": vocab_match,
            "fuzzy_score": fuzzy_score,
            "snap_confidence": float(probs[0][pred_idx].item()),
            "mode": "model",
        }


# ---------------------------------------------------------------------------
# L4 — EvidenceGate
# ---------------------------------------------------------------------------

class EvidenceGateLayer(nn.Module):
    """Visual/prior/spatial/consistency → composite S + route.

    Inference mode: rule-based weighted formula.
    Training mode: PyTorch MLP head.
    """

    LABELS = ["low_confidence", "auto"]
    WEIGHTS = {"visual": 0.40, "prior": 0.35, "spatial": 0.15, "consistency": 0.10}

    def __init__(self, hidden: int = 32, dropout: float = 0.1):
        super().__init__()
        self.head = ClassificationHead(4, hidden, 2, dropout)
        self.eval()

    def _rule_based(self, conf_visual: float, p_prior: float,
                    s_spatial: float, c_consistency: float,
                    bayesian_posterior: float | None = None,
                    bayesian_alpha: float | None = None,
                    prior_n: int = 0) -> dict:
        """Evidence-weighted composite score.

        If bayesian_posterior is provided, use it directly (posterior from
        BayesianScorer.score()). Otherwise fall back to the fixed-weight
        formula for backward compatibility.
        """
        if bayesian_posterior is not None:
            S = max(0.0, min(1.0, bayesian_posterior))
        else:
            S = (
                self.WEIGHTS["visual"] * max(0.0, min(1.0, conf_visual))
                + self.WEIGHTS["prior"] * max(0.0, min(1.0, p_prior))
                + self.WEIGHTS["spatial"] * max(0.0, min(1.0, s_spatial))
                + self.WEIGHTS["consistency"] * max(0.0, min(1.0, c_consistency))
            )
            S = max(0.0, min(1.0, S))
        if S >= 0.88:
            return {"composite_score": round(S, 4), "route": "auto",
                    "requires_human": False, "confidence": S,
                    "bayesian_alpha": bayesian_alpha, "prior_n": prior_n,
                    "mode": "rule"}
        return {"composite_score": round(S, 4), "route": "low_confidence",
                "requires_human": True, "confidence": 1.0 - S,
                "bayesian_alpha": bayesian_alpha, "prior_n": prior_n,
                "mode": "rule"}

    def forward(self, conf_visual: float, p_prior: float,
                s_spatial: float, c_consistency: float,
                bayesian_posterior: float | None = None,
                bayesian_alpha: float | None = None,
                prior_n: int = 0) -> dict:
        if not self.training:
            return self._rule_based(conf_visual, p_prior, s_spatial, c_consistency,
                                    bayesian_posterior, bayesian_alpha, prior_n)
        dev = self.head.net[0].weight.device
        x = _to_tensor([conf_visual, p_prior, s_spatial, c_consistency], dev).unsqueeze(0)
        logits = self.head(x)
        probs = F.softmax(logits, dim=-1)
        pred_idx = int(torch.argmax(probs, dim=-1).item())
        w = self.WEIGHTS
        S = w["visual"] * conf_visual + w["prior"] * p_prior + w["spatial"] * s_spatial + w["consistency"] * c_consistency
        S = max(0.0, min(1.0, S))
        if bayesian_posterior is not None:
            S = bayesian_posterior
        return {
            "decision": self.LABELS[pred_idx],
            "composite_score": round(S, 4),
            "route": "auto" if pred_idx == 1 else "low_confidence",
            "requires_human": pred_idx == 0,
            "confidence": float(probs.max().item()),
            "probs": probs.detach().cpu().tolist()[0],
            "mode": "model",
        }


# ---------------------------------------------------------------------------
# L5 — HouseholdQA
# ---------------------------------------------------------------------------

class HouseholdQALayer(nn.Module):
    """Member list → anomaly predictions.

    Inference mode: rule-based (head count, father age, wife gender).
    Training mode: PyTorch MLP head per member.
    """

    LABELS = ["ok", "anomaly", "critical"]

    def __init__(self, hidden: int = 32, dropout: float = 0.1, max_members: int = 20):
        super().__init__()
        self.max_members = max_members
        self.head = ClassificationHead(5, hidden, 3, dropout)
        self.eval()

    def _rule_based(self, members: list[dict], relations: list[str]) -> dict:
        results = []
        # Head count check
        heads = sum(1 for r in relations if r in ("स्वयं", "मुखिया", "HEAD", "SELF"))
        for i, m in enumerate(members):
            raw_age = m.get("age", None)
            age = 0.0
            age_known = raw_age is not None
            if age_known:
                try:
                    age = float(raw_age)
                except (TypeError, ValueError):
                    age_known = False
            rel = m.get("relation", "")
            gender = m.get("gender", "")
            if rel == "पत्नी" and gender == "पुरुष":
                results.append({"row_idx": i, "decision": "anomaly", "confidence": 0.95, "mode": "rule"})
            elif rel == "पिता" and age_known and age < 18:
                results.append({"row_idx": i, "decision": "anomaly", "confidence": 0.95, "mode": "rule"})
            else:
                results.append({"row_idx": i, "decision": "ok", "confidence": 0.90, "mode": "rule"})
        # Head count anomaly at row_idx=-1
        if heads != 1:
            results.append({"row_idx": -1, "decision": "critical" if heads == 0 else "anomaly",
                            "confidence": 0.95, "mode": "rule"})
        return {"member_decisions": results}

    def forward(self, members: list[dict], relations: list[str]) -> dict:
        if not self.training:
            return self._rule_based(members, relations)
        # Training mode: per-member MLP
        results = []
        while len(members) < self.max_members:
            members.append({})
        members = members[: self.max_members]
        dev = self.head.net[0].weight.device
        for i, m in enumerate(members):
            try:
                age = float(m.get("age", 0)) / 130.0
            except (TypeError, ValueError):
                age = 0.0
            rel = m.get("relation", "")
            is_head = 1.0 if rel in ("स्वयं", "मुखिया", "HEAD", "SELF") else 0.0
            gender = m.get("gender", "")
            gender_code = {"पुरुष": 1.0, "महिला": -1.0}.get(gender, 0.0)
            rel_code = {"स्वयं": 1.0, "पत्नी": 2.0, "पिता": 3.0, "माता": 4.0}.get(rel, 0.0)
            has_father = 1.0 if rel == "पिता" and age < 0.14 else 0.0
            wife_male = 1.0 if rel == "पत्नी" and gender == "पुरुष" else 0.0
            x = _to_tensor([age, is_head, gender_code, rel_code, max(has_father, wife_male)], dev).unsqueeze(0)
            logits = self.head(x)
            probs = F.softmax(logits, dim=-1)
            pred_idx = int(torch.argmax(probs, dim=-1).item())
            results.append({
                "row_idx": i, "decision": self.LABELS[pred_idx],
                "confidence": float(probs.max().item()),
                "probs": probs.detach().cpu().tolist()[0], "mode": "model",
            })
        return {"member_decisions": results}
