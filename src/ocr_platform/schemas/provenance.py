"""Provenance graph node types and edges.

The provenance of a value is a **directed graph**, not a single source
rectangle::

    DocumentRun → PageArtifact → TemplateManifest → RegistrationTransform
               → CropArtifact → EvidenceSet → {evidence nodes} → DecisionRevision

Every node carries an immutable ID, a content hash, a version and a creation
time. Nodes are content-addressed from their payload, so the same semantic
content always produces the same ID and a tampered node fails verification.

Every run records the exact template manifest **hash**. A mutable template name
is never sufficient, because the same name can point at different geometry.
"""

from __future__ import annotations

from collections.abc import Iterable
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ocr_platform.worker.provenance.hashing import content_hash, is_content_hash

MAX_GRAPH_NODES = 100_000


class NodeType(str, Enum):
    document_run = "document_run"
    page_artifact = "page_artifact"
    template_manifest = "template_manifest"
    registration_transform = "registration_transform"
    crop_artifact = "crop_artifact"
    evidence_set = "evidence_set"
    decision_revision = "decision_revision"
    derivation = "derivation"


class EdgeRelation(str, Enum):
    renders = "renders"
    templates = "templates"
    registers = "registers"
    crops = "crops"
    evidences = "evidences"
    decides = "decides"
    revises = "revises"
    derives = "derives"


class ProvenanceNode(BaseModel):
    """Immutable, content-addressed envelope shared by all graph nodes."""

    model_config = ConfigDict(frozen=True)

    node_id: str
    content_hash: str
    node_type: NodeType
    version: str = "1"
    created_at: float = 0.0

    def payload(self) -> dict[str, Any]:
        """The semantic content this node's hash and ID are derived from."""
        return self.model_dump(mode="json", exclude={"node_id", "content_hash", "created_at"})

    def expected_ids(self) -> tuple[str, str]:
        """Recompute ``(node_id, content_hash)`` from the payload."""
        digest = content_hash({"node_type": self.node_type.value, **self.payload()})
        return f"{self.node_type.value}:{digest[:24]}", digest

    def verify(self) -> bool:
        """True when the stored ID and hash still match the payload."""
        node_id, digest = self.expected_ids()
        return self.node_id == node_id and self.content_hash == digest

    @classmethod
    def build(cls, **fields: Any) -> ProvenanceNode:
        """Construct a node with its content-addressed ID and hash filled in.

        The hash covers the payload only, so it can be computed before the ID
        exists; the ID then derives from the digest.
        """
        probe = cls(node_id="pending", content_hash="0" * 64, **fields)
        node_id, digest = probe.expected_ids()
        return probe.model_copy(update={"node_id": node_id, "content_hash": digest})

    @model_validator(mode="after")
    def _validate_envelope(self) -> ProvenanceNode:
        if not is_content_hash(self.content_hash):
            raise ValueError(
                f"{self.node_type.value} node requires a sha256 content_hash, "
                f"got {self.content_hash!r}"
            )
        if not self.node_id:
            raise ValueError("provenance nodes require a non-empty node_id")
        return self


class DocumentRunNode(ProvenanceNode):
    node_type: Literal[NodeType.document_run] = NodeType.document_run
    run_id: str
    document_content_hash: str
    configuration_fingerprint: str
    template_version: str
    page_count: int


class PageArtifactNode(ProvenanceNode):
    node_type: Literal[NodeType.page_artifact] = NodeType.page_artifact
    artifact_id: str
    page_index: int
    page_content_hash: str
    render_metadata_hash: str
    width_px: int
    height_px: int


class TemplateManifestNode(ProvenanceNode):
    """The hash-rooted template package: manifest hash plus child file hashes."""

    node_type: Literal[NodeType.template_manifest] = NodeType.template_manifest
    template_version: str
    manifest_hash: str
    child_hashes: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_manifest(self) -> TemplateManifestNode:
        if not is_content_hash(self.manifest_hash):
            raise ValueError(f"manifest_hash must be a sha256 digest, got {self.manifest_hash!r}")
        for name, digest in self.child_hashes.items():
            if not is_content_hash(digest):
                raise ValueError(f"child hash for {name!r} must be a sha256 digest, got {digest!r}")
        return self


