# ocr-platform

Provenance-first OCR / data-extraction platform for the two-page family survey (`FAMILY_SURVEY_V1`).

**Invariant:** `FINAL_VALUE MUST NEVER EXIST WITHOUT PROVENANCE`

## Status

R0 production extraction remains a design scaffold. Separate benchmark and annotated-crop OCR/classifier experiments are implemented, with a real two-document trial recorded under `docs/test-results/`. Per-file responsibilities live under `docs/files/`; production implementation still depends on the docs, data and compatibility gates below.

## Engine selection benchmark

The local 1,446 WARD-42 PDFs are a sample of a corpus in the lakhs. A separate
benchmark now provides deterministic sampling, offline human labeling, Tesseract,
Google Document AI, and local vision-model adapters, with failure-aware accuracy
and configurable scale/cost reports. No engine has been selected by measured
accuracy yet; the production extractor below remains a design scaffold.

Setup and commands: [docs/benchmark.md](docs/benchmark.md). Generated labels and
reports stay under ignored `runs/`; raw data and its ZIP stay under ignored `data/`.

## Milestone

- **R0:** Reproducible single-process extractor on classified fixtures (identity registration + page-box normalize, pinned Paddle models post-spike, complete provenance, auto-accept **off**).
- **R0.5:** Affine registration + residual; handwriting review-only; dynamic-row metrics (`docs/accuracy-plan.md`).
- **R1+:** Thin async API, privacy, calibration-gated auto-accept, review console (`docs/market-roadmap.md`).
- Design SoT: `docs/architecture.md` (Approach B, staged provenance-first platform) + ADRs.

## Plans (read first)

| Doc | Topic |
|---|---|
| [docs/architecture.md](docs/architecture.md) | Layers, flows, trust boundaries, deployments |
| [docs/sequences.md](docs/sequences.md) | Key sequences |
| [docs/capacity.md](docs/capacity.md) | Hardware, throughput, GPU placement, optimization levers |
| [docs/accuracy-plan.md](docs/accuracy-plan.md) | Registration, handwriting, rows, calibration gates |
| [docs/data-plan.md](docs/data-plan.md) | Fixtures, PII, gold labels, template content |
| [docs/testing-plan.md](docs/testing-plan.md) | Test levels, fail-closed gates, R0 exit gate |
| [docs/observability.md](docs/observability.md) | Logging, metrics, provenance-as-audit (PII-free) |
| [docs/threat-model.md](docs/threat-model.md) | STRIDE-lite threats, controls, residual gaps |
| [docs/reason-codes.md](docs/reason-codes.md) | Canonical error/review/exit code registry |
| [docs/glossary.md](docs/glossary.md) | Canonical term definitions |
| [docs/research-gaps.md](docs/research-gaps.md) | Open-question register (RG-*) |
| [docs/market-roadmap.md](docs/market-roadmap.md) | Phased path to market |
| [docs/adr/](docs/adr/README.md) | Architecture decision records |
| [docs/files/README.md](docs/files/README.md) | Per-file spec index |

## Layout

```text
src/ocr_platform/     package (schemas, worker, export, fixtures)
templates/            FAMILY_SURVEY_V1 template package (manifest + boundary YAMLs)
configs/              runtime + AcceptancePolicy-v1
fixtures/             fixture manifest (classification gate)
scripts/              spike, extract CLI, template annotation
docker/               Dockerfile (cpu-spike / gpu-runtime targets)
docs/                 architecture, plans, ADRs
docs/files/           one .md per planned file (spec tree)
tests/                unit + integration
```

## Experimental OCR and classifier flow

The annotated-crop CLI connects local PaddleOCR recognition, field validation,
Laya occupation classification, and human review with immutable evidence.
Run `.venv/Scripts/python.exe -m ocr_platform.flow.cli demo` for a simulated smoke test.
See [docs/flow.md](docs/flow.md) for real checkpoint setup and testing.
This is an experiment; whole-form extraction is not implemented.
Local Laya classifier head fine-tuning is now implemented and was run in two
small pilots, without measured improvement. PaddleOCR fine-tuning is still
pending. See [fine-tuning outcomes](docs/test-results/fine-tuning-pilot-2026-10-05.md)
and the [documentation audit](docs/docs-audit-2026-10-05.md).

## Docs contract

Every non-trivial source/config/template file has `docs/files/<mirror-path>.md` with Role · Contracts · Infrastructure · Depends on · Tests · Milestone · Status · Owner. New file ⇒ new `.md` in the same change. System-level design lives under `docs/*.md` + `docs/adr/` (index in `docs/files/README.md`).

## Survey fixtures (layout references)

- `~/Documents/WARD-42/1RN-982-WARD NO-42/95.pdf`–`99.pdf`
- `~/Documents/WARD-42/11RN-985-WARD NO-42/95.pdf`–`99.pdf`

Not committed here until classified in `fixtures/fixture_manifest.json` (see `docs/data-plan.md`).
