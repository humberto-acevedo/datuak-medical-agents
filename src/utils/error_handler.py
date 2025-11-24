"""Comprehensive error handling system for medical record analysis."""
import logging
import traceback
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from enum import Enum
import json

from .audit_logger import AuditLogger
from ..models import (
    MedicalAnalysisError, XMLParsingError, DataValidationError, 
    ResearchError, ReportError, S3Error, AgentCommunicationError,
    HallucinationDetectedError
)

logger = logging.getLogger(__name__)

class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    """Error categories for classification."""
    SYSTEM = "system"
    DATA = "data"
    NETWORK = "network"
    SECURITY = "security"
    BUSINESS_LOGIC = "business_logic"
    EXTERNAL_API = "external_api"
    USER_INPUT = "user_input"

class ErrorContext:
    """Context information for error handling."""
    
    def __init__(self, 
                 operation: str,
                 patient_id: Optional[str] = None,
                 component: Optional[str] = None,
                 additional_data: Optional[Dict[str, Any]] = None):
        self.operation = operation
        self.patient_id = patient_id
        self.component = component
        self.additional_data = additional_data or {}
        self.timestamp = datetime.now()
        self.error_id = self._generate_error_id()
    
    def _generate_error_id(self) -> str:
        """Generate unique error ID."""
        timestamp = self.timestamp.strftime("%Y%m%d_%H%M%S")
        return f"ERR_{timestamp}_{hash(self.operation) % 10000:04d}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "error_id": self.error_id,
            "operation": self.operation,
            "patient_id": self.patient_id,
            "component": self.component,
            "timestamp": self.timestamp.isoformat(),
            "additional_data": self.additional_data
        }

