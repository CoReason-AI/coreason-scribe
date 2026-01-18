import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import pytest

from coreason_scribe.matrix import TraceabilityMatrixBuilder
from coreason_scribe.models import (
    AssayReport,
    AssayResult,
    AssayStatus,
    DraftArtifact,
    DraftSection,
    Requirement,
    RiskLevel,
)


def parse_mermaid(diagram: str) -> Tuple[Dict[str, str], List[Tuple[str, str]], Dict[str, str]]:
    """
    Parses a Mermaid graph to extract:
    - Nodes: {node_id: label}
    - Edges: [(src_id, dst_id)]
    - Styles: {node_id: style_class}
    """
    nodes = {}
    edges = []
    styles = {}

    # Regex for node definition: node_id["label"]:::style
    # Note: label might contain <br/> or spaces
    node_pattern = re.compile(r'(\w+)\["([^"]+)"\](?::{3}(\w+))?')
    edge_pattern = re.compile(r"(\w+) --> (\w+)")

    for line in diagram.split("\n"):
        line = line.strip()
        if not line:
            continue

        # Check node def
        m_node = node_pattern.match(line)
        if m_node:
            nid, label, style = m_node.groups()
            nodes[nid] = label
            if style:
                styles[nid] = style
            continue

        # Check edge
        m_edge = edge_pattern.match(line)
        if m_edge:
            src, dst = m_edge.groups()
            edges.append((src, dst))

    return nodes, edges, styles


def find_node_id_by_label_content(nodes: Dict[str, str], content_snippet: str) -> Optional[str]:
    for nid, label in nodes.items():
        if content_snippet in label:
            return nid
    return None


@pytest.fixture
def empty_assay_report() -> AssayReport:
    return AssayReport(
        id="RPT-EMPTY",
        timestamp=datetime.now(timezone.utc),
        results=[],
    )


@pytest.fixture
def empty_draft_artifact() -> DraftArtifact:
    return DraftArtifact(
        version="0.0.0",
        timestamp=datetime.now(timezone.utc),
        sections=[],
    )


def test_mermaid_empty_inputs(
    empty_assay_report: AssayReport,
    empty_draft_artifact: DraftArtifact,
) -> None:
    builder = TraceabilityMatrixBuilder()
    diagram = builder.generate_mermaid_diagram([], empty_assay_report, empty_draft_artifact)

    assert "graph TD" in diagram
    nodes, edges, styles = parse_mermaid(diagram)
    assert len(nodes) == 0
    assert len(edges) == 0


def test_mermaid_special_characters_and_escaping(
    empty_assay_report: AssayReport,
    empty_draft_artifact: DraftArtifact,
) -> None:
    reqs = [
        Requirement(id="REQ 001", description="Space ID", risk=RiskLevel.LOW),
    ]

    draft = DraftArtifact(
        version="1.0",
        timestamp=datetime.now(timezone.utc),
        sections=[
            DraftSection(
                id="func name with space",
                content="...",
                author="AI",
                is_modified=False,
                linked_requirements=["REQ 001"],
                linked_code_hash="abc",
            )
        ],
    )

    report = AssayReport(
        id="RPT",
        timestamp=datetime.now(timezone.utc),
        results=[
            AssayResult(
                test_id="Test Name With Space",
                status=AssayStatus.PASS,
                coverage=100.0,
                linked_requirements=["REQ 001"],
                timestamp=datetime.now(timezone.utc),
            )
        ],
    )

    builder = TraceabilityMatrixBuilder()
    diagram = builder.generate_mermaid_diagram(reqs, report, draft)

    nodes, edges, styles = parse_mermaid(diagram)

    # We expect labels to contain spaces
    req_nid = find_node_id_by_label_content(nodes, "REQ 001")
    code_nid = find_node_id_by_label_content(nodes, "func name with space")
    test_nid = find_node_id_by_label_content(nodes, "Test Name With Space")

    assert req_nid is not None
    assert code_nid is not None
    assert test_nid is not None

    # Verify links
    assert (code_nid, req_nid) in edges
    assert (req_nid, test_nid) in edges


def test_mermaid_unicode(
    empty_assay_report: AssayReport,
    empty_draft_artifact: DraftArtifact,
) -> None:
    reqs = [
        Requirement(id="REQ-µ", description="Micro Service", risk=RiskLevel.MED),
    ]

    builder = TraceabilityMatrixBuilder()
    diagram = builder.generate_mermaid_diagram(reqs, empty_assay_report, empty_draft_artifact)

    nodes, edges, styles = parse_mermaid(diagram)
    req_nid = find_node_id_by_label_content(nodes, "REQ-µ")
    assert req_nid is not None


def test_mermaid_complex_many_to_many() -> None:
    reqs = [
        Requirement(id="REQ-A", description="A", risk=RiskLevel.HIGH),
        Requirement(id="REQ-B", description="B", risk=RiskLevel.HIGH),
    ]

    draft = DraftArtifact(
        version="1.0",
        timestamp=datetime.now(timezone.utc),
        sections=[
            DraftSection(
                id="main.func",
                content="...",
                author="AI",
                is_modified=False,
                linked_requirements=["REQ-A", "REQ-B"],
                linked_code_hash="h",
            ),
        ],
    )

    report = AssayReport(
        id="RPT",
        timestamp=datetime.now(timezone.utc),
        results=[
            AssayResult(
                test_id="T1",
                status=AssayStatus.PASS,
                coverage=100,
                linked_requirements=["REQ-A"],
                timestamp=datetime.now(timezone.utc),
            ),
            AssayResult(
                test_id="T2",
                status=AssayStatus.PASS,
                coverage=100,
                linked_requirements=["REQ-A"],
                timestamp=datetime.now(timezone.utc),
            ),
            AssayResult(
                test_id="T3",
                status=AssayStatus.PASS,
                coverage=100,
                linked_requirements=["REQ-B"],
                timestamp=datetime.now(timezone.utc),
            ),
        ],
    )

    builder = TraceabilityMatrixBuilder()
    diagram = builder.generate_mermaid_diagram(reqs, report, draft)

    nodes, edges, styles = parse_mermaid(diagram)

    code = find_node_id_by_label_content(nodes, "main.func")
    req_a = find_node_id_by_label_content(nodes, "REQ-A")
    req_b = find_node_id_by_label_content(nodes, "REQ-B")
    t1 = find_node_id_by_label_content(nodes, "T1")
    t2 = find_node_id_by_label_content(nodes, "T2")
    t3 = find_node_id_by_label_content(nodes, "T3")

    assert code and req_a and req_b and t1 and t2 and t3

    assert (code, req_a) in edges
    assert (code, req_b) in edges
    assert (req_a, t1) in edges
    assert (req_a, t2) in edges
    assert (req_b, t3) in edges
