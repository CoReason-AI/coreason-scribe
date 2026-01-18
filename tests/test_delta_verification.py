# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason-scribe

from datetime import datetime
from typing import List

import pytest

from coreason_scribe.delta import SemanticDeltaEngine
from coreason_scribe.matrix import ComplianceStatus
from coreason_scribe.models import (
    AssayReport,
    AssayResult,
    AssayStatus,
    DraftArtifact,
    Requirement,
    RiskLevel,
)


@pytest.fixture
def empty_artifact() -> DraftArtifact:
    return DraftArtifact(
        version="1.0",
        timestamp=datetime.now(),
        sections=[],
    )


@pytest.fixture
def requirements() -> List[Requirement]:
    return [
        Requirement(id="REQ-HIGH", description="High Risk Req", risk=RiskLevel.HIGH),
        Requirement(id="REQ-MED", description="Med Risk Req", risk=RiskLevel.MED),
        Requirement(id="REQ-LOW", description="Low Risk Req", risk=RiskLevel.LOW),
    ]


def create_result(test_id: str, coverage: float, reqs: List[str]) -> AssayResult:
    return AssayResult(
        test_id=test_id,
        status=AssayStatus.PASS if coverage >= 100.0 else AssayStatus.FAIL,
        coverage=coverage,
        linked_requirements=reqs,
        timestamp=datetime.now(),
    )


@pytest.mark.parametrize(
    "prev_cov, curr_cov, req_id, expected_prev, expected_curr",
    [
        (100.0, 0.0, "REQ-HIGH", ComplianceStatus.PASS, ComplianceStatus.CRITICAL_GAP),
        (100.0, 50.0, "REQ-MED", ComplianceStatus.PASS, ComplianceStatus.WARNING),
    ],
)
def test_verification_regression(
    empty_artifact: DraftArtifact,
    requirements: List[Requirement],
    prev_cov: float,
    curr_cov: float,
    req_id: str,
    expected_prev: ComplianceStatus,
    expected_curr: ComplianceStatus,
) -> None:
    prev_report = AssayReport(
        id="rep-1",
        timestamp=datetime.now(),
        results=[create_result("TEST-1", prev_cov, [req_id])],
    )
    curr_report = AssayReport(
        id="rep-2",
        timestamp=datetime.now(),
        results=[create_result("TEST-1", curr_cov, [req_id])],
    )

    engine = SemanticDeltaEngine()
    delta = engine.compute_delta(
        current=empty_artifact,
        previous=empty_artifact,
        current_report=curr_report,
        previous_report=prev_report,
        requirements=requirements,
    )

    drift = next((d for d in delta.verification_drifts if d.requirement_id == req_id), None)
    assert drift is not None
    assert drift.previous_status == expected_prev.value
    assert drift.current_status == expected_curr.value


def test_no_drift_improvement(empty_artifact: DraftArtifact, requirements: List[Requirement]) -> None:
    # Fail -> Pass
    prev_report = AssayReport(
        id="rep-1",
        timestamp=datetime.now(),
        results=[create_result("TEST-1", 0.0, ["REQ-HIGH"])],
    )
    curr_report = AssayReport(
        id="rep-2",
        timestamp=datetime.now(),
        results=[create_result("TEST-1", 100.0, ["REQ-HIGH"])],
    )

    engine = SemanticDeltaEngine()
    delta = engine.compute_delta(
        current=empty_artifact,
        previous=empty_artifact,
        current_report=curr_report,
        previous_report=prev_report,
        requirements=requirements,
    )

    assert len(delta.verification_drifts) == 0


def test_missing_requirements_handling(empty_artifact: DraftArtifact, requirements: List[Requirement]) -> None:
    # This test ensures that even if a requirement has no tests (missing from report results),
    # it is handled correctly (likely 0% coverage -> CRITICAL/WARNING).
    # Since risk is constant, status remains constant (CRITICAL -> CRITICAL), so no drift.
    prev_report = AssayReport(id="rep-1", timestamp=datetime.now(), results=[])
    curr_report = AssayReport(id="rep-2", timestamp=datetime.now(), results=[])

    engine = SemanticDeltaEngine()
    delta = engine.compute_delta(
        current=empty_artifact,
        previous=empty_artifact,
        current_report=curr_report,
        previous_report=prev_report,
        requirements=requirements,
    )
    assert len(delta.verification_drifts) == 0


def test_no_verification_drift_when_reports_missing(
    empty_artifact: DraftArtifact, requirements: List[Requirement]
) -> None:
    engine = SemanticDeltaEngine()
    delta = engine.compute_delta(
        current=empty_artifact,
        previous=empty_artifact,
        requirements=requirements,
    )
    assert delta.verification_drifts == []
