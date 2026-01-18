# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_scribe

import json
from pathlib import Path

import pytest
import yaml

from coreason_scribe.matrix import TraceabilityMatrixBuilder


@pytest.fixture
def builder() -> TraceabilityMatrixBuilder:
    return TraceabilityMatrixBuilder()


def test_load_requirements_empty_list(builder: TraceabilityMatrixBuilder, tmp_path: Path) -> None:
    file_path = tmp_path / "empty.yaml"
    with open(file_path, "w") as f:
        yaml.dump([], f)

    reqs = builder.load_requirements(file_path)
    assert reqs == []


def test_load_requirements_unicode(builder: TraceabilityMatrixBuilder, tmp_path: Path) -> None:
    data = [{"id": "REQ-emoji", "description": "Handles unicode: 🚀 你好", "risk": "LOW"}]
    file_path = tmp_path / "unicode.yaml"
    with open(file_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f)

    reqs = builder.load_requirements(file_path)
    assert reqs[0].id == "REQ-emoji"
    assert reqs[0].description == "Handles unicode: 🚀 你好"


def test_load_assay_report_empty_results(builder: TraceabilityMatrixBuilder, tmp_path: Path) -> None:
    data = {"id": "REPORT-EMPTY", "timestamp": "2025-01-01T12:00:00", "results": []}
    file_path = tmp_path / "empty_results.json"
    with open(file_path, "w") as f:
        json.dump(data, f)

    report = builder.load_assay_report(file_path)
    assert report.id == "REPORT-EMPTY"
    assert report.results == []


def test_load_assay_report_complex_links(builder: TraceabilityMatrixBuilder, tmp_path: Path) -> None:
    data = {
        "id": "REPORT-COMPLEX",
        "timestamp": "2025-01-01T12:00:00",
        "results": [
            {
                "test_id": "TEST-MANY",
                "status": "PASS",
                "coverage": 95.5,
                "linked_requirements": ["REQ-001", "REQ-002", "REQ-003"],
                "timestamp": "2025-01-01T12:00:00",
            },
            {
                "test_id": "TEST-NONE",
                "status": "SKIPPED",
                "coverage": 0.0,
                "linked_requirements": [],
                "timestamp": "2025-01-01T12:00:00",
            },
        ],
    }
    file_path = tmp_path / "complex.json"
    with open(file_path, "w") as f:
        json.dump(data, f)

    report = builder.load_assay_report(file_path)
    assert len(report.results) == 2
    assert len(report.results[0].linked_requirements) == 3
    assert report.results[1].linked_requirements == []


def test_assay_coverage_boundaries(builder: TraceabilityMatrixBuilder, tmp_path: Path) -> None:
    # Test 0.0 and 100.0 (Valid)
    data_valid = {
        "id": "REPORT-BOUNDARIES",
        "timestamp": "2025-01-01T12:00:00",
        "results": [
            {
                "test_id": "TEST-ZERO",
                "status": "FAIL",
                "coverage": 0.0,
                "linked_requirements": [],
                "timestamp": "2025-01-01T12:00:00",
            },
            {
                "test_id": "TEST-FULL",
                "status": "PASS",
                "coverage": 100.0,
                "linked_requirements": [],
                "timestamp": "2025-01-01T12:00:00",
            },
        ],
    }
    file_path = tmp_path / "valid_boundaries.json"
    with open(file_path, "w") as f:
        json.dump(data_valid, f)

    report = builder.load_assay_report(file_path)
    assert report.results[0].coverage == 0.0
    assert report.results[1].coverage == 100.0


def test_assay_coverage_invalid_negative(builder: TraceabilityMatrixBuilder, tmp_path: Path) -> None:
    data = {
        "id": "REPORT-NEG",
        "timestamp": "2025-01-01T12:00:00",
        "results": [
            {
                "test_id": "TEST-NEG",
                "status": "FAIL",
                "coverage": -0.1,
                "linked_requirements": [],
                "timestamp": "2025-01-01T12:00:00",
            }
        ],
    }
    file_path = tmp_path / "invalid_neg.json"
    with open(file_path, "w") as f:
        json.dump(data, f)

    with pytest.raises(ValueError, match="Invalid assay report schema"):
        builder.load_assay_report(file_path)


def test_assay_coverage_invalid_over_hundred(builder: TraceabilityMatrixBuilder, tmp_path: Path) -> None:
    data = {
        "id": "REPORT-OVER",
        "timestamp": "2025-01-01T12:00:00",
        "results": [
            {
                "test_id": "TEST-OVER",
                "status": "PASS",
                "coverage": 100.1,
                "linked_requirements": [],
                "timestamp": "2025-01-01T12:00:00",
            }
        ],
    }
    file_path = tmp_path / "invalid_over.json"
    with open(file_path, "w") as f:
        json.dump(data, f)

    with pytest.raises(ValueError, match="Invalid assay report schema"):
        builder.load_assay_report(file_path)


def test_assay_invalid_timestamp(builder: TraceabilityMatrixBuilder, tmp_path: Path) -> None:
    data = {"id": "REPORT-BAD-TIME", "timestamp": "not-a-timestamp", "results": []}
    file_path = tmp_path / "bad_time.json"
    with open(file_path, "w") as f:
        json.dump(data, f)

    with pytest.raises(ValueError, match="Invalid assay report schema"):
        builder.load_assay_report(file_path)
