# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason-scribe

import hashlib
from datetime import datetime, timezone

import pytest

from coreason_identity.models import UserContext
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


@pytest.fixture
def user_context() -> UserContext:
    return UserContext(sub="user1", email="user1@example.com", permissions=[])


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


def test_sign_success(signing_room: SigningRoom, draft_artifact: DraftArtifact, user_context: UserContext) -> None:
    draft_artifact.status = DocumentState.APPROVED
    updated_artifact = signing_room.sign(draft_artifact, user_context, "Quality_Manager", "correct-password")

    assert updated_artifact.status == DocumentState.SIGNED
    assert updated_artifact.signature is not None
    assert updated_artifact.signature.signer_id == "user1"
    assert updated_artifact.signature.signer_role == "Quality_Manager"
    assert updated_artifact.signature.signature_token.startswith("mock-token-")
    assert len(updated_artifact.signature.document_hash) == 64  # SHA256 length


def test_sign_invalid_state(signing_room: SigningRoom, draft_artifact: DraftArtifact, user_context: UserContext) -> None:
    # Default is DRAFT
    with pytest.raises(ValueError, match="expected APPROVED"):
        signing_room.sign(draft_artifact, user_context, "role", "correct-password")


def test_sign_auth_failure(signing_room: SigningRoom, draft_artifact: DraftArtifact, user_context: UserContext) -> None:
    draft_artifact.status = DocumentState.APPROVED
    with pytest.raises(ValueError, match="Authentication failed"):
        signing_room.sign(draft_artifact, user_context, "role", "wrong-password")


def test_mock_identity_provider() -> None:
    provider = MockIdentityProvider()
    assert provider.authenticate("user", "correct-password") is not None
    assert provider.authenticate("user", "wrong") is None


# --- Edge Case & Complex Scenario Tests ---


def test_tampering_after_approval(
    signing_room: SigningRoom, draft_artifact: DraftArtifact, user_context: UserContext
) -> None:
    """
    Test that if content is modified after approval but before signing,
    the signature hash reflects the MODIFIED content.
    This asserts that the system signs exactly what is present at the moment of signing.
    """
    # 1. Approve
    draft_artifact.status = DocumentState.PENDING_REVIEW
    signing_room.approve(draft_artifact, "approver")

    # 2. Tamper
    original_content = draft_artifact.sections[0].content
    draft_artifact.sections[0].content = "MALICIOUS CONTENT"

    # 3. Sign
    signing_room.sign(draft_artifact, user_context, "role", "correct-password")

    # 4. Verify Hash matches modified content
    # Manually calculate hash of modified content
    content_to_hash = f"{draft_artifact.version}:{draft_artifact.timestamp.isoformat()}"
    content_to_hash += (
        f":{draft_artifact.sections[0].id}:MALICIOUS CONTENT:{draft_artifact.sections[0].linked_code_hash}"
    )
    expected_hash = hashlib.sha256(content_to_hash.encode("utf-8")).hexdigest()

    assert draft_artifact.signature is not None
    assert draft_artifact.signature.document_hash == expected_hash


def test_sign_draft(signing_room: SigningRoom, draft_artifact: DraftArtifact, user_context: UserContext) -> None:
    updated_artifact = signing_room.sign_draft(draft_artifact, user_context)
    assert updated_artifact.signature is not None
    assert updated_artifact.signature.signer_id == user_context.sub
    assert updated_artifact.signature.signer_role == "Generator"
    assert updated_artifact.signature.meaning == "Generated by Scribe Engine"


def test_empty_artifact_signing(signing_room: SigningRoom, user_context: UserContext) -> None:
    """
    Test the full lifecycle for an artifact with NO sections.
    """
    empty_artifact = DraftArtifact(
        version="0.0.0",
        timestamp=datetime.now(timezone.utc),
        sections=[],
        status=DocumentState.DRAFT,
    )

    # Draft -> Pending
    signing_room.submit_for_review(empty_artifact)
    # Pending -> Approved
    signing_room.approve(empty_artifact, "admin")
    # Approved -> Signed
    signing_room.sign(empty_artifact, user_context, "role", "correct-password")

    assert empty_artifact.status == DocumentState.SIGNED
    assert empty_artifact.signature is not None
    # Hash should be valid (just version and timestamp)
    assert len(empty_artifact.signature.document_hash) == 64


def test_unicode_content_signing(signing_room: SigningRoom, user_context: UserContext) -> None:
    """
    Test signing works with Unicode/Emoji characters in content.
    """
    unicode_artifact = DraftArtifact(
        version="1.0.U",
        timestamp=datetime.now(timezone.utc),
        sections=[
            DraftSection(
                id="sec_unicode",
                content="Testing Unicode: 💊 (Pill), ⚕️ (Medical), 测试 (Test)",
                author="AI",
                is_modified=True,
                linked_code_hash="hash_unicode",
            )
        ],
        status=DocumentState.DRAFT,
    )

    signing_room.submit_for_review(unicode_artifact)
    signing_room.approve(unicode_artifact, "admin")
    signing_room.sign(unicode_artifact, user_context, "role", "correct-password")

    assert unicode_artifact.status == DocumentState.SIGNED
    assert unicode_artifact.signature is not None
    # Re-verify hash to ensure encoding was handled correctly
    content_str = f"{unicode_artifact.version}:{unicode_artifact.timestamp.isoformat()}"
    content_str += f":sec_unicode:{unicode_artifact.sections[0].content}:hash_unicode"
    expected_hash = hashlib.sha256(content_str.encode("utf-8")).hexdigest()
    assert unicode_artifact.signature.document_hash == expected_hash


def test_strict_state_transitions_idempotency(
    signing_room: SigningRoom, draft_artifact: DraftArtifact, user_context: UserContext
) -> None:
    """
    Test that state transitions are strict and cannot be repeated (not idempotent in a loose sense,
    but strict about current state).
    """
    # 1. Double Submit
    signing_room.submit_for_review(draft_artifact)
    with pytest.raises(ValueError, match="expected DRAFT"):
        signing_room.submit_for_review(draft_artifact)

    # 2. Double Approve
    signing_room.approve(draft_artifact, "approver")
    with pytest.raises(ValueError, match="expected PENDING_REVIEW"):
        signing_room.approve(draft_artifact, "approver")

    # 3. Double Sign
    signing_room.sign(draft_artifact, user_context, "role", "correct-password")
    with pytest.raises(ValueError, match="expected APPROVED"):
        signing_room.sign(draft_artifact, user_context, "role", "correct-password")


def test_signature_integrity_verification(
    signing_room: SigningRoom, draft_artifact: DraftArtifact, user_context: UserContext
) -> None:
    """
    Verifies that the hash calculation logic is deterministic.
    """
    draft_artifact.status = DocumentState.APPROVED
    signing_room.sign(draft_artifact, user_context, "role", "correct-password")

    # Reconstruct the expected hash string
    s = draft_artifact.sections[0]
    expected_str = (
        f"{draft_artifact.version}:{draft_artifact.timestamp.isoformat()}:{s.id}:{s.content}:{s.linked_code_hash}"
    )
    expected_hash = hashlib.sha256(expected_str.encode("utf-8")).hexdigest()

    assert draft_artifact.signature is not None
    assert draft_artifact.signature.document_hash == expected_hash
