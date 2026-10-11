"""Tests for Laya layers — deterministic inference + PyTorch head shapes."""

from __future__ import annotations

import pytest
import torch

from ocr_platform.laya.layers import (
    CandidateSelectorLayer,
    ClassificationHead,
    EvidenceGateLayer,
    GeometryGateLayer,
    HouseholdQALayer,
    SemanticValidatorLayer,
)


# ── ClassificationHead ──────────────────────────────────────────────────

class TestClassificationHead:
    def test_output_shape(self):
        head = ClassificationHead(in_dim=4, hidden=16, out_classes=2)
        x = torch.randn(1, 4)
        out = head(x)
        assert out.shape == (1, 2)

    def test_batch(self):
        head = ClassificationHead(in_dim=8, hidden=32, out_classes=4)
        x = torch.randn(5, 8)
        out = head(x)
        assert out.shape == (5, 4)


# ── GeometryGateLayer ───────────────────────────────────────────────────

class TestGeometryGateLayer:
    def test_empty_cell(self):
        layer = GeometryGateLayer()
        result = layer(ink_density=0.001, contour_count=0, is_checkbox=False, is_code1=False)
        assert result["glyph_type"] == "empty"
        assert result["mode"] == "rule"
        assert result["confidence"] > 0.5

    def test_code1_stroke(self):
        layer = GeometryGateLayer()
        result = layer(ink_density=0.02, contour_count=1, is_checkbox=False, is_code1=True)
        assert result["glyph_type"] == "stroke"
        assert result["mode"] == "rule"

    def test_checkbox(self):
        layer = GeometryGateLayer()
        result = layer(ink_density=0.05, contour_count=4, is_checkbox=True, is_code1=False)
        assert result["glyph_type"] == "stroke"

    def test_printed(self):
        layer = GeometryGateLayer()
        result = layer(ink_density=0.05, contour_count=10, is_checkbox=False, is_code1=False)
        assert result["glyph_type"] == "printed"

    def test_handwritten(self):
        layer = GeometryGateLayer()
        result = layer(ink_density=0.05, contour_count=2, is_checkbox=False, is_code1=False)
        assert result["glyph_type"] == "handwritten"

    def test_training_mode_returns_probs(self):
        layer = GeometryGateLayer()
        layer.train()
        result = layer(ink_density=0.05, contour_count=5, is_checkbox=False, is_code1=False)
        assert result["mode"] == "model"
        assert "probs" in result
        probs = result["probs"]
        # probs can be nested list (batch dim) or flat list
        flat = probs[0] if isinstance(probs[0], list) else probs
        assert abs(sum(flat) - 1.0) < 0.01


# ── CandidateSelectorLayer ──────────────────────────────────────────────

class TestCandidateSelectorLayer:
    def test_no_candidates(self):
        layer = CandidateSelectorLayer()
        result = layer(candidates=[], glyph_type="printed")
        assert result["decision"] == "accept"
        assert result["escalate"] is False
        assert result["mode"] == "rule"

    def test_single_high_conf(self):
        layer = CandidateSelectorLayer()
        result = layer(
            candidates=[{"value": "test", "conf": 0.95, "engine": "paddle"}],
            glyph_type="printed",
        )
        assert result["decision"] == "accept"
        assert result["escalate"] is False

    def test_handwritten_escalates(self):
        layer = CandidateSelectorLayer()
        result = layer(
            candidates=[{"value": "x", "conf": 0.9, "engine": "paddle"}],
            glyph_type="handwritten",
        )
        assert result["decision"] == "escalate"
        assert result["escalate"] is True

    def test_low_conf_escalates(self):
        layer = CandidateSelectorLayer()
        result = layer(
            candidates=[{"value": "x", "conf": 0.5, "engine": "paddle"}],
            glyph_type="printed",
        )
        assert result["decision"] == "escalate"


# ── SemanticValidatorLayer ──────────────────────────────────────────────

class TestSemanticValidatorLayer:
    def test_closed_field_snap(self):
        layer = SemanticValidatorLayer()
        result = layer(raw="M", snapped="पुरुष", field_key="gender", closed_vocab_fields={"gender"})
        assert result["decision"] == "high_confidence"
        assert result["vocab_match"] == 1.0

    def test_open_field(self):
        layer = SemanticValidatorLayer()
        result = layer(raw="राम", snapped="राम", field_key="member_name", closed_vocab_fields=set())
        assert result["vocab_match"] == 0.0

    def test_empty_snapped(self):
        layer = SemanticValidatorLayer()
        result = layer(raw="", snapped="", field_key="member_name", closed_vocab_fields=set())
        assert result["decision"] == "low_confidence"


# ── EvidenceGateLayer ───────────────────────────────────────────────────

