"""Compatibility wrapper exposing a single AuditLogger implementation.

This module keeps the `initialize_audit_logging` and `get_audit_logger`
API stable while delegating to the single source-of-truth
implementation `src.utils.logging_config.AuditLogger`.
"""
from typing import Optional
from pathlib import Path
import warnings

from .logging_config import AuditLogger as LoggingAuditLogger

# Module-level global logger instance
_audit_logger: Optional[LoggingAuditLogger] = None

# Backwards-compatible name: some modules import `AuditLogger` directly
# from `src.utils.audit_logger`. Expose the class under that name.
AuditLogger = LoggingAuditLogger


"""HIPAA-compliant audit logging system for medical record analysis."""
import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
import hashlib
import uuid
from enum import Enum
from dataclasses import dataclass, asdict


class AuditEventType(Enum):
    """HIPAA audit event types."""
    ACCESS = "access"
    MODIFICATION = "modification"
    CREATION = "creation"
    DELETION = "deletion"
    EXPORT = "export"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    ERROR = "error"
    SYSTEM_EVENT = "system_event"


class AuditOutcome(Enum):
    """Audit event outcomes."""
    SUCCESS = "success"
    FAILURE = "failure"
    WARNING = "warning"


@dataclass
class AuditEvent:
    """HIPAA audit event structure."""
    event_id: str
    timestamp: str
    event_type: str
    outcome: str
    user_id: Optional[str]
    patient_id: Optional[str]
    operation: str
    component: str
    source_ip: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None
    resource_accessed: Optional[str] = None
    data_elements: Optional[List[str]] = None
    additional_context: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), default=str, ensure_ascii=False)


