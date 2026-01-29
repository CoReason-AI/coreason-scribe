# Requirements

Coreason Scribe is a Python-based application designed to run on modern Linux, macOS, or Windows environments.

## System Prerequisites

*   **Operating System**: Linux (Ubuntu 22.04+ recommended), macOS, or Windows (via WSL2).
*   **Python**: Version 3.12 or higher.
*   **Package Manager**: [Poetry](https://python-poetry.org/) (recommended) or pip.
*   **Git**: Required for version detection and semantic delta analysis.
*   **Docker** (Optional): For containerized deployment (Microservice mode).

## Core Dependencies

The application relies on the following key Python libraries:

*   **Web Framework (Server Mode)**:
    *   `fastapi` (>=0.115.0): For the REST API.
    *   `uvicorn` (>=0.34.0): ASGI server.
    *   `python-multipart` (>=0.0.20): For file upload support.

*   **Documentation & PDF Generation**:
    *   `weasyprint` (>=68.0): For rendering HTML/CSS to PDF.
    *   `jinja2` (>=3.1.6): For templating.

*   **Data Validation & Parsing**:
    *   `pydantic` (>=2.12.5): Data validation and settings management.
    *   `pyyaml` (>=6.0.3): parsing YAML configuration files.

*   **Utilities**:
    *   `loguru` (>=0.7.2): Enhanced logging.
    *   `gitpython` (>=3.1.46): Git repository interaction.
    *   `coreason-identity` (>=0.4.2): Identity and signature management (Private).

*   **Async & Networking**:
    *   `anyio` (>=4.12.1)
    *   `httpx` (>=0.28.1)

For a complete and exact list of locked dependencies, refer to `poetry.lock`.
