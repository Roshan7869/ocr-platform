"""Spatial Normalizer — Devanagari digit conversion, Unicode NFC, phone stripping,
income parsing, date validation, education normalization."""

from __future__ import annotations

import re
import unicodedata

DEV_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
LOOKALIKE = str.maketrans(
    {
        "O": "0",
        "o": "0",
        "D": "0",
        "Q": "0",
        "l": "1",
        "I": "1",
        "S": "5",
        "s": "5",
        "B": "8",
        "Z": "2",
    }
)
PHONE_RE = re.compile(r"[6-9]\d{9}")

INCOME_RE = re.compile(r"(\d+)\s*[kKक]")
DATE_RE = re.compile(r"(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2,4})")


def _nfc(text: str | None) -> str:
    if not text:
        return ""
    return unicodedata.normalize("NFC", text.strip())


def _deva_ratio(text: str) -> float:
    s = re.sub(r"\s+", "", _nfc(text))
    if not s:
        return 0.0
    return sum(1 for c in s if "ऀ" <= c <= "ॿ") / max(1, len(s))


def _parse_income(raw: str) -> tuple[str, str]:
    """Parse income like '10K', '12K', '1lK' → ('12000', 'income_parsed')."""
    m = INCOME_RE.search(raw)
    if m:
        val = int(m.group(1)) * 1000
        return str(val), "income_parsed"
    return raw, ""


def _parse_date(raw: str) -> tuple[str, str]:
    """Parse date DD/MM/YY or DD/MM/YYYY. Returns (normalized, 'future_date' | '')."""
    m = DATE_RE.search(raw.replace(" ", ""))
    if not m:
        return raw, ""
    d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if y < 100:
        y += 2000
    from datetime import date

    try:
        dt = date(y, mo, d)
        today = date.today()
        flag = "future_date" if dt > today else ""
        return dt.isoformat(), flag
    except ValueError:
        return raw, ""


def _normalize_education(raw: str) -> str:
    """Map education OCR values to canonical codes."""
    edu_map = {
        "1": "below_primary",
        "4": "primary",
        "5": "upper_primary",
        "6": "secondary",
        "8": "higher_secondary",
        "10": "matric",
        "11": "inter",
        "12": "sr_secondary",
        "BA": "graduate",
        "MA": "post_graduate",
        "NC": "not_known",
        "NURSERY": "nursery",
        " nursery ": "nursery",
        "nursery": "nursery",
    }
    t = raw.strip().upper()
    return edu_map.get(t, raw)


# Fields that should never receive ditto propagation
NO_DITTO_FIELDS = {
    "education",
    "age",
    "member_name",
    "head_name",
    "mobile",
    "survey_date",
    "monthly_income",
    "occupation",
}

# Integer identifier fields: Devanagari digits translate to ASCII digits that
# may carry leading zeros ("०५" -> "05"). Strip them ("05" -> "5") so numeric
# comparisons and QA rules operate on canonical values instead of crashing
# or mis-sorting on zero-padded strings.
INTEGER_ID_FIELDS = frozenset(
    {
        "sr_no",
        "age",
        "marriage_age",
        "resident_code",
        "ward",
        "ward_no",
        "zone",
        "zone_no",
        "family_count",
    }
)


class SpatialNormalizer:
    """Normalize raw OCR text with field-aware rules."""

    def normalize(self, raw: str, field_key: str) -> str:
        t = _nfc(raw).translate(DEV_DIGITS).translate(LOOKALIKE)
        flag = ""
        was_corrected = False

        # Phone: extract 10-digit number, strip from text
        if field_key in {"mobile", "head_mobile"}:
            phones = PHONE_RE.findall(t)
            if phones:
                t = phones[0]
                flag = "phone_extracted"
            else:
                flag = "phone_missing"
            return t, flag

        # Income: parse K variants
        if field_key == "monthly_income":
            t, flag = _parse_income(t)
            return t, flag

        # Date: parse and validate
        if field_key == "survey_date":
            t, flag = _parse_date(t)
            return t, flag

        # Education: map to canonical codes, never ditto
        if field_key == "education":
            t = _normalize_education(t)
            return t, ""

        # Integer identifiers: strip leading zeros ("05" -> "5").
        # Guarded on non-empty ASCII digits so "" and "-" pass through
        # untouched instead of raising on int().
        if field_key in INTEGER_ID_FIELDS and t and t.isdigit():
            stripped = str(int(t))
            if stripped != t:
                t = stripped
                was_corrected = True
                flag = "leading_zero_stripped"

        # Member name: strip embedded phone numbers
        if field_key == "member_name":
            for num in re.findall(r"\d{10}", t):
                t = t.replace(num, "").strip()
                was_corrected = True

        t = t.strip()
        if was_corrected and not flag:
            flag = "corrected"
        return t, flag
