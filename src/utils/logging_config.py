"""Logging configuration for HIPAA-compliant audit trails."""

import logging
import logging.handlers
import json
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

from ..config import config


class HIIPAAFormatter(logging.Formatter):
    """Custom formatter for HIPAA-compliant logging with audit trails."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with HIPAA compliance considerations."""
        
        # Create base log entry
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add request ID if available
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        
        # Add patient ID if available (for audit trail)
        if hasattr(record, 'patient_id'):
            log_entry['patient_id'] = record.patient_id
        
        # Add operation type for audit
        if hasattr(record, 'operation'):
            log_entry['operation'] = record.operation
        
        # Add AWS account info for compliance
        log_entry['aws_account'] = config.aws.account_id
        log_entry['aws_region'] = config.aws.region
        
        # Sanitize message to remove potential PII
        log_entry['message'] = self._sanitize_message(log_entry['message'])
        
        return json.dumps(log_entry)
    
    def _sanitize_message(self, message: str) -> str:
        """
        Sanitize log message to remove potential PII while preserving audit value.
        
        Args:
            message: Original log message
            
        Returns:
            Sanitized message safe for logging
        """
        # Replace potential patient names with placeholders
        import re
        
        # Replace email addresses
        message = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', message)
        
        # Replace phone numbers
        message = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', message)
        
        # Replace SSN patterns
        message = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]', message)
        
        # Replace potential names in XML content (basic pattern)
        message = re.sub(r'<name>.*?</name>', '<name>[PATIENT_NAME]</name>', message, flags=re.IGNORECASE)
        
        return message


class AuditLogger:
    """Specialized logger for HIPAA audit trails."""
    
    def __init__(self, name: str = "medical_analysis_audit"):
        """Initialize audit logger with HIPAA compliance."""
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Prevent duplicate handlers
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self):
        """Set up logging handlers for audit trail."""
        
        # Create logs directory
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Audit file handler (rotating for long-term storage)
        audit_handler = logging.handlers.RotatingFileHandler(
            log_dir / "audit.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=10
        )
        audit_handler.setLevel(logging.INFO)
        audit_handler.setFormatter(HIIPAAFormatter())
        
        # Error file handler
        error_handler = logging.handlers.RotatingFileHandler(
            log_dir / "errors.log",
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=5
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(HIIPAAFormatter())
        
        # Console handler for development
        if config.app.environment == "development":
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(HIIPAAFormatter())
            self.logger.addHandler(console_handler)
        
        self.logger.addHandler(audit_handler)
        self.logger.addHandler(error_handler)
    
    def log_data_access(self, patient_id: str, operation: str, 
                       details: Optional[Dict[str, Any]] = None, 
                       request_id: Optional[str] = None):
        """
        Log patient data access for HIPAA audit trail.
        
        Args:
            patient_id: Patient identifier
            operation: Type of operation (read, write, delete, etc.)
            details: Additional operation details
            request_id: Request identifier for tracing
        """
        extra = {
            'patient_id': patient_id,
            'operation': operation,
            'request_id': request_id or self._generate_request_id()
        }
        
        message = f"Data access: {operation} for patient {patient_id}"
        if details:
            message += f" - Details: {json.dumps(details)}"
        
        self.logger.info(message, extra=extra)
    
    def log_processing_start(self, patient_id: str, workflow_type: str, 
                           request_id: Optional[str] = None):
        """Log start of patient data processing."""
        extra = {
            'patient_id': patient_id,
            'operation': f'processing_start_{workflow_type}',
            'request_id': request_id or self._generate_request_id()
        }
        
        self.logger.info(f"Processing started: {workflow_type} for patient {patient_id}", extra=extra)
    
    def log_processing_complete(self, patient_id: str, workflow_type: str, 
                              duration_seconds: float, request_id: Optional[str] = None):
        """Log completion of patient data processing."""
        extra = {
            'patient_id': patient_id,
            'operation': f'processing_complete_{workflow_type}',
            'request_id': request_id or self._generate_request_id()
        }
        
        message = f"Processing completed: {workflow_type} for patient {patient_id} in {duration_seconds:.2f}s"
        self.logger.info(message, extra=extra)
    
    def log_error(self, patient_id: str, operation: str, error: Exception, 
                  request_id: Optional[str] = None):
        """Log processing errors with audit trail."""
        extra = {
            'patient_id': patient_id,
            'operation': f'error_{operation}',
            'request_id': request_id or self._generate_request_id()
        }
        
        message = f"Error in {operation} for patient {patient_id}: {str(error)}"
        self.logger.error(message, extra=extra, exc_info=True)
    
    def _generate_request_id(self) -> str:
        """Generate unique request ID for tracing."""
        import uuid
        return str(uuid.uuid4())


def setup_logging() -> AuditLogger:
    """
    Set up application logging with HIPAA compliance.
    
    Returns:
        Configured AuditLogger instance
    """
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, config.app.log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create audit logger
    audit_logger = AuditLogger()
    
    # Log system startup
    audit_logger.logger.info(
        f"Medical Analysis System started - Environment: {config.app.environment}, "
        f"Region: {config.aws.region}, Account: {config.aws.account_id}"
    )
    
    return audit_logger