class RegistrationTransformNode(ProvenanceNode):
    """The transform that placed the template on the page.

    R0 uses the canonical page-box normalize (identity fit to the unit box,
    ADR-002); R0.5 adds affine. ``residual`` is recorded so a high residual can
    force review rather than silently deskewing inside OCR.
    """

    node_type: Literal[NodeType.registration_transform] = NodeType.registration_transform
    transform_type: str
    residual: float
    params: dict[str, Any] = Field(default_factory=dict)
    template_manifest_hash: str

    @model_validator(mode="after")
    def _validate_registration(self) -> RegistrationTransformNode:
        if self.residual < 0.0:
            raise ValueError("registration residual cannot be negative")
        if not is_content_hash(self.template_manifest_hash):
            raise ValueError("template_manifest_hash must be a sha256 digest")
        return self


class CropArtifactNode(ProvenanceNode):
    node_type: Literal[NodeType.crop_artifact] = NodeType.crop_artifact
    crop_hash: str
    page_index: int
    region_id: str
    bbox: tuple[float, float, float, float]

    @model_validator(mode="after")
    def _validate_crop(self) -> CropArtifactNode:
        if not is_content_hash(self.crop_hash):
            raise ValueError(f"crop_hash must be a sha256 digest, got {self.crop_hash!r}")
        x0, y0, x1, y1 = self.bbox
        if x1 < x0 or y1 < y0:
            raise ValueError(f"degenerate crop bbox {self.bbox}")
        return self


class EvidenceSetNode(ProvenanceNode):
    node_type: Literal[NodeType.evidence_set] = NodeType.evidence_set
    set_id: str
    member_evidence_ids: tuple[str, ...] = ()
    member_content_hashes: tuple[str, ...] = ()


class DerivationNode(ProvenanceNode):
    """A derived or cross-field value, with the operation that produced it."""

    node_type: Literal[NodeType.derivation] = NodeType.derivation
    operation_id: str
    input_hashes: tuple[str, ...]
    output_hash: str
    rule_version: str
    template_version: str

    @model_validator(mode="after")
    def _validate_derivation(self) -> DerivationNode:
        if not self.input_hashes:
            raise ValueError("a derivation requires at least one input hash")
        if not all(is_content_hash(h) for h in self.input_hashes):
            raise ValueError("every derivation input must be a sha256 digest")
        if not is_content_hash(self.output_hash):
            raise ValueError("derivation output must be a sha256 digest")
        return self


class DecisionRevisionNode(ProvenanceNode):
    node_type: Literal[NodeType.decision_revision] = NodeType.decision_revision
    decision_id: str
    revision_index: int
    supersedes_node_id: str | None = None
    accepted_by: str = "none"
    evidence_set_node_id: str | None = None

    @model_validator(mode="after")
    def _validate_revision(self) -> DecisionRevisionNode:
        if self.revision_index < 0:
            raise ValueError("revision_index must be non-negative")
        if self.supersedes_node_id is not None and self.supersedes_node_id == self.node_id:
            raise ValueError("a revision cannot supersede itself")
        return self


AnyNode = (
    DocumentRunNode
    | PageArtifactNode
    | TemplateManifestNode
    | RegistrationTransformNode
    | CropArtifactNode
    | EvidenceSetNode
    | DerivationNode
    | DecisionRevisionNode
)

NODE_TYPES: dict[NodeType, type[ProvenanceNode]] = {
    NodeType.document_run: DocumentRunNode,
    NodeType.page_artifact: PageArtifactNode,
    NodeType.template_manifest: TemplateManifestNode,
    NodeType.registration_transform: RegistrationTransformNode,
    NodeType.crop_artifact: CropArtifactNode,
    NodeType.evidence_set: EvidenceSetNode,
    NodeType.derivation: DerivationNode,
    NodeType.decision_revision: DecisionRevisionNode,
}


class ProvenanceEdge(BaseModel):
    """A directed relation between two graph nodes."""

    model_config = ConfigDict(frozen=True)

    source_id: str
    target_id: str
    relation: EdgeRelation

    @model_validator(mode="after")
    def _validate(self) -> ProvenanceEdge:
        if self.source_id == self.target_id:
            raise ValueError("self-loops are not permitted in the provenance graph")
        return self


