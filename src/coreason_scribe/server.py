# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason-scribe

import shutil
import tempfile
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from coreason_scribe.inspector import SemanticInspector
from coreason_scribe.matrix import ComplianceEngine, ComplianceStatus, TraceabilityMatrixBuilder
from coreason_scribe.models import DraftArtifact
from coreason_scribe.pdf import PDFGenerator
from coreason_scribe.utils.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing Scribe Server components...")
    app.state.inspector = SemanticInspector()
    app.state.matrix_builder = TraceabilityMatrixBuilder()
    app.state.pdf_generator = PDFGenerator()
    yield
    # Shutdown
    logger.info("Scribe Server shutting down...")


app = FastAPI(
    title="CoReason Scribe API",
    version="0.2.0",
    lifespan=lifespan,
    description="Compliance Officer in a Box - GxP Documentation Microservice",
)


@app.post("/draft", response_model=DraftArtifact)
async def create_draft(
    version: Annotated[str, Form()],
    agent_yaml: Annotated[Optional[UploadFile], File()] = None,
    assay_report: Annotated[Optional[UploadFile], File()] = None,
):
    logger.info(f"Received draft request for version {version}")

    # Initialize DraftArtifact
    artifact = DraftArtifact(
        version=version,
        timestamp=datetime.now(timezone.utc),
        sections=[],  # Empty sections as source code is not provided
    )

    # Use a temporary directory for processing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Process uploads
        if agent_yaml:
            yaml_path = temp_path / "agent.yaml"
            with open(yaml_path, "wb") as f:
                shutil.copyfileobj(agent_yaml.file, f)
            try:
                # Validate requirements
                reqs = app.state.matrix_builder.load_requirements(yaml_path)
                logger.info(f"Validated {len(reqs)} requirements from agent.yaml")
            except Exception as e:
                raise HTTPException(status_code=422, detail=f"Invalid agent.yaml: {str(e)}")

        if assay_report:
            report_path = temp_path / "assay_report.json"
            with open(report_path, "wb") as f:
                shutil.copyfileobj(assay_report.file, f)
            try:
                # Validate report
                report = app.state.matrix_builder.load_assay_report(report_path)
                logger.info(f"Validated assay report {report.id} with {len(report.results)} results")
            except Exception as e:
                raise HTTPException(status_code=422, detail=f"Invalid assay_report.json: {str(e)}")

        # Generate PDF
        pdf_path = temp_path / "sds.pdf"
        try:
            app.state.pdf_generator.generate_sds(artifact, pdf_path)
            if not pdf_path.exists() or pdf_path.stat().st_size == 0:
                raise Exception("PDF file was not created or is empty")
            logger.info(f"Generated SDS at {pdf_path}")
        except Exception as e:
            logger.error(f"Failed to generate PDF: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")

    return artifact


@app.post("/check")
async def check_compliance(
    agent_yaml: Annotated[UploadFile, File()],
    assay_report: Annotated[UploadFile, File()],
):
    logger.info("Received compliance check request")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Save uploaded files
        yaml_path = temp_path / "agent.yaml"
        report_path = temp_path / "assay_report.json"

        with open(yaml_path, "wb") as f:
            shutil.copyfileobj(agent_yaml.file, f)

        with open(report_path, "wb") as f:
            shutil.copyfileobj(assay_report.file, f)

        try:
            # Load and parse
            reqs = app.state.matrix_builder.load_requirements(yaml_path)
            report = app.state.matrix_builder.load_assay_report(report_path)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Invalid input files: {str(e)}")

        # Evaluate compliance
        try:
            statuses = app.state.matrix_builder.compliance_engine.evaluate_compliance(reqs, report)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Compliance evaluation failed: {str(e)}")

        # Check for critical gaps
        has_critical_gap = any(status == ComplianceStatus.CRITICAL_GAP for status in statuses.values())

        if has_critical_gap:
            return JSONResponse(status_code=422, content={k: v.value for k, v in statuses.items()})

        return {k: v.value for k, v in statuses.items()}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "0.2.0"}
