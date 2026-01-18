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
def sample_requirements() -> List[Requirement]:
    return [
        Requirement(id="REQ-001", description="High Risk Req", risk=RiskLevel.HIGH),
        Requirement(id="REQ-002", description="Low Risk Req", risk=RiskLevel.LOW),
        Requirement(id="REQ-003", description="Covered High Risk", risk=RiskLevel.HIGH),
    ]


@pytest.fixture
def sample_assay_report() -> AssayReport:
    return AssayReport(
        id="RPT-001",
        timestamp=datetime.now(timezone.utc),
        results=[
            AssayResult(
                test_id="TEST-001",
                status=AssayStatus.FAIL,
                coverage=50.0,
                linked_requirements=["REQ-001"],
                timestamp=datetime.now(timezone.utc),
            ),
            AssayResult(
                test_id="TEST-002",
                status=AssayStatus.PASS,
                coverage=80.0,
                linked_requirements=["REQ-002"],
                timestamp=datetime.now(timezone.utc),
            ),
            AssayResult(
                test_id="TEST-003",
                status=AssayStatus.PASS,
                coverage=100.0,
                linked_requirements=["REQ-003"],
                timestamp=datetime.now(timezone.utc),
            ),
        ],
    )


@pytest.fixture
def sample_draft_artifact() -> DraftArtifact:
    return DraftArtifact(
        version="1.0.0",
        timestamp=datetime.now(timezone.utc),
        sections=[
            DraftSection(
                id="module.func_a",
                content="Function A",
                author="AI",
                is_modified=False,
                linked_requirements=["REQ-001"],
                linked_code_hash="hash1",
            ),
            DraftSection(
                id="module.func_b",
                content="Function B",
                author="HUMAN",
                is_modified=True,
                linked_requirements=["REQ-002", "REQ-003"],
                linked_code_hash="hash2",
            ),
        ],
    )


def test_generate_mermaid_diagram_structure(
    sample_requirements: List[Requirement],
    sample_assay_report: AssayReport,
    sample_draft_artifact: DraftArtifact,
) -> None:
    builder = TraceabilityMatrixBuilder()
    diagram = builder.generate_mermaid_diagram(sample_requirements, sample_assay_report, sample_draft_artifact)

    nodes, edges, styles = parse_mermaid(diagram)

    # Find IDs
    req1_id = find_node_id_by_label_content(nodes, "REQ-001")
    test1_id = find_node_id_by_label_content(nodes, "TEST-001")
    code_id = find_node_id_by_label_content(nodes, "module.func_a")

    assert req1_id is not None
    assert test1_id is not None
    assert code_id is not None

    # Verify Edges
    assert (code_id, req1_id) in edges
    assert (req1_id, test1_id) in edges


def test_generate_mermaid_diagram_styles(
    sample_requirements: List[Requirement],
    sample_assay_report: AssayReport,
    sample_draft_artifact: DraftArtifact,
) -> None:
    builder = TraceabilityMatrixBuilder()
    diagram = builder.generate_mermaid_diagram(sample_requirements, sample_assay_report, sample_draft_artifact)

    nodes, edges, styles = parse_mermaid(diagram)

    # Find IDs
    req1 = find_node_id_by_label_content(nodes, "REQ-001")
    req2 = find_node_id_by_label_content(nodes, "REQ-002")
    req3 = find_node_id_by_label_content(nodes, "REQ-003")

    test1 = find_node_id_by_label_content(nodes, "TEST-001")
    test3 = find_node_id_by_label_content(nodes, "TEST-003")

    # Assert not None to satisfy mypy
    assert req1 and req2 and req3 and test1 and test3

    # Verify Styles
    # REQ-001: High Risk, 50% Cov -> CRITICAL_GAP (Red)
    assert styles[req1] == "criticalGap"
    # REQ-002: Low Risk, 80% Cov -> WARNING (Orange)
    assert styles[req2] == "warning"
    # REQ-003: High Risk, 100% Cov -> PASS (Green)
    assert styles[req3] == "pass"

    # Test Styles
    assert styles[test1] == "fail"
    assert styles[test3] == "pass"


def test_generate_mermaid_diagram_orphans(
    sample_requirements: List[Requirement],
    sample_assay_report: AssayReport,
    sample_draft_artifact: DraftArtifact,
) -> None:
    # Add an orphan requirement (no code, no test)
    orphan_req = Requirement(id="REQ-ORPHAN", description="Orphan", risk=RiskLevel.HIGH)
    sample_requirements.append(orphan_req)

    builder = TraceabilityMatrixBuilder()
    diagram = builder.generate_mermaid_diagram(sample_requirements, sample_assay_report, sample_draft_artifact)

    nodes, edges, styles = parse_mermaid(diagram)

    req_orphan = find_node_id_by_label_content(nodes, "REQ-ORPHAN")
    assert req_orphan is not None
    assert styles[req_orphan] == "criticalGap"
