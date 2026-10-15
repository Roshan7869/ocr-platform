"""Classified fixture loader — fail-closed Gate G2.

Reads ``fixtures/fixture_manifest.json``, enforces per-entry classification
(``synthetic`` | ``approved_redacted``), verifies the sha256 of the exact
artifact bytes, and rejects everything else. Fail-closed: unknown fixture id,
missing hash, hash mismatch, unclassified/expired entries, wildcard paths, and
paths escaping the fixture root all raise a typed :class:`FixtureError` —
unchecked paths are never returned.

Stdlib only.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

MANIFEST_RELATIVE_PATH = Path("fixtures/fixture_manifest.json")
MANIFEST_ENV_ROOT = "OCR_FIXTURE_ROOT"

ALLOWED_CLASSIFICATIONS = frozenset({"synthetic", "approved_redacted"})
ALLOWED_SPLITS = frozenset({"train", "calibration", "test", "holdout", None})

#: Fields every manifest entry must carry. Everything else is optional metadata.
REQUIRED_FIELDS = (
    "fixture_id",
    "path",
    "content_hash_sha256",
    "classification",
    "template_version",
)


class FixtureError(Exception):
    """Base error for all fail-closed fixture rejections."""


class FixtureManifestError(FixtureError):
    """Manifest itself is unreadable or structurally invalid."""


class UnknownFixtureError(FixtureError):
    """No entry with the requested fixture id exists in the manifest."""


class FixtureHashMissingError(FixtureError):
    """Entry carries no content hash — cannot verify integrity."""


class FixtureHashMismatchError(FixtureError):
    """Artifact bytes do not match the manifest sha256 (moved/tampered file)."""


class FixtureClassificationError(FixtureError):
    """Entry classification is missing, unknown, or lacks required approvals."""


class FixtureExpiredError(FixtureError):
    """Entry expiry is in the past."""


@dataclass(frozen=True)
class FixtureRef:
    """A validated fixture reference. Only obtainable via the gated loaders."""

    fixture_id: str
    path: Path
    content_hash_sha256: str
    classification: str
    template_version: str
    role: str | None = None
    split: str | None = None


def _repo_root() -> Path:
    """Repo root inferred from this file's location (``src/ocr_platform/...``)."""
    return Path(__file__).resolve().parents[3]


def _fixture_root(explicit: Path | str | None = None) -> Path:
    """Base directory artifact paths resolve against.

    Explicit ``root`` wins, then ``$OCR_FIXTURE_ROOT``, else the repo root.
    """
    if explicit is not None:
        return Path(explicit).resolve()
    override = os.environ.get(MANIFEST_ENV_ROOT)
    if override:
        return Path(override).resolve()
    return _repo_root()


def _default_manifest_path() -> Path:
    return _fixture_root() / MANIFEST_RELATIVE_PATH


def load_manifest(manifest_path: Path | str | None = None) -> dict[str, Any]:
    """Read and parse the manifest JSON. Raises :class:`FixtureManifestError`."""
    path = Path(manifest_path) if manifest_path is not None else _default_manifest_path()
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise FixtureManifestError(f"Cannot read fixture manifest: {path}") from exc
    try:
        manifest = json.loads(text)
    except json.JSONDecodeError as exc:
        raise FixtureManifestError(f"Fixture manifest is not valid JSON: {path}") from exc
    if not isinstance(manifest, dict) or not isinstance(manifest.get("fixtures"), list):
        raise FixtureManifestError(
            f"Fixture manifest must be an object with a 'fixtures' list: {path}"
        )
    return manifest


