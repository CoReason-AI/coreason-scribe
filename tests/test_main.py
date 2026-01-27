# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason-scribe

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Generator
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from git import InvalidGitRepositoryError

from coreason_scribe.main import ScribeError, main, run_diff, run_draft
from coreason_scribe.models import (
    AssayResult,
    AssayStatus,
    DraftArtifact,
    Requirement,
    RiskLevel,
)


@pytest.fixture
def mock_repo() -> Generator[MagicMock, None, None]:
    with patch("coreason_scribe.main.Repo") as mock:
        repo_instance = MagicMock()
        repo_instance.head.commit.hexsha = "abcdef123456"
        repo_instance.git.ls_files.return_value = "src/module.py\ntests/test_module.py"
        repo_instance.working_dir = "/fake/repo"
        mock.return_value = repo_instance
        yield mock


@pytest.fixture
def mock_inspector() -> Generator[MagicMock, None, None]:
    with patch("coreason_scribe.main.SemanticInspector") as mock:
        inspector_instance = MagicMock()
        inspector_instance.inspect_source.return_value = []
        mock.return_value = inspector_instance
        yield mock


@pytest.fixture
def mock_pdf_generator() -> Generator[MagicMock, None, None]:
    with patch("coreason_scribe.main.PDFGenerator") as mock:
        yield mock


@pytest.fixture
def mock_matrix_builder() -> Generator[MagicMock, None, None]:
    with patch("coreason_scribe.main.TraceabilityMatrixBuilder") as mock:
        yield mock


def test_main_help(capsys: pytest.CaptureFixture[str]) -> None:
    with patch("sys.argv", ["scribe", "--help"]):
        with pytest.raises(SystemExit):
            main()
    captured = capsys.readouterr()
    assert "CoReason Scribe" in captured.out


def test_main_no_args(capsys: pytest.CaptureFixture[str]) -> None:
    with patch("sys.argv", ["scribe"]):
        main()
    captured = capsys.readouterr()
    # It should print help
    assert "CoReason Scribe" in captured.out


def test_run_draft_basic(
    mock_repo: MagicMock, mock_inspector: MagicMock, mock_pdf_generator: MagicMock, tmp_path: Path
) -> None:
    source_dir = tmp_path / "src"
    source_dir.mkdir()
    (source_dir / "module.py").write_text("def foo(): pass")

    # Adjust mock repo to return relative path to temp dir
    mock_repo.return_value.working_dir = str(tmp_path)
    mock_repo.return_value.git.ls_files.return_value = "src/module.py"

    output_dir = tmp_path / "output"

    with patch(
        "sys.argv",
        [
            "scribe",
            "draft",
            "--source",
            str(source_dir),
            "--output",
            str(output_dir),
            "--version",
            "1.0.0",
            "--user-id",
            "user1",
            "--email",
            "user1@example.com",
        ],
    ):
        assert main() == 0

    assert (output_dir / "artifact.json").exists()
    mock_pdf_generator.return_value.generate_sds.assert_called_once()

    with open(output_dir / "artifact.json") as f:
        data = json.load(f)
        assert data["version"] == "1.0.0"
        assert data["commit_hash"] == "abcdef123456"


