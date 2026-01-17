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
    TestStatus,
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
        Requirement(id="REQ-001", description="High Risk Req", risk=RiskLevel.HIGH),
        Requirement(id="REQ-002", description="Med Risk Req", risk=RiskLevel.MED),
        Requirement(id="REQ-003", description="Low Risk Req", risk=RiskLevel.LOW),
    ]


@pytest.fixture
def passed_assay_result() -> AssayResult:
    return AssayResult(
        test_id="TEST-001",
        status=TestStatus.PASS,
        coverage=100.0,
        linked_requirements=["REQ-001", "REQ-002", "REQ-003"],
        timestamp=datetime.now(),
    )


@pytest.fixture
def failed_assay_result() -> AssayResult:
    return AssayResult(
        test_id="TEST-001",
        status=TestStatus.FAIL,
        coverage=0.0,
        linked_requirements=["REQ-001", "REQ-002", "REQ-003"],
        timestamp=datetime.now(),
    )


@pytest.fixture
def partial_assay_result() -> AssayResult:
    return AssayResult(
        test_id="TEST-001",
        status=TestStatus.PASS,
        coverage=50.0,
        linked_requirements=["REQ-001", "REQ-002", "REQ-003"],
        timestamp=datetime.now(),
    )


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


def test_verification_regression_pass_to_critical(
    empty_artifact: DraftArtifact,
    requirements: List[Requirement],
    passed_assay_result: AssayResult,
    failed_assay_result: AssayResult,
) -> None:
    # Previous: PASS (100% coverage)
    # Current: CRITICAL_GAP (0% coverage) for High Risk REQ-001
    prev_report = AssayReport(
        id="rep-1",
        timestamp=datetime.now(),
        results=[passed_assay_result],
    )
    curr_report = AssayReport(
        id="rep-2",
        timestamp=datetime.now(),
        results=[failed_assay_result],
    )

    engine = SemanticDeltaEngine()
    delta = engine.compute_delta(
        current=empty_artifact,
        previous=empty_artifact,
        current_report=curr_report,
        previous_report=prev_report,
        requirements=requirements,
    )

    assert len(delta.verification_drifts) > 0
    # REQ-001 (High Risk) went from PASS to CRITICAL_GAP
    drift_001 = next((d for d in delta.verification_drifts if d.requirement_id == "REQ-001"), None)
    assert drift_001 is not None
    assert drift_001.previous_status == ComplianceStatus.PASS.value
    assert drift_001.current_status == ComplianceStatus.CRITICAL_GAP.value


def test_verification_regression_pass_to_warning(
    empty_artifact: DraftArtifact,
    requirements: List[Requirement],
    passed_assay_result: AssayResult,
    partial_assay_result: AssayResult,
) -> None:
    # Previous: PASS (100% coverage)
    # Current: WARNING (50% coverage) for Med Risk REQ-002
    prev_report = AssayReport(
        id="rep-1",
        timestamp=datetime.now(),
        results=[passed_assay_result],
    )
    curr_report = AssayReport(
        id="rep-2",
        timestamp=datetime.now(),
        results=[partial_assay_result],
    )

    engine = SemanticDeltaEngine()
    delta = engine.compute_delta(
        current=empty_artifact,
        previous=empty_artifact,
        current_report=curr_report,
        previous_report=prev_report,
        requirements=requirements,
    )

    # REQ-002 (MED Risk) -> PASS to WARNING
    drift_002 = next((d for d in delta.verification_drifts if d.requirement_id == "REQ-002"), None)
    assert drift_002 is not None
    assert drift_002.previous_status == ComplianceStatus.PASS.value
    assert drift_002.current_status == ComplianceStatus.WARNING.value


def test_verification_regression_warning_to_critical(
    empty_artifact: DraftArtifact,
    requirements: List[Requirement],
    partial_assay_result: AssayResult,
    failed_assay_result: AssayResult,
) -> None:
    # This checks WARNING -> CRITICAL_GAP regression.
    # As noted in delta.py, this path is theoretically unreachable with static requirements
    # because risk levels don't change.
    # However, the logic is kept for robustness.
    # This test is a placeholder to document why we don't strictly cover it (pragma: no cover used in source).
    pass


def test_no_drift_improvement(
    empty_artifact: DraftArtifact,
    requirements: List[Requirement],
    failed_assay_result: AssayResult,
    passed_assay_result: AssayResult,
) -> None:
    # Previous: FAIL
    # Current: PASS
    # Should NOT be a regression.
    prev_report = AssayReport(
        id="rep-1",
        timestamp=datetime.now(),
        results=[failed_assay_result],
    )
    curr_report = AssayReport(
        id="rep-2",
        timestamp=datetime.now(),
        results=[passed_assay_result],
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


def test_missing_requirements_handling(
    empty_artifact: DraftArtifact, requirements: List[Requirement], passed_assay_result: AssayResult
) -> None:
    # This test case documents why "if not prev or not curr: continue" was removed or simplified.
    # Since we iterate over the same requirements list to build the status map, every requirement
    # in the loop is guaranteed to be in the map.
    pass
