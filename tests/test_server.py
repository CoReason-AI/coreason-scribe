import json
from pathlib import Path
from datetime import datetime, timezone
from fastapi.testclient import TestClient
import pytest
import yaml

from coreason_scribe.server import app

@pytest.fixture
def client():
    with TestClient(app) as c:
        # Patch generate_sds to create a dummy file because weasyprint is mocked and doesn't write files
        original_generate_sds = c.app.state.pdf_generator.generate_sds

        def mock_generate_sds(artifact, output_path):
             # Simulate PDF generation by creating an empty file
             # But wait, st_size == 0 check will fail if empty.
             output_path.write_text("dummy pdf content")

        c.app.state.pdf_generator.generate_sds = mock_generate_sds

        yield c

        c.app.state.pdf_generator.generate_sds = original_generate_sds

@pytest.fixture
def sample_requirements_content():
    return [
        {
            "id": "REQ-001",
            "description": "Must do X",
            "risk": "HIGH",
            "source_sop": "SOP-1"
        },
        {
            "id": "REQ-002",
            "description": "Must do Y",
            "risk": "LOW",
            "source_sop": "SOP-1"
        }
    ]

@pytest.fixture
def sample_assay_report_content():
    return {
        "id": "report-1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "results": [
            {
                "test_id": "test_1",
                "status": "PASS",
                "coverage": 100.0,
                "linked_requirements": ["REQ-001"],
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            {
                "test_id": "test_2",
                "status": "PASS",
                "coverage": 100.0,
                "linked_requirements": ["REQ-002"],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        ]
    }

def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "version": "0.2.0"}

def test_draft_no_files(client):
    response = client.post("/draft", data={"version": "1.0.0"})
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == "1.0.0"
    assert data["sections"] == []

def test_draft_with_files(client, sample_requirements_content, sample_assay_report_content, tmp_path):
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
            "assay_report": ("assay_report.json", f_json, "application/json")
        }
        response = client.post("/draft", data={"version": "1.0.0"}, files=files)

    if response.status_code != 200:
        print(response.json())

    assert response.status_code == 200
    data = response.json()
    assert data["version"] == "1.0.0"

def test_check_pass(client, sample_requirements_content, sample_assay_report_content, tmp_path):
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
            "assay_report": ("assay_report.json", f_json, "application/json")
        }
        response = client.post("/check", files=files)

    if response.status_code != 200:
        print(response.json())

    assert response.status_code == 200
    data = response.json()
    assert data["REQ-001"] == "PASS"
    assert data["REQ-002"] == "PASS"

def test_check_fail_critical_gap(client, sample_requirements_content, sample_assay_report_content, tmp_path):
    # Modify report to introduce a gap in HIGH risk requirement
    content = sample_assay_report_content.copy()
    import copy
    content = copy.deepcopy(sample_assay_report_content)

    content["results"][0]["coverage"] = 50.0 # Partial coverage for REQ-001 (HIGH RISK)

    agent_yaml = tmp_path / "agent.yaml"
    with open(agent_yaml, "w") as f:
        yaml.dump(sample_requirements_content, f)

    assay_report = tmp_path / "assay_report.json"
    with open(assay_report, "w") as f:
        json.dump(content, f)

    with open(agent_yaml, "rb") as f_yaml, open(assay_report, "rb") as f_json:
        files = {
            "agent_yaml": ("agent.yaml", f_yaml, "application/yaml"),
            "assay_report": ("assay_report.json", f_json, "application/json")
        }
        response = client.post("/check", files=files)

    assert response.status_code == 422
    data = response.json()
    assert data["REQ-001"] == "CRITICAL_GAP"

def test_draft_invalid_yaml(client, tmp_path):
    agent_yaml = tmp_path / "agent.yaml"
    agent_yaml.write_text("invalid: yaml: : content")

    with open(agent_yaml, "rb") as f_yaml:
        files = {"agent_yaml": ("agent.yaml", f_yaml, "application/yaml")}
        response = client.post("/draft", data={"version": "1.0.0"}, files=files)

    assert response.status_code == 422
    assert "Invalid agent.yaml" in response.json()["detail"]

def test_check_invalid_json(client, tmp_path):
    agent_yaml = tmp_path / "agent.yaml"
    agent_yaml.write_text("[]") # valid yaml

    assay_report = tmp_path / "assay_report.json"
    assay_report.write_text("{ invalid json }")

    with open(agent_yaml, "rb") as f_yaml, open(assay_report, "rb") as f_json:
        files = {
            "agent_yaml": ("agent.yaml", f_yaml, "application/yaml"),
            "assay_report": ("assay_report.json", f_json, "application/json")
        }
        response = client.post("/check", files=files)

    assert response.status_code == 422
    assert "Invalid input files" in response.json()["detail"]
