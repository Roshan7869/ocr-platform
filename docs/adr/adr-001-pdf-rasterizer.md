# ADR-001: PDF rasterizer primary = pypdfium2 (spike-confirmed)

## Status

Accepted · 2026-09-24 · Spike may amend pin (see ADR review on spike go)

## Context

`renderer.py` must deterministically rasterize PDF → page images for OCR. Corpus is image-only PDFs (1-bit grayscale PNG/page, ~200 effective DPI). `pypdf` is already a dependency for structure/metadata but **cannot rasterize**. Dev host has `pdftoppm`/`pdftocairo` and PyMuPDF available; product needs a pinned, embeddable library path for Docker.

## Decision

1. **Primary candidate:** `pypdfium2` (bundled PDFium, no system poppler required, good for Docker).  
2. **Fallback candidates in spike matrix:** PyMuPDF (fitz), poppler via `pdftoppm`.  
3. `pypdf` remains for page count / encrypted detection / text layer probes where sufficient.  
4. Exact library + version goes into `runtime.yaml` / fingerprint + spike matrix **before** production pins.

## Consequences

- Renderer tests must hash pixels under fixed DPI/colorspace for the chosen binding.  
- Spike matrix includes rasterizer section (determinism across two runs).  
- Docker image does not depend on system poppler if pypdfium2 wins.

## Alternatives considered

- pypdf alone: no raster.  
- Ghostscript only: heavier, less embeddable.  
- ImageMagick: policy/security footguns.
