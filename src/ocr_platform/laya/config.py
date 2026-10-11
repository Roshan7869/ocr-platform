"""Laya configuration dataclass."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class LayaConfig:
    """Hyperparameters for the Laya multi-layer decision pipeline."""

    device: str = "cpu"
    hidden_dim: int = 32
    dropout: float = 0.1
    max_members: int = 20
    evidence_threshold: float = 0.88
    model_dir: str | None = None
    weights: dict = field(
        default_factory=lambda: {
            "visual": 0.40,
            "prior": 0.35,
            "spatial": 0.15,
            "consistency": 0.10,
        }
    )
