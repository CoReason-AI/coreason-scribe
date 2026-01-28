# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason-scribe

import sys
from unittest.mock import MagicMock

# Mock weasyprint before any tests are collected or imported.
# We unconditionally mock it to ensure the real library (which requires system DLLs)
# is never loaded during tests, preventing OSError in CI environments.
mock_weasyprint = MagicMock()
mock_weasyprint.HTML = MagicMock()
sys.modules["weasyprint"] = mock_weasyprint

# Mock coreason-identity
mock_identity = MagicMock()


class MockSecretStr:
    def __init__(self, value: str):
        self._value = value

    def get_secret_value(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return "SecretStr('**********')"


class MockUserContext:
    def __init__(self, user_id: MockSecretStr, roles=None, metadata=None):
        self.user_id = user_id
        self.roles = roles or []
        self.metadata = metadata or {}


mock_identity.models.UserContext = MockUserContext
mock_identity.types.SecretStr = MockSecretStr
sys.modules["coreason_identity"] = mock_identity
sys.modules["coreason_identity.models"] = mock_identity.models
sys.modules["coreason_identity.types"] = mock_identity.types

from contextlib import AbstractContextManager, contextmanager  # noqa: E402
from datetime import datetime  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Callable, Generator, List, Tuple  # noqa: E402
from unittest.mock import patch  # noqa: E402

import pytest  # noqa: E402

from coreason_scribe.models import AssayReport, AssayResult, Requirement  # noqa: E402


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
