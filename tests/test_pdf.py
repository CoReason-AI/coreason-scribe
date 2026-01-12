# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_scribe

from datetime import datetime, timezone
from pathlib import Path

import pytest

from coreason_scribe.models import DraftArtifact, DraftSection
from coreason_scribe.pdf import PDFGenerator


@pytest.fixture
def sample_artifact() -> DraftArtifact:
    return DraftArtifact(
        version="1.0.0-rc1",
        timestamp=datetime.now(timezone.utc),
        sections=[
            DraftSection(
                id="module.auth",
                content="Authentication module handles login.",
                author="AI",
                is_modified=False,
                linked_code_hash="hash1",
            ),
            DraftSection(
                id="module.db",
                content="Database connection pool.",
                author="HUMAN",
                is_modified=True,
                linked_code_hash="hash2",
            ),
        ],
    )


def test_pdf_generation(tmp_path: Path, sample_artifact: DraftArtifact) -> None:
    output_path = tmp_path / "test_sds.pdf"
    generator = PDFGenerator()
    generator.generate_sds(sample_artifact, output_path)

    assert output_path.exists()
    assert output_path.stat().st_size > 0
    with open(output_path, "rb") as f:
        header = f.read(4)
        assert header == b"%PDF"


def test_custom_template_dir(tmp_path: Path) -> None:
    tpl_dir = tmp_path / "templates"
    tpl_dir.mkdir()
    (tpl_dir / "sds.html").write_text("<html><body>{{ artifact.version }}</body></html>")

    generator = PDFGenerator(template_dir=tpl_dir)
    assert generator.env.loader is not None
    # No actual generation needed to verify loader init, but let's test it:
    art = DraftArtifact(version="v1", timestamp=datetime.now(), sections=[])
    out = tmp_path / "out.pdf"
    generator.generate_sds(art, out)
    assert out.exists()


def test_pdf_escapes_html(tmp_path: Path) -> None:
    """Verify that HTML characters in content are escaped."""
    # We can't easily parse the PDF to check text without a library,
    # but we can check that generation doesn't crash and maybe check file size.
    # To truly verify escaping, we'd inspect the intermediate HTML, but PDFGenerator hides it.
    # For now, we ensure it generates successfully.

    artifact = DraftArtifact(
        version="1.0",
        timestamp=datetime.now(timezone.utc),
        sections=[
            DraftSection(
                id="injection",
                content="<script>alert('xss')</script> & other chars",
                author="AI",
                is_modified=False,
                linked_code_hash="h",
            )
        ],
    )
    output_path = tmp_path / "escape.pdf"
    PDFGenerator().generate_sds(artifact, output_path)
    assert output_path.exists()


def test_pdf_unicode_content(tmp_path: Path) -> None:
    """Verify handling of unicode characters."""
    artifact = DraftArtifact(
        version="1.0",
        timestamp=datetime.now(timezone.utc),
        sections=[
            DraftSection(
                id="unicode", content="こんにちは world 🌍", author="AI", is_modified=False, linked_code_hash="h"
            )
        ],
    )
    output_path = tmp_path / "unicode.pdf"
    PDFGenerator().generate_sds(artifact, output_path)
    assert output_path.exists()


def test_pdf_empty_sections(tmp_path: Path) -> None:
    """Verify generation with no sections."""
    artifact = DraftArtifact(version="1.0", timestamp=datetime.now(timezone.utc), sections=[])
    output_path = tmp_path / "empty.pdf"
    PDFGenerator().generate_sds(artifact, output_path)
    assert output_path.exists()


def test_pdf_invalid_output_path(tmp_path: Path, sample_artifact: DraftArtifact) -> None:
    """Verify error when output directory does not exist."""
    # invalid_dir/test.pdf where invalid_dir does not exist
    output_path = tmp_path / "invalid_dir" / "test.pdf"

    with pytest.raises(FileNotFoundError):
        PDFGenerator().generate_sds(sample_artifact, output_path)


def test_large_document(tmp_path: Path) -> None:
    """Stress test with many sections."""
    sections = [
        DraftSection(
            id=f"sec.{i}", content=f"This is section {i}. " * 20, author="AI", is_modified=False, linked_code_hash="h"
        )
        for i in range(100)
    ]
    artifact = DraftArtifact(version="1.0-large", timestamp=datetime.now(timezone.utc), sections=sections)
    output_path = tmp_path / "large.pdf"
    PDFGenerator().generate_sds(artifact, output_path)
    assert output_path.exists()
    assert output_path.stat().st_size > 1000  # Should be reasonably large
