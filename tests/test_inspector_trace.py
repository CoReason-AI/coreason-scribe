# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason-scribe

from coreason_scribe.inspector import SemanticInspector
from coreason_scribe.utils.logger import logger


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


def test_inspector_ignores_invalid_requirement_ids() -> None:
    """Test that invalid requirement IDs (not matching REQ-[\\w-]+) are ignored and logged."""
    source_code = """
@trace("INVALID-01", "REQ-001", "REQ-!BAD", "REQ-99")
def bad_reqs():
    pass
    """

    # Capture logs using a custom sink
    messages = []
    sink_id = logger.add(lambda msg: messages.append(msg))

    try:
        inspector = SemanticInspector()
        sections = inspector.inspect_source(source_code, module_name="bad")

        assert len(sections) == 1
        # Only valid ones REQ-001 and REQ-99 should remain
        assert sections[0].linked_requirements == ["REQ-001", "REQ-99"]

        # Verify logs
        log_text = "".join([str(m) for m in messages])
        assert "Invalid Requirement ID format found: INVALID-01" in log_text
        assert "Invalid Requirement ID format found: REQ-!BAD" in log_text
    finally:
        logger.remove(sink_id)


def test_inspector_ignores_non_string_arguments() -> None:
    """Test that non-string arguments (e.g., ints, vars) are safely ignored."""
    source_code = """
CONST_REQ = "REQ-002"

@trace("REQ-001", 123, CONST_REQ)
def mixed_args():
    pass
    """
    inspector = SemanticInspector()
    sections = inspector.inspect_source(source_code, module_name="mixed")

    assert len(sections) == 1
    # Only the explicit string literal "REQ-001" is captured.
    # 123 is not a string. CONST_REQ is an ast.Name, not ast.Constant (string), so it's ignored.
    assert sections[0].linked_requirements == ["REQ-001"]


def test_inspector_separates_class_and_method_reqs() -> None:
    """Test that requirements on a class are not inherited by its methods."""
    source_code = """
@trace("REQ-100")
class MyClass:
    @trace("REQ-200")
    def my_method(self):
        pass
    """
    inspector = SemanticInspector()
    sections = inspector.inspect_source(source_code, module_name="oop")

    assert len(sections) == 2
    class_sec = next(s for s in sections if s.id == "oop.MyClass")
    method_sec = next(s for s in sections if s.id == "oop.MyClass.my_method")

    assert class_sec.linked_requirements == ["REQ-100"]
    assert method_sec.linked_requirements == ["REQ-200"]
