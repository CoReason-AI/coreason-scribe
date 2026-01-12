# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_scribe

from coreason_scribe.inspector import SemanticInspector


def test_inspector_extracts_trace_decorator() -> None:
    source_code = """
from coreason_scribe.decorators import trace

@trace("REQ-001")
def calculate_dose(weight):
    \"\"\"Calculates dose based on weight.\"\"\"
    return weight * 0.5
    """
    inspector = SemanticInspector()
    sections = inspector.inspect_source(source_code, module_name="dose_module")

    assert len(sections) == 1
    section = sections[0]
    assert section.id == "dose_module.calculate_dose"
    assert section.linked_requirements == ["REQ-001"]


def test_inspector_extracts_multiple_trace_requirements() -> None:
    source_code = """
from coreason_scribe.decorators import trace

@trace("REQ-001", "REQ-002")
class SafetyChecker:
    \"\"\"Checks safety constraints.\"\"\"
    pass
    """
    inspector = SemanticInspector()
    sections = inspector.inspect_source(source_code, module_name="safety")

    assert len(sections) == 1
    section = sections[0]
    assert section.id == "safety.SafetyChecker"
    assert section.linked_requirements == ["REQ-001", "REQ-002"]


def test_inspector_ignores_other_decorators() -> None:
    source_code = """
@staticmethod
@trace("REQ-003")
def validate():
    pass
    """
    inspector = SemanticInspector()
    sections = inspector.inspect_source(source_code, module_name="utils")

    assert len(sections) == 1
    section = sections[0]
    assert section.linked_requirements == ["REQ-003"]


def test_inspector_handles_no_trace_decorator() -> None:
    source_code = """
def simple_function():
    pass
    """
    inspector = SemanticInspector()
    sections = inspector.inspect_source(source_code, module_name="simple")

    assert len(sections) == 1
    assert sections[0].linked_requirements == []
