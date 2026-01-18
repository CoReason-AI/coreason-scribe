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


def test_inspector_mega_scenario_complex_class_structure() -> None:
    """
    Test a complex scenario involving:
    - Class with async methods and properties.
    - Nested functions.
    - Duplicate requirement IDs.
    - Mixed valid/invalid IDs.
    """
    source_code = """
from coreason_scribe.decorators import trace

@trace("REQ-001")
class MegaController:
    \"\"\"A complex controller.\"\"\"

    @trace("REQ-002", "REQ-002")  # Duplicate
    def __init__(self):
        pass

    @property
    @trace("REQ-003", "BAD-ID")
    def status(self):
        return "active"

    @trace("REQ-004")
    async def process_async(self):
        @trace("REQ-005")
        def inner_helper():
            pass
        pass

    @staticmethod
    @trace("REQ-006")
    def static_util():
        pass
    """
    inspector = SemanticInspector()
    sections = inspector.inspect_source(source_code, module_name="mega")

    # Expected Sections:
    # 1. mega.MegaController
    # 2. mega.MegaController.__init__
    # 3. mega.MegaController.status
    # 4. mega.MegaController.process_async
    # 5. mega.MegaController.inner_helper (Note: current visitor logic flattens nested functions
    #    to module level naming if not careful, or nests them under class if visited while class is current.
    #    Let's recall the visitor:
    #    visit_FunctionDef sets name = f"{current_class}.{name}" if current_class else name.
    #    It does NOT update current_class for nested functions.
    #    So `inner_helper` inside `process_async` inside `MegaController` will be named `MegaController.inner_helper`.
    #    This is slightly ambiguous but is the current behavior.
    # 6. mega.MegaController.static_util

    assert len(sections) == 6

    sec_map = {s.id: s for s in sections}

    # Class
    assert sec_map["mega.MegaController"].linked_requirements == ["REQ-001"]

    # Init (Duplicates preserved)
    assert sec_map["mega.MegaController.__init__"].linked_requirements == ["REQ-002", "REQ-002"]

    # Property (BAD-ID filtered)
    assert sec_map["mega.MegaController.status"].linked_requirements == ["REQ-003"]

    # Async
    assert sec_map["mega.MegaController.process_async"].linked_requirements == ["REQ-004"]

    # Nested (Naming limitation noted: it appears as method of class)
    assert sec_map["mega.MegaController.inner_helper"].linked_requirements == ["REQ-005"]

    # Static
    assert sec_map["mega.MegaController.static_util"].linked_requirements == ["REQ-006"]


def test_inspector_whitespace_strictness() -> None:
    """Test that IDs with leading/trailing whitespace are strictly rejected."""
    source_code = """
@trace(" REQ-001", "REQ-002 ", "REQ- 003")
def loose_formatting():
    pass
    """
    inspector = SemanticInspector()
    sections = inspector.inspect_source(source_code, module_name="strict")

    # All should be rejected by ^REQ-\d+$
    assert sections[0].linked_requirements == []


def test_inspector_multiple_classes_same_file() -> None:
    """Test multiple classes in one file do not bleed context."""
    source_code = """
@trace("REQ-100")
class ClassA:
    @trace("REQ-101")
    def method_a(self): pass

@trace("REQ-200")
class ClassB:
    @trace("REQ-201")
    def method_b(self): pass
    """
    inspector = SemanticInspector()
    sections = inspector.inspect_source(source_code, module_name="multi")

    sec_map = {s.id: s for s in sections}

    assert sec_map["multi.ClassA"].linked_requirements == ["REQ-100"]
    assert sec_map["multi.ClassA.method_a"].linked_requirements == ["REQ-101"]

    assert sec_map["multi.ClassB"].linked_requirements == ["REQ-200"]
    assert sec_map["multi.ClassB.method_b"].linked_requirements == ["REQ-201"]
