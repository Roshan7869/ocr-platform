# ADR-008: Rollback strategy — feature flags, criteria, and process

## Status

Accepted · 2026-09-27

## Context

R0.5 introduces affine registration (ADR-002). If affine regresses accuracy vs R0 identity, the team needs a documented path back. Without a rollback strategy, the only option is "fix forward" or "revert the commit," which doesn't address runs already produced with affine registration or in-flight jobs.

## Decision

1. **Feature flag for registration mode:** `registration_mode: identity | affine | auto` in `runtime.yaml`. Default `identity` (R0 behavior). R0.5 flips to `affine` or `auto`.
2. **Rollback criteria:** If R0.5 ships and field-level review rate increases by >10% vs R0 baseline on the same dev-gold set, rollback is triggered.
3. **Process:**
   - Flip `registration_mode` to `identity` in `runtime.yaml`
   - Bump `configuration_fingerprint` (automatic via config change)
   - Re-run dev-gold set with identity mode
   - Compare review rate and accuracy metrics
   - If metrics return to R0 baseline, rollback is confirmed
4. **In-flight jobs:** Jobs already queued or running complete with the config they started with. New jobs use the new config.
5. **Data migration:** None required. Runs are immutable records under their `run_id`. Old runs remain valid; they reference the config fingerprint used at run time.
6. **Communication:** If rollback happens, R1 plans that assumed affine registration need to be revised. Document the rollback in the ADR update log.

## Consequences

- `runtime.yaml` gains a `registration_mode` key (normative, part of fingerprint).
- `registration.py` reads the flag and dispatches to identity or affine path.
- Tests verify both paths work and that the flag is respected.
- Rollback is a config change, not a code revert — faster and safer.

## Alternatives considered

- **No rollback path (fix forward):** Rejected. If affine regresses, we need a way back without a code revert.
- **Code revert:** Rejected. Doesn't address in-flight jobs or already-produced runs.
- **Parallel running (identity + affine, pick best):** Rejected. Doubles compute cost; doesn't solve the problem of which to use in production.

## Update log

| Date | Change |
|---|---|
| 2026-09-27 | Initial ADR: feature flag, rollback criteria, process |
