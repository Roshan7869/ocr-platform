"""LayaPipeline — wires all 5 decision layers into a single forward pass.

Each cell flows through:
  L1 GeometryGate → L2 CandidateSelector → L3 SemanticValidator → L4 EvidenceGate
Household-level:
  L5 HouseholdQA (after all cells)
"""

from __future__ import annotations

import torch
from dataclasses import dataclass, field
from typing import Any

from ocr_platform.laya.config import LayaConfig
from ocr_platform.laya.layers import (
    CandidateSelectorLayer,
    EvidenceGateLayer,
    GeometryGateLayer,
    HouseholdQALayer,
    SemanticValidatorLayer,
)


@dataclass
class CellDecision:
    """Structured decision for one cell after all Laya layers."""
    cell_id: str
    row_idx: int
    col_idx: int
    field_key: str
    glyph_type: str
    geometry_confidence: float
    candidate_decision: str
    escalate: bool
    semantic_decision: str
    semantic_confidence: float
    composite_score: float
    route: str
    requires_human: bool
    evidence_confidence: float
    final_value: str
    laya_layers: dict = field(default_factory=dict)


class LayaPipeline:
    """Multi-layered decision classifier using PyTorch modules.

    All layers live on the same device. Models can be trained end-to-end
    or used frozen for inference.
    """

    def __init__(self, config: LayaConfig | None = None):
        self.config = config or LayaConfig()
        self.device = torch.device(self.config.device)
        self._init_layers()

    def _init_layers(self):
        cfg = self.config
        self.geometry_gate = GeometryGateLayer(hidden=cfg.hidden_dim, dropout=cfg.dropout).to(self.device)
        self.candidate_selector = CandidateSelectorLayer(hidden=cfg.hidden_dim, dropout=cfg.dropout).to(self.device)
        self.semantic_validator = SemanticValidatorLayer(hidden=cfg.hidden_dim, dropout=cfg.dropout).to(self.device)
        self.evidence_gate = EvidenceGateLayer(hidden=cfg.hidden_dim, dropout=cfg.dropout).to(self.device)
        self.household_qa = HouseholdQALayer(
            hidden=cfg.hidden_dim, dropout=cfg.dropout, max_members=cfg.max_members
        ).to(self.device)

    def process_cell(self, cell: dict, ocr_result: dict, final_value: str,
                     is_ditto: bool, conf_visual: float, s_spatial: float,
                     c_consistency: float, field_key: str, closed_vocab_fields: set) -> CellDecision:
        """Run all 4 cell-level Laya layers on a single cell."""
        self.geometry_gate.eval()
        self.candidate_selector.eval()
        self.semantic_validator.eval()
        self.evidence_gate.eval()

        # L1: GeometryGate
        geo = cell.get("geometry", {})
        with torch.no_grad():
            l1 = self.geometry_gate(
                ink_density=geo.get("ink_density", 0.0),
                contour_count=min(geo.get("contour_count", 0) / 20.0, 1.0),
                is_checkbox=geo.get("is_checkbox", False),
                is_code1=geo.get("is_code1_stroke", False),
            )

        # L2: CandidateSelector
        candidates = ocr_result.get("candidates", [])
        with torch.no_grad():
            l2 = self.candidate_selector(candidates=candidates, glyph_type=l1["glyph_type"])

        # L3: SemanticValidator
        raw_text = ocr_result.get("resolved", "")
        snapped = final_value
        with torch.no_grad():
            l3 = self.semantic_validator(
                raw=raw_text, snapped=snapped, field_key=field_key, closed_vocab_fields=closed_vocab_fields
            )

        # L4: EvidenceGate
        if field_key in {"member_name", "head_name", "remarks", "caste", "occupation", "education", "employment_nature", "monthly_income"}:
            p_prior = 1.0
        else:
            p_prior = 0.8
        with torch.no_grad():
            l4 = self.evidence_gate(
                conf_visual=max(0.0, min(1.0, conf_visual)),
                p_prior=p_prior,
                s_spatial=max(0.0, min(1.0, s_spatial)),
                c_consistency=max(0.0, min(1.0, c_consistency)),
            )

        return CellDecision(
            cell_id=cell.get("cell_id", ""),
            row_idx=cell.get("row_idx", 0),
            col_idx=cell.get("col_idx", 0),
            field_key=field_key,
            glyph_type=l1["glyph_type"],
            geometry_confidence=l1["confidence"],
            candidate_decision=l2["decision"],
            escalate=l2["escalate"],
            semantic_decision=l3["decision"],
            semantic_confidence=l3["confidence"],
            composite_score=l4["composite_score"],
            route=l4["route"],
            requires_human=l4["requires_human"],
            evidence_confidence=l4["confidence"],
            final_value=final_value,
            laya_layers={"L1": l1, "L2": l2, "L3": l3, "L4": l4},
        )

    def process_household(self, members: list[dict], relations: list[str]) -> dict:
        """Run L5 HouseholdQA on a complete household."""
        self.household_qa.eval()
        with torch.no_grad():
            l5 = self.household_qa(members=members, relations=relations)
        return l5

    def train_mode(self):
        """Switch all layers to training mode."""
        self.geometry_gate.train()
        self.candidate_selector.train()
        self.semantic_validator.train()
        self.evidence_gate.train()
        self.household_qa.train()

    def eval_mode(self):
        """Switch all layers to eval mode."""
        self.geometry_gate.eval()
        self.candidate_selector.eval()
        self.semantic_validator.eval()
        self.evidence_gate.eval()
        self.household_qa.eval()

    def state_dict(self) -> dict:
        return {
            "geometry_gate": self.geometry_gate.state_dict(),
            "candidate_selector": self.candidate_selector.state_dict(),
            "semantic_validator": self.semantic_validator.state_dict(),
            "evidence_gate": self.evidence_gate.state_dict(),
            "household_qa": self.household_qa.state_dict(),
        }

    def load_state_dict(self, state: dict):
        self.geometry_gate.load_state_dict(state["geometry_gate"])
        self.candidate_selector.load_state_dict(state["candidate_selector"])
        self.semantic_validator.load_state_dict(state["semantic_validator"])
        self.evidence_gate.load_state_dict(state["evidence_gate"])
        self.household_qa.load_state_dict(state["household_qa"])
