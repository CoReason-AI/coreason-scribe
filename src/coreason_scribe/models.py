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
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel


class RiskLevel(str, Enum):
    """
    Risk levels for requirements.
    HIGH: Patient Safety / GxP
    MED: Business Logic
    LOW: UI / Formatting
    """

    HIGH = "HIGH"
    MED = "MED"
    LOW = "LOW"


class Requirement(BaseModel):
    """
    A requirement for the system.
    """

    id: str
    description: str
    risk: RiskLevel
    source_sop: Optional[str] = None


class DraftSection(BaseModel):
    """
    A section of the draft documentation.
    """

    id: str
    content: str
    author: Literal["AI", "HUMAN"]
    is_modified: bool
    linked_code_hash: str


class SignatureBlock(BaseModel):
    """
    A block representing a digital signature.
    """

    document_hash: str
    signer_id: str
    signer_role: str
    timestamp: datetime
    meaning: str
    signature_token: str
