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
from pathlib import Path
from typing import Any, Callable
from unittest.mock import patch

import pytest

from coreason_scribe.main import main
from coreason_scribe.models import (
    AssayResult,
    AssayStatus,
    Requirement,
    RiskLevel,
)


def test_gate_no_requirements(
    tmp_path: Path, mock_traceability_context: Callable[..., Any], capsys: pytest.CaptureFixture[str]
) -> None:
    """Scenario: No requirements defined. Should PASS."""
    with mock_traceability_context(tmp_path, requirements=[], assay_results=[]) as (yaml_path, report_path):
        with patch("sys.argv", ["scribe", "check", "--agent-yaml", str(yaml_path), "--assay-report", str(report_path)]):
            assert main() == 0

    captured = capsys.readouterr()
    assert "SUCCESS" in captured.out
    assert "FATAL" not in captured.out


def test_gate_high_risk_no_tests(
    tmp_path: Path, mock_traceability_context: Callable[..., Any], capsys: pytest.CaptureFixture[str]
) -> None:
    """Scenario: High Risk Requirement exists, but no tests are present in the report."""
    req = Requirement(id="REQ-001", description="Safety", risk=RiskLevel.HIGH)
    with mock_traceability_context(tmp_path, requirements=[req], assay_results=[]) as (yaml_path, report_path):
        with patch("sys.argv", ["scribe", "check", "--agent-yaml", str(yaml_path), "--assay-report", str(report_path)]):
            assert main() == 1

    captured = capsys.readouterr()
    assert "FATAL" in captured.out
    assert "CRITICAL_GAP" in captured.out
    assert "REQ-001" in captured.out


def test_gate_mixed_risks(
    tmp_path: Path, mock_traceability_context: Callable[..., Any], capsys: pytest.CaptureFixture[str]
) -> None:
    """
    Scenario:
    - REQ-HIGH: 100% Coverage (PASS)
    - REQ-MED: 50% Coverage (WARNING)
    - REQ-LOW: 0% Coverage (WARNING)
    Outcome: Should PASS (Exit 0) because warnings do not block build.
    """
    reqs = [
        Requirement(id="REQ-HIGH", description="High", risk=RiskLevel.HIGH),
        Requirement(id="REQ-MED", description="Med", risk=RiskLevel.MED),
        Requirement(id="REQ-LOW", description="Low", risk=RiskLevel.LOW),
    ]
    results = [
        AssayResult(
            test_id="T1",
            status=AssayStatus.PASS,
            coverage=100.0,
            linked_requirements=["REQ-HIGH"],
            timestamp=datetime.now(),
        ),
        AssayResult(
            test_id="T2",
            status=AssayStatus.PASS,
            coverage=50.0,
            linked_requirements=["REQ-MED"],
            timestamp=datetime.now(),
        ),
    ]

    with mock_traceability_context(tmp_path, requirements=reqs, assay_results=results) as (yaml_path, report_path):
        with patch("sys.argv", ["scribe", "check", "--agent-yaml", str(yaml_path), "--assay-report", str(report_path)]):
            assert main() == 0

    captured = capsys.readouterr()
    assert "SUCCESS" in captured.out
    assert "[PASS] REQ-HIGH" in captured.out
    assert "[WARNING] REQ-MED" in captured.out
    assert "[WARNING] REQ-LOW" in captured.out


def test_gate_multiple_critical_gaps(
    tmp_path: Path, mock_traceability_context: Callable[..., Any], capsys: pytest.CaptureFixture[str]
) -> None:
    """Scenario: Multiple High Risk requirements fail. Report should list all."""
    reqs = [
        Requirement(id="REQ-H1", description="H1", risk=RiskLevel.HIGH),
        Requirement(id="REQ-H2", description="H2", risk=RiskLevel.HIGH),
    ]
    # T1 covers H1 partially (90%), H2 not covered.
    results = [
        AssayResult(
            test_id="T1",
            status=AssayStatus.PASS,
            coverage=90.0,
            linked_requirements=["REQ-H1"],
            timestamp=datetime.now(),
        )
    ]

    with mock_traceability_context(tmp_path, requirements=reqs, assay_results=results) as (yaml_path, report_path):
        with patch("sys.argv", ["scribe", "check", "--agent-yaml", str(yaml_path), "--assay-report", str(report_path)]):
            assert main() == 1

    captured = capsys.readouterr()
    assert "FATAL: 2 Critical Gaps detected" in captured.out
    assert "FAILED: REQ-H1" in captured.out
    assert "FAILED: REQ-H2" in captured.out


def test_gate_boundary_coverage(
    tmp_path: Path, mock_traceability_context: Callable[..., Any], capsys: pytest.CaptureFixture[str]
) -> None:
    """Scenario: High Risk with 99.99% coverage. Should FAIL."""
    req = Requirement(id="REQ-H1", description="H1", risk=RiskLevel.HIGH)
    results = [
        AssayResult(
            test_id="T1",
            status=AssayStatus.PASS,
            coverage=99.99,
            linked_requirements=["REQ-H1"],
            timestamp=datetime.now(),
        )
    ]

    with mock_traceability_context(tmp_path, requirements=[req], assay_results=results) as (yaml_path, report_path):
        with patch("sys.argv", ["scribe", "check", "--agent-yaml", str(yaml_path), "--assay-report", str(report_path)]):
            assert main() == 1

    captured = capsys.readouterr()
    assert "CRITICAL_GAP" in captured.out


def test_gate_orphaned_tests(
    tmp_path: Path, mock_traceability_context: Callable[..., Any], capsys: pytest.CaptureFixture[str]
) -> None:
    """Scenario: Tests link to a requirement that does not exist in agent.yaml. Should be ignored."""
    req = Requirement(id="REQ-001", description="Real", risk=RiskLevel.HIGH)
    results = [
        # T1 links to phantom requirement
        AssayResult(
            test_id="T1",
            status=AssayStatus.PASS,
            coverage=100.0,
            linked_requirements=["REQ-999"],
            timestamp=datetime.now(),
        ),
        # T2 links to real requirement
        AssayResult(
            test_id="T2",
            status=AssayStatus.PASS,
            coverage=100.0,
            linked_requirements=["REQ-001"],
            timestamp=datetime.now(),
        ),
    ]

    with mock_traceability_context(tmp_path, requirements=[req], assay_results=results) as (yaml_path, report_path):
        with patch("sys.argv", ["scribe", "check", "--agent-yaml", str(yaml_path), "--assay-report", str(report_path)]):
            assert main() == 0

    captured = capsys.readouterr()
    assert "SUCCESS" in captured.out
    assert "[PASS] REQ-001" in captured.out
    assert "REQ-999" not in captured.out
