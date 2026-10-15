"""Gate G6 (testing-plan §2, observability §§1/3): PII-free logs.

A known PII-ish value is injected through the exercised pipeline path
(OCR dispatch → normalize → semantic → arbiter → Laya → evidence store)
while the observability surface emits its structured JSON records. No log
record may contain the injected value. A second test pins the record
shape: every emitted record carries ``run_id`` and only PII-safe keys.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from ocr_platform import observability
from ocr_platform.document.loader import Page
from ocr_platform.orchestrator.pipeline import SurveyPipeline

FAKE_NAME = "Aarav Sharma"
FAKE_MOBILE = "9876543210"

SAFE_KEYS = {
    "event",
    "run_id",
    "wall_time",
    "reason_code",
    "field_id",
    "disposition",
    "primary_reason",
    "accepted_by",
    "accepted",
    "review",
    "errored",
    "wall_ms",
}

TEMPLATE = {
    "page_size": [200, 200],
    "row_dividers": [0, 100, 200],
    "column_dividers_top": [0, 100, 200],
    "column_dividers_bottom": [0, 100, 200],
    "fields": {},
    "member_table_cols": ["member_name", "remarks"],
    "members_start_row": 9,
    "header_rows": 5,
}


def _make_pipeline(tmp_path: Path) -> SurveyPipeline:
    template_path = tmp_path / "template.json"
    template_path.write_text(json.dumps(TEMPLATE))
    return SurveyPipeline(
        template_path=template_path,
        db_path=tmp_path / "evidence.db",
        output_dir=tmp_path / "out",
        use_hindi_vlm=False,
        allow_auto_accept=False,
    )


def _pii_cells():
    return [
        {
            "cell_id": "p0_r6_c1_name",
            "page_index": 0,
            "row_idx": 6,
            "col_idx": 1,
            "field_key": "member_name",
            "is_header": False,
            "crop_bgr": np.zeros((20, 20, 3), dtype=np.uint8),
            "sha256": "namecell",
            "box": [0, 0, 20, 20],
            "doc_id": "doc1",
        },
        {
            "cell_id": "p0_r6_c2_mobile",
            "page_index": 0,
            "row_idx": 6,
            "col_idx": 2,
            "field_key": "remarks",
            "is_header": False,
            "crop_bgr": np.zeros((20, 20, 3), dtype=np.uint8),
            "sha256": "mobilecell",
            "box": [20, 0, 40, 20],
            "doc_id": "doc1",
        },
    ]


def _fake_dispatch(cell_id, field_key, crop, handwriting, include_vlm=True):
    value = FAKE_NAME if field_key == "member_name" else FAKE_MOBILE
    return {
        "cell_id": cell_id,
        "field_key": field_key,
        "candidates": [{"value": value, "conf": 0.97, "engine": "paddle_en"}],
        "resolved": value,
        "reason": "best_paddle_en",
    }


@pytest.mark.parametrize("pii", [FAKE_NAME, FAKE_MOBILE])
def test_pipeline_logs_never_contain_field_values(tmp_path, caplog, pii):
    pipe = _make_pipeline(tmp_path)
    page = Page(
        doc_id="doc1",
        page_index=0,
        sha256="b" * 64,
        width=100,
        height=100,
        image_bytes=b"fakepng",
        source_path="fake",
        format="png",
    )
    with (
        patch.object(pipe.loader, "load", return_value=[page]),
        patch("cv2.imdecode", return_value=np.zeros((100, 100, 3), dtype=np.uint8)),
        patch.object(pipe, "_slice_cells", return_value=_pii_cells()),
        patch.object(pipe, "_dispatch_ocr", side_effect=_fake_dispatch),
    ):
        caplog.set_level(logging.INFO, logger="ocr_platform.observability")
        result = pipe.run(tmp_path / "src.png")
    assert "error" not in result
    records = [r for r in caplog.records if r.name == "ocr_platform.observability"]
    assert records, "expected observability records from run start/decision/complete"
    events = {json.loads(r.getMessage())["event"] for r in records}
    assert {"run.start", "field.decision", "run.complete"} <= events
    for record in records:
        assert pii not in record.getMessage()


def test_emitted_records_carry_run_id_and_safe_keys_only(tmp_path, caplog):
    pipe = _make_pipeline(tmp_path)
    page = Page(
        doc_id="doc1",
        page_index=0,
        sha256="c" * 64,
        width=100,
        height=100,
        image_bytes=b"fakepng",
        source_path="fake",
        format="png",
    )
    with (
        patch.object(pipe.loader, "load", return_value=[page]),
        patch("cv2.imdecode", return_value=np.zeros((100, 100, 3), dtype=np.uint8)),
        patch.object(pipe, "_slice_cells", return_value=_pii_cells()),
        patch.object(pipe, "_dispatch_ocr", side_effect=_fake_dispatch),
    ):
        caplog.set_level(logging.INFO, logger="ocr_platform.observability")
        result = pipe.run(tmp_path / "src.png")
    run_id = result["run_id"]
    records = [r for r in caplog.records if r.name == "ocr_platform.observability"]
    assert records
    for record in records:
        payload = json.loads(record.getMessage())
        assert payload["run_id"] == run_id
        assert set(payload) <= SAFE_KEYS, f"unsafe keys in log record: {set(payload) - SAFE_KEYS}"
    assert observability.EVENT_RUN_START in {json.loads(r.getMessage())["event"] for r in records}
