# ocr-platform

Provenance-first OCR / data-extraction platform for the two-page family survey (`FAMILY_SURVEY_V1`).

**Invariant:** `FINAL_VALUE MUST NEVER EXIST WITHOUT PROVENANCE`

## Status

R0 — docs-first. Per-file responsibility specs live under `docs/files/` (mirror tree). Source lands after each spec.

## Milestone

- **R0:** Reproducible single-process extractor on synthetic/approved-redacted fixtures (identity registration, pinned Paddle models, complete provenance).
- Design source of truth: gstack design doc (Approach B, staged provenance-first platform).

## Layout

```text
src/ocr_platform/     package (schemas, worker, export, fixtures)
templates/            FAMILY_SURVEY_V1 template package (manifest + boundary YAMLs)
configs/              runtime + AcceptancePolicy-v1
fixtures/             fixture manifest (classification gate)
scripts/              spike, extract CLI, template annotation
docker/               Dockerfile
docs/files/           one .md per planned file (this is the spec tree)
tests/                unit + integration
```

## Docs contract

Every non-trivial source/config/template file has `docs/files/<mirror-path>.md` with Role · Contracts · Infrastructure · Depends on · Tests · Milestone · Status · Owner. New file ⇒ new `.md` in the same change.

## Survey fixtures (layout references)

- `~/Documents/WARD-42/1RN-982-WARD NO-42/95.pdf`–`99.pdf`
- `~/Documents/WARD-42/11RN-985-WARD NO-42/95.pdf`–`99.pdf`

Not committed here until classified in `fixtures/fixture_manifest.json`.
