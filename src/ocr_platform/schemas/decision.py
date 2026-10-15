"""Field decision models and the orthogonal status vocabulary.

Four axes stay separate and are never collapsed into one overloaded status enum:

* ``scope`` — which entity the decision is about (document / page / field / cell)
* ``value_state`` — ``present`` | ``absent`` | ``unknown`` | ``unreadable`` | ``not_applicable``
* ``disposition`` — ``accepted`` | ``review`` | ``rejected`` | ``errored``
* ``reason_codes`` — multi-label, with one ``primary_reason`` by precedence

``AUTO_ACCEPTED`` and ``NORMALIZED_ACCEPTED`` are deliberately **not** enum
values: both are ``disposition=accepted`` distinguished by ``accepted_by`` plus
``acceptance_policy_version``. ``BOUNDARY_EXPAND`` is a proposal action, never a
disposition.

The reason-code registry lives in ``docs/reason-codes.md``; this module is its
typed mirror. New codes must be added there first.
"""

from __future__ import annotations

from collections.abc import Iterable
from enum import Enum

from pydantic import BaseModel, ConfigDict, model_validator

# --- reason-code registry ------------------------------------------------
# Tiers mirror docs/reason-codes.md §4 precedence, most severe first.

TIER_DOCUMENT_TERMINAL = 1
TIER_PAGE_BLOCKING = 2
TIER_STRUCTURAL_BOUNDARY = 3
TIER_EVIDENCE_QUALITY = 4
TIER_VALUE_SEMANTICS = 5

REASON_CODE_TIERS: dict[str, int] = {
    # 2.1 document-level (terminal, before any field decision)
    "ENCRYPTED_PDF": TIER_DOCUMENT_TERMINAL,
    "CORRUPT_PDF": TIER_DOCUMENT_TERMINAL,
    "EMPTY_DOCUMENT": TIER_DOCUMENT_TERMINAL,
    # 2.2 page-level (blocks field acceptance on that page)
    "PAGE_SET_MISMATCH": TIER_PAGE_BLOCKING,
    "REGISTRATION_RESIDUAL_HIGH": TIER_PAGE_BLOCKING,
    # 2.3 field / cell-level hard-review reasons
    "WRONG_TEMPLATE": TIER_STRUCTURAL_BOUNDARY,
    "OUT_OF_BOUNDARY": TIER_STRUCTURAL_BOUNDARY,
    "BOUNDARY_CROSS": TIER_STRUCTURAL_BOUNDARY,
    "BOUNDARY_TOUCH": TIER_STRUCTURAL_BOUNDARY,
    "BOUNDARY_OVERLAP": TIER_STRUCTURAL_BOUNDARY,
    "OCR_UNSTABLE": TIER_EVIDENCE_QUALITY,
    "OCR_CONFIDENCE_LOW": TIER_EVIDENCE_QUALITY,
    "HANDWRITING_SUSPECTED": TIER_EVIDENCE_QUALITY,
    "UNKNOWN_VOCABULARY_CODE": TIER_VALUE_SEMANTICS,
    "INVALID_NUMERIC": TIER_VALUE_SEMANTICS,
    "MULTIPLE_CANDIDATES": TIER_VALUE_SEMANTICS,
    "CONFLICTING_MARKS": TIER_VALUE_SEMANTICS,
    "MULTI_SINGLE_SELECT": TIER_VALUE_SEMANTICS,
    "UNKNOWN_SYMBOL": TIER_VALUE_SEMANTICS,
    "DITTO_UNRESOLVED": TIER_VALUE_SEMANTICS,
    "CROSS_FIELD_CONFLICT": TIER_VALUE_SEMANTICS,
    # 2.4 row-level
    "ROW_UNDERSEGMENT": TIER_VALUE_SEMANTICS,
    "ROW_OVERSEGMENT": TIER_VALUE_SEMANTICS,
    "ROW_UNCERTAIN": TIER_VALUE_SEMANTICS,
    # experimental crop/classifier additions
    "AUTO_ACCEPT_DISABLED": TIER_EVIDENCE_QUALITY,
    "DRAFT_RULES": TIER_VALUE_SEMANTICS,
    "EMPTY_OCR": TIER_EVIDENCE_QUALITY,
    "TEXT_TOO_LONG": TIER_VALUE_SEMANTICS,
    "UNCONFIGURED_FIELD": TIER_VALUE_SEMANTICS,
    "INVALID_INTEGER": TIER_VALUE_SEMANTICS,
    "INTEGER_OUT_OF_RANGE": TIER_VALUE_SEMANTICS,
    "INVALID_DIGIT_SEQUENCE": TIER_VALUE_SEMANTICS,
    "OCR_FAILED": TIER_EVIDENCE_QUALITY,
    "OCR_CONFIDENCE_UNAVAILABLE": TIER_EVIDENCE_QUALITY,
    "CLASSIFICATION_SKIPPED_UNCERTAIN_OCR": TIER_EVIDENCE_QUALITY,
    "INVALID_CLASSIFIER_RESPONSE": TIER_VALUE_SEMANTICS,
    "UNKNOWN_CATEGORY": TIER_VALUE_SEMANTICS,
    "LOW_CLASSIFICATION_CONFIDENCE": TIER_VALUE_SEMANTICS,
    "CLASSIFIER_FAILED": TIER_VALUE_SEMANTICS,
    # validator-emitted: a decision demoted by the provenance hard gate
    "PROVENANCE_INCOMPLETE": TIER_STRUCTURAL_BOUNDARY,
}

