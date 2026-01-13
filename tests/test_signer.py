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

from coreason_scribe.models import DocumentState, DraftArtifact, DraftSection
from coreason_scribe.signer import MockIdentityProvider, SigningRoom


@pytest.fixture
def mock_id_provider() -> MockIdentityProvider:
    return MockIdentityProvider()


@pytest.fixture
def signing_room(mock_id_provider: MockIdentityProvider) -> SigningRoom:
    return SigningRoom(mock_id_provider)


@pytest.fixture
def draft_artifact() -> DraftArtifact:
    return DraftArtifact(
        version="1.0.0",
        timestamp=datetime.now(timezone.utc),
        sections=[
            DraftSection(
                id="sec1",
                content="content1",
                author="HUMAN",
                is_modified=False,
                linked_code_hash="hash1",
            )
        ],
        status=DocumentState.DRAFT,
    )


def test_submit_for_review(signing_room: SigningRoom, draft_artifact: DraftArtifact) -> None:
    updated_artifact = signing_room.submit_for_review(draft_artifact)
    assert updated_artifact.status == DocumentState.PENDING_REVIEW


def test_submit_for_review_invalid_state(signing_room: SigningRoom, draft_artifact: DraftArtifact) -> None:
    draft_artifact.status = DocumentState.APPROVED
    with pytest.raises(ValueError, match="expected DRAFT"):
        signing_room.submit_for_review(draft_artifact)


def test_approve(signing_room: SigningRoom, draft_artifact: DraftArtifact) -> None:
    draft_artifact.status = DocumentState.PENDING_REVIEW
    updated_artifact = signing_room.approve(draft_artifact, "user1")
    assert updated_artifact.status == DocumentState.APPROVED


def test_approve_invalid_state(signing_room: SigningRoom, draft_artifact: DraftArtifact) -> None:
    with pytest.raises(ValueError, match="expected PENDING_REVIEW"):
        signing_room.approve(draft_artifact, "user1")


def test_sign_success(signing_room: SigningRoom, draft_artifact: DraftArtifact) -> None:
    draft_artifact.status = DocumentState.APPROVED
    updated_artifact = signing_room.sign(draft_artifact, "user1", "Quality_Manager", "correct-password")

    assert updated_artifact.status == DocumentState.SIGNED
    assert updated_artifact.signature is not None
    assert updated_artifact.signature.signer_id == "user1"
    assert updated_artifact.signature.signer_role == "Quality_Manager"
    assert updated_artifact.signature.signature_token.startswith("mock-token-")
    assert len(updated_artifact.signature.document_hash) == 64  # SHA256 length


def test_sign_invalid_state(signing_room: SigningRoom, draft_artifact: DraftArtifact) -> None:
    # Default is DRAFT
    with pytest.raises(ValueError, match="expected APPROVED"):
        signing_room.sign(draft_artifact, "user1", "role", "correct-password")


def test_sign_auth_failure(signing_room: SigningRoom, draft_artifact: DraftArtifact) -> None:
    draft_artifact.status = DocumentState.APPROVED
    with pytest.raises(ValueError, match="Authentication failed"):
        signing_room.sign(draft_artifact, "user1", "role", "wrong-password")


def test_mock_identity_provider() -> None:
    provider = MockIdentityProvider()
    assert provider.authenticate("user", "correct-password") is not None
    assert provider.authenticate("user", "wrong") is None
