# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_scribe

import sys
from unittest.mock import MagicMock

# Mock weasyprint before any tests are collected or imported.
# This prevents OSError when system libraries (pango/cairo) are missing.
# Note: We do this at the very top to ensure it runs before any imports
# from coreason_scribe, which might transitively import weasyprint.
if "weasyprint" not in sys.modules:
    mock_weasyprint = MagicMock()
    # We need to ensure HTML is available on the mock
    mock_weasyprint.HTML = MagicMock()
    sys.modules["weasyprint"] = mock_weasyprint

from contextlib import AbstractContextManager, contextmanager
from datetime import datetime
from pathlib import Path
from typing import Callable, Generator, List, Tuple
from unittest.mock import patch

import pytest

from coreason_scribe.models import AssayReport, AssayResult, Requirement


@pytest.fixture
def mock_traceability_context() -> Callable[
    [Path, List[Requirement], List[AssayResult]], AbstractContextManager[Tuple[Path, Path]]
]:
    """
    Returns a context manager that mocks the TraceabilityMatrixBuilder
    to return specific requirements and assay results.
    """

    @contextmanager
    def _context(
        tmp_path: Path, requirements: List[Requirement], assay_results: List[AssayResult]
    ) -> Generator[Tuple[Path, Path], None, None]:
        agent_yaml = tmp_path / "agent.yaml"
        assay_report_path = tmp_path / "report.json"
        agent_yaml.touch()
        assay_report_path.touch()

        # Create the report object to return
        report = AssayReport(
            id="report-1",
            timestamp=datetime.now(),
            results=assay_results,
        )

        with patch("coreason_scribe.main.TraceabilityMatrixBuilder") as mock_builder_cls:
            mock_builder = mock_builder_cls.return_value
            mock_builder.load_requirements.return_value = requirements
            mock_builder.load_assay_report.return_value = report
            yield agent_yaml, assay_report_path

    return _context
