"""Gate G3 (testing-plan §2): R0 flags disabled force review.

With OCR/native auto-accept disabled (``allow_auto_accept=False``), every
cell disposition is ``"review"`` regardless of confidence — the guard at
``orchestrator/pipeline.py`` forces ``"review"`` unless auto-accept is
explicitly enabled.

RED-without-guard: deleting ``allow_auto_accept and`` from the guard makes
``test_r0_flags_disabled_forces_review_at_high_confidence`` fail (the
high-confidence cell flips to ``"accepted"``). GREEN-with-guard: it passes.
``test_guard_is_sensitive`` pins the other direction so the suite cannot
pass vacuously.
"""

from __future__ import annotations

import json
import tempfile
from inspect import signature
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from ocr_platform.document.loader import Page
from ocr_platform.orchestrator.pipeline import SurveyPipeline

TEMPLATE = {
    "page_size": [200, 200],
    "row_dividers": [0, 100, 200],
    "column_dividers_top": [0, 100, 200],
    "column_dividers_bottom": [0, 100, 200],
    "fields": {},
    "member_table_cols": ["gender"],
    "members_start_row": 9,
    "header_rows": 5,
}


def _make_pipeline(tmp_path: Path, allow_auto_accept: bool) -> SurveyPipeline:
    template_path = tmp_path / "template.json"
    template_path.write_text(json.dumps(TEMPLATE))
    return SurveyPipeline(
        template_path=template_path,
        db_path=tmp_path / "evidence.db",
        output_dir=tmp_path / "out",
        use_hindi_vlm=False,
        allow_auto_accept=allow_auto_accept,
    )


def _run_single_cell(pipeline: SurveyPipeline, tmp_path: Path, conf: float) -> list[dict]:
    """Run the real pipeline with one mocked high-signal OCR observation."""
    page = Page(
        doc_id="doc1",
        page_index=0,
        sha256="a" * 64,
        width=100,
        height=100,
        image_bytes=b"fakepng",
        source_path="fake",
        format="png",
    )
    cell = {
        "cell_id": "p0_r6_c1_deadbeef",
        "page_index": 0,
        "row_idx": 6,
        "col_idx": 1,
        "field_key": "gender",
        "is_header": False,
        "crop_bgr": np.zeros((20, 20, 3), dtype=np.uint8),
        "sha256": "deadbeef",
        "box": [0, 0, 20, 20],
        "doc_id": "doc1",
    }

    def fake_dispatch(cell_id, field_key, crop, handwriting, include_vlm=True):
        return {
            "cell_id": cell_id,
            "field_key": field_key,
            "candidates": [{"value": "male", "conf": conf, "engine": "paddle_en"}],
            "resolved": "male",
            "reason": "best_paddle_en",
        }

    with (
        patch.object(pipeline.loader, "load", return_value=[page]),
        patch("cv2.imdecode", return_value=np.zeros((100, 100, 3), dtype=np.uint8)),
        patch.object(pipeline, "_slice_cells", return_value=[cell]),
        patch.object(pipeline, "_dispatch_ocr", side_effect=fake_dispatch),
    ):
        result = pipeline.run(tmp_path / "src.png")
    assert "error" not in result
    members = result["documents"][0]["members"]
    return [field for member in members for field in member["fields"].values()]


def test_default_is_review_first():
    default = signature(SurveyPipeline.__init__).parameters["allow_auto_accept"].default
    assert default is False
    with tempfile.TemporaryDirectory() as directory:
        pipe = _make_pipeline(Path(directory), allow_auto_accept=False)
        assert pipe.allow_auto_accept is False


@pytest.mark.parametrize("conf", [0.99, 0.95, 0.88, 0.50])
def test_r0_flags_disabled_forces_review_at_high_confidence(tmp_path, conf):
    pipe = _make_pipeline(tmp_path, allow_auto_accept=False)
    outputs = _run_single_cell(pipe, tmp_path, conf)
    assert outputs, "expected the mocked cell to flow through the pipeline"
    for output in outputs:
        assert output["disposition"] == "review"
        assert output["final_value"] is None


def test_guard_is_sensitive(tmp_path):
    """Auto-accept enabled + high confidence accepts — the G3 test is not vacuous."""
    pipe = _make_pipeline(tmp_path, allow_auto_accept=True)
    outputs = _run_single_cell(pipe, tmp_path, 0.99)
    assert outputs
    assert outputs[0]["disposition"] == "accepted"
    assert outputs[0]["final_value"] is not None
