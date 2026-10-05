# .github/workflows/benchmark.yml

## Role

Run the implemented benchmark's regression checks on pushes and pull requests.

## Contracts

Use Python 3.11 and dev/benchmark extras; run lint, format checks, and tests.
No real survey data, model downloads, API credentials, or provider calls in CI.
This is benchmark verification, not the broader unimplemented CI plan.

## Infrastructure

GitHub Actions Ubuntu runner; checkout/setup-python actions; pip dependencies.

## Depends on

pyproject.toml, src/ocr_platform/benchmark/, tests/test_benchmark.py.

## Tests

Local equivalent commands pass; hosted workflow has not yet run.

## Milestone

R0 evaluation prerequisite.

## Status

IMPLEMENTED.

## Owner

engineering.
