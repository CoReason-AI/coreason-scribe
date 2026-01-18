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
def base_timestamp() -> datetime:
    return datetime(2025, 1, 1, 12, 0, 0)


@pytest.fixture
def engine() -> SemanticDeltaEngine:
    return SemanticDeltaEngine()


def create_artifact(version: str, sections: list[DraftSection]) -> DraftArtifact:
    return DraftArtifact(version=version, timestamp=datetime.now(), sections=sections)


def create_section(
    sec_id: str, content: str = "content", code_hash: str = "hash123", author: Literal["AI", "HUMAN"] = "AI"
) -> DraftSection:
    return DraftSection(id=sec_id, content=content, author=author, is_modified=False, linked_code_hash=code_hash)


def test_no_changes(engine: SemanticDeltaEngine) -> None:
    """Test that identical artifacts produce no changes."""
    sections = [create_section("sec1")]
    prev = create_artifact("1.0", sections)
    curr = create_artifact("1.0", sections)  # Same content

    report: DeltaReport = engine.compute_delta(curr, prev)

    assert len(report.changes) == 0
    assert report.current_version == "1.0"
    assert report.previous_version == "1.0"


def test_logic_change(engine: SemanticDeltaEngine) -> None:
    """Test detection of code logic changes (hash mismatch)."""
    prev = create_artifact("1.0", [create_section("sec1", code_hash="old_hash")])
    curr = create_artifact("1.1", [create_section("sec1", code_hash="new_hash")])

    report: DeltaReport = engine.compute_delta(curr, prev)

    assert len(report.changes) == 1
    change = report.changes[0]
    assert change.section_id == "sec1"
    assert change.diff_type == DiffType.LOGIC_CHANGE
    assert change.previous_section is not None
    assert change.previous_section.linked_code_hash == "old_hash"
    assert change.current_section is not None
    assert change.current_section.linked_code_hash == "new_hash"


def test_text_change(engine: SemanticDeltaEngine) -> None:
    """Test detection of documentation text changes."""
    prev = create_artifact("1.0", [create_section("sec1", content="old text")])
    curr = create_artifact("1.1", [create_section("sec1", content="new text")])

    report: DeltaReport = engine.compute_delta(curr, prev)

    assert len(report.changes) == 1
    change = report.changes[0]
    assert change.section_id == "sec1"
    assert change.diff_type == DiffType.TEXT_CHANGE
    assert change.previous_section is not None
    assert change.previous_section.content == "old text"
    assert change.current_section is not None
    assert change.current_section.content == "new text"


def test_both_change(engine: SemanticDeltaEngine) -> None:
    """Test detection when both code and text change."""
    prev = create_artifact("1.0", [create_section("sec1", content="old", code_hash="old")])
    curr = create_artifact("1.1", [create_section("sec1", content="new", code_hash="new")])

    report: DeltaReport = engine.compute_delta(curr, prev)

    assert len(report.changes) == 1
    change = report.changes[0]
    assert change.diff_type == DiffType.BOTH


def test_new_section(engine: SemanticDeltaEngine) -> None:
    """Test detection of new sections."""
    prev = create_artifact("1.0", [])
    curr = create_artifact("1.1", [create_section("sec1")])

    report: DeltaReport = engine.compute_delta(curr, prev)

    assert len(report.changes) == 1
    change = report.changes[0]
    assert change.section_id == "sec1"
    assert change.diff_type == DiffType.NEW
    assert change.previous_section is None
    assert change.current_section is not None


def test_removed_section(engine: SemanticDeltaEngine) -> None:
    """Test detection of removed sections."""
    prev = create_artifact("1.0", [create_section("sec1")])
    curr = create_artifact("1.1", [])

    report: DeltaReport = engine.compute_delta(curr, prev)

    assert len(report.changes) == 1
    change = report.changes[0]
    assert change.section_id == "sec1"
    assert change.diff_type == DiffType.REMOVED
    assert change.previous_section is not None
    assert change.current_section is None


def test_mixed_changes(engine: SemanticDeltaEngine) -> None:
    """Test a mix of changes."""
    # sec1: logic change
    # sec2: text change
    # sec3: new
    # sec4: removed
    # sec5: no change

    prev_sections = [
        create_section("sec1", code_hash="h1"),
        create_section("sec2", content="c1"),
        create_section("sec4"),
        create_section("sec5"),
    ]
    curr_sections = [
        create_section("sec1", code_hash="h2"),
        create_section("sec2", content="c2"),
        create_section("sec3"),
        create_section("sec5"),
    ]

    prev = create_artifact("1.0", prev_sections)
    curr = create_artifact("1.1", curr_sections)

    report: DeltaReport = engine.compute_delta(curr, prev)

    assert len(report.changes) == 4
    changes_map = {c.section_id: c.diff_type for c in report.changes}

    assert changes_map["sec1"] == DiffType.LOGIC_CHANGE
    assert changes_map["sec2"] == DiffType.TEXT_CHANGE
    assert changes_map["sec3"] == DiffType.NEW
    assert changes_map["sec4"] == DiffType.REMOVED
    assert "sec5" not in changes_map
