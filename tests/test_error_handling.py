"""Tests for comprehensive error handling system."""
import pytest
import logging
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.utils.error_handler import (
    ErrorHandler, ErrorContext, ErrorSeverity, ErrorCategory,
    handle_with_context
)
from src.utils.audit_logger import AuditLogger, AuditOutcome
from src.models.exceptions import (
    XMLParsingError, DataValidationError, ResearchError,
    ReportError, S3Error, AgentCommunicationError, HallucinationDetectedError
)

class TestErrorContext:
    """Test ErrorContext class."""
    
    def test_error_context_creation(self):
        """Test error context creation."""
        context = ErrorContext(
            operation="test_operation",
            patient_id="PATIENT123",
            component="test_component",
            additional_data={"key": "value"}
        )
        
        assert context.operation == "test_operation"
        assert context.patient_id == "PATIENT123"
        assert context.component == "test_component"
        assert context.additional_data == {"key": "value"}
        assert context.error_id.startswith("ERR_")
        assert isinstance(context.timestamp, datetime)
    
    def test_error_context_to_dict(self):
        """Test error context dictionary conversion."""
        context = ErrorContext(
            operation="test_operation",
            patient_id="PATIENT123"
        )
        
        context_dict = context.to_dict()
        
        assert context_dict["operation"] == "test_operation"
        assert context_dict["patient_id"] == "PATIENT123"
        assert "error_id" in context_dict
        assert "timestamp" in context_dict

class TestErrorHandler:
    """Test ErrorHandler class."""
    
    @pytest.fixture
    def mock_audit_logger(self):
        """Create mock audit logger."""
        return Mock(spec=AuditLogger)
    
    @pytest.fixture
    def error_handler(self, mock_audit_logger):
        """Create error handler with mock audit logger."""
        return ErrorHandler(audit_logger=mock_audit_logger)
    
    def test_error_handler_initialization(self, error_handler):
        """Test error handler initialization."""
        assert error_handler.audit_logger is not None
        assert error_handler.error_callbacks == {}
        assert error_handler.error_statistics["total_errors"] == 0
    
    def test_error_classification(self, error_handler):
        """Test error classification."""
        # Test known error types
        xml_error = XMLParsingError("XML parsing failed")
        category, severity = error_handler._classify_error(xml_error)
        assert category == ErrorCategory.DATA
        assert severity == ErrorSeverity.HIGH
        
        # Test unknown error type
        unknown_error = RuntimeError("Unknown error")
        category, severity = error_handler._classify_error(unknown_error)
        assert category == ErrorCategory.SYSTEM
        assert severity == ErrorSeverity.HIGH
    
    def test_handle_error_basic(self, error_handler):
        """Test basic error handling."""
        error = ValueError("Test error")
        context = ErrorContext("test_operation", "PATIENT123", "test_component")
        
        result = error_handler.handle_error(error, context)
        
        assert result["handled"] is True
        assert result["error_id"] == context.error_id
        assert result["severity"] == "medium"
        assert result["category"] == "data"
        assert "user_message" in result
    
    def test_handle_error_with_recovery(self, error_handler):
        """Test error handling with recovery action."""
        error = ResearchError("Research API unavailable")
        context = ErrorContext("research_search", "PATIENT123", "research_searcher")
        recovery_action = "Continuing analysis without research correlation"
        
        result = error_handler.handle_error(error, context, recovery_action)
        
        assert result["handled"] is True
        assert result["is_recoverable"] is True
        assert result["recovery_action"] == recovery_action
    
    def test_handle_critical_error(self, error_handler):
        """Test handling of critical errors."""
        error = HallucinationDetectedError("Potential hallucination detected")
        context = ErrorContext("analysis", "PATIENT123", "medical_summarizer")
        
        result = error_handler.handle_error(error, context)
        
        assert result["handled"] is True
        assert result["severity"] == "critical"
        assert result["is_recoverable"] is False
    
    def test_error_statistics_update(self, error_handler):
        """Test error statistics updates."""
        initial_stats = error_handler.get_error_statistics()
        assert initial_stats["total_errors"] == 0
        
        # Handle an error
        error = DataValidationError("Invalid data")
        context = ErrorContext("validation", "PATIENT123", "validator")
        error_handler.handle_error(error, context)
        
        updated_stats = error_handler.get_error_statistics()
        assert updated_stats["total_errors"] == 1
        assert "data" in updated_stats["errors_by_category"]
        assert "medium" in updated_stats["errors_by_severity"]
    
    def test_audit_logging_integration(self, error_handler, mock_audit_logger):
        """Test integration with audit logger."""
        error = XMLParsingError("XML parsing failed")
        context = ErrorContext("xml_parsing", "PATIENT123", "xml_parser")
        
        error_handler.handle_error(error, context)
        
        # Verify audit logger was called
        mock_audit_logger.log_error.assert_called_once()
        call_args = mock_audit_logger.log_error.call_args
        assert call_args[1]["patient_id"] == "PATIENT123"
        assert call_args[1]["operation"] == "xml_parsing"
        assert call_args[1]["error"] == error
    
    def test_error_callbacks(self, error_handler):
        """Test error callback registration and execution."""
        callback_called = False
        callback_data = None
        
        def test_callback(error_record):
            nonlocal callback_called, callback_data
            callback_called = True
            callback_data = error_record
        
        # Register callback
        error_handler.register_error_callback("ValueError", test_callback)
        
        # Handle error
        error = ValueError("Test error")
        context = ErrorContext("test", "PATIENT123", "test")
        error_handler.handle_error(error, context)
        
        assert callback_called is True
        assert callback_data["error_type"] == "ValueError"
    
    def test_user_message_generation(self, error_handler):
        """Test user-friendly message generation."""
        # Test specific error message
        error = XMLParsingError("XML parsing failed")
        context = ErrorContext("xml_parsing", "PATIENT123", "xml_parser")
        result = error_handler.handle_error(error, context)
        
        assert "Unable to parse patient medical record" in result["user_message"]
        
        # Test generic error message
        error = RuntimeError("Unknown error")
        context = ErrorContext("unknown", "PATIENT123", "unknown")
        result = error_handler.handle_error(error, context)
        
        assert "significant error occurred" in result["user_message"]
    
    def test_recoverable_error_detection(self, error_handler):
        """Test recoverable error detection."""
        # Recoverable error
        recoverable_error = ResearchError("API timeout")
        assert error_handler._is_recoverable_error(recoverable_error, ErrorSeverity.MEDIUM) is True
        
        # Non-recoverable error
        critical_error = HallucinationDetectedError("Hallucination detected")
        assert error_handler._is_recoverable_error(critical_error, ErrorSeverity.CRITICAL) is False
    
    def test_recent_errors_tracking(self, error_handler):
        """Test recent errors tracking."""
        # Handle multiple errors
        for i in range(5):
            error = ValueError(f"Error {i}")
            context = ErrorContext(f"operation_{i}", "PATIENT123", "test")
            error_handler.handle_error(error, context)
        
        recent_errors = error_handler.get_recent_errors(3)
        assert len(recent_errors) == 3
        assert recent_errors[-1]["error_type"] == "ValueError"
    
    def test_error_statistics_clearing(self, error_handler):
        """Test error statistics clearing."""
        # Handle an error
        error = ValueError("Test error")
        context = ErrorContext("test", "PATIENT123", "test")
        error_handler.handle_error(error, context)
        
        assert error_handler.get_error_statistics()["total_errors"] == 1
        
        # Clear statistics
        error_handler.clear_error_statistics()
        assert error_handler.get_error_statistics()["total_errors"] == 0

