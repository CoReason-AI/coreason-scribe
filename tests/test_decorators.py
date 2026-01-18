# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason-scribe

from coreason_scribe.decorators import trace


def test_trace_decorator_runtime() -> None:
    """Test that the trace decorator works at runtime and preserves function behavior."""

    @trace("REQ-001", "REQ-002")
    def add(a: int, b: int) -> int:
        """Adds two numbers."""
        return a + b

    assert add(1, 2) == 3
    assert add.__name__ == "add"
    assert add.__doc__ == "Adds two numbers."

    # Check that metadata was attached (implementation detail, but good to verify)
    assert hasattr(add, "_linked_requirements")
    assert add._linked_requirements == ["REQ-001", "REQ-002"]


def test_trace_decorator_no_args() -> None:
    """Test that trace works even if no requirements are passed (though weird usage)."""

    @trace()
    def no_op() -> bool:
        return True

    assert no_op() is True
    assert hasattr(no_op, "_linked_requirements")
    assert no_op._linked_requirements == []
