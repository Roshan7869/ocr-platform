# ADR-005: Fail-closed acceptance; auto-accept requires spike **and** calibration evidence

## Status

Accepted · 2026-09-24

## Context

Design already disables `ocr_auto_accept_enabled` / `native_auto_accept_enabled` in R0 until spike. Spike alone only proves **compatibility** (models run, deterministic enough) — not **accuracy**. Market risk is flipping flags on a green spike while field precision is poor.

## Decision

1. Default: **conservative review**; no third “guess” disposition.  
2. Flag flip requires **both**:  
   - spike matrix **go**, and  
   - calibration report per `docs/accuracy-plan.md` (precision ≥97% proposed on would-be auto-accept, review-rate ceiling, holdout untouched, provenance 100%).  
3. Flip = versioned `AcceptancePolicy-v1` change + configuration fingerprint bump; report stored with run artifacts.  
4. Provenance validator remains zero-tolerance regardless of flags.

## Consequences

- No marketing of auto-extract until calibration gate.  
- `scripts/calibrate_policy.py` planned in market-roadmap backlog.  
- Tests: disabled gates force review (already in acceptance_policy specs).

## Alternatives considered

- Flip on spike only: accuracy theater.  
- Always manual: no product path; rejected in favor of gated flip.  
- Continuous online learning of thresholds: R5+ territory.
