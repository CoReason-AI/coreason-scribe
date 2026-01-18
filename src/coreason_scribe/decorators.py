# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason-scribe

from functools import wraps
from typing import Any, Callable, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def trace(*requirements: str) -> Callable[[F], F]:
    """
    Decorator to link code artifacts (functions/classes) to Requirements.

    Args:
        *requirements: Variable length argument list of Requirement IDs (e.g., "REQ-001", "REQ-002").

    Usage:
        @trace("REQ-001")
        def calculate_dose(weight):
            ...
    """

    def decorator(func: F) -> F:
        # In a real application, we might attach metadata to the function here.
        # For this static analysis tool, the presence of the decorator in the source is enough.
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        # Attach requirements metadata to the wrapper for runtime inspection if needed
        # We use setattr because the wrapper type (from @wraps) is not easily statically known
        # to have arbitrary attributes
        wrapper._linked_requirements = list(requirements)  # type: ignore[attr-defined]
        return wrapper  # type: ignore[return-value]

    return decorator
