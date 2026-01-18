# coreason-scribe

**The "Compliance Officer in a Box" | Unified GxP Documentation Engine**

[![CI](https://github.com/CoReason-AI/coreason_scribe/actions/workflows/ci.yml/badge.svg)](https://github.com/CoReason-AI/coreason_scribe/actions/workflows/ci.yml)

## Executive Summary

`coreason-scribe` is the GxP documentation automation engine for the CoReason ecosystem. It addresses the "Validation Gap" where documentation inevitably drifts from code.

By treating **Documentation as Code**, `coreason-scribe` parses your agent's logic, uses AI to generate human-readable summaries (System Design Specifications), enforces Risk-Based Traceability (Requirements ↔ Tests), and facilitates a rigorous **"Draft-Review-Sign"** workflow. It ensures that no release is published without a cryptographically signed artifact proving it meets all requirements.

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

## Documentation

- [Usage Guide](docs/usage.md)
- [Product Requirements Document](docs/product_requirements.md)

## Development

This project follows a strict iterative, atomic, test-driven development protocol.

- **Linting:** `poetry run pre-commit run --all-files`
- **Testing:** `poetry run pytest`
