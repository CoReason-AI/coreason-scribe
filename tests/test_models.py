# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_scribe

from datetime import datetime

import pytest
from pydantic import ValidationError

from coreason_scribe.models import DraftSection, Requirement, RiskLevel, SignatureBlock


def test_risk_level_enum() -> None:
    assert RiskLevel.HIGH == "HIGH"
    assert RiskLevel.MED == "MED"
    assert RiskLevel.LOW == "LOW"


def test_requirement_creation() -> None:
    req = Requirement(id="REQ-001", description="Test requirement", risk=RiskLevel.HIGH, source_sop="SOP-001")
    assert req.id == "REQ-001"
    assert req.description == "Test requirement"
    assert req.risk == RiskLevel.HIGH
    assert req.source_sop == "SOP-001"


def test_requirement_creation_defaults() -> None:
    req = Requirement(id="REQ-002", description="Test requirement 2", risk=RiskLevel.LOW)
    assert req.id == "REQ-002"
    assert req.source_sop is None


def test_requirement_invalid_risk() -> None:
    with pytest.raises(ValidationError):
        Requirement(
            id="REQ-003",
            description="Invalid risk",
            risk="EXTREME",  # type: ignore
        )


def test_draft_section_creation() -> None:
    section = DraftSection(
        id="sec-1", content="Some content", author="AI", is_modified=True, linked_code_hash="abc123hash"
    )
    assert section.id == "sec-1"
    assert section.author == "AI"
    assert section.is_modified is True


def test_draft_section_invalid_author() -> None:
    with pytest.raises(ValidationError):
        DraftSection(
            id="sec-2",
            content="Content",
            author="ROBOT",  # type: ignore
            is_modified=False,
            linked_code_hash="hash",
        )


def test_signature_block_creation() -> None:
    now = datetime.now()
    sig = SignatureBlock(
        document_hash="doc_hash",
        signer_id="user_123",
        signer_role="Quality Manager",
        timestamp=now,
        meaning="Approval",
        signature_token="token_xyz",
    )
    assert sig.document_hash == "doc_hash"
    assert sig.signer_id == "user_123"
    assert sig.timestamp == now


def test_signature_block_missing_field() -> None:
    with pytest.raises(ValidationError):
        SignatureBlock(  # type: ignore[call-arg]
            document_hash="doc_hash",
            signer_id="user_123",
            # Missing signer_role
            timestamp=datetime.now(),
            meaning="Approval",
            signature_token="token_xyz",
        )


def test_model_serialization_round_trip() -> None:
    req = Requirement(id="REQ-SERIAL", description="Serialization Test", risk=RiskLevel.MED, source_sop="SOP-JSON")
    json_str = req.model_dump_json()
    req_loaded = Requirement.model_validate_json(json_str)
    assert req_loaded == req


def test_empty_string_fields() -> None:
    # It is technically valid for these strings to be empty unless constrained
    req = Requirement(id="", description="", risk=RiskLevel.LOW)
    assert req.id == ""
    assert req.description == ""

    section = DraftSection(id="", content="", author="HUMAN", is_modified=False, linked_code_hash="")
    assert section.content == ""


def test_explicit_none_optional() -> None:
    req = Requirement(id="REQ-NONE", description="None test", risk=RiskLevel.MED, source_sop=None)
    assert req.source_sop is None


def test_large_content() -> None:
    large_text = "A" * 1000000  # 1MB string
    section = DraftSection(id="sec-large", content=large_text, author="AI", is_modified=False, linked_code_hash="hash")
    assert len(section.content) == 1000000
    assert section.content.startswith("AAAA")
