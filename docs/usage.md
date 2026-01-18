# Usage Guide

Coreason Scribe is a command-line interface (CLI) tool for generating, validating, and signing GxP-compliant documentation.

## Installation

Prerequisites:
- Python 3.12+
- Poetry

To install the dependencies:

```bash
poetry install
```

## CLI Commands

The tool is invoked via the `coreason-scribe` package. If running from source/poetry:

```bash
poetry run python -m coreason_scribe.main <command> [args]
```

### 1. Generating a Draft (`draft`)

Scans your source code, extracts logic summaries (from docstrings or AI), and generates a PDF System Design Specification (SDS).

**Arguments:**
- `--source`: Path to the source code directory (default: current directory).
- `--output`: Directory where artifacts (JSON, PDF) will be saved.
- `--version`: The version string for this release (e.g., "1.0.0").
- `--agent-yaml`: (Optional) Path to `agent.yaml` defining requirements.
- `--assay-report`: (Optional) Path to `assay_report.json` containing test results.

**Example:**

```bash
poetry run python -m coreason_scribe.main draft \
  --source ./src \
  --output ./build \
  --version "1.0.0" \
  --agent-yaml ./agent.yaml \
  --assay-report ./assay_report.json
```

**Output:**
- `build/artifact.json`: The structured data of the draft.
- `build/sds.pdf`: The rendered PDF document.
- `build/traceability.mmd`: (If inputs provided) A Mermaid.js diagram of the traceability matrix.

### 2. Semantic Diff (`diff`)

Compares two draft artifacts (e.g., the current build vs. the last signed release) to detect logical changes.

**Arguments:**
- `current`: Path to the new `artifact.json`.
- `previous`: Path to the previous `artifact.json`.

**Example:**

```bash
poetry run python -m coreason_scribe.main diff \
  ./build/artifact.json \
  ./releases/v1.0.0/artifact.json
```

**Output:**
- Prints a "Semantic Delta Report" to the console, highlighting logic changes, text changes, and verification drifts.

### 3. Compliance Check (`check`)

A CI/CD gate that verifies all requirements have sufficient test coverage based on their risk level.

**Arguments:**
- `--agent-yaml`: Path to `agent.yaml` defining requirements.
- `--assay-report`: Path to `assay_report.json` containing test results.

**Example:**

```bash
poetry run python -m coreason_scribe.main check \
  --agent-yaml ./agent.yaml \
  --assay-report ./assay_report.json
```

**Output:**
- Exits with status code `0` if all checks pass.
- Exits with status code `1` if critical gaps (e.g., High Risk requirement with <100% coverage) are found.

## Example Configuration Files

### `agent.yaml`

```yaml
- id: "REQ-001"
  description: "The system must validate user input."
  risk: "HIGH"
  source_sop: "SOP-101"
```

### `assay_report.json`

```json
{
  "id": "report-001",
  "timestamp": "2023-10-27T10:00:00Z",
  "results": [
    {
      "test_id": "test_input_validation",
      "status": "PASS",
      "coverage": 100.0,
      "linked_requirements": ["REQ-001"],
      "timestamp": "2023-10-27T09:55:00Z"
    }
  ]
}
```
