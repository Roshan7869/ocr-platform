# ADR-002: Registration = R0 identity + page-box normalize; R0.5 classical affine (pull from R3)

## Status

Accepted · 2026-09-24

## Context

Measured on WARD-42:

- Page box width varies ~79pt across samples; embedded image widths vary ~219px.  
- Page0 pixel correlation across layout batches ≈0.14–0.55; random corpus vs base often <0.30 (down to ≈−0.01).  
- Ink density stable (~0.11–0.15) → same printed form; **content** breaks pixel correlation.

Pure identity registration + `overlap_ratio >= 0.80` will fail closed to review at high rates outside tightly aligned layout refs. Deferring all registration work to historical R3 leaves market accuracy on the table.

## Decision

1. **R0:** `registration_mode=identity` only, plus **explicit canonical page-box normalize** (recorded in provenance — not silent deskew). Scope: smoke/layout refs.  
2. **R0.5 (new milestone):** **classical affine** from form structure (rulings, table grid, LEGEND/ANCHOR), residual threshold, fail-closed if residual high or anchors ambiguous.  
3. R3 enhanced registration remains future refinement, superseded by R0.5 where equal.  
4. Missing/ambiguous registration **never** yields accepted field decisions.

## Consequences

- `registration.py` + `coordinates.py` + `boundaries.py` specs amended for R0.5.  
- `docs/accuracy-plan.md` owns residual pass-rate gates (≥95% pages).  
- Pipeline records transform even when identity.

## Alternatives considered

- Identity only + accept review explosion: fails unit economics.  
- Affine inside R0: delays first extractable path; conflicts with locked sequencing (R0 then R0.5).  
- Template-only normalize without affine: insufficient for corpus corr stats.
