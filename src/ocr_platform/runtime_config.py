"""Fail-closed loader for ``configs/runtime.yaml``.

Parses the global render + coordinate + comparison-policy settings into a typed
object and contributes them to ``configuration_fingerprint``. Fail-closed: any
unknown key or any missing required key raises :class:`RuntimeConfigError` —
never a silent default. The normative key set lives in
``docs/files/configs/runtime.yaml.md``; this module enforces it.

Canonical JSON handling is owned by
``ocr_platform.worker.provenance.hashing`` — this module reuses
:func:`content_hash` / :func:`canonical_json` and asserts the file's
``comparison_policy.canonical_json`` block matches that implementation's
behavior (``sort_keys=True``, ``ensure_ascii=False``, ``repr`` floats).

Requires ``pyyaml``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ocr_platform.worker.provenance.hashing import canonical_json, content_hash

#: Single source of truth for the page-space coordinate convention.
COORDINATE_SYSTEM = "image_top_left_normalized"

#: Exact top-level sections. Anything else is rejected; anything missing fails closed.
REQUIRED_TOP_KEYS = ("render", "coordinates", "preprocess", "comparison_policy")

#: Exact required keys per section (normative R0 shape).
REQUIRED_SUB_KEYS: dict[str, tuple[str, ...]] = {
    "render": ("dpi", "colorspace", "rasterizer", "crop_padding_px"),
    "coordinates": ("coordinate_system",),
    "preprocess": ("deskew", "binarize"),
    "comparison_policy": (
        "artifact_byte_equality",
        "cpu_render_pixel_tolerance",
        "gpu_float_abs_tol",
        "gpu_float_rel_tol",
        "canonical_json",
    ),
}

#: The canonical-JSON policy ``hashing.py`` implements. The config must agree
#: exactly — a drift here would fork the comparison implementation.
CANONICAL_JSON_POLICY: dict[str, Any] = {
    "sort_keys": True,
    "ensure_ascii": False,
    "float_format": "repr",
}


class RuntimeConfigError(ValueError):
    """Raised when ``runtime.yaml`` violates the normative key set or types."""


def _repo_root() -> Path:
    """Repo root inferred from this file's location (``src/ocr_platform/...``)."""
    return Path(__file__).resolve().parents[2]


DEFAULT_RUNTIME_CONFIG_PATH = _repo_root() / "configs" / "runtime.yaml"


