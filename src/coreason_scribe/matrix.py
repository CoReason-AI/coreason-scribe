# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_scribe

from enum import Enum

from pydantic import BaseModel, Field

from coreason_scribe.models import Requirement, RiskLevel


class ComplianceStatus(str, Enum):
    """
    The compliance status of a requirement based on verification evidence.
    """

    PASS = "PASS"
    WARNING = "WARNING"
    CRITICAL_GAP = "CRITICAL_GAP"


class GapAnalysisResult(BaseModel):
    """
    Result of a gap analysis for a single requirement.
    """

    requirement_id: str
    status: ComplianceStatus
    risk_level: RiskLevel
    coverage_percentage: float = Field(ge=0.0, le=100.0)
    message: str


class RiskAnalyzer:
    """
    Analyzes the risk and coverage of requirements to determine compliance status.
    """

    @staticmethod
    def analyze_coverage(requirement: Requirement, coverage_percentage: float) -> GapAnalysisResult:
        """
        Evaluates the compliance status of a requirement based on its risk level and test coverage.

        Rules:
        - High Risk: Requires 100% coverage. If < 100%, returns CRITICAL_GAP.
        - Med/Low Risk: If < 100% coverage, returns WARNING.
        - Any Risk: If 100% coverage, returns PASS.

        Args:
            requirement: The requirement to analyze.
            coverage_percentage: The calculated test coverage percentage (0.0 to 100.0).

        Returns:
            A GapAnalysisResult object containing the status and details.
        """
        # Ensure coverage is clamped or valid (Pydantic validates, but we're passing to method)
        # We assume the caller provides a valid float.
        # Handle precision issues: 99.999999 should be treated carefully, but requirements say "< 100%".
        # We'll treat strictly less than 100 as a gap.

        is_fully_covered = coverage_percentage >= 100.0

        status: ComplianceStatus
        message: str

        if is_fully_covered:
            status = ComplianceStatus.PASS
            message = "Requirement verified with full coverage."
        else:
            if requirement.risk == RiskLevel.HIGH:
                status = ComplianceStatus.CRITICAL_GAP
                message = f"High Risk Requirement {requirement.id} has {coverage_percentage}% coverage (Requires 100%)."
            else:
                status = ComplianceStatus.WARNING
                message = (
                    f"{requirement.risk.value} Risk Requirement {requirement.id} has partial coverage "
                    f"({coverage_percentage}%)."
                )

        return GapAnalysisResult(
            requirement_id=requirement.id,
            status=status,
            risk_level=requirement.risk,
            coverage_percentage=coverage_percentage,
            message=message,
        )
