# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_scribe

import json
import math
from enum import Enum
from pathlib import Path
from typing import Dict, List, Set

import yaml
from pydantic import BaseModel, Field, ValidationError

from coreason_scribe.models import (
    AssayReport,
    AssayResult,
    DraftArtifact,
    Requirement,
    RiskLevel,
    TestStatus,
)


class ComplianceStatus(str, Enum):
    """
    The compliance status of a requirement based on verification evidence.
    """

    PASS = "PASS"
    WARNING = "WARNING"
    CRITICAL_GAP = "CRITICAL_GAP"


class GapAnalysisResult(BaseModel):
    """
    Result of a gap analysis for a single requirement.
    """

    requirement_id: str
    status: ComplianceStatus
    risk_level: RiskLevel
    coverage_percentage: float = Field(ge=0.0, le=100.0)
    message: str


class RiskAnalyzer:
    """
    Analyzes the risk and coverage of requirements to determine compliance status.
    """

    @staticmethod
    def analyze_coverage(requirement: Requirement, coverage_percentage: float) -> GapAnalysisResult:
        """
        Evaluates the compliance status of a requirement based on its risk level and test coverage.

        Rules:
        - High Risk: Requires 100% coverage. If < 100%, returns CRITICAL_GAP.
        - Med/Low Risk: If < 100% coverage, returns WARNING.
        - Any Risk: If 100% coverage, returns PASS.

        Args:
            requirement: The requirement to analyze.
            coverage_percentage: The calculated test coverage percentage (0.0 to 100.0).

        Returns:
            A GapAnalysisResult object containing the status and details.

        Raises:
            ValueError: If coverage_percentage is NaN, Infinite, or outside 0-100.
        """
        if not math.isfinite(coverage_percentage):
            raise ValueError(f"Coverage percentage must be a finite number, got {coverage_percentage}")

        if not (0.0 <= coverage_percentage <= 100.0):
            raise ValueError(f"Coverage percentage must be between 0.0 and 100.0, got {coverage_percentage}")

        # Strict floating point comparison for 100% compliance
        is_fully_covered = coverage_percentage >= 100.0

        status: ComplianceStatus
        message: str

        if is_fully_covered:
            status = ComplianceStatus.PASS
            message = "Requirement verified with full coverage."
        else:
            if requirement.risk == RiskLevel.HIGH:
                status = ComplianceStatus.CRITICAL_GAP
                message = f"High Risk Requirement {requirement.id} has {coverage_percentage}% coverage (Requires 100%)."
            else:
                status = ComplianceStatus.WARNING
                message = (
                    f"{requirement.risk.value} Risk Requirement {requirement.id} has partial coverage "
                    f"({coverage_percentage}%)."
                )

        return GapAnalysisResult(
            requirement_id=requirement.id,
            status=status,
            risk_level=requirement.risk,
            coverage_percentage=coverage_percentage,
            message=message,
        )