def _require_mapping(value: Any, what: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RuntimeConfigError(f"runtime.yaml: {what} must be a mapping")
    return value


def _check_exact_keys(mapping: dict[str, Any], required: tuple[str, ...], what: str) -> None:
    required_set = set(required)
    actual_set = set(mapping)
    missing = required_set - actual_set
    if missing:
        raise RuntimeConfigError(f"runtime.yaml: {what} missing required keys: {sorted(missing)}")
    unknown = actual_set - required_set
    if unknown:
        raise RuntimeConfigError(f"runtime.yaml: {what} has unknown keys: {sorted(unknown)}")


def _check_bool(mapping: dict[str, Any], key: str, what: str) -> None:
    if not isinstance(mapping[key], bool):
        raise RuntimeConfigError(f"runtime.yaml: {what}.{key} must be a boolean")


def _validate(render: dict[str, Any], section: str) -> None:
    _check_exact_keys(render, REQUIRED_SUB_KEYS[section], section)


def _validate_render(render: dict[str, Any]) -> None:
    _validate(render, "render")
    dpi = render["dpi"]
    if isinstance(dpi, bool) or not isinstance(dpi, int) or dpi <= 0:
        raise RuntimeConfigError("runtime.yaml: render.dpi must be a positive integer")
    for key in ("colorspace", "rasterizer"):
        if not isinstance(render[key], str) or not render[key]:
            raise RuntimeConfigError(f"runtime.yaml: render.{key} must be non-empty text")
    pad = render["crop_padding_px"]
    if isinstance(pad, bool) or not isinstance(pad, int) or pad < 0:
        raise RuntimeConfigError(
            "runtime.yaml: render.crop_padding_px must be a non-negative integer"
        )


def _validate_coordinates(coordinates: dict[str, Any]) -> None:
    _validate(coordinates, "coordinates")
    if coordinates["coordinate_system"] != COORDINATE_SYSTEM:
        raise RuntimeConfigError(
            f"runtime.yaml: coordinates.coordinate_system must be {COORDINATE_SYSTEM!r}"
        )


def _validate_preprocess(preprocess: dict[str, Any]) -> None:
    _validate(preprocess, "preprocess")
    _check_bool(preprocess, "deskew", "preprocess")
    _check_bool(preprocess, "binarize", "preprocess")


def _validate_comparison_policy(policy: dict[str, Any]) -> None:
    _validate(policy, "comparison_policy")
    _check_bool(policy, "artifact_byte_equality", "comparison_policy")
    tol = policy["cpu_render_pixel_tolerance"]
    if isinstance(tol, bool) or not isinstance(tol, int) or tol != 0:
        raise RuntimeConfigError(
            "runtime.yaml: comparison_policy.cpu_render_pixel_tolerance must be 0 in R0"
        )
    for key in ("gpu_float_abs_tol", "gpu_float_rel_tol"):
        value = policy[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
            raise RuntimeConfigError(
                f"runtime.yaml: comparison_policy.{key} must be a positive number"
            )
    declared = policy["canonical_json"]
    if not isinstance(declared, dict) or dict(declared) != CANONICAL_JSON_POLICY:
        raise RuntimeConfigError(
            "runtime.yaml: comparison_policy.canonical_json must match "
            f"{CANONICAL_JSON_POLICY} (worker/provenance/hashing.py behavior)"
        )


@dataclass(frozen=True)
class RuntimeConfig:
    """Validated runtime settings. Only obtainable via :func:`load_runtime_config`."""

    render: dict[str, Any] = field(compare=True)
    coordinates: dict[str, Any] = field(compare=True)
    preprocess: dict[str, Any] = field(compare=True)
    comparison_policy: dict[str, Any] = field(compare=True)
    fingerprint: str = field(compare=False)
    path: Path = field(compare=False)

    def as_dict(self) -> dict[str, Any]:
        """Plain-dict view of the settings (fingerprint input)."""
        return {
            "render": dict(self.render),
            "coordinates": dict(self.coordinates),
            "preprocess": dict(self.preprocess),
            "comparison_policy": dict(self.comparison_policy),
        }


def configuration_fingerprint(settings: dict[str, Any]) -> str:
    """sha256 over the canonical JSON of the settings (via ``hashing.py``)."""
    return content_hash(canonical_json(settings))


def load_runtime_config(path: Path | str | None = None) -> RuntimeConfig:
    """Load and fail-closed-validate ``configs/runtime.yaml``.

    Raises :class:`RuntimeConfigError` for unreadable files, non-mapping
    content, unknown keys, missing required keys, or type violations.
    """
    resolved = Path(path) if path is not None else DEFAULT_RUNTIME_CONFIG_PATH
    try:
        text = resolved.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeConfigError(f"Cannot read runtime config: {resolved}") from exc
    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise RuntimeConfigError(f"runtime.yaml is not valid YAML: {resolved}") from exc
    top = _require_mapping(raw, "top level")
    _check_exact_keys(top, REQUIRED_TOP_KEYS, "top level")
    sections = {
        name: _require_mapping(top[name], f"section {name!r}") for name in REQUIRED_TOP_KEYS
    }
    _validate_render(sections["render"])
    _validate_coordinates(sections["coordinates"])
    _validate_preprocess(sections["preprocess"])
    _validate_comparison_policy(sections["comparison_policy"])
    settings = {name: dict(sections[name]) for name in REQUIRED_TOP_KEYS}
    return RuntimeConfig(
        render=settings["render"],
        coordinates=settings["coordinates"],
        preprocess=settings["preprocess"],
        comparison_policy=settings["comparison_policy"],
        fingerprint=configuration_fingerprint(settings),
        path=resolved,
    )
