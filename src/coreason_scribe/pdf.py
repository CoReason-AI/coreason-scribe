# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason-scribe

from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

from coreason_identity.models import UserContext
from coreason_scribe.models import DraftArtifact
from coreason_scribe.utils.logger import logger


class PDFGenerator:
    """
    Generates PDF documents from DraftArtifacts using Jinja2 templates and WeasyPrint.
    """

    def __init__(self, template_dir: Optional[Path] = None):
        if template_dir is None:
            # Default to the templates directory within the package
            template_dir = Path(__file__).parent / "templates"

        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)), autoescape=select_autoescape(["html", "xml"])
        )
        self.template_dir = template_dir

    def generate_sds(self, artifact: DraftArtifact, output_path: Path, user_context: UserContext) -> None:
        """
        Generates the System Design Specification (SDS) PDF.

        Args:
            artifact: The draft artifact to render.
            output_path: The path to save the generated PDF.
            user_context: The user context for attribution.
        """
        logger.info(f"Generating SDS for version {artifact.version}...")

        template = self.env.get_template("sds.html")
        html_content = template.render(artifact=artifact, user_context=user_context)

        # We need to resolve relative paths (like style.css) relative to the template directory
        HTML(string=html_content, base_url=str(self.template_dir)).write_pdf(output_path)

        logger.info(f"SDS generated at {output_path}")