class TraceabilityMatrixBuilder:
    """
    Ingests Requirements and Assay Results to build the Traceability Matrix.
    """

    def load_requirements(self, yaml_path: Path) -> List[Requirement]:
        """
        Loads requirements from a YAML file.

        Args:
            yaml_path: Path to the agent.yaml file.

        Returns:
            A list of Requirement objects.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the file content is invalid or does not match schema.
        """
        if not yaml_path.exists():
            raise FileNotFoundError(f"Requirements file not found: {yaml_path}")

        try:
            with open(yaml_path, "r") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Failed to parse YAML: {e}") from e

        if not isinstance(data, list):
            raise ValueError("Requirements file must contain a list of requirements")

        requirements = []
        try:
            for item in data:
                requirements.append(Requirement(**item))
        except ValidationError as e:
            raise ValueError(f"Invalid requirement schema: {e}") from e

        return requirements

    def load_assay_report(self, json_path: Path) -> AssayReport:
        """
        Loads the assay report from a JSON file.

        Args:
            json_path: Path to the assay_report.json file.

        Returns:
            An AssayReport object.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the file content is invalid or does not match schema.
        """
        if not json_path.exists():
            raise FileNotFoundError(f"Assay report file not found: {json_path}")

        try:
            with open(json_path, "r") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON: {e}") from e

        try:
            report = AssayReport(**data)
        except ValidationError as e:
            raise ValueError(f"Invalid assay report schema: {e}") from e

        return report

    def _map_requirements_to_tests(self, assay_report: AssayReport) -> Dict[str, List[AssayResult]]:
        """
        Maps Requirement IDs to the list of AssayResults that verify them.
        """
        mapping: Dict[str, List[AssayResult]] = {}
        for result in assay_report.results:
            for req_id in result.linked_requirements:
                if req_id not in mapping:
                    mapping[req_id] = []
                mapping[req_id].append(result)
        return mapping

    def _calculate_requirement_coverage(self, linked_results: List[AssayResult]) -> float:
        """
        Calculates the aggregate coverage for a requirement based on linked test results.
        Strategy: Max Coverage.
        """
        if not linked_results:
            return 0.0
        return max(r.coverage for r in linked_results)

    def generate_mermaid_diagram(
        self, requirements: List[Requirement], assay_report: AssayReport, draft_artifact: DraftArtifact
    ) -> str:
        """
        Generates a Mermaid.js diagram representing the Traceability Matrix (Code -> Req -> Test).

        Args:
            requirements: The list of system requirements.
            assay_report: The test execution report.
            draft_artifact: The code analysis artifact.

        Returns:
            A string containing the Mermaid diagram definition.
        """
        lines = ["graph TD"]

        # Define styles
        lines.append("classDef pass fill:#e6fffa,stroke:#00cc99,stroke-width:2px;")
        lines.append("classDef warning fill:#fff4e6,stroke:#ff9900,stroke-width:2px;")
        lines.append("classDef criticalGap fill:#ffcccc,stroke:#ff0000,stroke-width:2px;")
        lines.append("classDef fail fill:#ffcccc,stroke:#ff0000,stroke-width:2px;")
        lines.append("classDef code fill:#e6f7ff,stroke:#1890ff,stroke-width:1px;")
        lines.append("classDef default fill:#ffffff,stroke:#000000;")

        # Maps for quick lookup
        req_to_tests = self._map_requirements_to_tests(assay_report)
        req_ids = {r.id for r in requirements}

        # 1. Code Nodes (from DraftArtifact)
        for section in draft_artifact.sections:
            # Escape section ID for mermaid if needed, but assuming valid ID chars for now
            # Code nodes link to Requirements
            node_id = section.id
            lines.append(f'{node_id}["{section.id}"]:::code')
            for linked_req in section.linked_requirements:
                if linked_req in req_ids:
                    lines.append(f"{node_id} --> {linked_req}")

        # 2. Requirement Nodes
        for req in requirements:
            linked_tests = req_to_tests.get(req.id, [])
            coverage = self._calculate_requirement_coverage(linked_tests)
            gap_result = RiskAnalyzer.analyze_coverage(req, coverage)

            # Assign style class
            style_class = "default"
            if gap_result.status == ComplianceStatus.PASS:
                style_class = "pass"
            elif gap_result.status == ComplianceStatus.WARNING:
                style_class = "warning"
            elif gap_result.status == ComplianceStatus.CRITICAL_GAP:
                style_class = "criticalGap"

            lines.append(f'{req.id}["{req.id}<br/>{req.risk.value}"]:::{style_class}')

            # Link Requirement to Tests
            for test in linked_tests:
                lines.append(f"{req.id} --> {test.test_id}")

        # 3. Test Nodes
        # We need to render test nodes only once.
        # Use a set to track rendered test IDs.
        rendered_tests: Set[str] = set()
        for result in assay_report.results:
            if result.test_id not in rendered_tests:
                style_class = "pass" if result.status == TestStatus.PASS else "fail"
                lines.append(f'{result.test_id}["{result.test_id}<br/>{result.status.value}"]:::{style_class}')
                rendered_tests.add(result.test_id)

        return "\n".join(lines)
