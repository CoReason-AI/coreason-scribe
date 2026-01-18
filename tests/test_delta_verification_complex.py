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
from typing import List

import pytest

from coreason_scribe.delta import SemanticDeltaEngine
from coreason_scribe.matrix import ComplianceStatus
from coreason_scribe.models import (
    AssayReport,
    AssayResult,
    DraftArtifact,
    Requirement,
    RiskLevel,
    AssayStatus,
)


@pytest.fixture
def empty_artifact() -> DraftArtifact:
    return DraftArtifact(
        version="1.0",
        timestamp=datetime.now(),
        sections=[],
    )


@pytest.fixture
def requirements_complex() -> List[Requirement]:
    return [
        Requirement(id="REQ-HIGH", description="High Risk", risk=RiskLevel.HIGH),
        Requirement(id="REQ-MED", description="Med Risk", risk=RiskLevel.MED),
        Requirement(id="REQ-LOW", description="Low Risk", risk=RiskLevel.LOW),
    ]


def create_result(test_id: str, coverage: float, reqs: List[str]) -> AssayResult:
    return AssayResult(
        test_id=test_id,
        status=AssayStatus.PASS if coverage >= 100.0 else AssayStatus.FAIL,
        coverage=coverage,
        linked_requirements=reqs,
        timestamp=datetime.now(),
    )


def test_redundancy_prevents_regression(empty_artifact: DraftArtifact, requirements_complex: List[Requirement]) -> None:
    """
    Scenario: REQ-HIGH is covered by Test-A and Test-B.
    Previous: Both Pass.
    Current: Test-A Fails, Test-B Passes.
    Result: Max coverage is still 100%. Status is PASS. No Drift.
    """
    # Previous: Test A (100%), Test B (100%)
    prev_results = [
        create_result("TEST-A", 100.0, ["REQ-HIGH"]),
        create_result("TEST-B", 100.0, ["REQ-HIGH"]),
    ]
    prev_report = AssayReport(id="prev", timestamp=datetime.now(), results=prev_results)

    # Current: Test A (0%), Test B (100%)
    curr_results = [
        create_result("TEST-A", 0.0, ["REQ-HIGH"]),
        create_result("TEST-B", 100.0, ["REQ-HIGH"]),
    ]
    curr_report = AssayReport(id="curr", timestamp=datetime.now(), results=curr_results)

    engine = SemanticDeltaEngine()
    delta = engine.compute_delta(
        current=empty_artifact,
        previous=empty_artifact,
        current_report=curr_report,
        previous_report=prev_report,
        requirements=requirements_complex,
    )

    # Expectation: REQ-HIGH status is PASS in both. No drift.
    assert delta.verification_drifts == []


def test_shared_test_failure_cascades(empty_artifact: DraftArtifact, requirements_complex: List[Requirement]) -> None:
    """
    Scenario: TEST-SHARED covers REQ-HIGH and REQ-MED.
    Previous: TEST-SHARED Passes (100%).
    Current: TEST-SHARED Fails (0%).
    Result:
        REQ-HIGH: PASS -> CRITICAL_GAP (Regression)
        REQ-MED: PASS -> WARNING (Regression)
    """
    # Previous: Shared Test 100%
    prev_results = [
        create_result("TEST-SHARED", 100.0, ["REQ-HIGH", "REQ-MED"]),
    ]
    prev_report = AssayReport(id="prev", timestamp=datetime.now(), results=prev_results)

    # Current: Shared Test 0%
    curr_results = [
        create_result("TEST-SHARED", 0.0, ["REQ-HIGH", "REQ-MED"]),
    ]
    curr_report = AssayReport(id="curr", timestamp=datetime.now(), results=curr_results)

    engine = SemanticDeltaEngine()
    delta = engine.compute_delta(
        current=empty_artifact,
        previous=empty_artifact,
        current_report=curr_report,
        previous_report=prev_report,
        requirements=requirements_complex,
    )

    assert len(delta.verification_drifts) == 2

    drift_high = next((d for d in delta.verification_drifts if d.requirement_id == "REQ-HIGH"), None)
    assert drift_high is not None
    assert drift_high.previous_status == ComplianceStatus.PASS.value
    assert drift_high.current_status == ComplianceStatus.CRITICAL_GAP.value

    drift_med = next((d for d in delta.verification_drifts if d.requirement_id == "REQ-MED"), None)
    assert drift_med is not None
    assert drift_med.previous_status == ComplianceStatus.PASS.value
    assert drift_med.current_status == ComplianceStatus.WARNING.value


