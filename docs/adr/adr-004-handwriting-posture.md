# ADR-004: Handwriting posture — review-only for text fields until dedicated path

## Status

Accepted · 2026-09-24

## Context

Survey forms are hand-filled. Print-oriented PaddleOCR (e.g. Devanagari PP-OCRv5 rec) has no validated accuracy on pen strokes in this corpus. Auto-accepting handwriting would violate the product’s provenance-trust story even if confidence looks high. Checkbox marks already use geometric `marks.py`, not question-text OCR.

## Decision

1. Optional **`handwriting_suspected`** signal on FIELD text observations (stroke/ink heuristics or low print-model trust).  
2. **R0–R0.5:** any suspected handwriting text field → **`disposition=review` only**. Never auto-accept via print model.  
3. Checkboxes/ditto remain geometry + cross_field rules.  
4. Dedicated handwriting recognition, fine-tune, or VLM/hybrid requires a **new ADR** and calibration evidence before accept enablement.  
5. Signal and rule encoded in acceptance policy config (versioned).

## Consequences

- Specs: `engine.py`, `marks.py`, `acceptance_policy*`, `review_candidates`.  
- Calibration metrics report print vs hand separately.  
- Market copy must not claim full auto-extract on handwriting until ADR supersession.

## Alternatives considered

- Trust OCR confidence alone: unproven on this data.  
- LLM/VLM in R0: outside locked R0 scope (Laya remains R4+ flag).  
- Ignore handwriting: silent accuracy failure.
