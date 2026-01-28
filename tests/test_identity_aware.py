# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason-scribe

import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from coreason_identity.models import UserContext
from coreason_identity.types import SecretStr
from coreason_scribe.signer import ScribeSigner
from coreason_scribe.inspector import ScribeInspector
from coreason_scribe.main import run_sign, run_verify, run_inspect, main, ScribeError

@pytest.fixture
def mock_context():
    return UserContext(
        user_id=SecretStr("test-user"),
        roles=["tester"],
        metadata={}
    )

@pytest.fixture
def pdf_path(tmp_path):
    p = tmp_path / "test.pdf"
    p.write_text("dummy content")
    return p

def test_signer_sign_pdf(mock_context, pdf_path):
    signer = ScribeSigner()
    # It should succeed
    signer.sign_pdf(pdf_path, mock_context)

def test_signer_verify_signature(mock_context, pdf_path):
    signer = ScribeSigner()
    assert signer.verify_signature(pdf_path, mock_context) is True

def test_inspector_inspect_pdf(mock_context, pdf_path):
    inspector = ScribeInspector()
    res = inspector.inspect_pdf(pdf_path, mock_context)
    assert isinstance(res, dict)

def test_missing_context_raises(pdf_path):
    signer = ScribeSigner()
    with pytest.raises(ValueError):
        signer.sign_pdf(pdf_path, None)

def test_missing_file_raises(mock_context, tmp_path):
    signer = ScribeSigner()
    with pytest.raises(FileNotFoundError):
        signer.sign_pdf(tmp_path / "nonexistent.pdf", mock_context)

# Coverage tests
def test_inspector_missing_context(pdf_path):
    inspector = ScribeInspector()
    with pytest.raises(ValueError):
        inspector.inspect_pdf(pdf_path, None)

def test_inspector_missing_file(mock_context, tmp_path):
    inspector = ScribeInspector()
    with pytest.raises(FileNotFoundError):
        inspector.inspect_pdf(tmp_path / "nonexistent.pdf", mock_context)

def test_signer_verify_missing_context(pdf_path):
    signer = ScribeSigner()
    with pytest.raises(ValueError):
        signer.verify_signature(pdf_path, None)

def test_signer_verify_missing_file(mock_context, tmp_path):
    signer = ScribeSigner()
    with pytest.raises(FileNotFoundError):
        signer.verify_signature(tmp_path / "nonexistent.pdf", mock_context)

# Test CLI integration
@patch("coreason_scribe.main.ScribeSigner")
@patch("coreason_scribe.main.UserContext")
def test_cli_sign(mock_uc_cls, mock_signer_cls, pdf_path):
    mock_signer = mock_signer_cls.return_value

    run_sign(pdf_path)

    mock_signer.sign_pdf.assert_called_once()

    # Verify UserContext initialization
    call_args = mock_uc_cls.call_args
    assert call_args.kwargs['user_id'].get_secret_value() == "cli-user"
    assert call_args.kwargs['roles'] == ["system"]

@patch("coreason_scribe.main.ScribeSigner")
def test_cli_verify(mock_signer_cls, pdf_path):
    mock_signer = mock_signer_cls.return_value
    run_verify(pdf_path)
    mock_signer.verify_signature.assert_called_once()

@patch("coreason_scribe.main.ScribeInspector")
def test_cli_inspect(mock_inspector_cls, pdf_path):
    mock_inspector = mock_inspector_cls.return_value
    run_inspect(pdf_path)
    mock_inspector.inspect_pdf.assert_called_once()

# CLI Exception tests
@patch("coreason_scribe.main.ScribeSigner")
def test_cli_sign_error(mock_signer_cls, pdf_path):
    mock_signer = mock_signer_cls.return_value
    mock_signer.sign_pdf.side_effect = Exception("Boom")
    with pytest.raises(ScribeError):
        run_sign(pdf_path)

@patch("coreason_scribe.main.ScribeSigner")
def test_cli_verify_error(mock_signer_cls, pdf_path):
    mock_signer = mock_signer_cls.return_value
    mock_signer.verify_signature.side_effect = Exception("Boom")
    with pytest.raises(ScribeError):
        run_verify(pdf_path)

@patch("coreason_scribe.main.ScribeInspector")
def test_cli_inspect_error(mock_inspector_cls, pdf_path):
    mock_inspector = mock_inspector_cls.return_value
    mock_inspector.inspect_pdf.side_effect = Exception("Boom")
    with pytest.raises(ScribeError):
        run_inspect(pdf_path)

# Main dispatch tests
@patch("coreason_scribe.main.run_sign")
def test_main_sign(mock_run, pdf_path):
    with patch.object(sys, 'argv', ["scribe", "sign", str(pdf_path)]):
        main()
    mock_run.assert_called_with(pdf_path)

@patch("coreason_scribe.main.run_verify")
def test_main_verify(mock_run, pdf_path):
    with patch.object(sys, 'argv', ["scribe", "verify", str(pdf_path)]):
        main()
    mock_run.assert_called_with(pdf_path)

@patch("coreason_scribe.main.run_inspect")
def test_main_inspect(mock_run, pdf_path):
    with patch.object(sys, 'argv', ["scribe", "inspect", str(pdf_path)]):
        main()
    mock_run.assert_called_with(pdf_path)
