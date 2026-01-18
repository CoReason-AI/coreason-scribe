# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_scribe

from pathlib import Path
from unittest.mock import patch

from coreason_scribe.main import main


def test_check_malformed_requirements(tmp_path: Path) -> None:
    """Test check command with invalid YAML in requirements file."""
    agent_yaml = tmp_path / "agent.yaml"
    assay_report = tmp_path / "report.json"

    agent_yaml.write_text("invalid: [yaml: content", encoding="utf-8")
    assay_report.write_text("{}", encoding="utf-8")

    # We use run_check directly or main?
    # run_check raises ScribeError. main catches and returns 1.
    # Let's test main to verify full flow.
    with patch("sys.argv", ["scribe", "check", "--agent-yaml", str(agent_yaml), "--assay-report", str(assay_report)]):
        assert main() == 1


def test_check_malformed_report(tmp_path: Path) -> None:
    """Test check command with invalid JSON in assay report."""
    agent_yaml = tmp_path / "agent.yaml"
    assay_report = tmp_path / "report.json"

    agent_yaml.write_text("- id: REQ-1\n  description: test\n  risk: HIGH", encoding="utf-8")
    assay_report.write_text("{invalid json}", encoding="utf-8")

    with patch("sys.argv", ["scribe", "check", "--agent-yaml", str(agent_yaml), "--assay-report", str(assay_report)]):
        assert main() == 1


def test_diff_malformed_artifact(tmp_path: Path) -> None:
    """Test diff command with malformed artifact JSON."""
    current = tmp_path / "current.json"
    previous = tmp_path / "previous.json"

    current.write_text("{bad json}", encoding="utf-8")
    previous.write_text("{}", encoding="utf-8")

    with patch("sys.argv", ["scribe", "diff", str(current), str(previous)]):
        assert main() == 1


def test_check_missing_fields_in_report(tmp_path: Path) -> None:
    """Test assay report with valid JSON but missing required fields (schema violation)."""
    agent_yaml = tmp_path / "agent.yaml"
    assay_report = tmp_path / "report.json"

    agent_yaml.write_text("- id: REQ-1\n  description: test\n  risk: HIGH", encoding="utf-8")
    # Missing 'results' list
    assay_report.write_text('{"id": "rep-1", "timestamp": "2023-01-01T00:00:00"}', encoding="utf-8")

    with patch("sys.argv", ["scribe", "check", "--agent-yaml", str(agent_yaml), "--assay-report", str(assay_report)]):
        assert main() == 1
