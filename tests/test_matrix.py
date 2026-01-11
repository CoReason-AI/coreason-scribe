# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_scribe

import pytest
from pydantic import ValidationError

from coreason_scribe.matrix import ComplianceStatus, RiskAnalyzer
from coreason_scribe.models import Requirement, RiskLevel


def test_analyze_high_risk_full_coverage() -> None:
    req = Requirement(id="REQ-001", description="Patient safety", risk=RiskLevel.HIGH)
    result = RiskAnalyzer.analyze_coverage(req, 100.0)

    assert result.status == ComplianceStatus.PASS
    assert result.requirement_id == "REQ-001"
    assert result.risk_level == RiskLevel.HIGH
    assert result.coverage_percentage == 100.0


def test_analyze_high_risk_partial_coverage() -> None:
    req = Requirement(id="REQ-002", description="Patient safety", risk=RiskLevel.HIGH)
    result = RiskAnalyzer.analyze_coverage(req, 99.9)

    assert result.status == ComplianceStatus.CRITICAL_GAP
    assert "Requires 100%" in result.message
    assert result.coverage_percentage == 99.9


def test_analyze_high_risk_zero_coverage() -> None:
    req = Requirement(id="REQ-003", description="Patient safety", risk=RiskLevel.HIGH)
    result = RiskAnalyzer.analyze_coverage(req, 0.0)

    assert result.status == ComplianceStatus.CRITICAL_GAP


def test_analyze_med_risk_partial_coverage() -> None:
    req = Requirement(id="REQ-004", description="Business Logic", risk=RiskLevel.MED)
    result = RiskAnalyzer.analyze_coverage(req, 50.0)

    assert result.status == ComplianceStatus.WARNING
    assert "MED Risk" in result.message


def test_analyze_low_risk_partial_coverage() -> None:
    req = Requirement(id="REQ-005", description="UI", risk=RiskLevel.LOW)
    result = RiskAnalyzer.analyze_coverage(req, 80.0)

    assert result.status == ComplianceStatus.WARNING


def test_analyze_low_risk_full_coverage() -> None:
    req = Requirement(id="REQ-006", description="UI", risk=RiskLevel.LOW)
    result = RiskAnalyzer.analyze_coverage(req, 100.0)

    assert result.status == ComplianceStatus.PASS


def test_analyze_over_100_coverage() -> None:
    # It's possible for coverage tools to report strange numbers or user error
    # But GapAnalysisResult constrains it to <= 100 via Pydantic Field
    req = Requirement(id="REQ-007", description="UI", risk=RiskLevel.LOW)

    # We expect validation error from Pydantic construction inside the method
    # Wait, the method constructs GapAnalysisResult.
    # So if we pass 101.0, it should raise ValidationError.

    with pytest.raises(ValidationError):
        RiskAnalyzer.analyze_coverage(req, 101.0)


def test_analyze_negative_coverage() -> None:
    req = Requirement(id="REQ-008", description="UI", risk=RiskLevel.LOW)
    with pytest.raises(ValidationError):
        RiskAnalyzer.analyze_coverage(req, -1.0)