#: Tokens that appear in prose but are NOT dispositions or reason codes.
NOT_REASON_CODES = frozenset(
    {
        "AUTO_ACCEPTED",
        "NORMALIZED_ACCEPTED",
        "BOUNDARY_EXPAND",
    }
)


class Scope(str, Enum):
    document = "document"
    page = "page"
    field = "field"
    cell = "cell"


class ValueState(str, Enum):
    present = "present"
    absent = "absent"
    unknown = "unknown"
    unreadable = "unreadable"
    not_applicable = "not_applicable"


class Disposition(str, Enum):
    accepted = "accepted"
    review = "review"
    rejected = "rejected"
    errored = "errored"


class AcceptedBy(str, Enum):
    none = "none"
    policy = "policy"
    human = "human"


REGION_REQUIRED_STATES = frozenset(
    {
        ValueState.absent,
        ValueState.unreadable,
        ValueState.not_applicable,
    }
)


def is_known_reason_code(code: str) -> bool:
    return code in REASON_CODE_TIERS


def primary_reason(codes: Iterable[str]) -> str | None:
    """Pick one ``primary_reason`` from *codes* by registry precedence.

    Most severe tier wins. Ties break lexicographically so the choice is
    deterministic. Unknown codes sort last, since an unregistered code cannot
    be ranked against the registry.
    """
    ranked = sorted(
        codes,
        key=lambda code: (REASON_CODE_TIERS.get(code, 99), code),
    )
    return ranked[0] if ranked else None