class ProvenanceGraph:
    """In-memory provenance graph with structural verification.

    Mutable *container* of immutable nodes: adding a node returns a new graph
    rather than editing a node in place, so no published graph can change under
    a reader.
    """

    def __init__(
        self,
        nodes: Iterable[AnyNode] = (),
        edges: Iterable[ProvenanceEdge] = (),
    ):
        self._nodes: dict[str, AnyNode] = {}
        self._edges: list[ProvenanceEdge] = []
        for node in nodes:
            self.add_node(node)
        for edge in edges:
            self.add_edge(edge)

    # -- construction ---------------------------------------------------

    def add_node(self, node: AnyNode) -> ProvenanceGraph:
        if node.node_id in self._nodes:
            raise ValueError(f"duplicate provenance node id {node.node_id}")
        if len(self._nodes) >= MAX_GRAPH_NODES:
            raise ValueError(f"provenance graph exceeds {MAX_GRAPH_NODES} nodes")
        self._nodes[node.node_id] = node
        return self

    def add_edge(self, edge: ProvenanceEdge) -> ProvenanceGraph:
        missing = [i for i in (edge.source_id, edge.target_id) if i not in self._nodes]
        if missing:
            raise ValueError(f"edge references unknown node(s): {missing}")
        self._edges.append(edge)
        if self._has_cycle():
            self._edges.pop()
            raise ValueError(f"edge {edge.source_id} -> {edge.target_id} would create a cycle")
        return self

    def with_node(self, node: AnyNode) -> ProvenanceGraph:
        """Return a new graph containing *node* (this graph is untouched)."""
        clone = ProvenanceGraph(self._nodes.values(), self._edges)
        clone.add_node(node)
        return clone

    def with_edge(self, edge: ProvenanceEdge) -> ProvenanceGraph:
        """Return a new graph containing *edge* (this graph is untouched)."""
        clone = ProvenanceGraph(self._nodes.values(), self._edges)
        clone.add_edge(edge)
        return clone

    # -- queries --------------------------------------------------------

    def __len__(self) -> int:
        return len(self._nodes)

    @property
    def nodes(self) -> tuple[AnyNode, ...]:
        return tuple(self._nodes.values())

    @property
    def edges(self) -> tuple[ProvenanceEdge, ...]:
        return tuple(self._edges)

    def node(self, node_id: str) -> AnyNode | None:
        return self._nodes.get(node_id)

    def nodes_of_type(self, node_type: NodeType) -> tuple[AnyNode, ...]:
        return tuple(n for n in self._nodes.values() if n.node_type is node_type)

    def outgoing(self, node_id: str) -> tuple[ProvenanceEdge, ...]:
        return tuple(e for e in self._edges if e.source_id == node_id)

    def incoming(self, node_id: str) -> tuple[ProvenanceEdge, ...]:
        return tuple(e for e in self._edges if e.target_id == node_id)

    def ancestors(self, node_id: str) -> set[str]:
        """Every node reachable backwards from *node_id*."""
        seen: set[str] = set()
        stack = [node_id]
        while stack:
            current = stack.pop()
            for edge in self.incoming(current):
                if edge.source_id not in seen:
                    seen.add(edge.source_id)
                    stack.append(edge.source_id)
        return seen

    def missing_intermediates(self, node_id: str) -> tuple[str, ...]:
        """Node IDs referenced by an ancestor path that are absent from the graph."""
        present = set(self._nodes)
        dangling: set[str] = set()
        for edge in self._edges:
            for endpoint in (edge.source_id, edge.target_id):
                if endpoint not in present:
                    dangling.add(endpoint)
        return tuple(sorted(dangling))

    def verify_hashes(self) -> tuple[str, ...]:
        """Node IDs whose stored hash no longer matches their payload."""
        return tuple(sorted(n.node_id for n in self._nodes.values() if not n.verify()))

    def _has_cycle(self) -> bool:
        WHITE, GREY, BLACK = 0, 1, 2
        colour = dict.fromkeys(self._nodes, WHITE)

        def visit(node_id: str) -> bool:
            colour[node_id] = GREY
            for edge in self.outgoing(node_id):
                state = colour.get(edge.target_id, WHITE)
                if state == GREY:
                    return True
                if state == WHITE and visit(edge.target_id):
                    return True
            colour[node_id] = BLACK
            return False

        return any(colour[n] == WHITE and visit(n) for n in list(self._nodes))


def node_ids(nodes: Iterable[ProvenanceNode]) -> tuple[str, ...]:
    """Sorted node IDs, for stable error messages and test assertions."""
    return tuple(sorted(node.node_id for node in nodes))
