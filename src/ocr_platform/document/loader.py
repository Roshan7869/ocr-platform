"""DocumentLoader — accepts PDF, ZIP of images, or image directory.

Produces a list of page dicts with image bytes, SHA256, and metadata.
Uses pypdfium2 for PDF rendering (matching the existing benchmark runner).
"""

from __future__ import annotations

import hashlib
import io
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image


@dataclass(frozen=True)
class Page:
    """One rendered page from a document."""
    doc_id: str
    page_index: int
    sha256: str
    width: int
    height: int
    image_bytes: bytes  # PNG
    source_path: str
    format: str = "png"


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _image_to_png(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class DocumentLoader:
    """Load documents from PDF, ZIP, or image directory.

    Parameters
    ----------
    dpi : int
        Rendering DPI for PDF pages (72–300).
    max_pages : int
        Safety cap per PDF (prevents runaway memory).
    max_image_pixels : int
        Pillow DecompressionBombError threshold override.
    """

    def __init__(self, dpi: int = 200, max_pages: int = 20, max_image_pixels: int = 50_000_000):
        self.dpi = dpi
        self.max_pages = max_pages
        Image.MAX_IMAGE_PIXELS = max_image_pixels

    def load(self, source: Path) -> list[Page]:
        """Load all pages from *source*.

        *source* may be:
        - A ``.pdf`` file → rendered page-by-page
        - A ``.zip`` archive → image files extracted and loaded
        - A directory  → image files enumerated
        """
        source = source.resolve()
        if not source.exists():
            raise FileNotFoundError(f"Document source not found: {source}")

        suffix = source.suffix.lower()
        if suffix == ".pdf":
            return self._load_pdf(source)
        if suffix == ".zip":
            return self._load_zip(source)
        if source.is_dir():
            return self._load_dir(source)
        if suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}:
            return self._load_single(source)
        raise ValueError(f"Unsupported source type: {source} (expected .pdf, .zip, directory, or image file)")

    # ------------------------------------------------------------------
    # Private loaders
    # ------------------------------------------------------------------

    def _load_pdf(self, path: Path) -> list[Page]:
        try:
            import pypdfium2
        except ImportError as exc:
            raise ImportError("Install pypdfium2 to load PDFs: pip install pypdfium2") from exc

        doc_id = path.stem
        pages: list[Page] = []
        with pypdfium2.PdfDocument(str(path)) as pdf:
            n = len(pdf)
            if n > self.max_pages:
                raise ValueError(f"PDF has {n} pages; exceeds max_pages={self.max_pages}")
            for idx in range(n):
                page = pdf[idx]
                try:
                    scale = self.dpi / 72
                    bitmap = page.render(scale=scale)
                    try:
                        pil = bitmap.to_pil().copy()
                        w, h = pil.size
                        if w * h > 30_000_000:
                            raise ValueError(f"Rendered page {idx} exceeds 30-megapixel cap")
                        png_bytes = _image_to_png(pil)
                        pages.append(Page(
                            doc_id=doc_id,
                            page_index=idx,
                            sha256=_digest(png_bytes),
                            width=w,
                            height=h,
                            image_bytes=png_bytes,
                            source_path=str(path),
                        ))
                    finally:
                        bitmap.close()
                finally:
                    page.close()
        return pages

    def _load_single(self, path: Path) -> list[Page]:
        """Load a single image file as a one-page document."""
        doc_id = path.stem
        data = path.read_bytes()
        img = Image.open(io.BytesIO(data)).convert("RGB")
        png_bytes = _image_to_png(img)
        w, h = img.size
        return [Page(
            doc_id=doc_id, page_index=0, sha256=_digest(png_bytes),
            width=w, height=h, image_bytes=png_bytes, source_path=str(path),
        )]

    def _load_zip(self, path: Path) -> list[Page]:
        doc_id = path.stem
        pages: list[Page] = []
        image_exts = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}
        with zipfile.ZipFile(path, "r") as zf:
            names = sorted(n for n in zf.namelist() if Path(n).suffix.lower() in image_exts)
            for idx, name in enumerate(names):
                data = zf.read(name)
                img = Image.open(io.BytesIO(data)).convert("RGB")
                png_bytes = _image_to_png(img)
                w, h = img.size
                pages.append(Page(
                    doc_id=doc_id,
                    page_index=idx,
                    sha256=_digest(png_bytes),
                    width=w,
                    height=h,
                    image_bytes=png_bytes,
                    source_path=str(path),
                ))
        return pages

    def _load_dir(self, path: Path) -> list[Page]:
        doc_id = path.name
        pages: list[Page] = []
        image_exts = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}
        files = sorted(
            p for p in path.iterdir()
            if p.is_file() and p.suffix.lower() in image_exts
        )
        for idx, f in enumerate(files):
            data = f.read_bytes()
            img = Image.open(io.BytesIO(data)).convert("RGB")
            png_bytes = _image_to_png(img)
            w, h = img.size
            pages.append(Page(
                doc_id=doc_id,
                page_index=idx,
                sha256=_digest(png_bytes),
                width=w,
                height=h,
                image_bytes=png_bytes,
                source_path=str(f),
            ))
        return pages
