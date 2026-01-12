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

import pytest
from pydantic import ValidationError

from coreason_scribe.models import (
    DeltaReport,
    DiffItem,
    DiffType,
    DraftArtifact,
    DraftSection,
    Requirement,
    RiskLevel,
    SignatureBlock,
)


def test_risk_level_enum() -> None:
    assert RiskLevel.HIGH == "HIGH"
    assert RiskLevel.MED == "MED"
    assert RiskLevel.LOW == "LOW"
    with pytest.raises(ValueError):
        RiskLevel("CRITICAL")


def test_requirement_valid() -> None:
    req = Requirement(
        id="REQ-001",
        description="Verify dose calculation",
        risk=RiskLevel.HIGH,
        source_sop="SOP-123",
    )
    assert req.id == "REQ-001"
    assert req.risk == RiskLevel.HIGH
    assert req.source_sop == "SOP-123"


def test_requirement_optional_sop() -> None:
    req = Requirement(
        id="REQ-002",
        description="Verify login page",
        risk=RiskLevel.LOW,
    )
    assert req.source_sop is None


def test_draft_section_valid() -> None:
    section = DraftSection(
        id="logic_summary",
        content="This function checks auth.",
        author="AI",
        is_modified=True,
        linked_code_hash="sha256:123456",
    )
    assert section.author == "AI"
    assert section.is_modified is True


def test_draft_section_invalid_author() -> None:
    with pytest.raises(ValidationError):
        DraftSection(
            id="test",
            content="content",
            author="ROBOT",  # type: ignore # Invalid
            is_modified=False,
            linked_code_hash="hash",
        )


def test_signature_block_valid() -> None:
    now = datetime.now(timezone.utc)
    sig = SignatureBlock(
        document_hash="hash_123",
        signer_id="user_001",
        signer_role="Quality_Manager",
        timestamp=now,
        meaning="I certify this.",
        signature_token="token_abc",
    )
    assert sig.signer_id == "user_001"
    assert sig.timestamp == now


def test_signature_block_invalid_types() -> None:
    with pytest.raises(ValidationError):
        SignatureBlock(
            document_hash=123,  # type: ignore # Should be string
            signer_id="u1",
            signer_role="role",
            timestamp="not-a-datetime",  # type: ignore # Should be datetime
            meaning="meaning",
            signature_token="token",
        )


def test_draft_artifact_valid() -> None:
    now = datetime.now(timezone.utc)
    section = DraftSection(id="s1", content="c", author="AI", is_modified=False, linked_code_hash="h")
    artifact = DraftArtifact(version="1.0", timestamp=now, sections=[section])
    assert artifact.version == "1.0"
    assert len(artifact.sections) == 1


def test_diff_type_enum() -> None:
    assert DiffType.NEW == "NEW"
    assert DiffType.REMOVED == "REMOVED"
    assert DiffType.LOGIC_CHANGE == "LOGIC_CHANGE"
    assert DiffType.TEXT_CHANGE == "TEXT_CHANGE"
    assert DiffType.BOTH == "BOTH"


def test_diff_item_valid() -> None:
    section = DraftSection(id="s1", content="c", author="AI", is_modified=False, linked_code_hash="h")
    item = DiffItem(
        section_id="s1",
        diff_type=DiffType.NEW,
        current_section=section,
        previous_section=None,
    )
    assert item.diff_type == DiffType.NEW
    assert item.current_section == section
    assert item.previous_section is None


def test_delta_report_valid() -> None:
    now = datetime.now(timezone.utc)
    report = DeltaReport(current_version="1.1", previous_version="1.0", timestamp=now, changes=[])
    assert report.current_version == "1.1"
    assert len(report.changes) == 0
