"""Pydantic models for run identity and page lifecycle.

Owns the run-identity tuple, the capability matrix, and the configuration
fingerprint shape. No I/O, no OCR, and no acceptance decisions happen here.

Run identity is ``(document_content_hash, configuration_fingerprint)``: identical
uploaded bytes under identical configuration produce the same ``run_id``, and a
retry never mints a new one. A retry is a separate *attempt* record under the
same run, so the identity stays stable while attempts are still countable.
"""

from __future__ import annotations

import hashlib
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ocr_platform.worker.provenance.hashing import content_hash, is_content_hash


class PageClass(str, Enum):
    """Capability matrix classification for one page."""

    scanned_only = "scanned_only"
    native_only = "native_only"
    mixed = "mixed"
    encrypted = "encrypted"
    corrupt = "corrupt"
    empty = "empty"
    page_set_mismatch = "page_set_mismatch"


TERMINAL_PAGE_CLASSES = frozenset({
    PageClass.encrypted,
    PageClass.corrupt,
    PageClass.empty,
})


class DocumentDisposition(str, Enum):
    ok = "ok"
    errored = "errored"


class DocumentErrorCode(str, Enum):
    ENCRYPTED_PDF = "ENCRYPTED_PDF"
    CORRUPT_PDF = "CORRUPT_PDF"
    EMPTY_DOCUMENT = "EMPTY_DOCUMENT"


PAGE_CLASS_ERROR_CODE = {
    PageClass.encrypted: DocumentErrorCode.ENCRYPTED_PDF,
    PageClass.corrupt: DocumentErrorCode.CORRUPT_PDF,
    PageClass.empty: DocumentErrorCode.EMPTY_DOCUMENT,
}


def document_content_hash(pdf_bytes: bytes) -> str:
    """sha256 of the exact uploaded PDF bytes (R0/R1 run identity)."""
    return hashlib.sha256(pdf_bytes).hexdigest()


class ConfigurationFingerprint(BaseModel):
    """Everything about a run that must be identical for reproducible output.

    The fingerprint is content-hashed, so adding or changing any field yields a
    different fingerprint and therefore a different ``run_id``.
    """

    model_config = ConfigDict(frozen=True)

    template_manifest_hash: str
    runtime_config_hash: str
    acceptance_policy_version: str
    canonical_algorithm_id: str
    dpi: int
    engine_versions: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate(self) -> "ConfigurationFingerprint":
        for field_name in ("template_manifest_hash", "runtime_config_hash"):
            value = getattr(self, field_name)
            if not is_content_hash(value):
                raise ValueError(f"{field_name} must be a sha256 hex digest, got {value!r}")
        if self.dpi <= 0:
            raise ValueError("dpi must be positive")
        return self

    def fingerprint(self) -> str:
        return content_hash(self.model_dump(mode="json"))


class RenderMetadata(BaseModel):
    """How a page was turned into pixels.

    ``media_box_pdf_points`` is recorded in PDF bottom-left native coordinates
    and converted explicitly by ``worker/render/coordinates.py``; it is never
    silently treated as image top-left space.
    """

    model_config = ConfigDict(frozen=True)

    renderer: str
    renderer_version: str
    dpi: int
    scale: float
    colorspace: str
    media_box_pdf_points: tuple[float, float, float, float]
    width_px: int
    height_px: int

    @model_validator(mode="after")
    def _validate(self) -> "RenderMetadata":
        if self.dpi <= 0 or self.scale <= 0:
            raise ValueError("dpi and scale must be positive")
        if self.width_px <= 0 or self.height_px <= 0:
            raise ValueError("rendered pixel dimensions must be positive")
        return self


class PageArtifact(BaseModel):
    """One rendered page: immutable identity plus its render record."""

    model_config = ConfigDict(frozen=True)

    artifact_id: str
    page_index: int
    page_class: PageClass
    content_hash: str
    render_metadata: RenderMetadata
    width_px: int
    height_px: int

    @model_validator(mode="after")
    def _validate(self) -> "PageArtifact":
        if self.page_index < 0:
            raise ValueError("page_index must be non-negative")
        if not is_content_hash(self.content_hash):
            raise ValueError("page content_hash must be a sha256 hex digest")
        if (self.width_px, self.height_px) != (
            self.render_metadata.width_px,
            self.render_metadata.height_px,
        ):
            raise ValueError("page pixel dimensions must match render metadata")
        return self