class FieldDecision(BaseModel):
    """One field/cell decision: state, disposition, reasons, and evidence links.

    ``final_value is None`` means *missing* — it is never conflated with ``""``,
    which is a real observed empty string. ``source_set`` holds evidence IDs and
    must resolve through a valid :class:`~ocr_platform.schemas.evidence.EvidenceSet`
    before any value is written (the validator enforces this).
    """

    model_config = ConfigDict(frozen=True)

    decision_id: str
    scope: Scope
    value_state: ValueState
    disposition: Disposition
    field_id: str | None = None
    page_index: int | None = None
    row_index: int | None = None
    col_index: int | None = None
    final_value: str | None = None
    reason_codes: tuple[str, ...] = ()
    primary_reason: str | None = None
    accepted_by: AcceptedBy = AcceptedBy.none
    acceptance_policy_version: str = ""
    template_version: str = ""
    source_set: tuple[str, ...] = ()
    revision_of_decision_id: str | None = None

    @model_validator(mode="after")
    def _validate(self) -> FieldDecision:
        unknown = [c for c in self.reason_codes if not is_known_reason_code(c)]
        if unknown:
            raise ValueError(
                f"unregistered reason code(s) {unknown}; register them in "
                "docs/reason-codes.md before use"
            )
        forbidden = [c for c in self.reason_codes if c in NOT_REASON_CODES]
        if forbidden:
            raise ValueError(
                f"{forbidden} are not reason codes; AUTO_ACCEPTED/NORMALIZED_ACCEPTED "
                "are dispositions distinguished by accepted_by"
            )
        if len(set(self.reason_codes)) != len(self.reason_codes):
            raise ValueError("reason_codes must not contain duplicates")

        # Semantic checks run before the primary_reason consistency check so a
        # malformed decision reports its real defect, not a downstream mismatch.
        if (
            self.value_state is ValueState.present
            and self.final_value is not None
            and not self.source_set
        ):
            raise ValueError(
                "FINAL_VALUE MUST NEVER EXIST WITHOUT PROVENANCE: a present "
                "value requires a non-empty source_set"
            )

        if self.value_state in REGION_REQUIRED_STATES and self.final_value is not None:
            raise ValueError(f"value_state={self.value_state.value} cannot carry a final_value")

        if self.disposition is Disposition.accepted:
            if self.value_state is not ValueState.present:
                raise ValueError("only value_state=present can be accepted")
            if self.final_value is None:
                raise ValueError("accepted decision requires a final_value")
            if not self.source_set:
                raise ValueError("accepted decision requires evidence links")
            if self.accepted_by is AcceptedBy.none:
                raise ValueError(
                    "accepted decision requires accepted_by; AUTO_ACCEPTED and "
                    "NORMALIZED_ACCEPTED are both 'accepted' plus accepted_by"
                )
            if not self.acceptance_policy_version:
                raise ValueError("accepted decision requires acceptance_policy_version")
            if self.reason_codes:
                raise ValueError(
                    f"accepted decision cannot carry review reason codes {list(self.reason_codes)}"
                )

        if self.disposition in (Disposition.review, Disposition.errored) and not self.reason_codes:
            raise ValueError(
                f"disposition={self.disposition.value} requires at least one reason code"
            )

        if self.page_index is not None and self.page_index < 0:
            raise ValueError("page_index must be non-negative")
        if self.row_index is not None and self.row_index < 0:
            raise ValueError("row_index must be non-negative")

        if self.reason_codes:
            expected = primary_reason(self.reason_codes)
            if self.primary_reason != expected:
                raise ValueError(
                    f"primary_reason {self.primary_reason!r} must equal the "
                    f"precedence winner {expected!r} for {list(self.reason_codes)}"
                )
        elif self.primary_reason is not None:
            raise ValueError("primary_reason set without any reason_codes")

        return self

    @property
    def is_missing(self) -> bool:
        """True when the value is absent, not merely empty."""
        return self.final_value is None

    @property
    def is_accepted(self) -> bool:
        return self.disposition is Disposition.accepted


class DecisionRevision(BaseModel):
    """An append-only correction to an existing decision.

    Corrections create revisions; they never overwrite the original. The prior
    decision ID is retained so the audit trail stays walkable.
    """

    model_config = ConfigDict(frozen=True)

    revision_id: str
    decision_id: str
    revision_index: int
    revised_decision: FieldDecision
    reviewer_id: str | None = None
    human_evidence_id: str | None = None
    created_at: float = 0.0

    @model_validator(mode="after")
    def _validate(self) -> DecisionRevision:
        if self.revised_decision.decision_id != self.decision_id:
            raise ValueError("revision must carry the same decision_id it revises")
        if self.revision_index < 1:
            raise ValueError("revision_index starts at 1; the original is index 0")
        if (
            self.reviewer_id is not None
            and self.revised_decision.accepted_by is not AcceptedBy.human
        ):
            raise ValueError("a human revision must record accepted_by=human")
        return self


# FAMILY_SURVEY_V1 label → storage mapping (docs/reason-codes.md §2.3 table).
FAMILY_SURVEY_LABEL_MAP: dict[str, tuple[ValueState, Disposition]] = {
    "CLEAR": (ValueState.present, Disposition.accepted),
    "NORMALIZED": (ValueState.present, Disposition.accepted),
    "AMBIGUOUS": (ValueState.present, Disposition.review),
    "INVALID": (ValueState.present, Disposition.review),
    "OUT_OF_BOUNDARY": (ValueState.present, Disposition.review),
    "UNREADABLE": (ValueState.unreadable, Disposition.review),
    "MISSING": (ValueState.absent, Disposition.review),
    "UNKNOWN_VALUE": (ValueState.unknown, Disposition.review),
}


def map_survey_label(label: str) -> tuple[ValueState, Disposition]:
    """Map a FAMILY_SURVEY_V1 field label onto the storage axes."""
    key = label.strip().upper()
    if key not in FAMILY_SURVEY_LABEL_MAP:
        raise ValueError(
            f"unknown FAMILY_SURVEY_V1 label {label!r}; "
            f"expected one of {sorted(FAMILY_SURVEY_LABEL_MAP)}"
        )
    return FAMILY_SURVEY_LABEL_MAP[key]


def registered_reason_codes() -> tuple[str, ...]:
    """Every registered reason code, sorted."""
    return tuple(sorted(REASON_CODE_TIERS))
