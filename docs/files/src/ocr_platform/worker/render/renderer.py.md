# src/ocr_platform/worker/render/renderer.py

## Role

Deterministic PDF → page image + `RenderMetadata` at fixed DPI and colorspace. Produces immutable `PageArtifact` inputs for template application and OCR. Handles capability-matrix classification hooks (encrypted/corrupt/empty detection lives at ingest boundary but uses render failure signals here).

## Contracts

- **Invariants:**
  - Same PDF + fixed render settings → deterministic pixels (R0 comparison policy: exact byte equality where encoding guarantees it; documented tolerance where not).
  - Render parameters (DPI, colorspace, renderer version) recorded in metadata and configuration fingerprint.
  - Page-space output uses top-left origin images; coordinate conversion documented with `render/coordinates.py`.
  - Empty/unreadable page → no accepted fields; page disposition `errored` or `review`.
- **Outputs:** page images (in-memory/temp), `RenderMetadata`, page count for page-set validation.
- **Forbidden:** mutating source PDF; applying template bounds here; OCR.

## Infrastructure

- **Python deps:** pypdf (structure/probe); **rasterizer primary: pypdfium2** (ADR-001); fallbacks in spike matrix: PyMuPDF or poppler `pdftoppm`; pillow
- **Config/artifacts:** `configs/runtime.yaml` (DPI, colorspace, rasterizer id)
- **Models/external:** none
- **Env vars:** none

## Milestone notes

- Rasterizer library + version recorded in spike matrix and configuration fingerprint before production pins (`docs/adr/adr-001-pdf-rasterizer.md`).

## Depends on

- **Calls:** `schemas/job.py` (PageArtifact, RenderMetadata)
- **Called by:** `worker/pipeline.py`

## Tests

- Unit: render determinism at fixed DPI/colorspace (hash of page pixels stable) for chosen rasterizer
- Unit: encrypted/corrupt PDF classified without crash
- Unit: page-count extraction for extra/missing/duplicate page tests
- Integration: R0 empty file / unreadable page fixtures
- Integration: spike matrix rasterizer section filled (two-run pixel compare)

## Milestone

R0

## Status

SPEC

## Owner

engineering
