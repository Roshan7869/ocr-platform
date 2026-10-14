"""Canonical JSON serialization and content-addressed hashing.

Single source of truth for turning a semantic object into bytes and bytes into
a sha256 hex digest. Every provenance node, template child file, configuration
fingerprint and reproducibility comparison goes through :func:`canonical_json`
or :func:`content_hash`, so two runs of the same computation agree bit-for-bit.

Policies decided here (and pinned by tests, not by loosening hashes):

* **Key order independence** — object keys are sorted, so ``{"a":1,"b":2}`` and
  ``{"b":2,"a":1}`` produce identical bytes.
* **Key stringification** — JSON object keys must be strings, so non-string keys
  are stringified before sorting. A collision after stringification
  (``{1: "a", "1": "b"}``) is an error, never a silent last-write-wins.
* **Number formatting** — floats use Python's shortest round-trip ``repr``.
  ``-0.0`` normalizes to ``0.0`` so signed zero cannot fork a hash. Integers are
  never rewritten as floats.
* **Non-finite floats are rejected** — ``NaN``/``Infinity`` are not valid JSON
  and are never silently dropped nor emitted as the non-standard tokens.
* **Tuples and lists are the same array** — ``(1, 2)`` and ``[1, 2]`` hash
  identically; sequences are semantic, not positional in memory.
* **Raw bytes are not JSON** — pass them straight to :func:`content_hash`.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any

HASH_ALGORITHM = "sha256"
CANONICAL_ALGORITHM_ID = "ocr-platform/canonical-json-sha256/v1"

_HEX_DIGITS = frozenset("0123456789abcdef")


class CanonicalJsonError(ValueError):
    """Raised when an object cannot be encoded as canonical JSON."""


def stable_number(value: Any) -> Any:
    """Normalize one scalar for canonical JSON.

    ``bool`` is checked before ``int`` because ``bool`` subclasses ``int`` and
    must stay a JSON boolean. Finite floats normalize ``-0.0`` to ``0.0``.
    Non-finite floats raise instead of being silently dropped.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise CanonicalJsonError(
                f"non-finite float {value!r} cannot be canonically encoded; "
                "resolve it before hashing"
            )
        return 0.0 if value == 0.0 else value
    return value


def _stringify_key(key: Any) -> str:
    if isinstance(key, str):
        return key
    return json.dumps(stable_number(key), ensure_ascii=False)


def _canonicalize(obj: Any) -> Any:
    if isinstance(obj, dict):
        encoded: dict[str, Any] = {}
        for key, value in obj.items():
            name = _stringify_key(key)
            if name in encoded:
                raise CanonicalJsonError(
                    f"key {name!r} collides after stringification; use distinct string keys"
                )
            encoded[name] = _canonicalize(value)
        return encoded
    if isinstance(obj, (list, tuple)):
        return [_canonicalize(item) for item in obj]
    if isinstance(obj, (bytes, bytearray, memoryview)):
        raise CanonicalJsonError(
            "bytes are not canonical-JSON encodable; hash them with content_hash()"
        )
    if isinstance(obj, float):
        return stable_number(obj)
    return obj


def canonical_json(obj: Any) -> bytes:
    """Serialize *obj* to canonical UTF-8 JSON bytes.

    Same semantic object in, same bytes out, independent of dict insertion
    order. Raises :class:`CanonicalJsonError` (a ``ValueError``) for objects
    that cannot be encoded without a silent policy decision.
    """
    return json.dumps(
        _canonicalize(obj),
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def content_hash(data: bytes | bytearray | memoryview | str | Any) -> str:
    """Return the sha256 hex digest of *data*.

    ``bytes``-like input is hashed as-is. ``str`` is UTF-8 encoded first, so
    ``content_hash("abc") == content_hash(b"abc")``. Anything else is
    canonicalized to JSON and then hashed, so equal semantic objects always
    produce equal digests.
    """
    if isinstance(data, (bytes, bytearray, memoryview)):
        payload = bytes(data)
    elif isinstance(data, str):
        payload = data.encode("utf-8")
    else:
        payload = canonical_json(data)
    return hashlib.sha256(payload).hexdigest()


def is_content_hash(value: Any) -> bool:
    """True when *value* is a lowercase sha256 hex digest."""
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in _HEX_DIGITS for character in value)
    )
