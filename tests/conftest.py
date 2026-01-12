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
from typing import Any
from unittest.mock import MagicMock

import pytest


@pytest.hookimpl(tryfirst=True)
def pytest_load_initial_conftests(early_config: Any, parser: Any, args: Any) -> None:
    """
    Mock weasyprint before any tests are collected or imported.
    This prevents OSError when system libraries (pango/cairo) are missing.
    """
    if "weasyprint" not in sys.modules:
        mock_weasyprint = MagicMock()
        mock_weasyprint.HTML = MagicMock()
        sys.modules["weasyprint"] = mock_weasyprint
