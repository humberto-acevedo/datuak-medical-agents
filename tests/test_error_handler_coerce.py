import logging
import pytest
from src.utils.error_handler import ErrorHandler, ErrorContext

class DummyError(Exception):
    pass


def test_classification_strings_are_coerced_and_logged(caplog, monkeypatch):
    """
    If the error_classification mapping contains string values instead of Enums,
    the handler should log the raw types and still coerce to enums and return
    valid category/severity strings in the result.
    """
    caplog.set_level(logging.WARNING)

    handler = ErrorHandler()

    # Inject a problematic mapping that uses plain strings
    handler.error_classification[DummyError] = ("network", "high")

    context = ErrorContext(operation="test_op")

    # Call handle_error and make sure it does not raise
    result = handler.handle_error(DummyError("boom"), context)

    # The handler should coerce to enums and return string values for category/severity
    assert result["category"] == "network"
    assert result["severity"] == "high"

    # And the logs should contain a warning about raw classification types
    warnings = [r.message for r in caplog.records if r.levelno == logging.WARNING]
    found = any("Raw classification types detected" in str(m) for m in warnings)
    assert found, f"Expected raw classification warning in logs, got: {warnings}"
