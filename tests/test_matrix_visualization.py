from datetime import datetime, timezone
from typing import List

import pytest

from coreason_scribe.matrix import TraceabilityMatrixBuilder
from coreason_scribe.models import (
    AssayReport,
    AssayResult,
    DraftArtifact,
    DraftSection,
    Requirement,
    RiskLevel,
    TestStatus,
)


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
                status=TestStatus.FAIL,
                coverage=50.0,
                linked_requirements=["REQ-001"],
                timestamp=datetime.now(timezone.utc),
            ),
            AssayResult(
                test_id="TEST-002",
                status=TestStatus.PASS,
                coverage=80.0,
                linked_requirements=["REQ-002"],
                timestamp=datetime.now(timezone.utc),
            ),
            AssayResult(
                test_id="TEST-003",
                status=TestStatus.PASS,
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

    # This method doesn't exist yet, so this test expects to define the contract
    diagram = builder.generate_mermaid_diagram(sample_requirements, sample_assay_report, sample_draft_artifact)

    # Basic Structure Checks
    assert "graph LR" in diagram or "graph TD" in diagram
    assert "classDef" in diagram

    # Check Nodes
    # REQ-001 is High Risk, 50% Coverage (Max from TEST-001) -> Critical Gap
    assert "REQ-001" in diagram
    assert "TEST-001" in diagram
    assert "module.func_a" in diagram

    # Check Edges
    assert "module.func_a --> REQ-001" in diagram
    assert "REQ-001 --> TEST-001" in diagram


def test_generate_mermaid_diagram_styles(
    sample_requirements: List[Requirement],
    sample_assay_report: AssayReport,
    sample_draft_artifact: DraftArtifact,
) -> None:
    builder = TraceabilityMatrixBuilder()
    diagram = builder.generate_mermaid_diagram(sample_requirements, sample_assay_report, sample_draft_artifact)

    # Styles
    # REQ-001: High Risk, 50% Cov -> CRITICAL_GAP (Red)
    # REQ-002: Low Risk, 80% Cov -> WARNING (Orange)
    # REQ-003: High Risk, 100% Cov -> PASS (Green)

    # We expect class assignments like `REQ-001["REQ-001<br/>HIGH"]:::criticalGap`
    # We check if the style is applied to the node definition
    assert 'REQ-001["REQ-001<br/>HIGH"]:::criticalGap' in diagram
    assert 'REQ-002["REQ-002<br/>LOW"]:::warning' in diagram
    assert 'REQ-003["REQ-003<br/>HIGH"]:::pass' in diagram

    # Tests
    # TEST-001: FAIL -> fail
    # TEST-003: PASS -> pass
    # TEST-001["TEST-001<br/>FAIL"]:::fail
    assert 'TEST-001["TEST-001<br/>FAIL"]:::fail' in diagram
    assert 'TEST-003["TEST-003<br/>PASS"]:::pass' in diagram


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

    assert "REQ-ORPHAN" in diagram
    # It has 0 coverage -> High Risk -> Critical Gap
    assert 'REQ-ORPHAN["REQ-ORPHAN<br/>HIGH"]:::criticalGap' in diagram
