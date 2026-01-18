# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason-scribe

import json
from pathlib import Path

import pytest
import yaml

from coreason_scribe.matrix import TraceabilityMatrixBuilder
from coreason_scribe.models import AssayStatus, RiskLevel


@pytest.fixture
def builder() -> TraceabilityMatrixBuilder:
    return TraceabilityMatrixBuilder()


def test_load_requirements_success(builder: TraceabilityMatrixBuilder, tmp_path: Path) -> None:
    # Create valid agent.yaml
    data = [
        {"id": "REQ-001", "description": "Test Req 1", "risk": "HIGH", "source_sop": "SOP-001"},
        {"id": "REQ-002", "description": "Test Req 2", "risk": "LOW"},
    ]
    file_path = tmp_path / "agent.yaml"
    with open(file_path, "w") as f:
        yaml.dump(data, f)

    reqs = builder.load_requirements(file_path)
    assert len(reqs) == 2
    assert reqs[0].id == "REQ-001"
    assert reqs[0].risk == RiskLevel.HIGH
    assert reqs[1].id == "REQ-002"
    assert reqs[1].source_sop is None


def test_load_requirements_file_not_found(builder: TraceabilityMatrixBuilder) -> None:
    with pytest.raises(FileNotFoundError):
        builder.load_requirements(Path("non_existent.yaml"))


def test_load_requirements_invalid_yaml(builder: TraceabilityMatrixBuilder, tmp_path: Path) -> None:
    file_path = tmp_path / "invalid.yaml"
    with open(file_path, "w") as f:
        f.write("key: value: invalid")

    with pytest.raises(ValueError, match="Failed to parse YAML"):
        builder.load_requirements(file_path)


def test_load_requirements_not_a_list(builder: TraceabilityMatrixBuilder, tmp_path: Path) -> None:
    file_path = tmp_path / "dict.yaml"
    with open(file_path, "w") as f:
        yaml.dump({"key": "value"}, f)

    with pytest.raises(ValueError, match="Requirements file must contain a list"):
        builder.load_requirements(file_path)


def test_load_requirements_invalid_schema(builder: TraceabilityMatrixBuilder, tmp_path: Path) -> None:
    data = [{"id": "REQ-001"}]  # Missing required fields
    file_path = tmp_path / "bad_schema.yaml"
    with open(file_path, "w") as f:
        yaml.dump(data, f)

    with pytest.raises(ValueError, match="Invalid requirement schema"):
        builder.load_requirements(file_path)


def test_load_assay_report_success(builder: TraceabilityMatrixBuilder, tmp_path: Path) -> None:
    data = {
        "id": "REPORT-001",
        "timestamp": "2025-01-01T12:00:00",
        "results": [
            {
                "test_id": "TEST-01",
                "status": "PASS",
                "coverage": 100.0,
                "linked_requirements": ["REQ-001"],
                "timestamp": "2025-01-01T12:00:00",
            }
        ],
    }
    file_path = tmp_path / "assay_report.json"
    with open(file_path, "w") as f:
        json.dump(data, f)

    report = builder.load_assay_report(file_path)
    assert report.id == "REPORT-001"
    assert len(report.results) == 1
    assert report.results[0].test_id == "TEST-01"
    assert report.results[0].status == AssayStatus.PASS


def test_load_assay_report_file_not_found(builder: TraceabilityMatrixBuilder) -> None:
    with pytest.raises(FileNotFoundError):
        builder.load_assay_report(Path("non_existent.json"))


def test_load_assay_report_invalid_json(builder: TraceabilityMatrixBuilder, tmp_path: Path) -> None:
    file_path = tmp_path / "invalid.json"
    with open(file_path, "w") as f:
        f.write("{invalid json")

    with pytest.raises(ValueError, match="Failed to parse JSON"):
        builder.load_assay_report(file_path)


def test_load_assay_report_invalid_schema(builder: TraceabilityMatrixBuilder, tmp_path: Path) -> None:
    data = {"id": "REPORT-001"}  # Missing required fields
    file_path = tmp_path / "bad_schema.json"
    with open(file_path, "w") as f:
        json.dump(data, f)

    with pytest.raises(ValueError, match="Invalid assay report schema"):
        builder.load_assay_report(file_path)
