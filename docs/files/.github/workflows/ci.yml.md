# .github/workflows/ci.yml

## Role

Production CI pipeline for the R0 exit gate: lint, unit/contract/property tests,
integration + determinism on merge/nightly, and the docs contract gate.

## Contracts

Four jobs (`lint` → `test` → `integration` → `docs-gate`) exactly as specified in
`docs/ci-spec.md §6`. Python 3.11 pinned on all jobs to match production.
PR runs lint + unit + contract + property + docs-gate only; merge/nightly add
integration and the spike determinism check. Release Docker builds remain planned
per `docs/ci-spec.md §2.8`. Does not disturb `benchmark.yml`.

## Infrastructure

GitHub Actions Ubuntu runners; checkout/setup-python actions; pip dependencies.

## Depends on

`docs/ci-spec.md §6`; pyproject dev extras; ruff; pytest suites; `scripts/run_spike.py`;
`scripts/check_docs_contract.py`.

## Tests

YAML parses via `yaml.safe_load`; job DAG matches `docs/ci-spec.md §6` (lint → test
→ integration gated on push/schedule; docs-gate standalone).

## Milestone

R0 exit gate.

## Status

IMPLEMENTED (hosted workflow has not yet run).

## Owner

engineering.
