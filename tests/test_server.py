import json
from datetime import datetime, timezone
from typing import Any, Dict, Generator, List, cast
from unittest.mock import MagicMock

import pytest
import yaml
from fastapi import FastAPI
from fastapi.testclient import TestClient

from coreason_scribe.server import app


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        # Patch generate_sds to create a dummy file because weasyprint is mocked and doesn't write files
        fastapi_app = cast(FastAPI, c.app)
        original_generate_sds = fastapi_app.state.pdf_generator.generate_sds

        def mock_generate_sds(artifact: Any, output_path: Any) -> None:
            # Simulate PDF generation by creating an empty file
            # But wait, st_size == 0 check will fail if empty.
            output_path.write_text("dummy pdf content")

        fastapi_app.state.pdf_generator.generate_sds = mock_generate_sds

        yield c

        fastapi_app.state.pdf_generator.generate_sds = original_generate_sds


@pytest.fixture
def sample_requirements_content() -> List[Dict[str, Any]]:
    return [
        {"id": "REQ-001", "description": "Must do X", "risk": "HIGH", "source_sop": "SOP-1"},
        {"id": "REQ-002", "description": "Must do Y", "risk": "LOW", "source_sop": "SOP-1"},
    ]


@pytest.fixture
def sample_assay_report_content() -> Dict[str, Any]:
    return {
        "id": "report-1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "results": [
            {
                "test_id": "test_1",
                "status": "PASS",
                "coverage": 100.0,
                "linked_requirements": ["REQ-001"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            {
                "test_id": "test_2",
                "status": "PASS",
                "coverage": 100.0,
                "linked_requirements": ["REQ-002"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        ],
    }


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "version": "0.4.0"}


def test_draft_no_files(client: TestClient) -> None:
    response = client.post("/draft", data={"version": "1.0.0"})
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == "1.0.0"
    assert data["sections"] == []


def test_draft_with_files(
    client: TestClient,
    sample_requirements_content: List[Dict[str, Any]],
    sample_assay_report_content: Dict[str, Any],
    tmp_path: Any,
) -> None:
    # Prepare files
    agent_yaml = tmp_path / "agent.yaml"
    with open(agent_yaml, "w") as f:
        yaml.dump(sample_requirements_content, f)

    assay_report = tmp_path / "assay_report.json"
    with open(assay_report, "w") as f:
        json.dump(sample_assay_report_content, f)

    with open(agent_yaml, "rb") as f_yaml, open(assay_report, "rb") as f_json:
        files = {
            "agent_yaml": ("agent.yaml", f_yaml, "application/yaml"),
            "assay_report": ("assay_report.json", f_json, "application/json"),
        }
        response = client.post("/draft", data={"version": "1.0.0"}, files=files)

    if response.status_code != 200:
        print(response.json())

    assert response.status_code == 200
    data = response.json()
    assert data["version"] == "1.0.0"


def test_check_pass(
    client: TestClient,
    sample_requirements_content: List[Dict[str, Any]],
    sample_assay_report_content: Dict[str, Any],
    tmp_path: Any,
) -> None:
    # Prepare files
    agent_yaml = tmp_path / "agent.yaml"
    with open(agent_yaml, "w") as f:
        yaml.dump(sample_requirements_content, f)

    assay_report = tmp_path / "assay_report.json"
    with open(assay_report, "w") as f:
        json.dump(sample_assay_report_content, f)

    with open(agent_yaml, "rb") as f_yaml, open(assay_report, "rb") as f_json:
        files = {
            "agent_yaml": ("agent.yaml", f_yaml, "application/yaml"),
            "assay_report": ("assay_report.json", f_json, "application/json"),
        }
        response = client.post("/check", files=files)

    if response.status_code != 200:
        print(response.json())

    assert response.status_code == 200
    data = response.json()
    assert data["REQ-001"] == "PASS"
    assert data["REQ-002"] == "PASS"


def test_check_fail_critical_gap(
    client: TestClient,
    sample_requirements_content: List[Dict[str, Any]],
    sample_assay_report_content: Dict[str, Any],
    tmp_path: Any,
) -> None:
    # Modify report to introduce a gap in HIGH risk requirement
    import copy

    content = copy.deepcopy(sample_assay_report_content)

    content["results"][0]["coverage"] = 50.0  # Partial coverage for REQ-001 (HIGH RISK)

    agent_yaml = tmp_path / "agent.yaml"
    with open(agent_yaml, "w") as f:
        yaml.dump(sample_requirements_content, f)

    assay_report = tmp_path / "assay_report.json"
    with open(assay_report, "w") as f:
        json.dump(content, f)

    with open(agent_yaml, "rb") as f_yaml, open(assay_report, "rb") as f_json:
        files = {
            "agent_yaml": ("agent.yaml", f_yaml, "application/yaml"),
            "assay_report": ("assay_report.json", f_json, "application/json"),
        }
        response = client.post("/check", files=files)

    assert response.status_code == 422
    data = response.json()
    assert data["REQ-001"] == "CRITICAL_GAP"


def test_draft_invalid_yaml(client: TestClient, tmp_path: Any) -> None:
    agent_yaml = tmp_path / "agent.yaml"
    agent_yaml.write_text("invalid: yaml: : content")

    with open(agent_yaml, "rb") as f_yaml:
        files = {"agent_yaml": ("agent.yaml", f_yaml, "application/yaml")}
        response = client.post("/draft", data={"version": "1.0.0"}, files=files)

    assert response.status_code == 422
    assert "Invalid agent.yaml" in response.json()["detail"]


def test_check_invalid_json(client: TestClient, tmp_path: Any) -> None:
    agent_yaml = tmp_path / "agent.yaml"
    agent_yaml.write_text("[]")  # valid yaml

    assay_report = tmp_path / "assay_report.json"
    assay_report.write_text("{ invalid json }")

    with open(agent_yaml, "rb") as f_yaml, open(assay_report, "rb") as f_json:
        files = {
            "agent_yaml": ("agent.yaml", f_yaml, "application/yaml"),
            "assay_report": ("assay_report.json", f_json, "application/json"),
        }
        response = client.post("/check", files=files)

    assert response.status_code == 422
    assert "Invalid input files" in response.json()["detail"]


def test_draft_pdf_generation_failure(client: TestClient) -> None:
    fastapi_app = cast(FastAPI, client.app)
    # Mock PDF generator to raise exception
    fastapi_app.state.pdf_generator.generate_sds = MagicMock(side_effect=Exception("PDF Error"))

    response = client.post("/draft", data={"version": "1.0.0"})
    assert response.status_code == 500
    assert "Failed to generate PDF" in response.json()["detail"]


def test_draft_pdf_empty_failure(client: TestClient) -> None:
    fastapi_app = cast(FastAPI, client.app)

    # Mock generation that produces empty file (or doesn't produce one)
    # The default mock in fixture produces "dummy pdf content".
    # We override it here to produce nothing.
    def mock_empty_generate(artifact: Any, output_path: Any) -> None:
        pass # Do nothing, file remains non-existent
        # Or create empty file
        output_path.touch()

    fastapi_app.state.pdf_generator.generate_sds = mock_empty_generate

    response = client.post("/draft", data={"version": "1.0.0"})
    assert response.status_code == 500
    assert "PDF file was not created or is empty" in response.json()["detail"]


def test_check_compliance_evaluation_failure(client: TestClient, tmp_path: Any) -> None:
    # Mock compliance engine to raise exception
    fastapi_app = cast(FastAPI, client.app)

    # We need to mock the evaluate_compliance method
    # Since matrix_builder is instantiated in lifespan, we access it via state
    fastapi_app.state.matrix_builder.compliance_engine.evaluate_compliance = MagicMock(
        side_effect=Exception("Engine Error")
    )

    agent_yaml = tmp_path / "agent.yaml"
    agent_yaml.write_text("[]")

    assay_report = tmp_path / "assay_report.json"
    assay_report.write_text("{}") # Minimal valid JSON for load_assay_report to pass or fail gracefully

    # Note: load_assay_report might fail on empty dict, so let's provide minimal valid structure
    assay_report.write_text('{"id": "1", "timestamp": "2023-01-01T00:00:00Z", "results": []}')

    with open(agent_yaml, "rb") as f_yaml, open(assay_report, "rb") as f_json:
        files = {
            "agent_yaml": ("agent.yaml", f_yaml, "application/yaml"),
            "assay_report": ("assay_report.json", f_json, "application/json"),
        }
        response = client.post("/check", files=files)

    assert response.status_code == 500
    assert "Compliance evaluation failed" in response.json()["detail"]


def test_draft_assay_report_generic_exception(
    client: TestClient,
    sample_requirements_content: List[Dict[str, Any]],
    tmp_path: Any,
) -> None:
    # Force generic exception during assay report loading in draft endpoint
    fastapi_app = cast(FastAPI, client.app)
    fastapi_app.state.matrix_builder.load_assay_report = MagicMock(side_effect=Exception("Generic Load Error"))

    agent_yaml = tmp_path / "agent.yaml"
    with open(agent_yaml, "w") as f:
        yaml.dump(sample_requirements_content, f)

    assay_report = tmp_path / "assay_report.json"
    assay_report.write_text("{}")

    with open(agent_yaml, "rb") as f_yaml, open(assay_report, "rb") as f_json:
        files = {
            "agent_yaml": ("agent.yaml", f_yaml, "application/yaml"),
            "assay_report": ("assay_report.json", f_json, "application/json"),
        }
        response = client.post("/draft", data={"version": "1.0.0"}, files=files)

    assert response.status_code == 422
    assert "Invalid assay_report.json" in response.json()["detail"]
