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
from typing import Dict, List, Set

from coreason_scribe.models import DeltaReport, DiffItem, DiffType, DraftArtifact, DraftSection


class SemanticDeltaEngine:
    """
    Compares two DraftArtifacts to identify semantic differences (Logic vs Text).
    """

    def compute_delta(self, current: DraftArtifact, previous: DraftArtifact) -> DeltaReport:
        """
        Compares the current draft against a previous version.

        Args:
            current: The current draft artifact.
            previous: The previous draft artifact (e.g., last signed release).

        Returns:
            A DeltaReport containing all detected changes.
        """
        changes: List[DiffItem] = []

        # Index sections by ID for efficient lookup
        current_map: Dict[str, DraftSection] = {s.id: s for s in current.sections}
        previous_map: Dict[str, DraftSection] = {s.id: s for s in previous.sections}

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

        return DeltaReport(
            current_version=current.version,
            previous_version=previous.version,
            timestamp=datetime.now(timezone.utc),
            changes=changes,
        )
