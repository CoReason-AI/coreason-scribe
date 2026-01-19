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
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from coreason_scribe.models import DocumentState, DraftArtifact, DraftSection, SignatureBlock
from coreason_scribe.pdf import PDFGenerator


@pytest.fixture
def sample_artifact() -> DraftArtifact:
    return DraftArtifact(
        version="1.0.0-rc1",
        timestamp=datetime.now(timezone.utc),
        sections=[
            DraftSection(
                id="module.auth",
                content="Authentication module handles login.",
                author="AI",
                is_modified=False,
                linked_code_hash="hash1",
            ),
            DraftSection(
                id="module.db",
                content="Database connection pool.",
                author="HUMAN",
                is_modified=True,
                linked_code_hash="hash2",
            ),
        ],
    )


def test_zombie_signed_state(tmp_path: Path, sample_artifact: DraftArtifact, mock_html_class: MagicMock) -> None:
    """
    Edge Case: Status is SIGNED but signature block is missing (e.g. data corruption).
    Expectation: No watermark (status is SIGNED) and NO signature page (no data to render).
    This ensures graceful handling of invalid states rather than crashing.
    """
    sample_artifact.status = DocumentState.SIGNED
    sample_artifact.signature = None
    output_path = tmp_path / "zombie.pdf"

    PDFGenerator().generate_sds(sample_artifact, output_path)

    call_args = mock_html_class.call_args
    html_content = call_args.kwargs.get("string", "")

    assert '<div class="watermark">DRAFT</div>' not in html_content
    assert '<div class="signature-page">' not in html_content


def test_mixed_state_draft_with_signature(
    tmp_path: Path, sample_artifact: DraftArtifact, mock_html_class: MagicMock
) -> None:
    """
    Edge Case: Status is DRAFT but a signature block is present (e.g. signature revoked or state reverted).
    Expectation: Watermark present (status is DRAFT) AND Signature Page present (data exists).
    This confirms the logic conditions are independent.
    """
    sample_artifact.status = DocumentState.DRAFT
    sample_artifact.signature = SignatureBlock(
        document_hash="hash",
        signer_id="user",
        signer_role="role",
        timestamp=datetime.now(timezone.utc),
        meaning="intent",
        signature_token="token",
    )
    output_path = tmp_path / "mixed.pdf"

    PDFGenerator().generate_sds(sample_artifact, output_path)

    call_args = mock_html_class.call_args
    html_content = call_args.kwargs.get("string", "")

    assert '<div class="watermark">DRAFT</div>' in html_content
    assert '<div class="signature-page">' in html_content


def test_signature_html_injection(tmp_path: Path, sample_artifact: DraftArtifact, mock_html_class: MagicMock) -> None:
    """
    Security Test: Verify that signature fields containing HTML are escaped.
    """
    sample_artifact.status = DocumentState.SIGNED
    sample_artifact.signature = SignatureBlock(
        document_hash="hash",
        signer_id="<script>alert('user')</script>",
        signer_role="<b>Role</b>",
        timestamp=datetime.now(timezone.utc),
        meaning="<intent>",
        signature_token="token",
    )
    output_path = tmp_path / "injection.pdf"

    PDFGenerator().generate_sds(sample_artifact, output_path)

    call_args = mock_html_class.call_args
    html_content = call_args.kwargs.get("string", "")

    # Should find escaped entities, not raw tags
    assert "&lt;script&gt;" in html_content
    assert "&lt;b&gt;" in html_content
    assert "&lt;intent&gt;" in html_content


def test_approved_state_watermark(tmp_path: Path, sample_artifact: DraftArtifact, mock_html_class: MagicMock) -> None:
    """
    Verify that APPROVED state still shows the watermark (as it is not yet SIGNED).
    """
    sample_artifact.status = DocumentState.APPROVED
    output_path = tmp_path / "approved.pdf"

    PDFGenerator().generate_sds(sample_artifact, output_path)

    call_args = mock_html_class.call_args
    html_content = call_args.kwargs.get("string", "")

    assert '<div class="watermark">DRAFT</div>' in html_content