class AuditLogger:
    """HIPAA-compliant audit logging system."""
    
    def __init__(self, 
                 audit_log_dir: str = "logs/audit",
                 enable_encryption: bool = True,
                 retention_days: int = 2555):  # 7 years for HIPAA
        """
        Initialize audit logger.
        
        Args:
            audit_log_dir: Directory for audit log files
            enable_encryption: Enable log encryption (recommended for production)
            retention_days: Log retention period in days (HIPAA requires 7 years)
        """
        self.audit_log_dir = Path(audit_log_dir)
        self.enable_encryption = enable_encryption
        self.retention_days = retention_days
        
        # Create audit log directory
        self.audit_log_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup audit logger
        self._setup_audit_logger()
        
        # Log system initialization
        self.log_system_event(
            operation="audit_system_initialization",
            component="audit_logger",
            outcome=AuditOutcome.SUCCESS,
            additional_context={"retention_days": retention_days}
        )
    
    def _setup_audit_logger(self):
        """Setup dedicated audit logger."""
        self.logger = logging.getLogger("hipaa_audit")
        self.logger.setLevel(logging.INFO)
        
        # Remove existing handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # Create audit log handler
        audit_file = self.audit_log_dir / f"audit_{datetime.now().strftime('%Y%m%d')}.log"
        handler = logging.FileHandler(audit_file)
        handler.setLevel(logging.INFO)
        
        # Use JSON formatter for structured audit logs
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        
        self.logger.addHandler(handler)
        self.logger.propagate = False  # Don't propagate to root logger
    
    def _generate_event_id(self) -> str:
        """Generate unique event ID."""
        return str(uuid.uuid4())
    
    def _hash_patient_id(self, patient_id: str) -> str:
        """Hash patient ID for privacy protection."""
        if not patient_id:
            return None
        
        # Use SHA-256 hash with salt for patient ID privacy
        salt = "medical_analysis_audit_salt_2024"  # In production, use secure random salt
        return hashlib.sha256(f"{salt}{patient_id}".encode()).hexdigest()[:16]
    
    def _create_audit_event(self,
                           event_type: AuditEventType,
                           outcome: AuditOutcome,
                           operation: str,
                           component: str,
                           patient_id: Optional[str] = None,
                           user_id: Optional[str] = None,
                           source_ip: Optional[str] = None,
                           user_agent: Optional[str] = None,
                           session_id: Optional[str] = None,
                           resource_accessed: Optional[str] = None,
                           data_elements: Optional[List[str]] = None,
                           additional_context: Optional[Dict[str, Any]] = None) -> AuditEvent:
        """Create audit event."""
        return AuditEvent(
            event_id=self._generate_event_id(),
            timestamp=datetime.now().isoformat(),
            event_type=getattr(event_type, 'value', str(event_type)),
            outcome=getattr(outcome, 'value', str(outcome)),
            user_id=user_id,
            patient_id=self._hash_patient_id(patient_id) if patient_id else None,
            operation=operation,
            component=component,
            source_ip=source_ip,
            user_agent=user_agent,
            session_id=session_id,
            resource_accessed=resource_accessed,
            data_elements=data_elements,
            additional_context=additional_context
        )
    
    def _log_audit_event(self, event: AuditEvent):
        """Log audit event."""
        try:
            # Log the event
            self.logger.info(event.to_json())
            
            # Rotate log file daily
            current_date = datetime.now().strftime('%Y%m%d')
            expected_file = self.audit_log_dir / f"audit_{current_date}.log"
            
            # Check if we need to rotate to new file
            current_handler = self.logger.handlers[0]
            if hasattr(current_handler, 'baseFilename'):
                current_file = Path(current_handler.baseFilename)
                if current_file.name != expected_file.name:
                    # Remove old handler and create new one
                    self.logger.removeHandler(current_handler)
                    current_handler.close()
                    
                    # Create new handler for new day
                    new_handler = logging.FileHandler(expected_file)
                    new_handler.setLevel(logging.INFO)
                    formatter = logging.Formatter('%(message)s')
                    new_handler.setFormatter(formatter)
                    self.logger.addHandler(new_handler)
            
        except Exception as e:
            # Critical: audit logging failure
            print(f"CRITICAL: Audit logging failed: {str(e)}")
            # In production, this should trigger alerts
    
    def log_patient_access(self,
                          patient_id: str,
                          operation: str,
                          component: str,
                          outcome: AuditOutcome = AuditOutcome.SUCCESS,
                          user_id: Optional[str] = None,
                          data_elements: Optional[List[str]] = None,
                          additional_context: Optional[Dict[str, Any]] = None):
        """Log patient data access."""
        event = self._create_audit_event(
            event_type=AuditEventType.ACCESS,
            outcome=outcome,
            operation=operation,
            component=component,
            patient_id=patient_id,
            user_id=user_id,
            data_elements=data_elements or ["medical_record", "patient_data"],
            additional_context=additional_context
        )
        self._log_audit_event(event)
    
    def log_data_modification(self,
                             patient_id: str,
                             operation: str,
                             component: str,
                             outcome: AuditOutcome = AuditOutcome.SUCCESS,
                             user_id: Optional[str] = None,
                             data_elements: Optional[List[str]] = None,
                             additional_context: Optional[Dict[str, Any]] = None):
        """Log patient data modification."""
        event = self._create_audit_event(
            event_type=AuditEventType.MODIFICATION,
            outcome=outcome,
            operation=operation,
            component=component,
            patient_id=patient_id,
            user_id=user_id,
            data_elements=data_elements,
            additional_context=additional_context
        )
        self._log_audit_event(event)
    
    def log_report_creation(self,
                           patient_id: str,
                           operation: str,
                           component: str,
                           outcome: AuditOutcome = AuditOutcome.SUCCESS,
                           user_id: Optional[str] = None,
                           report_type: Optional[str] = None,
                           additional_context: Optional[Dict[str, Any]] = None):
        """Log report creation."""
        context = additional_context or {}
        if report_type:
            context["report_type"] = report_type
        
        event = self._create_audit_event(
            event_type=AuditEventType.CREATION,
            outcome=outcome,
            operation=operation,
            component=component,
            patient_id=patient_id,
            user_id=user_id,
            data_elements=["analysis_report", "medical_summary"],
            additional_context=context
        )
        self._log_audit_event(event)
    
    def log_data_export(self,
                       patient_id: str,
                       operation: str,
                       component: str,
                       export_destination: str,
                       outcome: AuditOutcome = AuditOutcome.SUCCESS,
                       user_id: Optional[str] = None,
                       data_elements: Optional[List[str]] = None,
                       additional_context: Optional[Dict[str, Any]] = None):
        """Log data export."""
        context = additional_context or {}
        context["export_destination"] = export_destination
        
        event = self._create_audit_event(
            event_type=AuditEventType.EXPORT,
            outcome=outcome,
            operation=operation,
            component=component,
            patient_id=patient_id,
            user_id=user_id,
            data_elements=data_elements or ["analysis_report"],
            additional_context=context
        )
        self._log_audit_event(event)
    
    def log_authentication(self,
                          user_id: str,
                          operation: str,
                          outcome: AuditOutcome,
                          source_ip: Optional[str] = None,
                          user_agent: Optional[str] = None,
                          additional_context: Optional[Dict[str, Any]] = None):
        """Log authentication events."""
        event = self._create_audit_event(
            event_type=AuditEventType.AUTHENTICATION,
            outcome=outcome,
            operation=operation,
            component="authentication_system",
            user_id=user_id,
            source_ip=source_ip,
            user_agent=user_agent,
            additional_context=additional_context
        )
        self._log_audit_event(event)
    
    def log_authorization(self,
                         user_id: str,
                         operation: str,
                         resource_accessed: str,
                         outcome: AuditOutcome,
                         patient_id: Optional[str] = None,
                         additional_context: Optional[Dict[str, Any]] = None):
        """Log authorization events."""
        event = self._create_audit_event(
            event_type=AuditEventType.AUTHORIZATION,
            outcome=outcome,
            operation=operation,
            component="authorization_system",
            user_id=user_id,
            patient_id=patient_id,
            resource_accessed=resource_accessed,
            additional_context=additional_context
        )
        self._log_audit_event(event)
    
    def log_error(self,
                 operation: str = None,
                 component: str = None,
                 error: Exception = None,
                 patient_id: Optional[str] = None,
                 user_id: Optional[str] = None,
                 request_id: Optional[str] = None,
                 additional_context: Optional[Dict[str, Any]] = None):
        """Log error events.
        
        Supports multiple calling conventions for compatibility:
        - log_error(operation, component, error, ...)
        - log_error(patient_id, operation, error, request_id=...)
        """
        # Handle different calling conventions
        if error is None and isinstance(component, Exception):
            # Called as: log_error(patient_id, operation, error, request_id=...)
            error = component
            component = "unknown"
            if operation and patient_id is None:
                patient_id = operation
                operation = "error"
        
        if operation is None:
            operation = "error"
        if component is None:
            component = "unknown"
        if error is None:
            error = Exception("Unknown error")
        
        context = additional_context or {}
        context.update({
            "error_type": type(error).__name__,
            "error_message": str(error)
        })
        
        if request_id:
            context["request_id"] = request_id
        
        event = self._create_audit_event(
            event_type=AuditEventType.ERROR,
            outcome=AuditOutcome.FAILURE,
            operation=operation,
            component=component,
            patient_id=patient_id,
            user_id=user_id,
            additional_context=context
        )
        self._log_audit_event(event)
    
    def log_processing_start(self,
                            patient_id: str,
                            workflow_type: str = None,
                            operation: str = None,
                            component: str = None,
                            user_id: Optional[str] = None,
                            request_id: Optional[str] = None,
                            additional_context: Optional[Dict[str, Any]] = None):
        """Log the start of processing for a patient."""
        # Support both old and new calling conventions
        if operation is None and workflow_type:
            operation = f"processing_start_{workflow_type}"
        if component is None:
            component = "workflow"
        
        context = additional_context or {}
        if request_id:
            context["request_id"] = request_id
        if workflow_type:
            context["workflow_type"] = workflow_type
        
        event = self._create_audit_event(
            event_type=AuditEventType.ACCESS,
            outcome=AuditOutcome.SUCCESS,
            operation=operation,
            component=component,
            patient_id=patient_id,
            user_id=user_id,
            data_elements=["processing_start"],
            additional_context=context
        )
        self._log_audit_event(event)
    
    def log_data_access(self,
                       patient_id: str,
                       data_source: str = None,
                       operation: str = "data_access",
                       component: str = None,
                       user_id: Optional[str] = None,
                       request_id: Optional[str] = None,
                       details: Optional[Dict[str, Any]] = None,
                       additional_context: Optional[Dict[str, Any]] = None):
        """Log data access events (e.g., S3 retrieval, database query)."""
        if component is None:
            component = "data_access"
        if data_source is None:
            data_source = "unknown"
        
        context = additional_context or {}
        context["data_source"] = data_source
        if request_id:
            context["request_id"] = request_id
        if details:
            context.update(details)
        
        event = self._create_audit_event(
            event_type=AuditEventType.ACCESS,
            outcome=AuditOutcome.SUCCESS,
            operation=operation,
            component=component,
            patient_id=patient_id,
            user_id=user_id,
            data_elements=["patient_record", "xml_data"],
            additional_context=context
        )
        self._log_audit_event(event)
    
    def log_processing_complete(self,
                                patient_id: str,
                                workflow_type: str = None,
                                duration_seconds: float = None,
                                operation: str = None,
                                component: str = None,
                                user_id: Optional[str] = None,
                                request_id: Optional[str] = None,
                                additional_context: Optional[Dict[str, Any]] = None):
        """Log the completion of processing for a patient."""
        # Support both old and new calling conventions
        if operation is None and workflow_type:
            operation = f"processing_complete_{workflow_type}"
        if component is None:
            component = "workflow"
        
        context = additional_context or {}
        if request_id:
            context["request_id"] = request_id
        if workflow_type:
            context["workflow_type"] = workflow_type
        if duration_seconds is not None:
            context["duration_seconds"] = duration_seconds
        
        event = self._create_audit_event(
            event_type=AuditEventType.ACCESS,
            outcome=AuditOutcome.SUCCESS,
            operation=operation,
            component=component,
            patient_id=patient_id,
            user_id=user_id,
            data_elements=["processing_complete"],
            additional_context=context
        )
        self._log_audit_event(event)
    
    def log_system_event(self,
                        operation: str,
                        component: str,
                        outcome: AuditOutcome = AuditOutcome.SUCCESS,
                        additional_context: Optional[Dict[str, Any]] = None):
        """Log system events."""
        event = self._create_audit_event(
            event_type=AuditEventType.SYSTEM_EVENT,
            outcome=outcome,
            operation=operation,
            component=component,
            additional_context=additional_context
        )
        self._log_audit_event(event)
    
    def get_audit_statistics(self) -> Dict[str, Any]:
        """Get audit log statistics."""
        stats = {
            "total_events": 0,
            "events_by_type": {},
            "events_by_outcome": {},
            "events_by_component": {},
            "log_files": []
        }
        
        # Count events in current day's log
        current_date = datetime.now().strftime('%Y%m%d')
        current_log = self.audit_log_dir / f"audit_{current_date}.log"
        
        if current_log.exists():
            try:
                with open(current_log, 'r') as f:
                    for line in f:
                        try:
                            event_data = json.loads(line.strip())
                            stats["total_events"] += 1
                            
                            # Count by type
                            event_type = event_data.get("event_type", "unknown")
                            stats["events_by_type"][event_type] = stats["events_by_type"].get(event_type, 0) + 1
                            
                            # Count by outcome
                            outcome = event_data.get("outcome", "unknown")
                            stats["events_by_outcome"][outcome] = stats["events_by_outcome"].get(outcome, 0) + 1
                            
                            # Count by component
                            component = event_data.get("component", "unknown")
                            stats["events_by_component"][component] = stats["events_by_component"].get(component, 0) + 1
                            
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                print(f"Error reading audit log: {str(e)}")
        
        # List all audit log files
        for log_file in self.audit_log_dir.glob("audit_*.log"):
            stats["log_files"].append({
                "filename": log_file.name,
                "size_bytes": log_file.stat().st_size,
                "modified": datetime.fromtimestamp(log_file.stat().st_mtime).isoformat()
            })
        
        return stats
    
    def cleanup_old_logs(self):
        """Clean up audit logs older than retention period."""
        cutoff_date = datetime.now().timestamp() - (self.retention_days * 24 * 60 * 60)
        
        deleted_files = []
        for log_file in self.audit_log_dir.glob("audit_*.log"):
            if log_file.stat().st_mtime < cutoff_date:
                try:
                    log_file.unlink()
                    deleted_files.append(log_file.name)
                except Exception as e:
                    print(f"Error deleting old audit log {log_file.name}: {str(e)}")
        
        if deleted_files:
            self.log_system_event(
                operation="audit_log_cleanup",
                component="audit_logger",
                outcome=AuditOutcome.SUCCESS,
                additional_context={"deleted_files": deleted_files}
            )
        
        return deleted_files

# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def initialize_audit_logging(audit_log_dir: str = "logs/audit",
                           enable_encryption: bool = True,
                           retention_days: int = 2555) -> AuditLogger:
    """Initialize global audit logger."""
    global _audit_logger
    _audit_logger = AuditLogger(
        audit_log_dir=audit_log_dir,
        enable_encryption=enable_encryption,
        retention_days=retention_days
    )
    return _audit_logger


def get_audit_logger() -> Optional[AuditLogger]:
    """Get global audit logger instance."""
    return _audit_logger