class TestEvidenceGateLayer:
    def test_high_score_auto(self):
        layer = EvidenceGateLayer()
        result = layer(conf_visual=0.95, p_prior=1.0, s_spatial=1.0, c_consistency=1.0)
        assert result["composite_score"] >= 0.88
        assert result["route"] == "auto"
        assert result["requires_human"] is False
        assert result["mode"] == "rule"

    def test_low_score_flagged(self):
        layer = EvidenceGateLayer()
        result = layer(conf_visual=0.2, p_prior=0.5, s_spatial=0.5, c_consistency=0.5)
        assert result["composite_score"] < 0.88
        assert result["route"] == "low_confidence"
        assert result["requires_human"] is True

    def test_score_bounds(self):
        layer = EvidenceGateLayer()
        for cv, pp, ss, cc in [(0, 0, 0, 0), (1, 1, 1, 1), (0.5, 0.5, 0.5, 0.5)]:
            result = layer(cv, pp, ss, cc)
            assert 0.0 <= result["composite_score"] <= 1.0


# ── HouseholdQALayer ────────────────────────────────────────────────────

class TestHouseholdQALayer:
    def test_valid_household(self):
        layer = HouseholdQALayer()
        members = [
            {"relation": "स्वयं", "gender": "पुरुष", "age": 35},
            {"relation": "पत्नी", "gender": "महिला", "age": 30},
            {"relation": "बेटा", "gender": "पुरुष", "age": 10},
        ]
        result = layer(members=members, relations=[m.get("relation", "") for m in members])
        assert "member_decisions" in result
        assert len(result["member_decisions"]) == 3
        assert all(d["mode"] == "rule" for d in result["member_decisions"])

    def test_wife_male_flagged(self):
        layer = HouseholdQALayer()
        members = [
            {"relation": "स्वयं", "gender": "पुरुष", "age": 35},
            {"relation": "पत्नी", "gender": "पुरुष", "age": 30},
        ]
        result = layer(members=members, relations=[m.get("relation", "") for m in members])
        wife = result["member_decisions"][1]
        assert wife["decision"] == "anomaly"
        assert wife["confidence"] == 0.95

    def test_father_under_18(self):
        layer = HouseholdQALayer()
        members = [
            {"relation": "स्वयं", "gender": "पुरुष", "age": 35},
            {"relation": "पिता", "gender": "पुरुष", "age": 15},
        ]
        result = layer(members=members, relations=[m.get("relation", "") for m in members])
        pita = result["member_decisions"][1]
        assert pita["decision"] == "anomaly"

    def test_no_head(self):
        layer = HouseholdQALayer()
        members = [{"relation": "बेटा", "gender": "पुरुष", "age": 10}]
        result = layer(members=members, relations=[m.get("relation", "") for m in members])
        head_anom = [d for d in result["member_decisions"] if d["row_idx"] == -1]
        assert len(head_anom) == 1
        assert head_anom[0]["decision"] == "critical"


# ── LayaPipeline ────────────────────────────────────────────────────────

class TestLayaPipeline:
    def test_process_cell_gender(self):
        from ocr_platform.laya.config import LayaConfig
        from ocr_platform.laya.pipeline import LayaPipeline
        pipeline = LayaPipeline(config=LayaConfig(device="cpu"))
        cell = {
            "cell_id": "test_0_0", "row_idx": 0, "col_idx": 0,
            "field_key": "gender", "geometry": {},
        }
        ocr_result = {
            "candidates": [{"value": "M", "conf": 0.9, "engine": "paddle"}],
            "resolved": "M",
        }
        result = pipeline.process_cell(
            cell=cell, ocr_result=ocr_result, final_value="पुरुष",
            is_ditto=False, conf_visual=0.9, s_spatial=1.0, c_consistency=1.0,
            field_key="gender", closed_vocab_fields={"gender"},
        )
        assert result.field_key == "gender"
        assert result.glyph_type in GeometryGateLayer.LABELS
        assert 0.0 <= result.composite_score <= 1.0
        assert result.route in ("auto", "low_confidence")
        assert "laya_layers" in result.__dict__

    def test_process_household(self):
        from ocr_platform.laya.config import LayaConfig
        from ocr_platform.laya.pipeline import LayaPipeline
        pipeline = LayaPipeline(config=LayaConfig(device="cpu"))
        members = [{"relation": "स्वयं", "gender": "पुरुष", "age": 40}]
        result = pipeline.process_household(members=members, relations=["स्वयं"])
        assert "member_decisions" in result

    def test_state_dict_roundtrip(self):
        from ocr_platform.laya.config import LayaConfig
        from ocr_platform.laya.pipeline import LayaPipeline
        pipeline = LayaPipeline(config=LayaConfig(device="cpu"))
        state = pipeline.state_dict()
        assert "geometry_gate" in state
        assert "candidate_selector" in state
        assert "semantic_validator" in state
        assert "evidence_gate" in state
        assert "household_qa" in state
