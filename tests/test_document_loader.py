"""Tests for DocumentLoader — PDF, ZIP, directory loading."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest
from PIL import Image

from ocr_platform.document.loader import DocumentLoader, Page, _digest, _image_to_png


class TestDigest:
    def test_deterministic(self):
        assert _digest(b"hello") == _digest(b"hello")

    def test_different_inputs(self):
        assert _digest(b"hello") != _digest(b"world")

    def test_length(self):
        assert len(_digest(b"test")) == 64


class TestImageToPng:
    def test_roundtrip(self):
        img = Image.new("RGB", (100, 100), "white")
        data = _image_to_png(img)
        assert data[:4] == b"\x89PNG"
        recovered = Image.open(io.BytesIO(data))
        assert recovered.size == (100, 100)


class TestDocumentLoaderDir:
    def test_load_directory(self, tmp_path: Path):
        # Create test images
        for i in range(3):
            img = Image.new("RGB", (200, 200), "white")
            img.save(tmp_path / f"img_{i}.png")

        loader = DocumentLoader(dpi=200)
        pages = loader.load(tmp_path)
        assert len(pages) == 3
        assert all(p.format == "png" for p in pages)
        assert all(len(p.sha256) == 64 for p in pages)
        assert pages[0].doc_id == tmp_path.name

    def test_missing_source(self, tmp_path: Path):
        loader = DocumentLoader()
        with pytest.raises(FileNotFoundError):
            loader.load(tmp_path / "nonexistent.zip")

    def test_unsupported_type(self, tmp_path: Path):
        (tmp_path / "file.txt").write_text("hello")
        loader = DocumentLoader()
        with pytest.raises(ValueError, match="Unsupported source type"):
            loader.load(tmp_path / "file.txt")


class TestDocumentLoaderZip:
    def test_load_zip(self, tmp_path: Path):
        zip_path = tmp_path / "test.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            for i in range(2):
                img = Image.new("RGB", (100, 100), "white")
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                zf.writestr(f"page_{i}.png", buf.getvalue())

        loader = DocumentLoader(dpi=200)
        pages = loader.load(zip_path)
        assert len(pages) == 2
        assert pages[0].doc_id == "test"
