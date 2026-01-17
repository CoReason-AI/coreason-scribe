# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_scribe

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from git import InvalidGitRepositoryError, Repo

from coreason_scribe.delta import SemanticDeltaEngine
from coreason_scribe.inspector import SemanticInspector
from coreason_scribe.matrix import TraceabilityMatrixBuilder
from coreason_scribe.models import DraftArtifact
from coreason_scribe.pdf import PDFGenerator
from coreason_scribe.utils.logger import logger


def main() -> None:
    parser = argparse.ArgumentParser(description="CoReason Scribe - GxP Documentation Engine")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: draft
    draft_parser = subparsers.add_parser("draft", help="Generate a draft artifact from source code")
    draft_parser.add_argument("--source", type=Path, default=Path.cwd(), help="Source directory to scan")
    draft_parser.add_argument("--output", type=Path, default=Path.cwd() / "output", help="Output directory")
    draft_parser.add_argument("--version", type=str, required=True, help="Version string for the artifact")
    draft_parser.add_argument("--agent-yaml", type=Path, help="Path to agent.yaml (requirements)")
    draft_parser.add_argument("--assay-report", type=Path, help="Path to assay_report.json (test results)")

    # Command: check
    check_parser = subparsers.add_parser("check", help="Check for semantic drift between artifacts")
    check_parser.add_argument("current", type=Path, help="Path to current artifact.json")
    check_parser.add_argument("previous", type=Path, help="Path to previous signed artifact.json")

    args = parser.parse_args()

    if args.command == "draft":
        run_draft(args.source, args.output, args.version, args.agent_yaml, args.assay_report)
    elif args.command == "check":
        run_check(args.current, args.previous)
    else:
        parser.print_help()


def run_draft(
    source_dir: Path,
    output_dir: Path,
    version: str,
    agent_yaml: Optional[Path] = None,
    assay_report: Optional[Path] = None,
) -> None:
    logger.info(f"Starting draft generation for version {version}...")

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Initialize Git Repo & Get Commit Hash
    try:
        repo = Repo(source_dir, search_parent_directories=True)
        commit_hash = repo.head.commit.hexsha
        logger.info(f"Detected git commit: {commit_hash}")

        # Get all tracked files (respects .gitignore)
        # ls-files returns paths relative to the repo root
        git_files = repo.git.ls_files().splitlines()

        # Filter for Python files and convert to absolute paths
        # We need to handle the case where source_dir is a subdirectory of the repo root
        repo_root = Path(repo.working_dir)
        tracked_py_files = []
        for file_rel_path in git_files:
            abs_path = repo_root / file_rel_path
            # Check if file is inside our source_dir and is a .py file
            if abs_path.is_relative_to(source_dir) and abs_path.suffix == ".py":
                tracked_py_files.append(abs_path)

    except InvalidGitRepositoryError:
        logger.error(f"Directory {source_dir} is not a valid git repository.")
        sys.exit(1)

    # 2. Run Semantic Inspector
    inspector = SemanticInspector()
    all_sections = []

    for file_path in tracked_py_files:
        try:
            content = file_path.read_text(encoding="utf-8")
            # Calculate module name relative to source_dir
            rel_path = file_path.relative_to(source_dir)
            module_name = ".".join(rel_path.with_suffix("").parts)

            sections = inspector.inspect_source(content, module_name)
            all_sections.extend(sections)
            logger.debug(f"Processed {file_path}: Found {len(sections)} sections.")
        except Exception as e:
            logger.error(f"Failed to process {file_path}: {e}")

    # 3. Create DraftArtifact
    artifact = DraftArtifact(
        version=version,
        timestamp=datetime.now(timezone.utc),
        sections=all_sections,
        commit_hash=commit_hash,
    )

    # 4. Save Artifact JSON
    json_path = output_dir / "artifact.json"
    with open(json_path, "w") as f:
        f.write(artifact.model_dump_json(indent=2))
    logger.info(f"Draft artifact saved to {json_path}")

    # 5. Generate PDF
    pdf_path = output_dir / "sds.pdf"
    pdf_gen = PDFGenerator()
    try:
        pdf_gen.generate_sds(artifact, pdf_path)
        logger.info(f"SDS PDF generated at {pdf_path}")
    except Exception as e:
        logger.error(f"Failed to generate PDF: {e}")

    # 6. Generate Traceability Matrix (Mermaid) if inputs provided
    if agent_yaml and assay_report:
        try:
            builder = TraceabilityMatrixBuilder()
            reqs = builder.load_requirements(agent_yaml)
            report = builder.load_assay_report(assay_report)

            mermaid_content = builder.generate_mermaid_diagram(reqs, report, artifact)

            mmd_path = output_dir / "traceability.mmd"
            mmd_path.write_text(mermaid_content, encoding="utf-8")
            logger.info(f"Traceability diagram saved to {mmd_path}")

        except Exception as e:
            logger.error(f"Failed to generate traceability matrix: {e}")


def run_check(current_path: Path, previous_path: Path) -> None:
    logger.info("Running semantic check...")

    try:
        with open(current_path, "r") as f:
            current = DraftArtifact.model_validate_json(f.read())

        with open(previous_path, "r") as f:
            previous = DraftArtifact.model_validate_json(f.read())

    except Exception as e:
        logger.error(f"Failed to load artifacts: {e}")
        sys.exit(1)

    delta_engine = SemanticDeltaEngine()
    delta_report = delta_engine.compute_delta(current, previous)

    # Print Summary
    print("\n--- Semantic Delta Report ---")
    print(f"Current: {delta_report.current_version} | Previous: {delta_report.previous_version}")
    print(f"Timestamp: {delta_report.timestamp}")
    print(f"Total Changes: {len(delta_report.changes)}")

    if not delta_report.changes:
        print("\nNo semantic changes detected.")
        return

    print("\nDetails:")
    for change in delta_report.changes:
        print(f"[{change.diff_type.value}] {change.section_id}")
        if change.diff_type in ("LOGIC_CHANGE", "BOTH"):
            print("  WARNING: Logic Changed! (Hash mismatch)")
        if change.diff_type in ("TEXT_CHANGE", "BOTH"):
            print("  Info: Content text changed.")


if __name__ == "__main__":  # pragma: no cover
    main()
