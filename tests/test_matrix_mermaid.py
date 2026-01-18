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
    AssayStatus,
    DraftArtifact,
    DraftSection,
    Requirement,
    RiskLevel,
)


def test_generate_mermaid_complex_graph() -> None:
    """
    Verifies that the Mermaid.js diagram is generated correctly for a complex scenario
    involving Code, Requirements, and Tests with various states.
    """
    builder = TraceabilityMatrixBuilder()

    # 1. Define Requirements
    reqs = [
        Requirement(id="REQ-001", description="Safety Critical Logic", risk=RiskLevel.HIGH),
        Requirement(id="REQ-002", description="Business Rule", risk=RiskLevel.MED),
        Requirement(id="REQ-003", description="UI Formatting", risk=RiskLevel.LOW),
        Requirement(id="REQ-004", description="Unimplemented Req", risk=RiskLevel.HIGH),
    ]

    # 2. Define Assay Report (Test Results)
    report = AssayReport(
        id="REPORT-2023-X",
        timestamp=datetime.now(timezone.utc),
        results=[
            # REQ-001: High Risk, 100% Coverage -> PASS
            AssayResult(
                test_id="test_safety_logic",
                status=AssayStatus.PASS,
                coverage=100.0,
                linked_requirements=["REQ-001"],
                timestamp=datetime.now(timezone.utc),
            ),
            # REQ-002: Med Risk, 80% Coverage -> WARNING
            AssayResult(
                test_id="test_business_rule_partial",
                status=AssayStatus.PASS,
                coverage=80.0,
                linked_requirements=["REQ-002"],
                timestamp=datetime.now(timezone.utc),
            ),
            # REQ-003: Low Risk, 0% Coverage (Fail) -> WARNING
            # (fail doesn't mean 0 coverage necessarily, but let's say 0 here)
            AssayResult(
                test_id="test_ui_broken",
                status=AssayStatus.FAIL,
                coverage=0.0,
                linked_requirements=["REQ-003"],
                timestamp=datetime.now(timezone.utc),
            ),
            # REQ-004: No tests linked -> Will be Critical Gap
        ],
    )

    # 3. Define Draft Artifact (Code Structure)
    draft = DraftArtifact(
        version="1.0.0",
        timestamp=datetime.now(timezone.utc),
        sections=[
            DraftSection(
                id="module.safety",
                content="Safety code",
                author="HUMAN",
                is_modified=False,
                linked_requirements=["REQ-001"],
                linked_code_hash="abc",
            ),
            DraftSection(
                id="module.business",
                content="Business code",
                author="AI",
                is_modified=True,
                linked_requirements=["REQ-002", "REQ-003"],
                linked_code_hash="def",
            ),
            DraftSection(
                id='module."quoted"',  # Test escaping
                content="Edge case",
                author="AI",
                is_modified=False,
                linked_requirements=["REQ-004"],
                linked_code_hash="ghi",
            ),
        ],
    )

    # Generate Diagram
    diagram = builder.generate_mermaid_diagram(reqs, report, draft)

    # Verify Output Structure
    assert "graph TD" in diagram

    # Verify Classes
    assert "classDef pass" in diagram
    assert "classDef warning" in diagram
    assert "classDef criticalGap" in diagram
    assert "classDef fail" in diagram

    # Verify Code Nodes & Edges
    # Use generic regex or substring checks because IDs are auto-generated (node_1, node_2...)
    # But labels should be present.
    assert '["module.safety"]:::code' in diagram
    assert '["module.business"]:::code' in diagram
    # Escaping check
    assert "[\"module.'quoted'\"]:::code" in diagram

    # Verify Requirement Nodes & Styles
    # REQ-001 -> PASS (High Risk, 100% Cov)
    assert '["REQ-001<br/>HIGH"]:::pass' in diagram
    # REQ-002 -> WARNING (Med Risk, 80% Cov)
    assert '["REQ-002<br/>MED"]:::warning' in diagram
    # REQ-003 -> WARNING (Low Risk, 0% Cov)
    assert '["REQ-003<br/>LOW"]:::warning' in diagram
    # REQ-004 -> CRITICAL GAP (High Risk, 0% Cov / No tests)
    assert '["REQ-004<br/>HIGH"]:::criticalGap' in diagram

    # Verify Test Nodes & Styles
    assert '["test_safety_logic<br/>PASS"]:::pass' in diagram
    assert '["test_ui_broken<br/>FAIL"]:::fail' in diagram

    # Verify Linkage (Logic Check)
    # Since we don't know the exact node IDs, we can't easily assert "node_1 --> node_2".
    # But we can check that we have enough arrows.
    # Code->Req links: 4 (Safety->Req1, Biz->Req2, Biz->Req3, Quoted->Req4)
    # Req->Test links: 3 (Req1->TestSafety, Req2->TestBiz, Req3->TestUI)
    arrow_count = diagram.count("-->")
    assert arrow_count == 7