class ErrorHandler:
    """Comprehensive error handling system."""
    
    def __init__(self, audit_logger: Optional[AuditLogger] = None):
        """
        Initialize error handler.
        
        Args:
            audit_logger: Optional audit logger for HIPAA compliance
        """
        self.audit_logger = audit_logger
        self.error_callbacks: Dict[str, List[Callable]] = {}
        self.error_statistics = {
            "total_errors": 0,
            "errors_by_category": {},
            "errors_by_severity": {},
            "recent_errors": []
        }
        
        # Error classification mapping
        self.error_classification = {
            XMLParsingError: (ErrorCategory.DATA, ErrorSeverity.HIGH),
            DataValidationError: (ErrorCategory.DATA, ErrorSeverity.MEDIUM),
            ResearchError: (ErrorCategory.EXTERNAL_API, ErrorSeverity.MEDIUM),
            ReportError: (ErrorCategory.BUSINESS_LOGIC, ErrorSeverity.HIGH),
            S3Error: (ErrorCategory.NETWORK, ErrorSeverity.HIGH),
            AgentCommunicationError: (ErrorCategory.SYSTEM, ErrorSeverity.HIGH),
            HallucinationDetectedError: (ErrorCategory.SECURITY, ErrorSeverity.CRITICAL),
            ConnectionError: (ErrorCategory.NETWORK, ErrorSeverity.HIGH),
            TimeoutError: (ErrorCategory.NETWORK, ErrorSeverity.MEDIUM),
            PermissionError: (ErrorCategory.SECURITY, ErrorSeverity.CRITICAL),
            ValueError: (ErrorCategory.DATA, ErrorSeverity.MEDIUM),
            KeyError: (ErrorCategory.DATA, ErrorSeverity.MEDIUM),
            FileNotFoundError: (ErrorCategory.SYSTEM, ErrorSeverity.MEDIUM)
        }
        
        logger.info("Error handler initialized")
    
    def handle_error(self, 
                    error: Exception, 
                    context: ErrorContext,
                    recovery_action: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle an error with comprehensive logging and classification.
        
        Args:
            error: The exception that occurred
            context: Error context information
            recovery_action: Optional description of recovery action taken
            
        Returns:
            Dict[str, Any]: Error handling result with metadata
        """
        try:
            # Classify error
            category, severity = self._classify_error(error)

            # Defensive: ensure category/severity are Enum instances (they may sometimes be strings)
            try:
                if not isinstance(category, ErrorCategory):
                    category = ErrorCategory(category)
                if not isinstance(severity, ErrorSeverity):
                    severity = ErrorSeverity(severity)
            except Exception:
                logger.warning("Error classification returned unexpected types; falling back to SYSTEM/HIGH")
                category = ErrorCategory.SYSTEM
                severity = ErrorSeverity.HIGH
            
            # Create error record (use safe conversions for category/severity)
            category_value = category.value if isinstance(category, ErrorCategory) else str(category)
            severity_value = severity.value if isinstance(severity, ErrorSeverity) else str(severity)

            error_record = {
                "error_id": context.error_id,
                "error_type": type(error).__name__,
                "error_message": str(error),
                "category": category_value,
                "severity": severity_value,
                "context": context.to_dict(),
                "recovery_action": recovery_action,
                "stack_trace": traceback.format_exc(),
                "timestamp": datetime.now().isoformat()
            }
            
            # Log error
            self._log_error(error_record, severity)
            
            # Update statistics
            self._update_error_statistics(category, severity, error_record)
            
            # Audit log for HIPAA compliance
            if self.audit_logger and context.patient_id:
                self.audit_logger.log_error(
                    operation=context.operation,
                    component=context.component or "error_handler",
                    error=error,
                    patient_id=context.patient_id,
                    additional_context={
                        "error_id": context.error_id,
                        "category": category_value,
                        "severity": severity_value,
                        "recovery_action": recovery_action
                    }
                )
            
            # Execute error callbacks
            self._execute_error_callbacks(error_record)
            
            # Determine if error is recoverable
            is_recoverable = self._is_recoverable_error(error, severity)
            
            return {
                "error_id": context.error_id,
                "handled": True,
                "severity": severity_value if isinstance(severity_value, str) else severity_value,
                "category": category_value if isinstance(category_value, str) else category_value,
                "is_recoverable": is_recoverable,
                "recovery_action": recovery_action,
                "user_message": self._generate_user_message(error, severity, category)
            }
            
        except Exception as handler_error:
            # Error in error handler - log and return basic info
            logger.critical(f"Error handler failed: {str(handler_error)}")
            return {
                "error_id": context.error_id,
                "handled": False,
                "severity": "critical",
                "category": "system",
                "is_recoverable": False,
                "user_message": "A system error occurred. Please contact support."
            }
    
    def _classify_error(self, error: Exception) -> tuple[ErrorCategory, ErrorSeverity]:
        """Classify error by category and severity."""
        error_type = type(error)
        
        # Check exact type match first
        if error_type in self.error_classification:
            category, severity = self.error_classification[error_type]
            # If mapping contains raw values (e.g., strings), log them for diagnostics
            if not isinstance(category, ErrorCategory) or not isinstance(severity, ErrorSeverity):
                logger.warning(
                    "Raw classification types detected: category=%r (%s), severity=%r (%s)",
                    category, type(category), severity, type(severity)
                )
            return category, severity

        # Check inheritance hierarchy
        for error_class, (category, severity) in self.error_classification.items():
            if isinstance(error, error_class):
                if not isinstance(category, ErrorCategory) or not isinstance(severity, ErrorSeverity):
                    logger.warning(
                        "Raw classification types detected (inherited match): category=%r (%s), severity=%r (%s)",
                        category, type(category), severity, type(severity)
                    )
                return category, severity

        # Default classification for unknown errors
        return ErrorCategory.SYSTEM, ErrorSeverity.HIGH
    
    def _log_error(self, error_record: Dict[str, Any], severity: ErrorSeverity):
        """Log error with appropriate level."""
        log_message = (
            f"[{error_record['error_id']}] {error_record['error_type']}: "
            f"{error_record['error_message']} "
            f"(Category: {error_record['category']}, Severity: {error_record['severity']})"
        )
        
        if severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message, extra={"error_record": error_record})
        elif severity == ErrorSeverity.HIGH:
            logger.error(log_message, extra={"error_record": error_record})
        elif severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message, extra={"error_record": error_record})
        else:
            logger.info(log_message, extra={"error_record": error_record})
    
    def _update_error_statistics(self, category: ErrorCategory, 
                               severity: ErrorSeverity, 
                               error_record: Dict[str, Any]):
        """Update error statistics."""
        self.error_statistics["total_errors"] += 1

        # Update category statistics
        cat_key = category.value if isinstance(category, ErrorCategory) else str(category)
        if cat_key not in self.error_statistics["errors_by_category"]:
            self.error_statistics["errors_by_category"][cat_key] = 0
        self.error_statistics["errors_by_category"][cat_key] += 1

        # Update severity statistics
        sev_key = severity.value if isinstance(severity, ErrorSeverity) else str(severity)
        if sev_key not in self.error_statistics["errors_by_severity"]:
            self.error_statistics["errors_by_severity"][sev_key] = 0
        self.error_statistics["errors_by_severity"][sev_key] += 1
        
        # Keep recent errors (last 100)
        self.error_statistics["recent_errors"].append({
            "error_id": error_record["error_id"],
            "error_type": error_record["error_type"],
            "category": cat_key,
            "severity": sev_key,
            "timestamp": error_record["timestamp"]
        })
        
        # Limit recent errors list
        if len(self.error_statistics["recent_errors"]) > 100:
            self.error_statistics["recent_errors"] = self.error_statistics["recent_errors"][-100:]
    
    def _execute_error_callbacks(self, error_record: Dict[str, Any]):
        """Execute registered error callbacks."""
        error_type = error_record["error_type"]
        
        # Execute type-specific callbacks
        if error_type in self.error_callbacks:
            for callback in self.error_callbacks[error_type]:
                try:
                    callback(error_record)
                except Exception as callback_error:
                    logger.warning(f"Error callback failed: {str(callback_error)}")
        
        # Execute general callbacks
        if "*" in self.error_callbacks:
            for callback in self.error_callbacks["*"]:
                try:
                    callback(error_record)
                except Exception as callback_error:
                    logger.warning(f"General error callback failed: {str(callback_error)}")
    
    def _is_recoverable_error(self, error: Exception, severity: ErrorSeverity) -> bool:
        """Determine if error is recoverable."""
        # Critical and security errors are generally not recoverable
        if severity == ErrorSeverity.CRITICAL:
            return False
        
        # Specific error types that are recoverable
        recoverable_types = {
            ResearchError,  # Can continue without research
            ConnectionError,  # Can retry
            TimeoutError,  # Can retry
            DataValidationError  # Can skip invalid data
        }
        
        return type(error) in recoverable_types or isinstance(error, tuple(recoverable_types))
    
    def _generate_user_message(self, error: Exception, 
                             severity: ErrorSeverity, 
                             category: ErrorCategory) -> str:
        """Generate user-friendly error message."""
        error_type = type(error).__name__
        
        # Specific messages for known error types
        user_messages = {
            "XMLParsingError": "Unable to parse patient medical record. Please verify the patient name and try again.",
            "DataValidationError": "Invalid data detected in medical record. Analysis may be incomplete.",
            "ResearchError": "Unable to access medical research databases. Analysis will continue without research correlation.",
            "ReportError": "Unable to generate analysis report. Please try again or contact support.",
            "S3Error": "Unable to save analysis report. The analysis was completed but storage failed.",
            "AgentCommunicationError": "System communication error occurred. Please try again.",
            "HallucinationDetectedError": "Potential data integrity issue detected. Analysis has been halted for review.",
            "ConnectionError": "Network connection error. Please check your connection and try again.",
            "TimeoutError": "Operation timed out. Please try again or contact support if the problem persists.",
            "PermissionError": "Access denied. Please check your permissions or contact an administrator."
        }
        
        if error_type in user_messages:
            return user_messages[error_type]
        
        # Generic messages based on severity
        if severity == ErrorSeverity.CRITICAL:
            return "A critical system error occurred. Please contact support immediately."
        elif severity == ErrorSeverity.HIGH:
            return "A significant error occurred. The operation could not be completed."
        elif severity == ErrorSeverity.MEDIUM:
            return "An error occurred, but the operation may have partially completed."
        else:
            return "A minor issue was encountered. The operation should continue normally."
    
    def register_error_callback(self, error_type: str, callback: Callable[[Dict[str, Any]], None]):
        """Register callback for specific error type."""
        if error_type not in self.error_callbacks:
            self.error_callbacks[error_type] = []
        self.error_callbacks[error_type].append(callback)
        logger.info(f"Registered error callback for {error_type}")
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get current error statistics."""
        return self.error_statistics.copy()
    
    def get_recent_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent errors."""
        return self.error_statistics["recent_errors"][-limit:]
    
    def clear_error_statistics(self):
        """Clear error statistics (for testing or maintenance)."""
        self.error_statistics = {
            "total_errors": 0,
            "errors_by_category": {},
            "errors_by_severity": {},
            "recent_errors": []
        }
        logger.info("Error statistics cleared")

def handle_with_context(operation: str, 
                       patient_id: Optional[str] = None,
                       component: Optional[str] = None,
                       error_handler: Optional[ErrorHandler] = None):
    """Decorator for automatic error handling with context."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            context = ErrorContext(
                operation=operation,
                patient_id=patient_id,
                component=component
            )
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if error_handler:
                    result = error_handler.handle_error(e, context)
                    if not result["is_recoverable"]:
                        raise
                    logger.warning(f"Recovered from error: {result['error_id']}")
                    return None
                else:
                    raise
        return wrapper
    return decorator