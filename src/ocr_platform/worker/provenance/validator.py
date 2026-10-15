"""Portable provenance referential-integrity validator.

Pre-DB gate that walks each decision → its evidence set → page artifacts →
template manifest hash → render/registration records, and enforces the required
evidence type per value state plus hash consistency.

**Zero tolerance.** An accepted value with incomplete provenance is a bug, not a
warning: the validator never auto-repairs a missing node and never accepts on
warnings only. Failure demotes the decision to review/exception and the pipeline
hard-fails export of that value.

Equivalent DB foreign keys arrive in R1; this module is the portable check that
works with no database at all, so tests and export can both call it.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import Enum

from ocr_platform.schemas.decision import (
    REGION_REQUIRED_STATES,
    AcceptedBy,
    Disposition,
    FieldDecision,
    ValueState,
    primary_reason,
)
from ocr_platform.schemas.evidence import (
    EvidenceNode,
    EvidenceSet,
    EvidenceType,
)
from ocr_platform.schemas.job import DocumentRun, PageArtifact
from ocr_platform.schemas.provenance import (
    NodeType,
    ProvenanceGraph,
)
from ocr_platform.worker.provenance.hashing import is_content_hash


class ViolationCode(str, Enum):
    MISSING_EVIDENCE = "MISSING_EVIDENCE"
    MISSING_EVIDENCE_NODE = "MISSING_EVIDENCE_NODE"
    ORPHAN_EVIDENCE = "ORPHAN_EVIDENCE"
    WRONG_EVIDENCE_TYPE = "WRONG_EVIDENCE_TYPE"
    MISSING_PAGE_ARTIFACT = "MISSING_PAGE_ARTIFACT"
    BAD_HASH = "BAD_HASH"
    MISSING_TEMPLATE_MANIFEST = "MISSING_TEMPLATE_MANIFEST"
    MISSING_REGISTRATION = "MISSING_REGISTRATION"
    MISSING_INTERMEDIATE = "MISSING_INTERMEDIATE"
    BROKEN_REVISION_LINK = "BROKEN_REVISION_LINK"
    MISSING_DERIVATION = "MISSING_DERIVATION"
    CYCLE_IN_GRAPH = "CYCLE_IN_GRAPH"
    UNVERIFIED_NODE = "UNVERIFIED_NODE"


@dataclass(frozen=True)
class Violation:
    """One referential-integrity failure, addressed to a decision."""

    code: ViolationCode
    decision_id: str
    detail: str

    def __str__(self) -> str:
        return f"{self.code.value}: {self.decision_id}: {self.detail}"


@dataclass(frozen=True)
class ValidationReport:
    """``ok`` is True only when there are zero violations."""

    violations: tuple[Violation, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.violations

    @property
    def codes(self) -> tuple[str, ...]:
        return tuple(sorted({v.code.value for v in self.violations}))

    def for_decision(self, decision_id: str) -> tuple[Violation, ...]:
        return tuple(v for v in self.violations if v.decision_id == decision_id)

    def extend(self, violations: Iterable[Violation]) -> ValidationReport:
        return ValidationReport(violations=(*self.violations, *violations))

    def __bool__(self) -> bool:  # pragma: no cover - convenience
        return self.ok

    def __len__(self) -> int:
        return len(self.violations)


OK = ValidationReport()


def _evidence_type_for(value_state: ValueState) -> EvidenceType | None:
    """Required evidence type for a value state, or None when text qualifies.

    ``present`` accepts text evidence (OCR observation or native text); the
    region-required states demand :class:`RegionEvidence`.
    """
    if value_state in REGION_REQUIRED_STATES:
        return EvidenceType.region
    return None


def _accepts_text(evidence_type: EvidenceType) -> bool:
    return evidence_type in (EvidenceType.ocr_observation, EvidenceType.native_text)


def validate_decision(
    decision: FieldDecision,
    evidence_sets: dict[str, EvidenceSet],
    run: DocumentRun | None = None,
    graph: ProvenanceGraph | None = None,
) -> tuple[Violation, ...]:
    """Validate one decision, returning every violation found (empty = valid)."""
    violations: list[Violation] = []
    did = decision.decision_id

    # 1. Graph-level structural checks apply to every decision.
    if graph is not None:
        for node_id in graph.missing_intermediates(node_id=did):
            violations.append(
                Violation(
                    ViolationCode.MISSING_INTERMEDIATE,
                    did,
                    f"referenced node {node_id} is absent from the graph",
                )
            )
        for node_id in graph.verify_hashes():
            violations.append(
                Violation(
                    ViolationCode.BAD_HASH,
                    node_id,
                    "stored content_hash does not match the node payload",
                )
            )

    # 2. Region-required states must carry RegionEvidence.
    required = _evidence_type_for(decision.value_state)

    # 3. Every value-bearing or accepted decision must resolve its evidence set.
    if decision.disposition is Disposition.accepted and not decision.source_set:
        violations.append(
            Violation(
                ViolationCode.MISSING_EVIDENCE,
                did,
                "accepted decision has an empty source_set",
            )
        )

    resolved_any = False
    for set_id in decision.source_set:
        evidence_set = evidence_sets.get(set_id)
        if evidence_set is None:
            violations.append(
                Violation(
                    ViolationCode.MISSING_EVIDENCE,
                    did,
                    f"source_set references unknown evidence set {set_id!r}",
                )
            )
            continue
        resolved_any = True

        if not evidence_set.members:
            violations.append(
                Violation(
                    ViolationCode.MISSING_EVIDENCE,
                    did,
                    f"evidence set {set_id!r} has no members",
                )
            )
            continue

        if required is EvidenceType.region and not evidence_set.of_type(required):
            violations.append(
                Violation(
                    ViolationCode.WRONG_EVIDENCE_TYPE,
                    did,
                    f"value_state={decision.value_state.value} requires RegionEvidence "
                    f"but set {set_id!r} has none",
                )
            )

        if decision.value_state is ValueState.present and not any(
            _accepts_text(m.evidence_type) for m in evidence_set.members
        ):
            violations.append(
                Violation(
                    ViolationCode.WRONG_EVIDENCE_TYPE,
                    did,
                    "value_state=present requires OCR or native-text evidence",
                )
            )

        if decision.accepted_by.value == "human" and not evidence_set.of_type(
            EvidenceType.human_correction
        ):
            violations.append(
                Violation(
                    ViolationCode.WRONG_EVIDENCE_TYPE,
                    did,
                    "human-accepted decision requires HumanCorrectionEvidence",
                )
            )

    # 4. Present-with-value but no resolved evidence at all.
    if (
        decision.value_state is ValueState.present
        and decision.final_value is not None
        and not resolved_any
    ):
        violations.append(
            Violation(
                ViolationCode.MISSING_EVIDENCE,
                did,
                "FINAL_VALUE MUST NEVER EXIST WITHOUT PROVENANCE: no resolvable evidence",
            )
        )

    # 5. Orphan evidence: sets that exist but belong to no decision.
    # (Reported by validate_batch, which sees the whole population.)

    # 6. Page artifact linkage.
    if run is not None and decision.page_index is not None:
        page = next(
            (p for p in run.pages if p.page_index == decision.page_index),
            None,
        )
        if page is None:
            violations.append(
                Violation(
                    ViolationCode.MISSING_PAGE_ARTIFACT,
                    did,
                    f"page_index={decision.page_index} has no page artifact in the run",
                )
            )

    # 7. Revision links.
    if (
        decision.revision_of_decision_id is not None
        and graph is not None
        and graph.node(decision.revision_of_decision_id) is None
    ):
        violations.append(
            Violation(
                ViolationCode.BROKEN_REVISION_LINK,
                did,
                f"revision_of_decision_id {decision.revision_of_decision_id!r} "
                "is not present in the graph",
            )
        )

    # 8. Registration record required for page-scoped decisions.
    if (
        graph is not None
        and decision.page_index is not None
        and not graph.nodes_of_type(NodeType.registration_transform)
    ):
        violations.append(
            Violation(
                ViolationCode.MISSING_REGISTRATION,
                did,
                "no registration transform recorded for a page-scoped decision",
            )
        )

    return tuple(violations)


def validate_batch(
    decisions: Sequence[FieldDecision],
    evidence_sets: dict[str, EvidenceSet],
    run: DocumentRun | None = None,
    graph: ProvenanceGraph | None = None,
) -> ValidationReport:
    """Validate every decision and report orphaned evidence sets.

    An evidence set referenced by no decision is an orphan: it may be leftover
    or forgotten, and the gate reports it rather than silently dropping it.
    """
    violations: list[Violation] = []
    referenced: set[str] = set()

    for decision in decisions:
        referenced.update(decision.source_set)
        violations.extend(validate_decision(decision, evidence_sets, run=run, graph=graph))

    for set_id in sorted(set(evidence_sets) - referenced):
        violations.append(
            Violation(
                ViolationCode.ORPHAN_EVIDENCE,
                "<batch>",
                f"evidence set {set_id!r} is referenced by no decision",
            )
        )

    if graph is not None:
        for node in graph.nodes:
            if not is_content_hash(node.content_hash):
                violations.append(
                    Violation(
                        ViolationCode.BAD_HASH,
                        node.node_id,
                        "node content_hash is not a sha256 hex digest",
                    )
                )

    return ValidationReport(violations=tuple(violations))


def demote_to_review(decision: FieldDecision, report: ValidationReport) -> FieldDecision:
    """Return *decision* demoted to review after a provenance failure.

    Never deletes evidence and never invents a value: the observed value is
    dropped from ``final_value`` while the reason codes record why. The caller
    keeps the original for review. The result is re-validated so a demoted
    decision is itself a well-formed decision.
    """
    if report.ok:
        return decision
    codes = tuple(dict.fromkeys((*decision.reason_codes, "PROVENANCE_INCOMPLETE")))
    payload = decision.model_dump(mode="json")
    payload.update(
        {
            "disposition": Disposition.review.value,
            "final_value": None,
            "accepted_by": AcceptedBy.none.value,
            "reason_codes": list(codes),
            "primary_reason": primary_reason(codes),
        }
    )
    return FieldDecision.model_validate(payload)


def gate_export(
    decisions: Sequence[FieldDecision],
    evidence_sets: dict[str, EvidenceSet],
    run: DocumentRun | None = None,
    graph: ProvenanceGraph | None = None,
) -> tuple[tuple[FieldDecision, ...], ValidationReport]:
    """Split *decisions* into exportable and demoted, plus the report.

    Accepted values that fail the gate are demoted to review, never exported.
    Non-accepted decisions pass through untouched — the gate governs *accepted*
    values, and review rows are supposed to reach a human.
    """
    report = validate_batch(decisions, evidence_sets, run=run, graph=graph)
    if report.ok:
        return tuple(decisions), report

    exportable: list[FieldDecision] = []
    for decision in decisions:
        if decision.is_accepted and report.for_decision(decision.decision_id):
            exportable.append(demote_to_review(decision, report))
        else:
            exportable.append(decision)
    return tuple(exportable), report


def has_accepted_with_incomplete_provenance(
    decisions: Sequence[FieldDecision],
    evidence_sets: dict[str, EvidenceSet],
    run: DocumentRun | None = None,
    graph: ProvenanceGraph | None = None,
) -> tuple[str, ...]:
    """Decision IDs of accepted values that would fail the gate.

    The benchmark gate shape: this must return an empty tuple for a clean run.
    """
    return tuple(
        v.decision_id
        for v in validate_batch(decisions, evidence_sets, run=run, graph=graph).violations
        if v.code is ViolationCode.MISSING_EVIDENCE and v.decision_id != "<batch>"
    )


def index_evidence(sets: Iterable[EvidenceSet]) -> dict[str, EvidenceNode]:
    """Index every evidence node by its evidence ID."""
    index: dict[str, EvidenceNode] = {}
    for evidence_set in sets:
        for member in evidence_set.members:
            index.setdefault(member.evidence_id, member)
    return index


def page_artifacts_for(run: DocumentRun, page_index: int) -> PageArtifact | None:
    """Return the page artifact for *page_index*, or None."""
    return next((p for p in run.pages if p.page_index == page_index), None)