class TestErrorHandlerDecorator:
    """Test error handler decorator."""
    
    @pytest.fixture
    def error_handler(self):
        """Create error handler."""
        return ErrorHandler()
    
    def test_decorator_success(self, error_handler):
        """Test decorator with successful operation."""
        @handle_with_context("test_operation", "PATIENT123", "test_component", error_handler)
        def successful_function():
            return "success"
        
        result = successful_function()
        assert result == "success"
    
    def test_decorator_recoverable_error(self, error_handler):
        """Test decorator with recoverable error."""
        @handle_with_context("test_operation", "PATIENT123", "test_component", error_handler)
        def recoverable_error_function():
            raise ResearchError("API unavailable")
        
        # Should return None for recoverable error
        result = recoverable_error_function()
        assert result is None
    
    def test_decorator_non_recoverable_error(self, error_handler):
        """Test decorator with non-recoverable error."""
        @handle_with_context("test_operation", "PATIENT123", "test_component", error_handler)
        def critical_error_function():
            raise HallucinationDetectedError("Critical error")
        
        # Should re-raise non-recoverable error
        with pytest.raises(HallucinationDetectedError):
            critical_error_function()
    
    def test_decorator_without_error_handler(self):
        """Test decorator without error handler."""
        @handle_with_context("test_operation", "PATIENT123", "test_component", None)
        def error_function():
            raise ValueError("Test error")
        
        # Should re-raise error when no error handler
        with pytest.raises(ValueError):
            error_function()

class TestErrorHandlerIntegration:
    """Test error handler integration scenarios."""
    
    def test_multiple_error_types(self):
        """Test handling multiple different error types."""
        error_handler = ErrorHandler()
        
        errors = [
            (XMLParsingError("XML error"), "xml_parser"),
            (DataValidationError("Validation error"), "validator"),
            (ResearchError("Research error"), "research_searcher"),
            (ReportError("Report error"), "report_generator"),
            (S3Error("S3 error"), "s3_persister")
        ]
        
        for error, component in errors:
            context = ErrorContext("test_operation", "PATIENT123", component)
            result = error_handler.handle_error(error, context)
            assert result["handled"] is True
        
        stats = error_handler.get_error_statistics()
        assert stats["total_errors"] == len(errors)
    
    def test_error_handler_failure_recovery(self):
        """Test error handler's own error recovery."""
        # Create error handler with problematic audit logger
        problematic_audit_logger = Mock()
        problematic_audit_logger.log_error.side_effect = Exception("Audit logger failed")
        
        error_handler = ErrorHandler(audit_logger=problematic_audit_logger)
        
        # Should still handle error even if audit logging fails
        error = ValueError("Test error")
        context = ErrorContext("test", "PATIENT123", "test")
        result = error_handler.handle_error(error, context)
        
        assert result["handled"] is True
    
    @patch('src.utils.error_handler.logger')
    def test_logging_integration(self, mock_logger):
        """Test integration with logging system."""
        error_handler = ErrorHandler()
        
        error = XMLParsingError("XML parsing failed")
        context = ErrorContext("xml_parsing", "PATIENT123", "xml_parser")
        error_handler.handle_error(error, context)
        
        # Verify logging was called
        mock_logger.error.assert_called()
        
        # Check log message format
        call_args = mock_logger.error.call_args
        log_message = call_args[0][0]
        assert "XMLParsingError" in log_message
        assert "Category: data" in log_message
        assert "Severity: high" in log_message