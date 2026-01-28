# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason-scribe

import ast
import hashlib
import re
from pathlib import Path
from typing import List, Literal, Optional

from coreason_identity.models import UserContext

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
        self.req_pattern = re.compile(r"^REQ-\d+$")

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

    def _extract_requirements(self, node: ast.AST) -> List[str]:
        requirements: List[str] = []
        # Safe access to decorator_list (only present on FunctionDef/ClassDef)
        decorator_list = getattr(node, "decorator_list", [])

        for decorator in decorator_list:
            # Handle @trace("REQ-001")
            if isinstance(decorator, ast.Call):
                func = decorator.func
                is_trace = False

                if isinstance(func, ast.Name) and func.id == "trace":
                    is_trace = True
                elif isinstance(func, ast.Attribute) and func.attr == "trace":
                    is_trace = True

                if is_trace:
                    for arg in decorator.args:
                        # Only accept string constants
                        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                            req_id = arg.value
                            if self.req_pattern.match(req_id):
                                requirements.append(req_id)
                            else:
                                logger.warning(f"Invalid Requirement ID format found: {req_id}. Expected 'REQ-\\d+'.")
                        # Explicitly ignore other types (non-strings) or non-constant nodes
                        # (e.g., variables passed to @trace are not supported by static analysis)

        return requirements

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

        linked_reqs = self._extract_requirements(node)

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
                linked_requirements=linked_reqs,
                linked_code_hash=code_hash,
            )
        )


class ScribeInspector:
    """
    Handles identity-aware document inspection.
    """

    def inspect_pdf(self, pdf_path: Path, context: UserContext) -> dict:
        """
        Inspects a PDF document's metadata and signatures.

        Args:
            pdf_path: Path to the PDF file.
            context: The identity context of the inspector.

        Returns:
            A dictionary containing metadata.
        """
        if context is None:
            raise ValueError("UserContext is required.")

        logger.info(
            "Inspecting document metadata",
            user_id=context.user_id.get_secret_value(),
            document=str(pdf_path),
        )

        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        # Placeholder for actual inspection logic.
        # This implementation currently only performs identity validation and logging.
        # Future work: Extract metadata and signatures from the PDF using a library.
        return {}