def test_run_draft_with_traceability(
    mock_repo: MagicMock,
    mock_inspector: MagicMock,
    mock_pdf_generator: MagicMock,
    mock_matrix_builder: MagicMock,
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "src"
    source_dir.mkdir()
    output_dir = tmp_path / "output"
    agent_yaml = tmp_path / "agent.yaml"
    agent_yaml.touch()
    assay_report = tmp_path / "assay_report.json"
    assay_report.touch()

    mock_repo.return_value.working_dir = str(tmp_path)
    mock_repo.return_value.git.ls_files.return_value = "src/module.py"

    mock_builder_instance = mock_matrix_builder.return_value
    mock_builder_instance.generate_mermaid_diagram.return_value = "graph TD; A-->B;"

    with patch(
        "sys.argv",
        [
            "scribe",
            "draft",
            "--source",
            str(source_dir),
            "--output",
            str(output_dir),
            "--version",
            "1.0.0",
            "--user-id",
            "user1",
            "--email",
            "user1@example.com",
            "--agent-yaml",
            str(agent_yaml),
            "--assay-report",
            str(assay_report),
        ],
    ):
        assert main() == 0

    assert (output_dir / "traceability.mmd").exists()
    assert (output_dir / "traceability.mmd").read_text() == "graph TD; A-->B;"


def test_draft_invalid_git_repo(tmp_path: Path) -> None:
    from coreason_identity.models import UserContext

    user_context = UserContext(sub="user1", email="user1@example.com", permissions=[])
    with patch("coreason_scribe.main.Repo", side_effect=InvalidGitRepositoryError):
        with pytest.raises(ScribeError):
            run_draft(tmp_path, tmp_path / "out", "1.0.0", user_context)


def test_draft_invalid_git_repo_via_main(tmp_path: Path) -> None:
    """Test invalid git repo via main() to verify ScribeError handling."""
    with patch("coreason_scribe.main.Repo", side_effect=InvalidGitRepositoryError):
        with patch("coreason_scribe.main.logger") as mock_logger:
            with patch(
                "sys.argv",
                [
                    "scribe",
                    "draft",
                    "--source",
                    str(tmp_path),
                    "--output",
                    str(tmp_path / "out"),
                    "--version",
                    "1.0.0",
                    "--user-id",
                    "user1",
                    "--email",
                    "user1@example.com",
                ],
            ):
                assert main() == 1

            # Verify logger.error was called with the exception string
            assert mock_logger.error.called
            # We can inspect the arguments if we want strict checking
            args, _ = mock_logger.error.call_args
            assert "not a valid git repository" in str(args[0])


def test_draft_pdf_generation_failure(
    mock_repo: MagicMock, mock_inspector: MagicMock, mock_pdf_generator: MagicMock, tmp_path: Path
) -> None:
    source_dir = tmp_path / "src"
    source_dir.mkdir()
    (source_dir / "module.py").write_text("def foo(): pass")
    mock_repo.return_value.working_dir = str(tmp_path)
    mock_repo.return_value.git.ls_files.return_value = "src/module.py"
    output_dir = tmp_path / "output"

    # Mock PDF generator to raise an exception
    mock_pdf_generator.return_value.generate_sds.side_effect = Exception("PDF Fail")

    with patch(
        "sys.argv",
        [
            "scribe",
            "draft",
            "--source",
            str(source_dir),
            "--output",
            str(output_dir),
            "--version",
            "1.0.0",
            "--user-id",
            "user1",
            "--email",
            "user1@example.com",
        ],
    ):
        # Should not crash, just log error
        assert main() == 0

    assert (output_dir / "artifact.json").exists()


def test_draft_inspection_failure(
    mock_repo: MagicMock, mock_inspector: MagicMock, mock_pdf_generator: MagicMock, tmp_path: Path
) -> None:
    """Test exception handling during source inspection."""
    source_dir = tmp_path / "src"
    source_dir.mkdir()
    (source_dir / "module.py").write_text("def foo(): pass")
    mock_repo.return_value.working_dir = str(tmp_path)
    mock_repo.return_value.git.ls_files.return_value = "src/module.py"
    output_dir = tmp_path / "output"

    # Mock inspector to raise exception
    mock_inspector.return_value.inspect_source.side_effect = Exception("Inspection Fail")

    with patch(
        "sys.argv",
        [
            "scribe",
            "draft",
            "--source",
            str(source_dir),
            "--output",
            str(output_dir),
            "--version",
            "1.0.0",
            "--user-id",
            "user1",
            "--email",
            "user1@example.com",
        ],
    ):
        assert main() == 0

    # Should still create artifact, just with empty sections
    assert (output_dir / "artifact.json").exists()


def test_draft_traceability_failure(
    mock_repo: MagicMock,
    mock_inspector: MagicMock,
    mock_pdf_generator: MagicMock,
    mock_matrix_builder: MagicMock,
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "src"
    source_dir.mkdir()
    output_dir = tmp_path / "output"
    agent_yaml = tmp_path / "agent.yaml"
    agent_yaml.touch()

    mock_repo.return_value.working_dir = str(tmp_path)
    mock_repo.return_value.git.ls_files.return_value = "src/module.py"

    # Mock builder to raise exception
    mock_matrix_builder.return_value.load_requirements.side_effect = Exception("Matrix Fail")

    with patch(
        "sys.argv",
        [
            "scribe",
            "draft",
            "--source",
            str(source_dir),
            "--output",
            str(output_dir),
            "--version",
            "1.0.0",
            "--user-id",
            "user1",
            "--email",
            "user1@example.com",
            "--agent-yaml",
            str(agent_yaml),
            "--assay-report",
            str(tmp_path / "report.json"),
        ],
    ):
        # Should not crash
        assert main() == 0


def test_run_diff(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    current = tmp_path / "current.json"
    previous = tmp_path / "previous.json"

    # Create valid artifacts
    a1 = DraftArtifact(version="1.0.0", timestamp=datetime(2023, 1, 1, 0, 0, 0), sections=[])
    a2 = DraftArtifact(version="0.9.0", timestamp=datetime(2022, 1, 1, 0, 0, 0), sections=[])

    current.write_text(a1.model_dump_json())
    previous.write_text(a2.model_dump_json())

    with patch("sys.argv", ["scribe", "diff", str(current), str(previous)]):
        assert main() == 0

    captured = capsys.readouterr()
    assert "Semantic Delta Report" in captured.out
    assert "No semantic changes detected" in captured.out


def test_run_diff_with_changes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from coreason_scribe.models import DraftSection

    s1 = DraftSection(
        id="mod.func",
        content="new content",
        author="AI",
        is_modified=True,
        linked_code_hash="hash2",
        linked_requirements=[],
    )
    s2 = DraftSection(
        id="mod.func",
        content="old content",
        author="AI",
        is_modified=False,
        linked_code_hash="hash1",
        linked_requirements=[],
    )

    a1 = DraftArtifact(version="1.0.0", timestamp=datetime(2023, 1, 1, 0, 0, 0), sections=[s1])
    a2 = DraftArtifact(version="0.9.0", timestamp=datetime(2022, 1, 1, 0, 0, 0), sections=[s2])

    current = tmp_path / "current.json"
    previous = tmp_path / "previous.json"

    current.write_text(a1.model_dump_json())
    previous.write_text(a2.model_dump_json())

    with patch("sys.argv", ["scribe", "diff", str(current), str(previous)]):
        assert main() == 0

    captured = capsys.readouterr()
    assert "Total Changes: 1" in captured.out
    assert "[BOTH] mod.func" in captured.out
    assert "Logic Changed!" in captured.out


def test_diff_file_not_found() -> None:
    with pytest.raises(ScribeError):
        run_diff(Path("nonexistent1"), Path("nonexistent2"))


# --- New Check (Gate) Tests (Refactored to use fixture where possible) ---


def test_check_passes(
    tmp_path: Path, mock_traceability_context: Callable[..., Any], capsys: pytest.CaptureFixture[str]
) -> None:
    """Refactored to use the shared mock_traceability_context fixture."""
    req = Requirement(id="REQ-001", description="Safety", risk=RiskLevel.HIGH)
    # We must patch ComplianceEngine return value to PASS, OR use real ComplianceEngine?
    # The fixture mocks MatrixBuilder. MatrixBuilder returns Req and Report.
    # run_check instantiates ComplianceEngine() real object.
    # The real ComplianceEngine logic will pass if coverage >= 100.
    # So if we provide an AssayResult with 100% coverage, we don't need to patch ComplianceEngine!
    # This is a better integration test anyway.

    # 100% Coverage Result
    result = AssayResult(
        test_id="T1",
        status=AssayStatus.PASS,
        coverage=100.0,
        linked_requirements=["REQ-001"],
        timestamp=datetime.now(),
    )

    with mock_traceability_context(tmp_path, requirements=[req], assay_results=[result]) as (yaml_path, report_path):
        with patch("sys.argv", ["scribe", "check", "--agent-yaml", str(yaml_path), "--assay-report", str(report_path)]):
            assert main() == 0

    captured = capsys.readouterr()
    assert "SUCCESS" in captured.out
    assert "[PASS] REQ-001" in captured.out


def test_check_fails_critical_gap(
    tmp_path: Path, mock_traceability_context: Callable[..., Any], capsys: pytest.CaptureFixture[str]
) -> None:
    """Refactored to use shared fixture + real ComplianceEngine logic."""
    req = Requirement(id="REQ-001", description="Safety", risk=RiskLevel.HIGH)
    # 50% Coverage Result (Critical Gap)
    result = AssayResult(
        test_id="T1",
        status=AssayStatus.PASS,
        coverage=50.0,
        linked_requirements=["REQ-001"],
        timestamp=datetime.now(),
    )

    with mock_traceability_context(tmp_path, requirements=[req], assay_results=[result]) as (yaml_path, report_path):
        with patch("sys.argv", ["scribe", "check", "--agent-yaml", str(yaml_path), "--assay-report", str(report_path)]):
            assert main() == 1

    captured = capsys.readouterr()
    assert "FATAL" in captured.out
    assert "CRITICAL_GAP" in captured.out


def test_check_fails_critical_gap_via_main_exception(
    tmp_path: Path, mock_traceability_context: Callable[..., Any]
) -> None:
    """Explicitly verify main catches ComplianceGateFailure and logs correct message."""
    req = Requirement(id="REQ-001", description="Safety", risk=RiskLevel.HIGH)
    # 50% Coverage Result (Critical Gap)
    result = AssayResult(
        test_id="T1",
        status=AssayStatus.PASS,
        coverage=50.0,
        linked_requirements=["REQ-001"],
        timestamp=datetime.now(),
    )

    with mock_traceability_context(tmp_path, requirements=[req], assay_results=[result]) as (yaml_path, report_path):
        with patch("coreason_scribe.main.logger") as mock_logger:
            with patch(
                "sys.argv", ["scribe", "check", "--agent-yaml", str(yaml_path), "--assay-report", str(report_path)]
            ):
                assert main() == 1

            assert mock_logger.error.called
            args, _ = mock_logger.error.call_args
            assert "Build failed due to Critical Gaps" in str(args[0])


def test_check_invalid_files(tmp_path: Path, mock_matrix_builder: MagicMock) -> None:
    agent_yaml = tmp_path / "agent.yaml"
    assay_report = tmp_path / "report.json"

    mock_matrix_builder.return_value.load_requirements.side_effect = Exception("Bad YAML")

    with patch("sys.argv", ["scribe", "check", "--agent-yaml", str(agent_yaml), "--assay-report", str(assay_report)]):
        # main() catches ScribeError and exits 1
        assert main() == 1


def test_check_unexpected_error(tmp_path: Path, mock_traceability_context: Callable[..., Any]) -> None:
    """Test handling of unexpected exceptions in main()."""
    with mock_traceability_context(tmp_path, requirements=[], assay_results=[]) as (yaml_path, report_path):
        with patch("coreason_scribe.main.ComplianceEngine") as MockEngine:
            MockEngine.return_value.evaluate_compliance.side_effect = ValueError("Boom")

            with patch("coreason_scribe.main.logger") as mock_logger:
                with patch(
                    "sys.argv", ["scribe", "check", "--agent-yaml", str(yaml_path), "--assay-report", str(report_path)]
                ):
                    assert main() == 1

                assert mock_logger.exception.called
                args, _ = mock_logger.exception.call_args
                assert "Unexpected error" in str(args[0])


# --- New Edge Case Tests ---


def test_draft_empty_git_repo_no_commits(
    mock_repo: MagicMock, mock_inspector: MagicMock, mock_pdf_generator: MagicMock, tmp_path: Path
) -> None:
    """Test handling of a git repository with no commits (fresh init)."""
    source_dir = tmp_path / "src"
    source_dir.mkdir()
    (source_dir / "module.py").write_text("def foo(): pass")

    # Simulate ValueError when accessing hexsha
    type(mock_repo.return_value.head.commit).hexsha = PropertyMock(side_effect=ValueError("Ref not found"))
    mock_repo.return_value.working_dir = str(tmp_path)
    mock_repo.return_value.git.ls_files.return_value = "src/module.py"

    output_dir = tmp_path / "output"

    with patch(
        "sys.argv",
        [
            "scribe",
            "draft",
            "--source",
            str(source_dir),
            "--output",
            str(output_dir),
            "--version",
            "1.0.0",
            "--user-id",
            "user1",
            "--email",
            "user1@example.com",
        ],
    ):
        assert main() == 0

    assert (output_dir / "artifact.json").exists()
    with open(output_dir / "artifact.json") as f:
        data = json.load(f)
        assert data["commit_hash"] is None


def test_draft_nested_structure(
    mock_repo: MagicMock, mock_inspector: MagicMock, mock_pdf_generator: MagicMock, tmp_path: Path
) -> None:
    """Test correct module ID generation for nested files."""
    source_dir = tmp_path / "src"
    source_dir.mkdir()
    nested_dir = source_dir / "a" / "b"
    nested_dir.mkdir(parents=True)
    (nested_dir / "c.py").write_text("def bar(): pass")

    mock_repo.return_value.working_dir = str(tmp_path)
    mock_repo.return_value.git.ls_files.return_value = "src/a/b/c.py"

    output_dir = tmp_path / "output"

    # We need the inspector to actually be called with correct module name
    with patch(
        "sys.argv",
        [
            "scribe",
            "draft",
            "--source",
            str(source_dir),
            "--output",
            str(output_dir),
            "--version",
            "1.0.0",
            "--user-id",
            "user1",
            "--email",
            "user1@example.com",
        ],
    ):
        assert main() == 0

    # Verify inspector call
    mock_inspector.return_value.inspect_source.assert_called()
    # Check the module name argument of the last call
    args, _ = mock_inspector.return_value.inspect_source.call_args
    assert args[1] == "a.b.c"


def test_draft_unicode_source(
    mock_repo: MagicMock, mock_inspector: MagicMock, mock_pdf_generator: MagicMock, tmp_path: Path
) -> None:
    """Test reading source files with unicode characters."""
    source_dir = tmp_path / "src"
    source_dir.mkdir()
    content = "def emoji():\n    '''🚀'''\n    pass"
    (source_dir / "unicode.py").write_text(content, encoding="utf-8")

    mock_repo.return_value.working_dir = str(tmp_path)
    mock_repo.return_value.git.ls_files.return_value = "src/unicode.py"

    output_dir = tmp_path / "output"

    with patch(
        "sys.argv",
        [
            "scribe",
            "draft",
            "--source",
            str(source_dir),
            "--output",
            str(output_dir),
            "--version",
            "1.0.0",
            "--user-id",
            "user1",
            "--email",
            "user1@example.com",
        ],
    ):
        assert main() == 0

    # Verify content was read correctly
    args, _ = mock_inspector.return_value.inspect_source.call_args
    assert args[0] == content


def test_check_invalid_json_model(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Test diff command with valid JSON that doesn't match the model."""
    current = tmp_path / "current.json"
    previous = tmp_path / "previous.json"

    current.write_text('{"version": "1.0", "missing": "fields"}')  # Invalid DraftArtifact
    previous.write_text('{"version": "1.0", "missing": "fields"}')

    with patch("sys.argv", ["scribe", "diff", str(current), str(previous)]):
        assert main() == 1


def test_draft_partial_traceability(
    mock_repo: MagicMock,
    mock_inspector: MagicMock,
    mock_pdf_generator: MagicMock,
    mock_matrix_builder: MagicMock,
    tmp_path: Path,
) -> None:
    """Test that providing only agent-yaml without assay-report (or vice versa) skips generation gracefully."""
    source_dir = tmp_path / "src"
    source_dir.mkdir()
    output_dir = tmp_path / "output"
    agent_yaml = tmp_path / "agent.yaml"
    agent_yaml.touch()

    mock_repo.return_value.working_dir = str(tmp_path)
    mock_repo.return_value.git.ls_files.return_value = "src/module.py"

    with patch(
        "sys.argv",
        [
            "scribe",
            "draft",
            "--source",
            str(source_dir),
            "--output",
            str(output_dir),
            "--version",
            "1.0.0",
            "--user-id",
            "user1",
            "--email",
            "user1@example.com",
            "--agent-yaml",
            str(agent_yaml),
            # Missing --assay-report
        ],
    ):
        assert main() == 0

    # Should succeed but NOT generate mmd
    assert (output_dir / "artifact.json").exists()
    assert not (output_dir / "traceability.mmd").exists()
