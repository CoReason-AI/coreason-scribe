# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_scribe

from datetime import datetime
from typing import Literal

import pytest

from coreason_scribe.delta import SemanticDeltaEngine
from coreason_scribe.models import DeltaReport, DiffType, DraftArtifact, DraftSection


@pytest.fixture
def engine() -> SemanticDeltaEngine:
    return SemanticDeltaEngine()


def create_artifact(version: str, sections: list[DraftSection]) -> DraftArtifact:
    return DraftArtifact(version=version, timestamp=datetime.now(), sections=sections)


def create_section(
    sec_id: str, content: str = "content", code_hash: str = "hash123", author: Literal["AI", "HUMAN"] = "AI"
) -> DraftSection:
    return DraftSection(id=sec_id, content=content, author=author, is_modified=False, linked_code_hash=code_hash)


def test_empty_comparison(engine: SemanticDeltaEngine) -> None:
    """Test comparison of two empty artifacts."""
    prev = create_artifact("1.0", [])
    curr = create_artifact("1.1", [])

    report: DeltaReport = engine.compute_delta(curr, prev)

    assert len(report.changes) == 0
    assert report.current_version == "1.1"
    assert report.previous_version == "1.0"


def test_duplicate_ids_raises_error(engine: SemanticDeltaEngine) -> None:
    """Test that duplicates in artifact raise ValueError."""
    sections = [create_section("dup_id"), create_section("dup_id")]
    bad_artifact = create_artifact("1.0", sections)
    good_artifact = create_artifact("1.1", [])

    with pytest.raises(ValueError, match="Duplicate Section ID found"):
        engine.compute_delta(bad_artifact, good_artifact)

    with pytest.raises(ValueError, match="Duplicate Section ID found"):
        engine.compute_delta(good_artifact, bad_artifact)


def test_rename_detection(engine: SemanticDeltaEngine) -> None:
    """Test that renaming a function results in REMOVED + NEW."""
    # Renaming 'old_func' to 'new_func'
    prev = create_artifact("1.0", [create_section("old_func")])
    curr = create_artifact("1.1", [create_section("new_func")])

    report: DeltaReport = engine.compute_delta(curr, prev)

    assert len(report.changes) == 2
    types = {c.diff_type for c in report.changes}
    ids = {c.section_id for c in report.changes}

    assert DiffType.NEW in types
    assert DiffType.REMOVED in types
    assert "old_func" in ids
    assert "new_func" in ids


def test_whitespace_sensitivity(engine: SemanticDeltaEngine) -> None:
    """Test that whitespace changes in content trigger TEXT_CHANGE."""
    prev = create_artifact("1.0", [create_section("sec1", content="Hello")])
    curr = create_artifact("1.1", [create_section("sec1", content="Hello ")])  # Trailing space

    report: DeltaReport = engine.compute_delta(curr, prev)

    assert len(report.changes) == 1
    assert report.changes[0].diff_type == DiffType.TEXT_CHANGE


def test_large_scale_comparison(engine: SemanticDeltaEngine) -> None:
    """Test comparison with large number of sections."""
    count = 2000
    prev_sections = [create_section(f"sec_{i}", code_hash=f"hash_{i}") for i in range(count)]
    # Modify every even section
    curr_sections = []
    for i in range(count):
        if i % 2 == 0:
            # Modify hash
            curr_sections.append(create_section(f"sec_{i}", code_hash=f"hash_{i}_mod"))
        else:
            # Keep same
            curr_sections.append(create_section(f"sec_{i}", code_hash=f"hash_{i}"))

    prev = create_artifact("1.0", prev_sections)
    curr = create_artifact("1.1", curr_sections)

    start_time = datetime.now()
    report: DeltaReport = engine.compute_delta(curr, prev)
    end_time = datetime.now()

    duration = (end_time - start_time).total_seconds()

    # 1000 changes expected
    assert len(report.changes) == count // 2
    assert duration < 2.0  # Should be very fast
