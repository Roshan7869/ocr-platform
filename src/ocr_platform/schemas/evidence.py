"""Typed evidence nodes and :class:`EvidenceSet`.

Evidence is immutable, content-addressed input to decisions. It is never
rewritten by normalization or acceptance, and it never carries a composite
confidence — aggregation is a decision-layer concern and lives in
``schemas/decision.py`` and the Laya layers.

Layout note: ``schemas/provenance.py`` and this module each name the other in
their spec "Calls" lists, which forms a cycle. At runtime this module depends
only on ``worker/provenance/hashing.py`` (content hashes and ID well-formedness);
provenance nodes reference evidence by ID string, so no runtime import is needed
in that direction.

Coordinate systems are owned here as bbox constants; the transforms that convert
between them live in ``worker/render/coordinates.py``.
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Any, Iterable, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ocr_platform.worker.provenance.hashing import content_hash, is_content_hash

IMAGE_TOP_LEFT_PIXEL = "image_top_left_pixel"
PAGE_SPACE_SYSTEM = "image_top_left_normalized"
PDF_BOTTOM_LEFT_NATIVE = "pdf_bottom_left_native"
CROP_LOCAL_TOP_LEFT = "crop_local_top_left"

COORDINATE_SYSTEMS = frozenset({
    IMAGE_TOP_LEFT_PIXEL,
    PAGE_SPACE_SYSTEM,
    PDF_BOTTOM_LEFT_NATIVE,
    CROP_LOCAL_TOP_LEFT,
})
CROP_LOCAL_SYSTEMS = frozenset({CROP_LOCAL_TOP_LEFT})


class BBox(BaseModel):
    """A rectangle that always knows its coordinate system.

    ``coordinate_system`` is required, so a box can never be created without
    one. Page-space boxes must be normalized into the unit box; crop-local
    boxes are tagged and never accepted as evidence page-space boxes.
    """

    model_config = ConfigDict(frozen=True)

    x0: float
    y0: float
    x1: float
    y1: float
    coordinate_system: str

    @model_validator(mode="after")
    def _validate(self) -> "BBox":
        if self.coordinate_system not in COORDINATE_SYSTEMS:
            raise ValueError(
                f"unknown coordinate_system {self.coordinate_system!r}; "
                f"expected one of {sorted(COORDINATE_SYSTEMS)}"
            )
        if self.x1 < self.x0 or self.y1 < self.y0:
            raise ValueError(
                f"degenerate bbox ({self.x0}, {self.y0}, {self.x1}, {self.y1})"
            )
        if self.coordinate_system == PAGE_SPACE_SYSTEM and not (
            0.0 <= self.x0 <= self.x1 <= 1.0 and 0.0 <= self.y0 <= self.y1 <= 1.0
        ):
            raise ValueError("normalized page-space bbox must lie within the unit box")
        return self

    @property
    def is_page_space(self) -> bool:
        return self.coordinate_system == PAGE_SPACE_SYSTEM

    @property
    def is_crop_local(self) -> bool:
        return self.coordinate_system in CROP_LOCAL_SYSTEMS

    @property
    def as_tuple(self) -> tuple[float, float, float, float]:
        return (self.x0, self.y0, self.x1, self.y1)


class EvidenceType(str, Enum):
    ocr_observation = "ocr_observation"
    native_text = "native_text"
    region = "region"
    human_correction = "human_correction"


class EvidenceNode(BaseModel):
    """Immutable envelope shared by every evidence kind.

    ``evidence_id`` is derived from the content hash, so it is stable and
    read-only. ``source_region_id`` is mandatory: evidence without a source
    region is invented evidence.
    """

    model_config = ConfigDict(frozen=True)

    evidence_type: EvidenceType
    source_page_index: int
    source_region_id: str
    content_hash: str
    created_at: float = Field(default_factory=time.time)

    @property
    def evidence_id(self) -> str:
        return f"{self.evidence_type.value}:{self.content_hash[:24]}"

    @model_validator(mode="after")
    def _validate_envelope(self) -> "EvidenceNode":
        """Envelope checks shared by every evidence kind."""
        if not is_content_hash(self.content_hash):
            raise ValueError(
                f"{self.evidence_type.value} evidence requires a sha256 hex "
                f"content_hash, got {self.content_hash!r}"
            )
        if self.source_page_index < 0:
            raise ValueError("source_page_index must be non-negative")
        if not self.source_region_id:
            raise ValueError(
                "evidence requires a source_region_id; inventing evidence "
                "without a source region is forbidden"
            )
        return self


class OcrObservation(EvidenceNode):
    """One det+rec recognition result.

    Carries model versions, raw OCR confidence, and render/preprocess metadata
    so a reader can tell which stack produced it. ``bbox`` is page-space;
    ``crop_local_bbox`` is the crop-local intermediate and is never mixed in.
    """

    evidence_type: Literal[EvidenceType.ocr_observation] = EvidenceType.ocr_observation

    raw_text: str
    raw_confidence: float
    det_model_version: str
    rec_model_version: str
    render_metadata_hash: str
    preprocess_metadata_hash: str
    field_id: str | None = None
    row_index: int | None = None
    col_index: int | None = None
    bbox: BBox | None = None
    crop_local_bbox: BBox | None = None

    @model_validator(mode="after")
    def _validate_observation(self) -> "OcrObservation":
        if not 0.0 <= self.raw_confidence <= 1.0:
            raise ValueError(f"raw_confidence must be within [0, 1], got {self.raw_confidence}")
        if self.bbox is not None and not self.bbox.is_page_space:
            raise ValueError(
                "evidence bbox must be page-space "
                f"({PAGE_SPACE_SYSTEM}); crop-local boxes go in crop_local_bbox"
            )
        if self.crop_local_bbox is not None and not self.crop_local_bbox.is_crop_local:
            raise ValueError("crop_local_bbox must use a crop_local_* coordinate system")
        return self


class NativeTextEvidence(EvidenceNode):
    """Text lifted from a digital PDF's own text layer.

    This is a *source* observation, not an OCR observation: it deliberately has
    no ``raw_confidence`` and no recognition model version, so it can never be
    mistaken for one.
    """

    evidence_type: Literal[EvidenceType.native_text] = EvidenceType.native_text

    raw_text: str
    extractor: str
    extractor_version: str
    bbox: BBox | None = None


class RegionState(str, Enum):
    absent = "absent"
    unreadable = "unreadable"
    not_applicable = "not_applicable"


class RegionEvidence(EvidenceNode):
    """Proof that a region was empty, unreadable, or not applicable.

    Required for the ``absent`` / ``unreadable`` / ``not_applicable`` value
    states; a decision in one of those states without this node is invalid.
    """

    evidence_type: Literal[EvidenceType.region] = EvidenceType.region

    region_state: RegionState
    detection_method: str


class HumanCorrectionEvidence(EvidenceNode):
    """A human override recorded against prior evidence (R2+ review path).

    Can replace an OCR claim without faking OCR: the original observation node
    is left untouched and referenced by ``revision_of_evidence_id``.
    """

    evidence_type: Literal[EvidenceType.human_correction] = EvidenceType.human_correction

    corrected_value: str
    reviewer_id: str
    revision_of_evidence_id: str | None = None


class EvidenceSet(BaseModel):
    """An immutable membership grouping of evidence nodes for one cell.

    Deliberately exposes **no** confidence aggregation — there is no composite
    ``final_confidence`` anywhere on this type. Duplicate detections stay
    separate members until :meth:`collapse_exact_duplicates` records a policy
    operation that collapses them.
    """

    model_config = ConfigDict(frozen=True)

    set_id: str
    members: tuple[EvidenceNode, ...] = ()

    def evidence_ids(self) -> tuple[str, ...]:
        return tuple(member.evidence_id for member in self.members)

    def of_type(self, evidence_type: EvidenceType) -> tuple[EvidenceNode, ...]:
        return tuple(m for m in self.members if m.evidence_type is evidence_type)

    def by_id(self, evidence_id: str) -> EvidenceNode | None:
        return next((m for m in self.members if m.evidence_id == evidence_id), None)

    def collapse_exact_duplicates(self, policy_id: str) -> tuple["EvidenceSet", str]:
        """Collapse byte-identical detections under a recorded policy operation.

        Returns a *new* set plus the operation id that produced it. Exact
        duplicates (equal ``content_hash``) are the only ones collapsed; merely
        similar text stays as distinct nodes.
        """
        kept: list[EvidenceNode] = []
        seen: set[str] = set()
        for member in self.members:
            if member.content_hash in seen:
                continue
            seen.add(member.content_hash)
            kept.append(member)
        operation_id = content_hash({
            "policy_id": policy_id,
            "set_id": self.set_id,
            "input_hashes": [member.content_hash for member in self.members],
            "kept_hashes": [member.content_hash for member in kept],
        })
        collapsed = self.model_copy(update={
            "set_id": f"{self.set_id}:collapsed:{operation_id[:12]}",
            "members": tuple(kept),
        })
        return collapsed, operation_id


def page_space_bbox(x0: float, y0: float, x1: float, y1: float) -> BBox:
    """Convenience constructor for a normalized page-space box."""
    return BBox(x0=x0, y0=y0, x1=x1, y1=y1, coordinate_system=PAGE_SPACE_SYSTEM)


def iter_evidence(sets: Iterable[EvidenceSet]) -> Iterable[EvidenceNode]:
    """Yield every evidence node across *sets*, preserving order."""
    for evidence_set in sets:
        yield from evidence_set.members


def evidence_type_names(types: Iterable[EvidenceType]) -> tuple[str, ...]:
    """Sorted type names, for stable error messages."""
    return tuple(sorted(t.value for t in types))
