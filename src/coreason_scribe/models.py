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
    HIGH = "HIGH"  # Patient Safety / GxP
    MED = "MED"  # Business Logic
    LOW = "LOW"  # UI / Formatting


class Requirement(BaseModel):
    id: str  # "REQ-001"
    description: str
    risk: RiskLevel
    source_sop: Optional[str] = None  # "SOP-999"


class DraftSection(BaseModel):
    id: str  # "logic_summary_safety"
    content: str  # "The safety module checks..."
    author: Literal["AI", "HUMAN"]
    is_modified: bool  # Logic Diff vs Previous Version
    linked_code_hash: str  # SHA256 of the python source


class DraftArtifact(BaseModel):
    version: str
    timestamp: datetime
    sections: List[DraftSection]


class SignatureBlock(BaseModel):
    document_hash: str  # SHA-256 of the PDF content
    signer_id: str  # User UUID
    signer_role: str  # "Quality_Manager"
    timestamp: datetime
    meaning: str  # "I certify this design specification."
    signature_token: str  # Cryptographic proof from Identity


class DiffType(str, Enum):
    NEW = "NEW"
    REMOVED = "REMOVED"
    LOGIC_CHANGE = "LOGIC_CHANGE"
    TEXT_CHANGE = "TEXT_CHANGE"
    BOTH = "BOTH"


class DiffItem(BaseModel):
    section_id: str
    diff_type: DiffType
    current_section: Optional[DraftSection]
    previous_section: Optional[DraftSection]


class DeltaReport(BaseModel):
    current_version: str
    previous_version: str
    timestamp: datetime
    changes: List[DiffItem]
