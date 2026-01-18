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


def test_inspector_stacked_decorators() -> None:
    source_code = """
from coreason_scribe.decorators import trace

@trace("REQ-001")
@trace("REQ-002", "REQ-003")
def stacked_demo():
    pass
    """
    inspector = SemanticInspector()
    sections = inspector.inspect_source(source_code, module_name="stacked")

    assert len(sections) == 1
    # We expect all requirements to be collected. Order depends on decorator list order in AST (top-down).
    assert sorted(sections[0].linked_requirements) == ["REQ-001", "REQ-002", "REQ-003"]


def test_inspector_attribute_access() -> None:
    source_code = """
import coreason_scribe.decorators as d

@d.trace("REQ-004")
def attr_demo():
    pass
    """
    inspector = SemanticInspector()
    sections = inspector.inspect_source(source_code, module_name="attr")

    assert len(sections) == 1
    assert sections[0].linked_requirements == ["REQ-004"]


def test_inspector_nested_functions() -> None:
    source_code = """
from coreason_scribe.decorators import trace

@trace("REQ-100")
def outer():
    @trace("REQ-101")
    def inner():
        pass
    """
    inspector = SemanticInspector()
    sections = inspector.inspect_source(source_code, module_name="nest")

    # Should find 'nest.outer' and 'nest.outer.inner' (or just 'nest.inner' depending on visitor logic)
    # The current visitor logic:
    # visit_FunctionDef -> _process_node -> generic_visit -> visit_FunctionDef
    # It builds IDs using `current_class`, but it doesn't track `current_function` stack for naming.
    # So `inner` inside `outer` might just be `nest.inner` or `nest.outer.<locals>.inner`?
    # Let's check the implementation:
    # It doesn't track function nesting in names, only Class nesting.
    # So 'inner' inside 'outer' (if not in a class) will likely just be named 'nest.inner'.
    # This might be an ambiguity in the current simplistic implementation, but we test the current behavior.

    assert len(sections) == 2
    ids = [s.id for s in sections]
    assert "nest.outer" in ids
    assert "nest.inner" in ids

    outer_sec = next(s for s in sections if s.id == "nest.outer")
    inner_sec = next(s for s in sections if s.id == "nest.inner")

    assert outer_sec.linked_requirements == ["REQ-100"]
    assert inner_sec.linked_requirements == ["REQ-101"]


def test_inspector_async_function() -> None:
    source_code = """
from coreason_scribe.decorators import trace

@trace("REQ-200")
async def async_worker():
    pass
    """
    inspector = SemanticInspector()
    sections = inspector.inspect_source(source_code, module_name="async")

    assert len(sections) == 1
    assert sections[0].id == "async.async_worker"
    assert sections[0].linked_requirements == ["REQ-200"]


def test_inspector_mixed_argument_types() -> None:
    source_code = """
from coreason_scribe.decorators import trace

@trace("REQ-300", 123, None, "REQ-301")
def mixed_args():
    pass
    """
    inspector = SemanticInspector()
    sections = inspector.inspect_source(source_code, module_name="mixed")

    assert len(sections) == 1
    # Should only capture the strings
    assert sections[0].linked_requirements == ["REQ-300", "REQ-301"]
