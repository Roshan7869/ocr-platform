"""Arbiter — deterministic candidate selection.

Selects the highest-confidence OCR candidate.
No human review UI; all decisions are automatic with provenance.
"""

from __future__ import annotations

from typing import Any


class ArbiterDecision:
    """Structured arbiter output."""

    __slots__ = ("cell_id", "conf", "decision", "engine", "field_key", "value")

    def __init__(
        self, cell_id: str, field_key: str, decision: str, value: str, engine: str, conf: float
    ):
        self.cell_id = cell_id
        self.field_key = field_key
        self.decision = decision
        self.value = value
        self.engine = engine
        self.conf = conf

    def to_dict(self) -> dict[str, Any]:
        return {
            "cell_id": self.cell_id,
            "field_key": self.field_key,
            "decision": self.decision,
            "value": self.value,
            "engine": self.engine,
            "conf": self.conf,
        }


class Arbiter:
    """Pick best OCR candidate deterministically."""

    def decide(self, cell_id: str, fk: str, ocr_result: dict[str, Any]) -> ArbiterDecision:
        candidates = ocr_result.get("candidates", [])
        if not candidates:
            return ArbiterDecision(
                cell_id=cell_id, field_key=fk, decision="NULL", value="", engine="none", conf=0.0
            )
        best = max(candidates, key=lambda c: c.get("conf", 0.0))
        dec = "ACCEPT" if len(candidates) == 1 else "ACCEPT_MULTI"
        return ArbiterDecision(
            cell_id=cell_id,
            field_key=fk,
            decision=dec,
            value=best.get("value", ""),
            engine=best.get("engine", "unknown"),
            conf=best.get("conf", 0.0),
        )
