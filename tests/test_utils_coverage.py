from pathlib import Path

from coreason_scribe.utils.logger import logger


def test_logger_setup() -> None:
    assert logger is not None

    # Check if logs directory exists (it should be created by the module import)
    log_path = Path("logs")
    assert log_path.exists()

    # Test logging
    logger.info("Test log message")


def test_logger_mkdir_coverage() -> None:
    import importlib
    import shutil

    import coreason_scribe.utils.logger

    # Remove logs directory if it exists
    log_path = Path("logs")
    if log_path.exists():
        shutil.rmtree(log_path)

    # Reload the module
    importlib.reload(coreason_scribe.utils.logger)

    # Check if created
    assert log_path.exists()
