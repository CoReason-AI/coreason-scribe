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
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional

from coreason_scribe.models import DocumentState, DraftArtifact, SignatureBlock
from coreason_scribe.utils.logger import logger


class IdentityProvider(ABC):
    """
    Abstract base class for Identity Providers.
    """

    @abstractmethod
    def authenticate(self, user_id: str, credential: str) -> Optional[str]:
        """
        Authenticates a user and returns a signature token if successful.
        """
        pass  # pragma: no cover


class MockIdentityProvider(IdentityProvider):
    """
    A mock identity provider for testing and development.
    """

    def authenticate(self, user_id: str, credential: str) -> Optional[str]:
        """
        Returns a mock token if credential is 'correct-password'.
        """
        if credential == "correct-password":
            return f"mock-token-{uuid.uuid4()}"
        return None


class SigningRoom:
    """
    Manages the lifecycle of a document from Draft to Signed.
    """

    def __init__(self, identity_provider: IdentityProvider):
        self.identity_provider = identity_provider

    def submit_for_review(self, artifact: DraftArtifact) -> DraftArtifact:
        """
        Transitions a document from DRAFT to PENDING_REVIEW.
        """
        if artifact.status != DocumentState.DRAFT:
            raise ValueError(f"Cannot submit for review. Current status is {artifact.status}, expected DRAFT.")

        artifact.status = DocumentState.PENDING_REVIEW
        logger.info(f"Artifact version {artifact.version} submitted for review.")
        return artifact

    def approve(self, artifact: DraftArtifact, approver_id: str) -> DraftArtifact:
        """
        Transitions a document from PENDING_REVIEW to APPROVED.
        """
        if artifact.status != DocumentState.PENDING_REVIEW:
            raise ValueError(f"Cannot approve. Current status is {artifact.status}, expected PENDING_REVIEW.")

        artifact.status = DocumentState.APPROVED
        logger.info(f"Artifact version {artifact.version} approved by {approver_id}.")
        return artifact

    def sign(self, artifact: DraftArtifact, signer_id: str, signer_role: str, credential: str) -> DraftArtifact:
        """
        Signs an APPROVED document.
        """
        if artifact.status != DocumentState.APPROVED:
            raise ValueError(f"Cannot sign. Current status is {artifact.status}, expected APPROVED.")

        # Authenticate
        token = self.identity_provider.authenticate(signer_id, credential)
        if not token:
            raise ValueError("Authentication failed. Invalid credential.")

        # Calculate Hash
        # We hash the string representation of the sections and version to ensure integrity.
        # In a real PDF scenario, we might hash the PDF bytes. Here we hash the content.
        content_to_hash = f"{artifact.version}:{artifact.timestamp.isoformat()}"
        for section in artifact.sections:
            content_to_hash += f":{section.id}:{section.content}:{section.linked_code_hash}"

        document_hash = hashlib.sha256(content_to_hash.encode("utf-8")).hexdigest()

        # Create Signature Block
        signature = SignatureBlock(
            document_hash=document_hash,
            signer_id=signer_id,
            signer_role=signer_role,
            timestamp=datetime.now(timezone.utc),
            meaning="I certify this design specification.",
            signature_token=token,
        )

        artifact.status = DocumentState.SIGNED
        artifact.signature = signature
        logger.info(f"Artifact version {artifact.version} signed by {signer_id}.")

        return artifact
