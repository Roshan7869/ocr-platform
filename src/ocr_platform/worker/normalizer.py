"""Spatial Normalizer — Devanagari digit conversion, Unicode NFC, phone stripping."""

from __future__ import annotations

import re
import unicodedata

DEV_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
LOOKALIKE = str.maketrans({
    "O": "0", "o": "0", "D": "0", "Q": "0",
    "l": "1", "I": "1", "S": "5", "s": "5",
    "B": "8", "Z": "2",
})
PHONE_RE = re.compile(r"^[6-9]\d{9}$")


def _nfc(text: str | None) -> str:
    if not text:
        return ""
    return unicodedata.normalize("NFC", text.strip())


def _deva_ratio(text: str) -> float:
    s = re.sub(r"\s+", "", _nfc(text))
    if not s:
        return 0.0
    return sum(1 for c in s if "ऀ" <= c <= "ॿ") / max(1, len(s))


class SpatialNormalizer:
    """Normalize raw OCR text: Devanagari digits → ASCII, NFC, strip injected phone numbers."""

    def normalize(self, raw: str, field_key: str) -> str:
        t = _nfc(raw).translate(DEV_DIGITS).translate(LOOKALIKE)
        if field_key == "member_name":
            for num in re.findall(r"\d{10}", t):
                if PHONE_RE.match(num) and _deva_ratio(t.replace(num, "")) >= 0.70:
                    t = t.replace(num, "").strip()
        return t.strip()
