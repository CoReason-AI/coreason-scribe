# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_scribe

from datetime import datetime, timezone

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


def test_mermaid_empty_inputs() -> None:
    """
    Verifies that empty inputs produce a valid minimal graph.
    """
    builder = TraceabilityMatrixBuilder()
    reqs: list[Requirement] = []
    report = AssayReport(
        id="EMPTY",
        timestamp=datetime.now(timezone.utc),
        results=[],
    )
    draft = DraftArtifact(
        version="0.0.0",
        timestamp=datetime.now(timezone.utc),
        sections=[],
    )

    diagram = builder.generate_mermaid_diagram(reqs, report, draft)

    # Should contain header and style defs, but no nodes
    assert "graph TD" in diagram
    assert "classDef pass" in diagram
    assert "-->" not in diagram


def test_mermaid_special_characters() -> None:
    """
    Verifies handling of special characters in IDs and labels.
    """
    builder = TraceabilityMatrixBuilder()

    # IDs with confusing characters for Mermaid
    reqs = [
        Requirement(id="REQ(A):1", description="Complex ID", risk=RiskLevel.HIGH),
        Requirement(id="REQ[B]", description="Brackets", risk=RiskLevel.LOW),
        Requirement(id="REQ 🚀", description="Emoji", risk=RiskLevel.MED),
    ]

    report = AssayReport(
        id="R1",
        timestamp=datetime.now(timezone.utc),
        results=[
            AssayResult(
                test_id="test:subtest(1)",
                status=TestStatus.PASS,
                coverage=100.0,
                linked_requirements=["REQ(A):1"],
                timestamp=datetime.now(timezone.utc),
            )
        ],
    )

    draft = DraftArtifact(
        version="1.0",
        timestamp=datetime.now(timezone.utc),
        sections=[
            DraftSection(
                id="func<int>",
                content="...",
                author="HUMAN",
                is_modified=False,
                linked_requirements=["REQ 🚀"],
                linked_code_hash="123",
            )
        ],
    )

    diagram = builder.generate_mermaid_diagram(reqs, report, draft)

    # Check that labels appear (partially escaped or raw if safe)
    # The current implementation replaces " with ' but doesn't do aggressive escaping.
    # Mermaid handles many chars inside ["..."] quotes, but we should verify.

    assert '["REQ(A):1<br/>HIGH"]' in diagram
    assert '["REQ[B]<br/>LOW"]' in diagram
    assert '["REQ 🚀<br/>MED"]' in diagram
    assert '["func<int>"]' in diagram
    assert '["test:subtest(1)<br/>PASS"]' in diagram

    # Ensure connections exist despite weird IDs
    # We can't easily regex the node IDs (node_1, node_2), but we know there should be edges.
    assert diagram.count("-->") == 2  # func->REQ_emoji, REQ_A->test


def test_mermaid_disconnected_and_orphaned_nodes() -> None:
    """
    Verifies that disconnected nodes are rendered and orphans are handled.
    """
    builder = TraceabilityMatrixBuilder()

    reqs = [
        Requirement(id="REQ-ISOLATED", description="No code, no tests", risk=RiskLevel.MED),
        Requirement(id="REQ-TESTED", description="Has tests", risk=RiskLevel.HIGH),
    ]

    report = AssayReport(
        id="R1",
        timestamp=datetime.now(timezone.utc),
        results=[
            AssayResult(
                test_id="test_orphan",
                status=TestStatus.PASS,
                coverage=100.0,
                linked_requirements=["REQ-NONEXISTENT"],  # Linked to unknown req
                timestamp=datetime.now(timezone.utc),
            ),
            AssayResult(
                test_id="test_linked",
                status=TestStatus.PASS,
                coverage=100.0,
                linked_requirements=["REQ-TESTED"],
                timestamp=datetime.now(timezone.utc),
            ),
        ],
    )

    draft = DraftArtifact(
        version="1.0",
        timestamp=datetime.now(timezone.utc),
        sections=[
            DraftSection(
                id="code_orphan",  # No requirements
                content="...",
                author="AI",
                is_modified=False,
                linked_requirements=[],
                linked_code_hash="111",
            )
        ],
    )

    diagram = builder.generate_mermaid_diagram(reqs, report, draft)

    # Isolated Requirement should be present
    assert '["REQ-ISOLATED<br/>MED"]' in diagram
    # It should be a WARNING because coverage is 0 (implicit)
    assert '["REQ-ISOLATED<br/>MED"]:::warning' in diagram

    # Code orphan should be present
    assert '["code_orphan"]:::code' in diagram

    # Test orphan (test_orphan) should be present
    assert '["test_orphan<br/>PASS"]' in diagram

    # The link from test_orphan to REQ-NONEXISTENT should NOT exist
    # because REQ-NONEXISTENT is not in the reqs list, so no node is created for it.
    # The builder iterates `reqs` to create req nodes and then looks up tests for them.
    # So `test_orphan` will be a loose node.

    # Verify edges
    # Only REQ-TESTED -> test_linked should exist
    assert diagram.count("-->") == 1


def test_mermaid_many_to_many() -> None:
    """
    Verifies dense graph generation (Code M:N Req, Req M:N Test).
    """
    builder = TraceabilityMatrixBuilder()

    reqs = [
        Requirement(id="R1", description="...", risk=RiskLevel.LOW),
        Requirement(id="R2", description="...", risk=RiskLevel.LOW),
    ]

    # One test verifies both requirements
    report = AssayReport(
        id="R",
        timestamp=datetime.now(timezone.utc),
        results=[
            AssayResult(
                test_id="T1",
                status=TestStatus.PASS,
                coverage=100.0,
                linked_requirements=["R1", "R2"],
                timestamp=datetime.now(timezone.utc),
            )
        ],
    )

    # One code section implements both requirements
    draft = DraftArtifact(
        version="1",
        timestamp=datetime.now(timezone.utc),
        sections=[
            DraftSection(
                id="C1",
                content="...",
                author="HUMAN",
                is_modified=False,
                linked_requirements=["R1", "R2"],
                linked_code_hash="h",
            )
        ],
    )

    diagram = builder.generate_mermaid_diagram(reqs, report, draft)

    # Edges expected:
    # C1 -> R1
    # C1 -> R2
    # R1 -> T1
    # R2 -> T1
    assert diagram.count("-->") == 4
