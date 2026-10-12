"""Worker modules: morphology, normalizer, semantic, arbiter, validation.

Lazy imports — modules with heavy deps (cv2, torch) are only imported
when accessed, so lightweight modules like bayesian can be used standalone.
"""
from __future__ import annotations

# Lightweight modules (no heavy deps)
from ocr_platform.worker.bayesian import BayesianScorer, BayesianConfig, FieldPrior

# Modules requiring cv2 — imported lazily via __getattr__
_LAZY = {
    "Arbiter": "ocr_platform.worker.arbiter",
    "ArbiterDecision": "ocr_platform.worker.arbiter",
    "ContourMorphologyEngine": "ocr_platform.worker.morphology",
    "GeometryProfile": "ocr_platform.worker.morphology",
    "SpatialNormalizer": "ocr_platform.worker.normalizer",
    "SemanticEngine": "ocr_platform.worker.semantic",
    "CLOSED_VOCAB": "ocr_platform.worker.semantic",
    "HindiVLMEngine": "ocr_platform.worker.hindi_vlm",
    "RelationalQA": "ocr_platform.worker.validation.qa",
}

_loaded: dict[str, Any] = {}


def __getattr__(name: str) -> Any:
    if name in _loaded:
        return _loaded[name]
    if name in _LAZY:
        import importlib
        mod = importlib.import_module(_LAZY[name])
        obj = getattr(mod, name)
        _loaded[name] = obj
        return obj
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "BayesianScorer", "BayesianConfig", "FieldPrior",
    "Arbiter", "ArbiterDecision",
    "ContourMorphologyEngine", "GeometryProfile",
    "SpatialNormalizer",
    "SemanticEngine", "CLOSED_VOCAB",
    "HindiVLMEngine",
    "RelationalQA",
]
