import ast
import hashlib

from coreason_scribe.inspector import _InspectorVisitor


def test_inspect_node_without_segment() -> None:
    # This test is tricky because ast.parse usually populates positions.
    # We can manually create a node without source info to hit the edge case,
    # but the inspector uses ast.parse internally.
    # To hit line 72 (segment is None), we need ast.get_source_segment to return None.
    # This happens if the node lacks lineno/end_lineno info.

    # We can't easily force ast.parse to do this, but we can verify that the code handles it
    # if we mock the tree or monkeypatch?
    # Or we can construct a case where source segment is not found.
    # Actually, if we subclass SemanticInspector and override, or just pass a crafted tree?
    # But inspect_source takes string and parses it.

    # Let's try to hit it by modifying the tree after parse but before visit?
    # We can access the visitor directly.

    code = "def foo(): pass"
    visitor = _InspectorVisitor(code, "test")

    # Create a dummy node without location info
    # Adding type_params=[] to satisfy 3.12 AST node requirement
    # We use args as keyword arguments to avoid call-overload issues if possible
    node = ast.FunctionDef(
        name="foo",
        args=ast.arguments(posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[], defaults=[]),
        body=[ast.Pass()],
        decorator_list=[],
        type_params=[],
    )
    # Ensure it has no line numbers which causes get_source_segment to return None

    # We can just construct it and delete lineno attributes if they exist
    for attr in ["lineno", "end_lineno", "col_offset", "end_col_offset"]:
        try:
            delattr(node, attr)
        except AttributeError:
            pass

    # Also need to make sure it doesn't have them set via constructor defaults if any

    visitor.visit(node)

    assert len(visitor.sections) == 1
    assert visitor.sections[0].linked_code_hash == hashlib.sha256(b"").hexdigest()