def _parse_expiry(value: Any, fixture_id: str) -> datetime | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise FixtureManifestError(f"Fixture '{fixture_id}': expiry must be ISO-8601 text")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise FixtureManifestError(f"Fixture '{fixture_id}': unparseable expiry {value!r}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def _check_entry_fields(entry: Any) -> dict[str, Any]:
    if not isinstance(entry, dict):
        raise FixtureManifestError("Fixture manifest entry must be an object")
    fixture_id = entry.get("fixture_id", "<missing-id>")
    for field in REQUIRED_FIELDS:
        if entry.get(field) in (None, ""):
            if field == "content_hash_sha256":
                raise FixtureHashMissingError(
                    f"Fixture '{fixture_id}': missing content_hash_sha256"
                )
            raise FixtureManifestError(f"Fixture '{fixture_id}': missing field '{field}'")
    return entry


def _check_classification(entry: dict[str, Any]) -> None:
    fixture_id = entry["fixture_id"]
    classification = entry["classification"]
    if classification not in ALLOWED_CLASSIFICATIONS:
        raise FixtureClassificationError(
            f"Fixture '{fixture_id}': unclassified or unknown classification "
            f"{classification!r} (allowed: {sorted(ALLOWED_CLASSIFICATIONS)})"
        )
    if classification == "approved_redacted" and not (
        entry.get("redaction_method") and entry.get("redaction_approver")
    ):
        raise FixtureClassificationError(
            f"Fixture '{fixture_id}': approved_redacted requires "
            "redaction_method + redaction_approver"
        )


def _check_expiry(entry: dict[str, Any]) -> None:
    expiry = _parse_expiry(entry.get("expiry"), entry["fixture_id"])
    if expiry is not None and expiry <= datetime.now(UTC):
        raise FixtureExpiredError(f"Fixture '{entry['fixture_id']}': expired at {entry['expiry']}")


def _resolve_artifact(entry: dict[str, Any], root: Path) -> Path:
    fixture_id = entry["fixture_id"]
    rel = entry["path"]
    if not isinstance(rel, str) or rel == "":
        raise FixtureManifestError(f"Fixture '{fixture_id}': path must be non-empty text")
    if "*" in rel or "?" in rel:
        raise FixtureManifestError(
            f"Fixture '{fixture_id}': wildcard paths are not loadable: {rel!r}"
        )
    candidate = (root / rel).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise FixtureManifestError(
            f"Fixture '{fixture_id}': path escapes fixture root: {rel!r}"
        ) from exc
    if not candidate.is_file():
        raise FixtureManifestError(f"Fixture '{fixture_id}': artifact not found: {candidate}")
    return candidate


def _verify_hash(artifact: Path, expected: str, fixture_id: str) -> None:
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    if digest.lower() != str(expected).lower():
        raise FixtureHashMismatchError(
            f"Fixture '{fixture_id}': sha256 mismatch for {artifact} "
            f"(manifest {expected}, actual {digest})"
        )


def _validate_entry(entry: Any, root: Path) -> FixtureRef:
    """Run every fail-closed gate on one manifest entry and return its ref."""
    checked = _check_entry_fields(entry)
    _check_classification(checked)
    _check_expiry(checked)
    split = checked.get("split")
    if split not in ALLOWED_SPLITS:
        raise FixtureManifestError(f"Fixture '{checked['fixture_id']}': unknown split {split!r}")
    artifact = _resolve_artifact(checked, root)
    _verify_hash(artifact, checked["content_hash_sha256"], checked["fixture_id"])
    return FixtureRef(
        fixture_id=checked["fixture_id"],
        path=artifact,
        content_hash_sha256=checked["content_hash_sha256"],
        classification=checked["classification"],
        template_version=checked["template_version"],
        role=checked.get("role"),
        split=split,
    )


def load_fixture(
    fixture_id: str,
    manifest_path: Path | str | None = None,
    root: Path | str | None = None,
) -> FixtureRef:
    """Load one classified fixture by id, verifying hash before returning.

    Raises :class:`UnknownFixtureError` for unknown ids and the matching
    :class:`FixtureError` subclass for any gate failure. Never returns an
    unchecked path.
    """
    base = _fixture_root(root)
    manifest = load_manifest(manifest_path)
    for entry in manifest["fixtures"]:
        if isinstance(entry, dict) and entry.get("fixture_id") == fixture_id:
            return _validate_entry(entry, base)
    raise UnknownFixtureError(f"Unknown fixture id: {fixture_id!r}")


def iter_fixtures(
    manifest_path: Path | str | None = None,
    root: Path | str | None = None,
    role: str | None = None,
) -> list[FixtureRef]:
    """Return all manifest entries that pass every gate (optionally by role).

    Entries failing any gate raise instead of being silently skipped.
    """
    base = _fixture_root(root)
    manifest = load_manifest(manifest_path)
    refs = [_validate_entry(entry, base) for entry in manifest["fixtures"]]
    if role is not None:
        refs = [ref for ref in refs if ref.role == role]
    return refs
