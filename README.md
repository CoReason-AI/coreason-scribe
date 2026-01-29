# coreason-scribe

**The "Compliance Officer in a Box" | Unified GxP Documentation Engine**

[![CI/CD](https://github.com/CoReason-AI/coreason-scribe/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/CoReason-AI/coreason-scribe/actions/workflows/ci-cd.yml)
[![codecov](https://codecov.io/gh/CoReason-AI/coreason-scribe/graph/badge.svg)](https://codecov.io/gh/CoReason-AI/coreason-scribe)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)
[![Poetry](https://img.shields.io/endpoint?url=https://python-poetry.org/badge/v0.json)](https://python-poetry.org/)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)](LICENSE)

## Executive Summary

`coreason-scribe` is the GxP documentation automation engine for the CoReason ecosystem. It addresses the "Validation Gap" where documentation inevitably drifts from code.

By treating **Documentation as Code**, `coreason-scribe` parses your agent's logic, uses AI to generate human-readable summaries (System Design Specifications), enforces Risk-Based Traceability (Requirements ↔ Tests), and facilitates a rigorous **"Draft-Review-Sign"** workflow. It ensures that no release is published without a cryptographically signed artifact proving it meets all requirements.

`coreason-scribe` can operate as a local CLI tool for developers or as a **Compliance Microservice** (FastAPI) integrated into CI/CD pipelines (e.g., `coreason-publisher`) and review platforms (`coreason-foundry`).

## Core Philosophy: "Code is Truth. AI Drafts. Humans Ratify. Diffs Reveal Risk."

1.  **AI as the Drafter:** Scans Python AST and generates plain-English business logic summaries.
2.  **Risk-Based Traceability:** Enforces 100% test coverage for High Risk features.
3.  **Semantic Delta:** Surfaces logical drift between versions, not just line-by-line diffs.
4.  **21 CFR Part 11 Signatures:** Requires cryptographic signatures for release certification.

## Getting Started

### Prerequisites

- Python 3.12+
- Poetry

### Installation

```bash
poetry install
```

### Basic Usage

Generate a draft SDS from your source code:

```bash
poetry run python -m coreason_scribe.main draft \
  --source ./src \
  --output ./build \
  --version "0.1.0"
```

Run a compliance check (CI/CD Gate):

```bash
poetry run python -m coreason_scribe.main check \
  --agent-yaml ./agent.yaml \
  --assay-report ./assay_report.json
```

For detailed instructions, see the [Usage Guide](docs/usage.md).

### Server Mode (Microservice)

Start the REST API server:

```bash
poetry run uvicorn coreason_scribe.server:app --port 8001
# OR
docker run -p 8001:8001 coreason-scribe:latest
```

## Documentation

- [Requirements](docs/requirements.md)
- [Usage Guide](docs/usage.md)
- [Product Requirements Document](docs/product_requirements.md)

## Development

This project follows a strict iterative, atomic, test-driven development protocol.

- **Linting:** `poetry run pre-commit run --all-files`
- **Testing:** `poetry run pytest`
