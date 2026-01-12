# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_scribe

import ast
import hashlib
from typing import List, Literal, Optional

from coreason_scribe.models import DraftSection
from coreason_scribe.utils.logger import logger


class SemanticInspector:
    """
    Analyzes Python source code to extract semantic information and generate draft documentation sections.
    """

    def inspect_source(self, source_code: str, module_name: str = "unknown") -> List[DraftSection]:
        """
        Parses the source code and extracts draft sections for classes and functions.

        Args:
            source_code: The Python source code to analyze.
            module_name: The name of the module being analyzed (used for ID generation).

        Returns:
            A list of DraftSection objects representing the code constructs.
        """
        tree = ast.parse(source_code)
        inspector = _InspectorVisitor(source_code, module_name)
        inspector.visit(tree)
        return inspector.sections


class _InspectorVisitor(ast.NodeVisitor):
    def __init__(self, source_code: str, module_name: str):
        self.source_code = source_code
        self.module_name = module_name
        self.sections: List[DraftSection] = []
        self.current_class: Optional[str] = None

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        old_class = self.current_class
        self.current_class = node.name
        self._process_node(node, node.name)
        self.generic_visit(node)
        self.current_class = old_class

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._handle_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._handle_function(node)

    def _handle_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        name = node.name
        if self.current_class:
            name = f"{self.current_class}.{name}"
        self._process_node(node, name)
        # Continue visiting children (e.g. nested functions)
        self.generic_visit(node)

    def _process_node(self, node: ast.AST, name: str) -> None:
        docstring = ast.get_docstring(node)  # type: ignore
        if docstring:
            content = docstring
        else:
            content = "[MISSING DOCUMENTATION]"
            logger.warning(f"Missing documentation for {name}")

        segment = ast.get_source_segment(self.source_code, node)
        if segment is None:
            segment = ""

        code_hash = hashlib.sha256(segment.encode("utf-8")).hexdigest()

        section_id = f"{self.module_name}.{name}"

        # In a real implementation, we would call coreason-arbitrage here.
        # Since we are falling back to docstrings (which are written by humans),
        # we mark the author as HUMAN.
        author_type: Literal["AI", "HUMAN"] = "HUMAN" if docstring else "AI"

        self.sections.append(
            DraftSection(
                id=section_id,
                content=content,
                author=author_type,
                is_modified=False,
                linked_code_hash=code_hash,
            )
        )
