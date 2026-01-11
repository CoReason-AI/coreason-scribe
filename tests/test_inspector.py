# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_scribe

import hashlib
import textwrap

import pytest

from coreason_scribe.inspector import SemanticInspector


def test_inspect_simple_function() -> None:
    source = textwrap.dedent("""
        def add(a, b):
            '''Adds two numbers.'''
            return a + b
    """)
    inspector = SemanticInspector()
    sections = inspector.inspect_source(source, "test_module")

    assert len(sections) == 1
    section = sections[0]
    assert section.id == "test_module.add"
    assert section.content == "Adds two numbers."
    assert section.author == "HUMAN"
    assert not section.is_modified

    # Calculate expected hash
    # Note: ast.get_source_segment preserves exact whitespace/newlines from source
    expected_hash = hashlib.sha256(source.strip().encode("utf-8")).hexdigest()
    assert section.linked_code_hash == expected_hash


def test_inspect_class_and_methods() -> None:
    source = textwrap.dedent("""
        class Calculator:
            '''A simple calculator.'''

            def add(self, a, b):
                '''Adds two numbers.'''
                return a + b

            async def subtract(self, a, b):
                return a - b
    """)
    inspector = SemanticInspector()
    sections = inspector.inspect_source(source, "math_lib")

    assert len(sections) == 3

    # Class section
    class_section = next(s for s in sections if s.id == "math_lib.Calculator")
    assert class_section.content == "A simple calculator."

    # Method section
    add_section = next(s for s in sections if s.id == "math_lib.Calculator.add")
    assert add_section.content == "Adds two numbers."

    # Async method section (missing docstring)
    sub_section = next(s for s in sections if s.id == "math_lib.Calculator.subtract")
    assert sub_section.content == "[MISSING DOCUMENTATION]"


def test_inspect_nested_structure() -> None:
    # Not strictly required by prompt but good for robustness
    source = textwrap.dedent("""
        def outer():
            def inner():
                pass
            pass
    """)
    inspector = SemanticInspector()
    sections = inspector.inspect_source(source, "nested")

    # Now we support nested functions
    assert len(sections) == 2
    ids = {s.id for s in sections}
    assert "nested.outer" in ids
    # The inner function name depends on how we handle nesting naming.
    # Currently _handle_function uses node.name.
    # It does NOT properly scope nested functions (it would just be "inner", or "Class.inner" if inside class).
    # Since we reset current_class in visit_ClassDef, but we don't track function scope stack.
    # So it will likely be "nested.inner".

    assert "nested.inner" in ids


def test_missing_docstring_warning(caplog: pytest.LogCaptureFixture) -> None:
    source = "def foo(): pass"
    inspector = SemanticInspector()

    # We need to make sure loguru propogates to caplog
    # pytest-caplog captures logging from 'logging' module, but loguru handles it differently.
    # However, loguru has an 'intercept' handler or we can check stderr.
    # But usually caplog works if loguru is configured to propagate or intercept.
    # The error message shows the log IS in stderr.

    # Let's inspect what is in caplog.
    # The error says "assert ... in ''". So caplog is empty.
    # This means loguru is not propagating to standard logging which caplog captures.

    # Instead of caplog, let's use a custom sink for loguru to verify.
    from loguru import Message

    from coreason_scribe.utils.logger import logger

    messages = []

    def sink(message: Message) -> None:
        messages.append(message.record["message"])

    logger_id = logger.add(sink)
    try:
        inspector.inspect_source(source, "warn_test")
    finally:
        logger.remove(logger_id)

    # The output says "Missing documentation for foo".
    # Wait, the ID generation logic:
    # section_id = f"{self.module_name}.{name}"
    # BUT the logging logic inside _process_node(self, node, name):
    # logger.warning(f"Missing documentation for {name}")
    # 'name' passed to _process_node is "foo" or "Class.foo".
    # It does NOT include module_name.
    # So we should expect "Missing documentation for foo".

    assert any("Missing documentation for foo" in m for m in messages)


def test_hash_change_on_modification() -> None:
    source1 = textwrap.dedent("""
        def process(data):
            '''Process data.'''
            return data * 2
    """)

    source2 = textwrap.dedent("""
        def process(data):
            '''Process data.'''
            return data * 3
    """)

    inspector = SemanticInspector()
    sections1 = inspector.inspect_source(source1, "mod")
    sections2 = inspector.inspect_source(source2, "mod")

    assert sections1[0].id == sections2[0].id
    assert sections1[0].content == sections2[0].content
    assert sections1[0].linked_code_hash != sections2[0].linked_code_hash
