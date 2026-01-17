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
from typing import Dict, List, Optional, Set

from coreason_scribe.matrix import ComplianceEngine, ComplianceStatus
from coreason_scribe.models import (
    AssayReport,
    DeltaReport,
    DiffItem,
    DiffType,
    DraftArtifact,
    DraftSection,
    Requirement,
    VerificationDrift,
)


class SemanticDeltaEngine:
    """
    Compares two DraftArtifacts to identify semantic differences (Logic vs Text).
    Also detects Verification Drift if AssayReports are provided.
    """

    def _index_sections(self, sections: List[DraftSection]) -> Dict[str, DraftSection]:
        """
        Helper to index sections by ID. Raises ValueError on duplicates.
        """
        mapping: Dict[str, DraftSection] = {}
        for s in sections:
            if s.id in mapping:
                raise ValueError(f"Duplicate Section ID found: {s.id}")
            mapping[s.id] = s
        return mapping

    def compute_delta(
        self,
        current: DraftArtifact,
        previous: DraftArtifact,
        current_report: Optional[AssayReport] = None,
        previous_report: Optional[AssayReport] = None,
        requirements: Optional[List[Requirement]] = None,
    ) -> DeltaReport:
        """
        Compares the current draft against a previous version.

        Args:
            current: The current draft artifact.
            previous: The previous draft artifact (e.g., last signed release).
            current_report: Optional current assay report for verification drift.
            previous_report: Optional previous assay report for verification drift.
            requirements: Optional list of requirements for risk analysis.

        Returns:
            A DeltaReport containing all detected changes.

        Raises:
            ValueError: If either artifact contains duplicate section IDs.
        """
        changes: List[DiffItem] = []

        # Index sections by ID for efficient lookup
        current_map = self._index_sections(current.sections)
        previous_map = self._index_sections(previous.sections)

        all_ids: Set[str] = set(current_map.keys()) | set(previous_map.keys())

        for section_id in all_ids:
            curr_sec = current_map.get(section_id)
            prev_sec = previous_map.get(section_id)

            if curr_sec and not prev_sec:
                # NEW
                changes.append(
                    DiffItem(
                        section_id=section_id,
                        diff_type=DiffType.NEW,
                        current_section=curr_sec,
                        previous_section=None,
                    )
                )
            elif prev_sec and not curr_sec:
                # REMOVED
                changes.append(
                    DiffItem(
                        section_id=section_id,
                        diff_type=DiffType.REMOVED,
                        current_section=None,
                        previous_section=prev_sec,
                    )
                )
            elif curr_sec and prev_sec:
                # Compare content and hash
                has_logic_change = curr_sec.linked_code_hash != prev_sec.linked_code_hash
                has_text_change = curr_sec.content != prev_sec.content

                if has_logic_change and has_text_change:
                    changes.append(
                        DiffItem(
                            section_id=section_id,
                            diff_type=DiffType.BOTH,
                            current_section=curr_sec,
                            previous_section=prev_sec,
                        )
                    )
                elif has_logic_change:
                    changes.append(
                        DiffItem(
                            section_id=section_id,
                            diff_type=DiffType.LOGIC_CHANGE,
                            current_section=curr_sec,
                            previous_section=prev_sec,
                        )
                    )
                elif has_text_change:
                    changes.append(
                        DiffItem(
                            section_id=section_id,
                            diff_type=DiffType.TEXT_CHANGE,
                            current_section=curr_sec,
                            previous_section=prev_sec,
                        )
                    )
                # Else: No change, do not append to report

        # Verification Drift Detection
        verification_drifts: List[VerificationDrift] = []
        if current_report and previous_report and requirements:
            verification_drifts = self._detect_verification_drift(current_report, previous_report, requirements)

        return DeltaReport(
            current_version=current.version,
            previous_version=previous.version,
            timestamp=datetime.now(timezone.utc),
            changes=changes,
            verification_drifts=verification_drifts,
        )

    def _detect_verification_drift(
        self,
        current_report: AssayReport,
        previous_report: AssayReport,
        requirements: List[Requirement],
    ) -> List[VerificationDrift]:
        """
        Detects regressions in requirement compliance status.
        """
        compliance_engine = ComplianceEngine()

        current_statuses = compliance_engine.evaluate_compliance(requirements, current_report)
        previous_statuses = compliance_engine.evaluate_compliance(requirements, previous_report)

        drifts = []
        for req in requirements:
            # Since we iterate over the same requirements list, both reports will produce a status
            # (defaulting to 0% coverage if no tests are found).
            prev = previous_statuses[req.id]
            curr = current_statuses[req.id]

            # Check for regression:
            # PASS -> WARNING
            # PASS -> CRITICAL_GAP
            # WARNING -> CRITICAL_GAP (Only possible if risk level changes dynamically, preventing here)

            is_regression = False
            if prev == ComplianceStatus.PASS and curr != ComplianceStatus.PASS:
                is_regression = True
            # The transition WARNING -> CRITICAL_GAP is impossible given a static requirement risk level
            # for the same requirement ID in a single run.
            # However, we keep the check for semantic completeness and mark it for coverage exclusion.
            elif prev == ComplianceStatus.WARNING and curr == ComplianceStatus.CRITICAL_GAP:  # pragma: no cover
                is_regression = True

            if is_regression:
                drifts.append(
                    VerificationDrift(
                        requirement_id=req.id,
                        previous_status=prev.value,
                        current_status=curr.value,
                    )
                )

        return drifts
