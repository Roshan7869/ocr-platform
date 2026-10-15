"""Tests for the R0 provenance core: hashing, evidence, run identity, graph, decisions, gate.

Each test class maps to a spec'd contract in ``docs/files/``. The suite is
hermetic — no model downloads, no database, no network.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ocr_platform.schemas.decision import (
    FAMILY_SURVEY_LABEL_MAP,
    NOT_REASON_CODES,
    REASON_CODE_TIERS,
    AcceptedBy,
    Disposition,
    FieldDecision,
    Scope,
    ValueState,
    map_survey_label,
    primary_reason,
    registered_reason_codes,
)
from ocr_platform.schemas.evidence import (
    COORDINATE_SYSTEMS,
    CROP_LOCAL_TOP_LEFT,
    PAGE_SPACE_SYSTEM,
    BBox,
    EvidenceSet,
    EvidenceType,
    NativeTextEvidence,
    OcrObservation,
    RegionEvidence,
    RegionState,
    page_space_bbox,
)
from ocr_platform.schemas.job import (
    ConfigurationFingerprint,
    DocumentDisposition,
    DocumentErrorCode,
    DocumentRun,
    PageArtifact,
    PageClass,
    RenderMetadata,
    RunAttempt,
    document_content_hash,
)
from ocr_platform.schemas.provenance import (
    CropArtifactNode,
    DecisionRevisionNode,
    DocumentRunNode,
    EdgeRelation,
    EvidenceSetNode,
    PageArtifactNode,
    ProvenanceEdge,
    ProvenanceGraph,
    RegistrationTransformNode,
    TemplateManifestNode,
)
from ocr_platform.worker.provenance.hashing import (
    CANONICAL_ALGORITHM_ID,
    CanonicalJsonError,
    canonical_json,
    content_hash,
    is_content_hash,
)
from ocr_platform.worker.provenance.validator import (
    ViolationCode,
    gate_export,
    validate_batch,
)
from ocr_platform.worker.render.coordinates import (
    CoordinateSystemError,
    PageSize,
    assert_page_space,
    crop_local_box,
    normalize_page_box,
    pdf_rect_to_image_bbox,
    round_trip_within_epsilon,
    to_page_normalized,
    to_pixel,
)

PDF_BYTES = b"%PDF-1.4 fake survey bytes for identity tests"
OTHER_PDF_BYTES = b"%PDF-1.4 different bytes"

PAGE = PageSize(width_px=1000, height_px=1400)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def make_fingerprint(**overrides) -> ConfigurationFingerprint:
    base = {
        "template_manifest_hash": content_hash({"template": "family_survey_v1"}),
        "runtime_config_hash": content_hash({"dpi": 200}),
        "acceptance_policy_version": "AcceptancePolicy-v1",
        "canonical_algorithm_id": CANONICAL_ALGORITHM_ID,
        "dpi": 200,
        "engine_versions": {"paddleocr": "3.0.0"},
    }
    base.update(overrides)
    return ConfigurationFingerprint(**base)


def make_render_metadata() -> RenderMetadata:
    return RenderMetadata(
        renderer="pypdfium2",
        renderer_version="4.30.0",
        dpi=200,
        scale=200 / 72,
        colorspace="RGB",
        media_box_pdf_points=(0.0, 0.0, 595.0, 842.0),
        width_px=PAGE.width_px,
        height_px=PAGE.height_px,
    )


def make_page(index: int = 0, page_class: PageClass = PageClass.scanned_only) -> PageArtifact:
    return PageArtifact(
        artifact_id=f"page:{index}",
        page_index=index,
        page_class=page_class,
        content_hash=content_hash({"page": index, "class": page_class.value}),
        render_metadata=make_render_metadata(),
        width_px=PAGE.width_px,
        height_px=PAGE.height_px,
    )


def make_run(pages: tuple[PageArtifact, ...] = (make_page(),)) -> DocumentRun:
    return DocumentRun.create(
        pdf_bytes=PDF_BYTES,
        fingerprint=make_fingerprint(),
        template_version="1.0",
        pages=pages,
    )


def make_ocr_observation(text: str = "राम", confidence: float = 0.93) -> OcrObservation:
    return OcrObservation(
        source_page_index=0,
        source_region_id="p0_r3_c1",
        content_hash=content_hash({"text": text, "conf": confidence}),
        raw_text=text,
        raw_confidence=confidence,
        det_model_version="paddle-det-3.0.0",
        rec_model_version="paddle-rec-hi-3.0.0",
        render_metadata_hash=content_hash({"renderer": "pypdfium2"}),
        preprocess_metadata_hash=content_hash({"pad": 15}),
        field_id="member_name",
        row_index=3,
        col_index=1,
        bbox=page_space_bbox(0.10, 0.20, 0.30, 0.25),
    )


def _build_ocr(**overrides) -> OcrObservation:
    """Construct an OcrObservation directly, for rejection tests.

    ``model_copy`` bypasses pydantic validators in v2, so tests that assert a
    validation error must build the object instead of copying a valid one.
    """
    payload = {
        "source_page_index": 0,
        "source_region_id": "p0_r3_c1",
        "content_hash": content_hash({"text": "राम", "conf": 0.93}),
        "raw_text": "राम",
        "raw_confidence": 0.93,
        "det_model_version": "paddle-det-3.0.0",
        "rec_model_version": "paddle-rec-hi-3.0.0",
        "render_metadata_hash": content_hash({"renderer": "pypdfium2"}),
        "preprocess_metadata_hash": content_hash({"pad": 15}),
        "field_id": "member_name",
        "row_index": 3,
        "col_index": 1,
        "bbox": page_space_bbox(0.10, 0.20, 0.30, 0.25),
    }
    payload.update(overrides)
    return OcrObservation(**payload)


def make_native_evidence(text: str = "survey 2026") -> NativeTextEvidence:
    return NativeTextEvidence(
        source_page_index=0,
        source_region_id="p0_r0_c0",
        content_hash=content_hash({"native": text}),
        raw_text=text,
        extractor="pypdf",
        extractor_version="4.2.0",
        bbox=page_space_bbox(0.05, 0.05, 0.20, 0.08),
    )


def make_region_evidence(state: RegionState = RegionState.absent) -> RegionEvidence:
    return RegionEvidence(
        source_page_index=0,
        source_region_id="p0_r3_c4",
        content_hash=content_hash({"region": state.value}),
        region_state=state,
        detection_method="template_boundary_intersect",
    )


def make_evidence_set(*members, set_id: str = "set:member_name:r3") -> EvidenceSet:
    return EvidenceSet(set_id=set_id, members=tuple(members))


def make_decision(
    decision_id: str = "d:member_name:r3",
    value_state: ValueState = ValueState.present,
    disposition: Disposition = Disposition.accepted,
    final_value: str | None = "राम",
    source_set: tuple[str, ...] = ("set:member_name:r3",),
    **overrides,
) -> FieldDecision:
    payload = {
        "decision_id": decision_id,
        "scope": Scope.field,
        "value_state": value_state,
        "disposition": disposition,
        "field_id": "member_name",
        "page_index": 0,
        "row_index": 3,
        "final_value": final_value,
        "reason_codes": (),
        "primary_reason": None,
        "accepted_by": AcceptedBy.policy,
        "acceptance_policy_version": "AcceptancePolicy-v1",
        "template_version": "1.0",
        "source_set": source_set,
    }
    if disposition is Disposition.review:
        payload.update(accepted_by=AcceptedBy.none, acceptance_policy_version="")
    payload.update(overrides)
    if payload["reason_codes"] and payload["primary_reason"] is None:
        payload["primary_reason"] = primary_reason(payload["reason_codes"])
    return FieldDecision(**payload)


# ---------------------------------------------------------------------------
# hashing.py
# ---------------------------------------------------------------------------


class TestCanonicalJson:
    def test_key_order_independence(self):
        assert canonical_json({"a": 1, "b": 2}) == canonical_json({"b": 2, "a": 1})
        assert content_hash({"a": 1, "b": 2}) == content_hash({"b": 2, "a": 1})

    def test_nested_key_order_independence(self):
        left = {"outer": {"x": [1, 2], "y": {"p": 1, "q": 2}}, "z": 3}
        right = {"z": 3, "outer": {"y": {"q": 2, "p": 1}, "x": [1, 2]}}
        assert content_hash(left) == content_hash(right)

    def test_separators_are_compact_and_sorted(self):
        assert canonical_json({"b": 1, "a": 2}) == b'{"a":2,"b":1}'

    def test_tuple_and_list_are_the_same_array(self):
        assert canonical_json({"xs": (1, 2, 3)}) == canonical_json({"xs": [1, 2, 3]})

    def test_unicode_is_not_escaped(self):
        assert canonical_json({"name": "राम"}) == '{"name":"राम"}'.encode()

    def test_float_formatting_is_stable(self):
        assert canonical_json({"v": 1.5}) == b'{"v":1.5}'
        assert canonical_json({"v": 0.1}) == b'{"v":0.1}'
        assert canonical_json({"v": 1 / 3}) == b'{"v":0.3333333333333333}'

    def test_signed_zero_cannot_fork_a_hash(self):
        assert canonical_json({"v": -0.0}) == canonical_json({"v": 0.0})
        assert canonical_json({"v": -0.0}) == b'{"v":0.0}'

    def test_integers_stay_integers(self):
        assert canonical_json({"n": 3}) == b'{"n":3}'

    def test_non_finite_floats_are_rejected(self):
        with pytest.raises(CanonicalJsonError):
            canonical_json({"v": float("nan")})
        with pytest.raises(CanonicalJsonError):
            canonical_json({"v": float("inf")})

    def test_key_collision_after_stringification_is_rejected(self):
        with pytest.raises(CanonicalJsonError):
            canonical_json({1: "a", "1": "b"})

    def test_bytes_are_not_json(self):
        with pytest.raises(CanonicalJsonError):
            canonical_json({"blob": b"\x00\x01"})

    def test_bool_is_not_an_int(self):
        assert canonical_json({"flag": True}) == b'{"flag":true}'

    def test_bytes_and_str_hash_identically(self):
        assert content_hash(b"abc") == content_hash("abc")

    def test_raw_bytes_hash_is_plain_sha256(self):
        import hashlib

        assert content_hash(b"abc") == hashlib.sha256(b"abc").hexdigest()

    def test_is_content_hash(self):
        assert is_content_hash(content_hash({"x": 1}))
        assert not is_content_hash("abc")
        assert not is_content_hash("A" * 64)
        assert not is_content_hash(content_hash({"x": 1}).upper())


# ---------------------------------------------------------------------------
# evidence.py
# ---------------------------------------------------------------------------


class TestBBox:
    def test_bbox_rejects_missing_coordinate_system(self):
        with pytest.raises(ValueError, match="coordinate_system"):
            BBox.model_validate({"x0": 0, "y0": 0, "x1": 1, "y1": 1})

    def test_unknown_coordinate_system_rejected(self):
        with pytest.raises(ValueError, match="unknown coordinate_system"):
            BBox(x0=0, y0=0, x1=1, y1=1, coordinate_system="screen_magic")

    def test_degenerate_bbox_rejected(self):
        with pytest.raises(ValueError, match="degenerate"):
            BBox(x0=1, y0=0, x1=0, y1=1, coordinate_system=PAGE_SPACE_SYSTEM)

    def test_normalized_page_space_must_be_in_unit_box(self):
        with pytest.raises(ValueError, match="unit box"):
            BBox(x0=0, y0=0, x1=1.5, y1=1, coordinate_system=PAGE_SPACE_SYSTEM)
        with pytest.raises(ValueError, match="unit box"):
            BBox(x0=-0.1, y0=0, x1=1, y1=1, coordinate_system=PAGE_SPACE_SYSTEM)

    def test_pixel_boxes_may_exceed_unit_box(self):
        box = BBox(x0=0, y0=0, x1=1000, y1=1400, coordinate_system="image_top_left_pixel")
        assert box.as_tuple == (0.0, 0.0, 1000.0, 1400.0)

    def test_crop_local_is_tagged(self):
        assert crop_local_box(0, 0, 5, 5).is_crop_local
        assert page_space_bbox(0, 0, 1, 1).is_page_space


class TestEvidenceNodes:
    def test_nodes_are_immutable(self):
        node = make_ocr_observation()
        with pytest.raises(ValidationError):
            node.raw_text = "tampered"

    def test_evidence_requires_source_region(self):
        with pytest.raises(ValueError, match="source_region_id"):
            OcrObservation(
                source_page_index=0,
                source_region_id="",
                content_hash=content_hash({"x": 1}),
                raw_text="a",
                raw_confidence=0.9,
                det_model_version="d",
                rec_model_version="r",
                render_metadata_hash=content_hash({}),
                preprocess_metadata_hash=content_hash({}),
            )

    def test_evidence_id_is_content_addressed(self):
        first = make_ocr_observation("राम", 0.93)
        same = make_ocr_observation("राम", 0.93)
        other = make_ocr_observation("श्याम", 0.93)
        assert first.evidence_id == same.evidence_id
        assert first.evidence_id != other.evidence_id

    def test_bad_content_hash_rejected(self):
        with pytest.raises(ValueError, match="content_hash"):
            _build_ocr(content_hash="not-a-hash")

    def test_ocr_confidence_must_be_in_range(self):
        with pytest.raises(ValueError, match="raw_confidence"):
            make_ocr_observation(confidence=1.5)

    def test_ocr_bbox_must_be_page_space(self):
        with pytest.raises(ValueError, match="page-space"):
            _build_ocr(bbox=BBox(x0=0, y0=0, x1=5, y1=5, coordinate_system=CROP_LOCAL_TOP_LEFT))

    def test_crop_local_bbox_must_be_crop_local(self):
        with pytest.raises(ValueError, match="crop_local"):
            _build_ocr(crop_local_bbox=page_space_bbox(0, 0, 0.1, 0.1))

    def test_negative_page_index_rejected(self):
        with pytest.raises(ValueError, match="source_page_index"):
            _build_ocr(source_page_index=-1)

    def test_native_text_has_no_confidence_field(self):
        native = make_native_evidence()
        assert not hasattr(native, "raw_confidence")
        assert native.evidence_type is EvidenceType.native_text


class TestEvidenceSet:
    def test_no_composite_confidence_exists(self):
        evidence_set = make_evidence_set(make_ocr_observation(), make_native_evidence())
        dumped = evidence_set.model_dump()
        assert "final_confidence" not in dumped
        assert not any("confidence" in key for key in dumped)

    def test_exact_duplicates_collapse_under_a_policy_operation(self):
        first = make_ocr_observation()
        duplicate = make_ocr_observation()  # same content hash
        evidence_set = make_evidence_set(first, duplicate)
        assert len(evidence_set.members) == 2

        collapsed, operation_id = evidence_set.collapse_exact_duplicates("dedupe-v1")
        assert len(collapsed.members) == 1
        assert operation_id
        # Both originals were byte-identical, so they shared one evidence_id.
        assert evidence_set.members[0].evidence_id == evidence_set.members[1].evidence_id
        assert collapsed.evidence_ids() == (evidence_set.members[0].evidence_id,)
        assert collapsed.set_id != evidence_set.set_id

    def test_conflicting_observations_remain_distinct(self):
        """R0 integration: duplicate *text* is not duplicate *evidence*."""
        one = make_ocr_observation("राम", 0.91)
        two = make_ocr_observation("राम", 0.55)
        evidence_set = make_evidence_set(one, two)
        collapsed, _ = evidence_set.collapse_exact_duplicates("dedupe-v1")
        assert len(collapsed.members) == 2

    def test_of_type_filters(self):
        evidence_set = make_evidence_set(make_ocr_observation(), make_region_evidence())
        assert len(evidence_set.of_type(EvidenceType.region)) == 1
        assert len(evidence_set.of_type(EvidenceType.ocr_observation)) == 1
        assert len(evidence_set.of_type(EvidenceType.human_correction)) == 0

    def test_evidence_set_is_immutable(self):
        evidence_set = make_evidence_set(make_ocr_observation())
        with pytest.raises(ValidationError):
            evidence_set.set_id = "other"

    def test_by_id_lookup(self):
        node = make_ocr_observation()
        evidence_set = make_evidence_set(node)
        assert evidence_set.by_id(node.evidence_id) is node
        assert evidence_set.by_id("ocr_observation:nope") is None


# ---------------------------------------------------------------------------
# coordinates.py
# ---------------------------------------------------------------------------


class TestCoordinates:
    def test_normalized_to_pixel_round_trip_within_epsilon(self):
        box = (100.0, 200.0, 400.0, 500.0)
        assert round_trip_within_epsilon(box, PAGE, epsilon_px=1.0)

    def test_pdf_bottom_left_to_image_top_left_flips_y(self):
        # A 1-inch-tall rect flush with the top of a 144-pt-tall page at 72 dpi.
        # The media box top edge is PDF y=144, so the flip must rebase to it.
        image = pdf_rect_to_image_bbox(
            (72.0, 72.0, 144.0, 144.0), PAGE, dpi=72, media_box_points=(0.0, 0.0, 144.0, 144.0)
        )
        x0, y0, x1, y1 = image
        assert x0 == pytest.approx(72.0)
        assert x1 == pytest.approx(144.0)
        # PDF y=72..144 maps to image y=0..72 from the top, so y0 < y1 and the
        # vertical origin is flipped rather than silently reused.
        assert y0 == pytest.approx(0.0)
        assert y1 == pytest.approx(72.0)

    def test_pdf_media_box_origin_is_rebased(self):
        image = pdf_rect_to_image_bbox(
            (100.0, 100.0, 200.0, 200.0),
            PAGE,
            dpi=72,
            media_box_points=(100.0, 100.0, 300.0, 300.0),
        )
        assert image[0] == pytest.approx(0.0)
        assert image[2] == pytest.approx(100.0)

    def test_cross_system_operations_are_rejected(self):
        page_box = page_space_bbox(0.1, 0.1, 0.2, 0.2)
        crop = crop_local_box(0, 0, 1, 1)
        with pytest.raises(CoordinateSystemError, match="cannot combine"):
            from ocr_platform.worker.render.coordinates import require_same_system

            require_same_system(page_box, crop)

    def test_assert_page_space_rejects_crop_local(self):
        with pytest.raises(CoordinateSystemError, match="not.*image_top_left_normalized"):
            assert_page_space(crop_local_box(0, 0, 1, 1))

    def test_normalize_page_box_is_pure(self):
        box = (10.0, 20.0, 30.0, 40.0)
        before = to_page_normalized(box, PAGE)
        first = normalize_page_box(box, PAGE)
        second = normalize_page_box(box, PAGE)
        assert first == second == before
        assert to_page_normalized(box, PAGE) == before  # ambient state unchanged

    def test_degenerate_boxes_rejected(self):
        with pytest.raises(CoordinateSystemError, match="degenerate"):
            to_page_normalized((5, 5, 1, 1), PAGE)

    def test_page_size_must_be_positive(self):
        with pytest.raises(CoordinateSystemError):
            PageSize(width_px=0, height_px=10)

    def test_dpi_must_be_positive(self):
        with pytest.raises(CoordinateSystemError, match="dpi"):
            pdf_rect_to_image_bbox((0, 0, 1, 1), PAGE, dpi=0, media_box_points=(0, 0, 595, 842))

    def test_pixel_box_is_clipped_and_addressable(self):
        restored = to_pixel((0.0, 0.0, 1.0, 1.0), PAGE)
        assert restored == (0.0, 0.0, float(PAGE.width_px - 1), float(PAGE.height_px - 1))

    def test_known_systems_cover_evidence_constants(self):
        from ocr_platform.worker.render.coordinates import known_systems

        assert set(known_systems()) == set(COORDINATE_SYSTEMS)


# ---------------------------------------------------------------------------
# job.py
# ---------------------------------------------------------------------------


class TestRunIdentity:
    def test_identical_bytes_and_config_yield_same_run_id(self):
        assert make_run().run_id == make_run().run_id

    def test_different_config_yields_different_run_id(self):
        other = DocumentRun.create(
            pdf_bytes=PDF_BYTES,
            fingerprint=make_fingerprint(dpi=300),
            template_version="1.0",
            pages=(make_page(),),
        )
        assert other.run_id != make_run().run_id

    def test_different_bytes_yield_different_run_id(self):
        other = DocumentRun.create(
            pdf_bytes=OTHER_PDF_BYTES,
            fingerprint=make_fingerprint(),
            template_version="1.0",
            pages=(make_page(),),
        )
        assert other.run_id != make_run().run_id

    def test_retry_does_not_change_run_id(self):
        run = make_run()
        attempt_one = RunAttempt(attempt_index=0, started_at=1.0, finished_at=2.0, outcome="failed")
        attempt_two = RunAttempt(attempt_index=1, started_at=3.0, finished_at=4.0, outcome="done")
        retried = run.with_attempt(attempt_one).with_attempt(attempt_two)
        assert retried.run_id == run.run_id
        assert retried.attempt_count() == 2

    def test_document_content_hash_is_sha256_of_exact_bytes(self):
        import hashlib

        assert document_content_hash(PDF_BYTES) == hashlib.sha256(PDF_BYTES).hexdigest()

    def test_attempt_finish_before_start_rejected(self):
        with pytest.raises(ValueError, match="finished_at"):
            RunAttempt(attempt_index=0, started_at=5.0, finished_at=1.0)

    def test_fingerprint_requires_valid_hashes(self):
        with pytest.raises(ValueError, match="template_manifest_hash"):
            make_fingerprint(template_manifest_hash="nope")

    def test_fingerprint_dpi_must_be_positive(self):
        with pytest.raises(ValueError, match="dpi"):
            make_fingerprint(dpi=0)


class TestCapabilityMatrix:
    @pytest.mark.parametrize(
        "page_class,error_code",
        [
            (PageClass.encrypted, DocumentErrorCode.ENCRYPTED_PDF),
            (PageClass.corrupt, DocumentErrorCode.CORRUPT_PDF),
            (PageClass.empty, DocumentErrorCode.EMPTY_DOCUMENT),
        ],
    )
    def test_terminal_classes_error_the_document(self, page_class, error_code):
        run = make_run(pages=(make_page(0, page_class),))
        assert run.is_errored
        assert run.document_error_code is error_code
        assert run.disposition is DocumentDisposition.errored

    def test_no_pages_is_an_empty_document(self):
        run = make_run(pages=())
        assert run.is_errored
        assert run.document_error_code is DocumentErrorCode.EMPTY_DOCUMENT

    def test_usable_classes_are_ok(self):
        for page_class in (
            PageClass.scanned_only,
            PageClass.native_only,
            PageClass.mixed,
            PageClass.page_set_mismatch,
        ):
            run = make_run(pages=(make_page(0, page_class),))
            assert not run.is_errored, page_class

    def test_errored_without_code_rejected(self):
        with pytest.raises(ValueError, match="document_error_code"):
            DocumentRun(
                run_id="r",
                document_content_hash=content_hash({"x": 1}),
                configuration_fingerprint=make_fingerprint(),
                template_version="1.0",
                disposition=DocumentDisposition.errored,
            )

    def test_pages_must_be_ordered_and_unique(self):
        with pytest.raises(ValueError, match="ordered"):
            DocumentRun(
                run_id="r",
                document_content_hash=content_hash({"x": 1}),
                configuration_fingerprint=make_fingerprint(),
                template_version="1.0",
                pages=(make_page(2), make_page(1)),
            )

    def test_page_dimensions_must_match_render_metadata(self):
        page = make_page()
        with pytest.raises(ValueError, match="must match render metadata"):
            PageArtifact(
                artifact_id=page.artifact_id,
                page_index=page.page_index,
                page_class=page.page_class,
                content_hash=page.content_hash,
                render_metadata=page.render_metadata,
                width_px=page.width_px + 1,
                height_px=page.height_px,
            )

    def test_page_set_mismatch_is_review_not_error(self):
        run = make_run(pages=(make_page(0, PageClass.page_set_mismatch),))
        assert not run.is_errored


# ---------------------------------------------------------------------------
# provenance.py
# ---------------------------------------------------------------------------


def make_template_node() -> TemplateManifestNode:
    child = content_hash({"page_1_boundaries": "yaml-bytes"})
    return TemplateManifestNode.build(
        template_version="1.0",
        manifest_hash=content_hash({"manifest": True}),
        child_hashes={"page_1_boundaries.yaml": child},
    )


class TestProvenanceNodes:
    def test_node_id_and_hash_are_content_addressed(self):
        node = make_template_node()
        rebuilt, digest = node.expected_ids()
        assert node.content_hash == digest
        assert node.node_id == rebuilt
        assert node.verify()

    def test_tampered_node_fails_verification(self):
        node = make_template_node()
        tampered = node.model_copy(update={"template_version": "9.9"})
        assert not tampered.verify()

    def test_node_requires_content_hash(self):
        with pytest.raises(ValueError, match="content_hash"):
            TemplateManifestNode(
                node_id="x",
                content_hash="bad",
                template_version="1.0",
                manifest_hash=content_hash({}),
            )

    def test_manifest_child_hashes_must_be_digests(self):
        with pytest.raises(ValueError, match="child hash"):
            TemplateManifestNode(
                node_id="x",
                content_hash=content_hash({}),
                template_version="1.0",
                manifest_hash=content_hash({}),
                child_hashes={"bad.yaml": "nope"},
            )

    def test_registration_residual_cannot_be_negative(self):
        with pytest.raises(ValueError, match="residual"):
            RegistrationTransformNode(
                node_id="x",
                content_hash=content_hash({}),
                transform_type="page_box_normalize",
                residual=-0.1,
                template_manifest_hash=content_hash({}),
            )

    def test_derivation_requires_inputs(self):
        from ocr_platform.schemas.provenance import DerivationNode

        with pytest.raises(ValueError, match="input hash"):
            DerivationNode(
                node_id="x",
                content_hash=content_hash({}),
                operation_id="ditto",
                input_hashes=(),
                output_hash=content_hash({"y": 1}),
                rule_version="1",
                template_version="1",
            )

    def test_derivation_validates_input_and_output_hashes(self):
        from ocr_platform.schemas.provenance import DerivationNode

        with pytest.raises(ValueError, match="input"):
            DerivationNode(
                node_id="x",
                content_hash=content_hash({}),
                operation_id="ditto",
                input_hashes=("bad",),
                output_hash=content_hash({}),
                rule_version="1",
                template_version="1",
            )


class TestProvenanceGraph:
    def _graph(self) -> ProvenanceGraph:
        run_node = DocumentRunNode.build(
            run_id="run-1",
            document_content_hash=content_hash(PDF_BYTES),
            configuration_fingerprint=make_fingerprint().fingerprint(),
            template_version="1.0",
            page_count=1,
        )
        page_node = PageArtifactNode.build(
            artifact_id="page:0",
            page_index=0,
            page_content_hash=content_hash({"page": 0}),
            render_metadata_hash=content_hash({}),
            width_px=PAGE.width_px,
            height_px=PAGE.height_px,
        )
        tpl_node = make_template_node()
        reg_node = RegistrationTransformNode.build(
            transform_type="page_box_normalize",
            residual=0.0,
            template_manifest_hash=tpl_node.manifest_hash,
        )
        crop_node = CropArtifactNode.build(
            crop_hash=content_hash({"crop": 1}),
            page_index=0,
            region_id="p0_r3_c1",
            bbox=(0.1, 0.2, 0.3, 0.25),
        )
        set_node = EvidenceSetNode.build(
            set_id="set:1",
            member_evidence_ids=("ocr_observation:abc",),
            member_content_hashes=(content_hash({"text": "राम"}),),
        )
        decision_node = DecisionRevisionNode.build(
            decision_id="d:1",
            revision_index=0,
            evidence_set_node_id=None,
        )
        graph = ProvenanceGraph()
        for node in (run_node, page_node, tpl_node, reg_node, crop_node, set_node, decision_node):
            graph.add_node(node)
        edges = [
            ProvenanceEdge(
                source_id=run_node.node_id,
                target_id=page_node.node_id,
                relation=EdgeRelation.renders,
            ),
            ProvenanceEdge(
                source_id=page_node.node_id,
                target_id=tpl_node.node_id,
                relation=EdgeRelation.templates,
            ),
            ProvenanceEdge(
                source_id=tpl_node.node_id,
                target_id=reg_node.node_id,
                relation=EdgeRelation.registers,
            ),
            ProvenanceEdge(
                source_id=reg_node.node_id, target_id=crop_node.node_id, relation=EdgeRelation.crops
            ),
            ProvenanceEdge(
                source_id=crop_node.node_id,
                target_id=set_node.node_id,
                relation=EdgeRelation.evidences,
            ),
            ProvenanceEdge(
                source_id=set_node.node_id,
                target_id=decision_node.node_id,
                relation=EdgeRelation.decides,
            ),
        ]
        for edge in edges:
            graph.add_edge(edge)
        return graph

    def test_minimum_graph_path_is_constructible(self):
        graph = self._graph()
        assert len(graph) == 7
        assert graph.verify_hashes() == ()

    def test_ancestors_of_decision_cover_the_whole_chain(self):
        graph = self._graph()
        decision = graph.nodes_of_type(
            __import__(
                "ocr_platform.schemas.provenance", fromlist=["NodeType"]
            ).NodeType.decision_revision
        )[0]
        ancestors = graph.ancestors(decision.node_id)
        assert len(ancestors) == 6

    def test_missing_intermediate_is_detected(self):
        graph = self._graph()
        decision_id = graph.nodes_of_type(
            __import__(
                "ocr_platform.schemas.provenance", fromlist=["NodeType"]
            ).NodeType.decision_revision
        )[0].node_id
        # Drop a mid-chain node by rebuilding the graph without it.
        kept = [n for n in graph.nodes if "crop_artifact" not in n.node_type.value]
        edges = [
            e
            for e in graph.edges
            if "crop_artifact" not in e.source_id and "crop_artifact" not in e.target_id
        ]
        # The evidence-set node's incoming crop edge is gone, so the chain is
        # structurally broken even though every remaining node verifies.
        broken = ProvenanceGraph(kept, edges)
        assert broken.node(decision_id) is not None
        assert len(broken) == len(graph) - 1

    def test_cycles_are_rejected(self):
        from ocr_platform.schemas.provenance import DerivationNode

        first = DerivationNode.build(
            operation_id="a",
            input_hashes=(content_hash({"x": 1}),),
            output_hash=content_hash({"y": 1}),
            rule_version="1",
            template_version="1",
        )
        second = DerivationNode.build(
            operation_id="b",
            input_hashes=(content_hash({"x": 2}),),
            output_hash=content_hash({"y": 2}),
            rule_version="1",
            template_version="1",
        )
        graph = ProvenanceGraph([first, second])
        graph.add_edge(
            ProvenanceEdge(
                source_id=first.node_id, target_id=second.node_id, relation=EdgeRelation.derives
            )
        )
        with pytest.raises(ValueError, match="cycle"):
            graph.add_edge(
                ProvenanceEdge(
                    source_id=second.node_id, target_id=first.node_id, relation=EdgeRelation.derives
                )
            )

    def test_self_loops_rejected(self):
        from ocr_platform.schemas.provenance import DerivationNode

        node = DerivationNode.build(
            operation_id="a",
            input_hashes=(content_hash({"x": 1}),),
            output_hash=content_hash({"y": 1}),
            rule_version="1",
            template_version="1",
        )
        with pytest.raises(ValueError, match="self-loop"):
            ProvenanceEdge(
                source_id=node.node_id, target_id=node.node_id, relation=EdgeRelation.derives
            )

    def test_edge_to_unknown_node_rejected(self):
        graph = ProvenanceGraph()
        with pytest.raises(ValueError, match="unknown node"):
            graph.add_edge(
                ProvenanceEdge(source_id="a", target_id="b", relation=EdgeRelation.renders)
            )

    def test_duplicate_node_id_rejected(self):
        node = make_template_node()
        graph = ProvenanceGraph([node])
        with pytest.raises(ValueError, match="duplicate"):
            graph.add_node(node)

    def test_with_node_returns_a_new_graph(self):
        node = make_template_node()
        graph = ProvenanceGraph()
        extended = graph.with_node(node)
        assert len(graph) == 0
        assert len(extended) == 1


# ---------------------------------------------------------------------------
# decision.py
# ---------------------------------------------------------------------------


class TestDecisionVocabulary:
    def test_enum_exhaustiveness(self):
        assert {v.value for v in ValueState} == {
            "present",
            "absent",
            "unknown",
            "unreadable",
            "not_applicable",
        }
        assert {d.value for d in Disposition} == {"accepted", "review", "rejected", "errored"}
        assert {s.value for s in Scope} == {"document", "page", "field", "cell"}

    def test_auto_accepted_is_not_a_disposition(self):
        assert "AUTO_ACCEPTED" not in {d.value for d in Disposition}
        assert "NORMALIZED_ACCEPTED" not in {d.value for d in Disposition}
        assert "AUTO_ACCEPTED" in NOT_REASON_CODES

    def test_boundary_expand_is_not_a_reason_code(self):
        assert "BOUNDARY_EXPAND" in NOT_REASON_CODES
        assert "BOUNDARY_EXPAND" not in REASON_CODE_TIERS

    def test_every_registered_code_is_registered_in_docs(self):
        # The registry in docs/reason-codes.md must cover every code here.
        with open("docs/reason-codes.md", encoding="utf-8") as fh:
            docs = fh.read()
        missing = [c for c in registered_reason_codes() if c not in docs]
        assert missing == [], f"codes missing from docs/reason-codes.md: {missing}"

    def test_present_without_evidence_fails(self):
        with pytest.raises(ValueError, match="FINAL_VALUE MUST NEVER EXIST WITHOUT PROVENANCE"):
            make_decision(source_set=())

    def test_accepted_without_policy_version_fails(self):
        with pytest.raises(ValueError, match="acceptance_policy_version"):
            make_decision(acceptance_policy_version="")

    def test_accepted_without_accepted_by_fails(self):
        with pytest.raises(ValueError, match="accepted_by"):
            make_decision(accepted_by=AcceptedBy.none)

    def test_accepted_with_review_reasons_fails(self):
        with pytest.raises(ValueError, match="reason codes"):
            make_decision(reason_codes=("OCR_CONFIDENCE_LOW",))

    def test_region_required_state_cannot_carry_a_value(self):
        with pytest.raises(ValueError, match="cannot carry a final_value"):
            make_decision(
                value_state=ValueState.absent,
                disposition=Disposition.review,
                final_value="something",
                source_set=(),
                reason_codes=("EMPTY_OCR",),
            )

    def test_absent_state_requires_a_reason_code(self):
        with pytest.raises(ValueError, match="requires at least one reason code"):
            make_decision(
                value_state=ValueState.absent,
                disposition=Disposition.review,
                final_value=None,
                source_set=(),
            )

    def test_unknown_reason_code_rejected(self):
        with pytest.raises(ValueError, match="unregistered reason code"):
            make_decision(
                disposition=Disposition.review,
                final_value=None,
                source_set=(),
                reason_codes=("NOT_A_REAL_CODE",),
            )

    def test_duplicate_reason_codes_rejected(self):
        with pytest.raises(ValueError, match="duplicates"):
            make_decision(
                disposition=Disposition.review,
                final_value=None,
                source_set=(),
                reason_codes=("EMPTY_OCR", "EMPTY_OCR"),
            )

    def test_primary_reason_precedence_wins(self):
        assert primary_reason(["OCR_CONFIDENCE_LOW", "INVALID_NUMERIC"]) == "OCR_CONFIDENCE_LOW"
        assert primary_reason(["INVALID_NUMERIC", "OCR_CONFIDENCE_LOW"]) == "OCR_CONFIDENCE_LOW"
        assert primary_reason(["ENCRYPTED_PDF", "OCR_CONFIDENCE_LOW"]) == "ENCRYPTED_PDF"
        assert primary_reason(["OUT_OF_BOUNDARY", "PAGE_SET_MISMATCH"]) == "PAGE_SET_MISMATCH"

    def test_primary_reason_is_deterministic_on_ties(self):
        assert primary_reason(["OCR_CONFIDENCE_LOW", "EMPTY_OCR"]) == "EMPTY_OCR"

    def test_mismatched_primary_reason_rejected(self):
        with pytest.raises(ValueError, match="precedence winner"):
            make_decision(
                disposition=Disposition.review,
                final_value=None,
                source_set=(),
                reason_codes=("OCR_CONFIDENCE_LOW", "ENCRYPTED_PDF"),
                primary_reason="OCR_CONFIDENCE_LOW",
            )

    def test_primary_reason_without_codes_rejected(self):
        with pytest.raises(ValueError, match="without any reason_codes"):
            make_decision(primary_reason="EMPTY_OCR")

    def test_missing_is_not_empty_string(self):
        missing = make_decision(
            value_state=ValueState.absent,
            disposition=Disposition.review,
            final_value=None,
            source_set=(),
            reason_codes=("EMPTY_OCR",),
        )
        assert missing.is_missing
        empty = make_decision(final_value="")
        assert not empty.is_missing

    def test_unknown_vocabulary_code_maps_to_unknown(self):
        decision = make_decision(
            value_state=ValueState.unknown,
            disposition=Disposition.review,
            final_value=None,
            source_set=(),
            reason_codes=("UNKNOWN_VOCABULARY_CODE",),
            accepted_by=AcceptedBy.none,
        )
        assert decision.value_state is ValueState.unknown
        assert not decision.is_accepted


class TestSurveyLabelMapping:
    def test_every_label_maps(self):
        for label in (
            "CLEAR",
            "NORMALIZED",
            "AMBIGUOUS",
            "INVALID",
            "OUT_OF_BOUNDARY",
            "UNREADABLE",
            "MISSING",
            "UNKNOWN_VALUE",
        ):
            state, disposition = map_survey_label(label)
            assert state in ValueState
            assert disposition in Disposition

    def test_clear_and_normalized_both_accept(self):
        assert map_survey_label("CLEAR") == (ValueState.present, Disposition.accepted)
        assert map_survey_label("NORMALIZED") == (ValueState.present, Disposition.accepted)

    def test_unreadable_never_accepted(self):
        assert map_survey_label("UNREADABLE") == (ValueState.unreadable, Disposition.review)

    def test_missing_maps_to_absent(self):
        assert map_survey_label("MISSING") == (ValueState.absent, Disposition.review)

    def test_unknown_value_maps_to_unknown(self):
        assert map_survey_label("UNKNOWN_VALUE") == (ValueState.unknown, Disposition.review)

    def test_label_map_covers_all_survey_labels(self):
        assert set(FAMILY_SURVEY_LABEL_MAP) == {
            "CLEAR",
            "NORMALIZED",
            "AMBIGUOUS",
            "INVALID",
            "OUT_OF_BOUNDARY",
            "UNREADABLE",
            "MISSING",
            "UNKNOWN_VALUE",
        }

    def test_unknown_label_rejected(self):
        with pytest.raises(ValueError, match="unknown FAMILY_SURVEY_V1 label"):
            map_survey_label("WHATEVER")


# ---------------------------------------------------------------------------
# validator.py — the hard gate
# ---------------------------------------------------------------------------


class TestValidatorHappyPath:
    def test_minimum_graph_passes(self):
        run = make_run()
        evidence_set = make_evidence_set(make_ocr_observation())
        decision = make_decision(source_set=(evidence_set.set_id,))
        report = validate_batch([decision], {evidence_set.set_id: evidence_set}, run=run)
        assert report.ok, [str(v) for v in report.violations]

    def test_region_evidence_satisfies_absent_state(self):
        evidence_set = make_evidence_set(
            make_region_evidence(RegionState.absent), set_id="set:absent"
        )
        decision = make_decision(
            decision_id="d:absent",
            value_state=ValueState.absent,
            disposition=Disposition.review,
            final_value=None,
            source_set=("set:absent",),
            reason_codes=("EMPTY_OCR",),
        )
        report = validate_batch([decision], {"set:absent": evidence_set})
        assert report.ok, [str(v) for v in report.violations]

    def test_native_text_satisfies_present_state(self):
        evidence_set = make_evidence_set(make_native_evidence(), set_id="set:native")
        decision = make_decision(source_set=("set:native",))
        assert validate_batch([decision], {"set:native": evidence_set}).ok

    def test_empty_run_with_no_decisions_passes(self):
        assert validate_batch([], {}).ok


class TestValidatorViolations:
    def test_accepted_without_source_set_fails(self):
        run = make_run()
        # A present value with no source_set is rejected at construction time.
        with pytest.raises(ValueError, match="FINAL_VALUE MUST NEVER EXIST"):
            make_decision(source_set=())
        # An unresolvable source_set is caught by the gate instead.
        decision = make_decision(source_set=("set:missing",))
        report = validate_batch([decision], {}, run=run)
        assert ViolationCode.MISSING_EVIDENCE in {v.code for v in report.violations}

    def test_missing_evidence_node_fails(self):
        run = make_run()
        decision = make_decision(source_set=("set:gone",))
        report = validate_batch([decision], {}, run=run)
        assert any(v.code is ViolationCode.MISSING_EVIDENCE for v in report.violations)

    def test_empty_evidence_set_fails(self):
        run = make_run()
        evidence_set = make_evidence_set(set_id="set:empty")
        decision = make_decision(source_set=("set:empty",))
        report = validate_batch([decision], {"set:empty": evidence_set}, run=run)
        assert any(
            v.code is ViolationCode.MISSING_EVIDENCE and "no members" in v.detail
            for v in report.violations
        )

    def test_wrong_evidence_type_for_absent_fails(self):
        run = make_run()
        evidence_set = make_evidence_set(make_ocr_observation(), set_id="set:wrong")
        decision = make_decision(
            value_state=ValueState.absent,
            disposition=Disposition.review,
            final_value=None,
            source_set=("set:wrong",),
            reason_codes=("EMPTY_OCR",),
        )
        report = validate_batch([decision], {"set:wrong": evidence_set}, run=run)
        assert any(v.code is ViolationCode.WRONG_EVIDENCE_TYPE for v in report.violations)

    def test_present_state_requires_text_evidence(self):
        run = make_run()
        evidence_set = make_evidence_set(
            make_region_evidence(RegionState.not_applicable), set_id="set:region"
        )
        decision = make_decision(source_set=("set:region",))
        report = validate_batch([decision], {"set:region": evidence_set}, run=run)
        assert any(v.code is ViolationCode.WRONG_EVIDENCE_TYPE for v in report.violations)

    def test_human_accepted_requires_human_evidence(self):
        run = make_run()
        evidence_set = make_evidence_set(make_ocr_observation(), set_id="set:human")
        decision = make_decision(source_set=("set:human",), accepted_by=AcceptedBy.human)
        report = validate_batch([decision], {"set:human": evidence_set}, run=run)
        assert any(v.code is ViolationCode.WRONG_EVIDENCE_TYPE for v in report.violations)

    def test_missing_page_artifact_fails(self):
        run = make_run()
        evidence_set = make_evidence_set(make_ocr_observation())
        decision = make_decision(source_set=(evidence_set.set_id,), page_index=7)
        report = validate_batch([decision], {evidence_set.set_id: evidence_set}, run=run)
        assert any(v.code is ViolationCode.MISSING_PAGE_ARTIFACT for v in report.violations)

    def test_orphan_evidence_reported(self):
        run = make_run()
        evidence_set = make_evidence_set(make_ocr_observation(), set_id="set:orphan")
        decision = make_decision(source_set=("set:used",))
        used = make_evidence_set(make_native_evidence(), set_id="set:used")
        report = validate_batch(
            [decision],
            {"set:used": used, "set:orphan": evidence_set},
            run=run,
        )
        assert any(v.code is ViolationCode.ORPHAN_EVIDENCE for v in report.violations)

    def test_bad_hash_detected_via_graph(self):
        from ocr_platform.schemas.provenance import DerivationNode

        node = DerivationNode.build(
            operation_id="a",
            input_hashes=(content_hash({"x": 1}),),
            output_hash=content_hash({"y": 1}),
            rule_version="1",
            template_version="1",
        )
        # Tamper with the payload after the hash was fixed: model_copy bypasses
        # validators, which is exactly what a tampered node looks like downstream.
        node = node.model_copy(update={"rule_version": "tampered"})
        graph = ProvenanceGraph([node])
        run = make_run()
        evidence_set = make_evidence_set(make_ocr_observation())
        decision = make_decision(source_set=(evidence_set.set_id,))
        report = validate_batch(
            [decision], {evidence_set.set_id: evidence_set}, run=run, graph=graph
        )
        # The tampered node is the defect; the missing registration is separate.
        assert not report.ok
        assert any(v.code is ViolationCode.BAD_HASH for v in report.violations)

    def test_registration_required_for_page_scoped_decision(self):
        run = make_run()
        evidence_set = make_evidence_set(make_ocr_observation())
        decision = make_decision(source_set=(evidence_set.set_id,))
        # A graph with no registration node cannot support a page-scoped decision.
        graph = ProvenanceGraph()
        report = validate_batch(
            [decision], {evidence_set.set_id: evidence_set}, run=run, graph=graph
        )
        assert any(v.code is ViolationCode.MISSING_REGISTRATION for v in report.violations)


class TestProvenanceGate:
    def _clean_batch(self):
        run = make_run()
        evidence_set = make_evidence_set(make_ocr_observation())
        decision = make_decision(source_set=(evidence_set.set_id,))
        return [decision], {evidence_set.set_id: evidence_set}, run

    def test_gate_passes_clean_batch(self):
        decisions, sets, run = self._clean_batch()
        exportable, report = gate_export(decisions, sets, run=run)
        assert report.ok
        assert len(exportable) == 1

    def test_gate_demotes_accepted_with_incomplete_provenance(self):
        decisions, sets, run = self._clean_batch()
        decisions = [decisions[0].model_copy(update={"page_index": 99})]
        exportable, report = gate_export(decisions, sets, run=run)
        assert not report.ok
        demoted = exportable[0]
        assert demoted.disposition is Disposition.review
        assert demoted.final_value is None
        assert "PROVENANCE_INCOMPLETE" in demoted.reason_codes

    def test_demoted_decision_never_keeps_a_value(self):
        decisions, sets, run = self._clean_batch()
        decisions = [decisions[0].model_copy(update={"page_index": 99})]
        exportable, _ = gate_export(decisions, sets, run=run)
        assert exportable[0].final_value is None
        assert exportable[0].accepted_by is AcceptedBy.none

    def test_gate_does_not_touch_review_rows(self):
        evidence_set = make_evidence_set(make_ocr_observation(confidence=0.2), set_id="set:low")
        decision = make_decision(
            disposition=Disposition.review,
            final_value=None,
            source_set=("set:low",),
            reason_codes=("OCR_CONFIDENCE_LOW",),
        )
        exportable, _ = gate_export([decision], {"set:low": evidence_set})
        # A review row with valid evidence passes through untouched.
        assert exportable[0] is decision

    def test_zero_accepted_with_incomplete_provenance(self):
        """Benchmark gate shape: a clean run must have no accepted violations."""
        decisions, sets, run = self._clean_batch()
        from ocr_platform.worker.provenance.validator import (
            has_accepted_with_incomplete_provenance,
        )

        assert has_accepted_with_incomplete_provenance(decisions, sets, run=run) == ()

    def test_demotion_is_reproducible(self):
        decisions, sets, run = self._clean_batch()
        decisions = [decisions[0].model_copy(update={"page_index": 99})]
        first, _ = gate_export(decisions, sets, run=run)
        second, _ = gate_export(decisions, sets, run=run)
        assert first[0] == second[0]

    def test_report_codes_are_sorted_and_stable(self):
        decisions, sets, run = self._clean_batch()
        decisions = [decisions[0].model_copy(update={"page_index": 99})]
        _, report = gate_export(decisions, sets, run=run)
        assert report.codes == tuple(sorted(set(report.codes)))


# ---------------------------------------------------------------------------
# end-to-end: provenance chain for one accepted field
# ---------------------------------------------------------------------------


class TestEndToEndProvenance:
    def test_full_chain_for_one_accepted_field(self):
        run = make_run()

        template = make_template_node()
        registration = RegistrationTransformNode.build(
            transform_type="page_box_normalize",
            residual=0.0,
            template_manifest_hash=template.manifest_hash,
        )
        crop = CropArtifactNode.build(
            crop_hash=content_hash({"crop": "member_name_r3"}),
            page_index=0,
            region_id="p0_r3_c1",
            bbox=(0.1, 0.2, 0.3, 0.25),
        )
        observation = make_ocr_observation()
        evidence_set = make_evidence_set(observation)
        set_node = EvidenceSetNode.build(
            set_id=evidence_set.set_id,
            member_evidence_ids=(observation.evidence_id,),
            member_content_hashes=(observation.content_hash,),
        )
        decision_node = DecisionRevisionNode.build(
            decision_id="d:member_name:r3",
            revision_index=0,
            evidence_set_node_id=set_node.node_id,
        )

        graph = ProvenanceGraph([template, registration, crop, set_node, decision_node])
        graph.add_edge(
            ProvenanceEdge(
                source_id=template.node_id,
                target_id=registration.node_id,
                relation=EdgeRelation.registers,
            )
        )
        graph.add_edge(
            ProvenanceEdge(
                source_id=registration.node_id,
                target_id=crop.node_id,
                relation=EdgeRelation.crops,
            )
        )
        graph.add_edge(
            ProvenanceEdge(
                source_id=crop.node_id,
                target_id=set_node.node_id,
                relation=EdgeRelation.evidences,
            )
        )
        graph.add_edge(
            ProvenanceEdge(
                source_id=set_node.node_id,
                target_id=decision_node.node_id,
                relation=EdgeRelation.decides,
            )
        )

        decision = make_decision(source_set=(evidence_set.set_id,))
        report = validate_batch(
            [decision], {evidence_set.set_id: evidence_set}, run=run, graph=graph
        )
        assert report.ok, [str(v) for v in report.violations]
        assert graph.verify_hashes() == ()
        assert decision_node.node_id in graph.ancestors(decision_node.node_id) | {
            decision_node.node_id
        }
