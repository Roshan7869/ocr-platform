"""Unit tests for the fail-closed fixtures loader (Gate G2).

Every loader gate has a passing test: unknown ids, hash mismatches,
unclassified entries, and expired entries are all rejected — never a path.
"""

from __future__ import annotations

import hashlib
import json

import pytest

from ocr_platform.fixtures.loader import (
    FixtureClassificationError,
    FixtureExpiredError,
    FixtureHashMismatchError,
    UnknownFixtureError,
    load_fixture,
)


def _write_manifest(tmp_path, entries) -> str:
    manifest = tmp_path / "fixture_manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "template_version": "FAMILY_SURVEY_V1",
                "fixtures": entries,
            }
        ),
        encoding="utf-8",
    )
    return str(manifest)


def _entry(fixture_id="t-001", payload=b"synthetic-bytes", **overrides):
    artifact_hash = hashlib.sha256(payload).hexdigest()
    entry = {
        "fixture_id": fixture_id,
        "path": f"{fixture_id}.bin",
        "content_hash_sha256": artifact_hash,
        "classification": "synthetic",
        "template_version": "FAMILY_SURVEY_V1",
    }
    entry.update(overrides)
    return entry, payload


def _stage(tmp_path, entries_payloads):
    entries = []
    for entry, payload in entries_payloads:
        (tmp_path / entry["path"]).write_bytes(payload)
        entries.append(entry)
    return _write_manifest(tmp_path, entries)


def test_valid_synthetic_entry_loads(tmp_path):
    entry, payload = _entry()
    manifest = _stage(tmp_path, [(entry, payload)])
    ref = load_fixture("t-001", manifest_path=manifest, root=tmp_path)
    assert ref.fixture_id == "t-001"
    assert ref.classification == "synthetic"
    assert ref.path.read_bytes() == payload


def test_tampered_bytes_rejected(tmp_path):
    entry, payload = _entry()
    manifest = _stage(tmp_path, [(entry, payload)])
    (tmp_path / entry["path"]).write_bytes(payload + b"tampered")
    with pytest.raises(FixtureHashMismatchError):
        load_fixture("t-001", manifest_path=manifest, root=tmp_path)


def test_unknown_id_rejected(tmp_path):
    entry, payload = _entry()
    manifest = _stage(tmp_path, [(entry, payload)])
    with pytest.raises(UnknownFixtureError):
        load_fixture("no-such-fixture", manifest_path=manifest, root=tmp_path)


def test_unclassified_entry_rejected(tmp_path):
    entry, payload = _entry(classification="raw_scan")
    manifest = _stage(tmp_path, [(entry, payload)])
    with pytest.raises(FixtureClassificationError):
        load_fixture("t-001", manifest_path=manifest, root=tmp_path)


def test_expired_entry_rejected(tmp_path):
    entry, payload = _entry(expiry="2000-01-01T00:00:00+00:00")
    manifest = _stage(tmp_path, [(entry, payload)])
    with pytest.raises(FixtureExpiredError):
        load_fixture("t-001", manifest_path=manifest, root=tmp_path)


def test_real_smoke_fixture_passes_gates():
    ref = load_fixture("smoke-001")
    assert ref.classification == "synthetic"
    assert ref.template_version == "FAMILY_SURVEY_V1"
    assert ref.path.is_file()
