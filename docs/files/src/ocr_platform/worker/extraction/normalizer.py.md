# src/ocr_platform/worker/extraction/normalizer.py

## Role

Field-type-specific normalization profiles applied to raw evidence without mutating raw values: NAME (Devanagari recognizer output as-is + trim), INTEGER, DATE, MOBILE/digits, coded_text, income shorthand (`10K`→10000 with raw kept), Devanagari word numbers only if approved rule exists.

## Contracts

- **Invariants:**
  - Raw input always preserved on decision/observation (`*_raw` / raw text).
  - Different profiles for name vs integer vs date vs mobile — not one pipeline (design §3).
  - Numeric normalization does not blindly strip separators or reinterpret unknown codes.
  - `10K` → 10000; ambiguous `1OK` → VALUE_REVIEW unless unambiguous context.
  - `"thirty"` for age → review unless verified conversion rule version exists.
  - Unicode normalization + whitespace collapse + punctuation-preserving compare only where policy says (native/OCR equality lives in policy, not silent here).
  - No dictionary matching of names to force similarity.
- **Outputs:** normalized candidates + rule version IDs attached for decisions.
- **Forbidden:** overwriting raw; auto-mapping unknown vocabulary codes.

## Infrastructure

- **Python deps:** pydantic, unicodedata
- **Config/artifacts:** profiles keyed by `field_types.yaml` types; rules version in fingerprint
- **Models/external:** none
- **Env vars:** none

## Depends on

- **Calls:** `schemas/decision.py`, `schemas/evidence.py`
- **Called by:** `worker/pipeline.py`, `worker/extraction/vocabulary.py` (codes), `worker/extraction/acceptance_policy.py`

## Tests

- Unit: each profile preserves raw; golden cases from design (10K, 30, 1.5, H/h)
- Unit: no silent strip of ambiguous OCR letter O vs zero
- Unit: native exact-match normalization used only for comparison path
- Integration: R0 normalization rules tests (design unit list)

## Milestone

R0

## Status

SPEC

## Owner

engineering