def test_total_test_loss(empty_artifact: DraftArtifact, requirements_complex: List[Requirement]) -> None:
    """
    Scenario: All requirements passed previously. Current report is empty.
    (e.g. CI failure didn't generate report properly but we have empty object).
    Result: All requirements regress.
    """
    prev_results = [
        create_result("TEST-1", 100.0, ["REQ-HIGH"]),
        create_result("TEST-2", 100.0, ["REQ-MED"]),
        create_result("TEST-3", 100.0, ["REQ-LOW"]),
    ]
    prev_report = AssayReport(id="prev", timestamp=datetime.now(), results=prev_results)

    curr_report = AssayReport(id="curr", timestamp=datetime.now(), results=[])

    engine = SemanticDeltaEngine()
    delta = engine.compute_delta(
        current=empty_artifact,
        previous=empty_artifact,
        current_report=curr_report,
        previous_report=prev_report,
        requirements=requirements_complex,
    )

    assert len(delta.verification_drifts) == 3
    # Check REQ-HIGH
    drift_high = next(d for d in delta.verification_drifts if d.requirement_id == "REQ-HIGH")
    assert drift_high.current_status == ComplianceStatus.CRITICAL_GAP.value

    # Check REQ-MED
    drift_med = next(d for d in delta.verification_drifts if d.requirement_id == "REQ-MED")
    assert drift_med.current_status == ComplianceStatus.WARNING.value

    # Check REQ-LOW
    drift_low = next(d for d in delta.verification_drifts if d.requirement_id == "REQ-LOW")
    assert drift_low.current_status == ComplianceStatus.WARNING.value


def test_mixed_bag_drift(empty_artifact: DraftArtifact, requirements_complex: List[Requirement]) -> None:
    """
    Scenario:
    REQ-HIGH: PASS -> FAIL (Regression)
    REQ-MED: FAIL -> PASS (Improvement)
    REQ-LOW: PASS -> PASS (Stable)
    """
    # Previous: HIGH=PASS, MED=FAIL(0%), LOW=PASS
    prev_results = [
        create_result("TEST-H", 100.0, ["REQ-HIGH"]),
        create_result("TEST-M", 0.0, ["REQ-MED"]),
        create_result("TEST-L", 100.0, ["REQ-LOW"]),
    ]
    prev_report = AssayReport(id="prev", timestamp=datetime.now(), results=prev_results)

    # Current: HIGH=FAIL(0%), MED=PASS, LOW=PASS
    curr_results = [
        create_result("TEST-H", 0.0, ["REQ-HIGH"]),
        create_result("TEST-M", 100.0, ["REQ-MED"]),
        create_result("TEST-L", 100.0, ["REQ-LOW"]),
    ]
    curr_report = AssayReport(id="curr", timestamp=datetime.now(), results=curr_results)

    engine = SemanticDeltaEngine()
    delta = engine.compute_delta(
        current=empty_artifact,
        previous=empty_artifact,
        current_report=curr_report,
        previous_report=prev_report,
        requirements=requirements_complex,
    )

    # Only REQ-HIGH should be in drifts
    assert len(delta.verification_drifts) == 1
    assert delta.verification_drifts[0].requirement_id == "REQ-HIGH"
    assert delta.verification_drifts[0].previous_status == ComplianceStatus.PASS.value
    assert delta.verification_drifts[0].current_status == ComplianceStatus.CRITICAL_GAP.value