class RunAttempt(BaseModel):
    """One execution attempt under a stable ``run_id``.

    Retries append attempts; they never change the run identity.
    """

    model_config = ConfigDict(frozen=True)

    attempt_index: int
    started_at: float
    finished_at: float | None = None
    outcome: str = "running"

    @model_validator(mode="after")
    def _validate(self) -> "RunAttempt":
        if self.attempt_index < 0:
            raise ValueError("attempt_index must be non-negative")
        if self.finished_at is not None and self.finished_at < self.started_at:
            raise ValueError("finished_at cannot precede started_at")
        return self


class DocumentRun(BaseModel):
    """Run identity and lifecycle for one uploaded document.

    Encrypted/corrupt/empty documents are ``errored`` with a terminal reason
    code and carry **zero** field decisions — the document never reaches any
    per-field acceptance step.
    """

    model_config = ConfigDict(frozen=True)

    run_id: str
    document_content_hash: str
    configuration_fingerprint: ConfigurationFingerprint
    template_version: str
    pages: tuple[PageArtifact, ...] = ()
    attempts: tuple[RunAttempt, ...] = ()
    disposition: DocumentDisposition = DocumentDisposition.ok
    document_error_code: DocumentErrorCode | None = None
    created_at: float = Field(default_factory=lambda: 0.0)

    @classmethod
    def create(
        cls,
        pdf_bytes: bytes,
        fingerprint: ConfigurationFingerprint,
        template_version: str,
        pages: tuple[PageArtifact, ...] = (),
        created_at: float = 0.0,
    ) -> "DocumentRun":
        """Build a run, deriving identity and any terminal document error.

        Identity is a pure function of the uploaded bytes plus the
        configuration fingerprint, so it is reproducible across processes.
        """
        digest = document_content_hash(pdf_bytes)
        run_id = content_hash({
            "document_content_hash": digest,
            "configuration_fingerprint": fingerprint.fingerprint(),
        })
        error_code: DocumentErrorCode | None = None
        terminal = [p for p in pages if p.page_class in TERMINAL_PAGE_CLASSES]
        if terminal:
            error_code = PAGE_CLASS_ERROR_CODE[terminal[0].page_class]
        if not pages:
            error_code = DocumentErrorCode.EMPTY_DOCUMENT
        disposition = (
            DocumentDisposition.errored if error_code is not None else DocumentDisposition.ok
        )
        return cls(
            run_id=run_id,
            document_content_hash=digest,
            configuration_fingerprint=fingerprint,
            template_version=template_version,
            pages=pages,
            disposition=disposition,
            document_error_code=error_code,
            created_at=created_at,
        )

    @model_validator(mode="after")
    def _validate(self) -> "DocumentRun":
        if self.disposition is DocumentDisposition.errored and self.document_error_code is None:
            raise ValueError("errored document requires a document_error_code")
        if self.disposition is DocumentDisposition.ok and self.document_error_code is not None:
            raise ValueError("non-errored document cannot carry a document_error_code")
        indices = [page.page_index for page in self.pages]
        if indices != sorted(indices):
            raise ValueError("pages must be ordered by page_index")
        if len(set(indices)) != len(indices):
            raise ValueError("duplicate page_index in run")
        return self

    @property
    def is_errored(self) -> bool:
        return self.disposition is DocumentDisposition.errored

    def with_attempt(self, attempt: RunAttempt) -> "DocumentRun":
        """Return a new run with *attempt* appended (runs are immutable)."""
        return self.model_copy(update={"attempts": (*self.attempts, attempt)})

    def attempt_count(self) -> int:
        return len(self.attempts)


def fingerprint_payload(extra: dict[str, Any] | None = None) -> str:
    """Content-hash an arbitrary fingerprint payload deterministically."""
    return content_hash(extra or {})
