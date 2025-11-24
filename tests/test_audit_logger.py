"""Tests for HIPAA-compliant audit logging system."""
import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch

from src.utils.audit_logger import (
    AuditLogger, AuditEvent, AuditEventType, AuditOutcome,
    initialize_audit_logging, get_audit_logger
)

class TestAuditEvent:
    """Test AuditEvent class."""
    
    def test_audit_event_creation(self):
        """Test audit event creation."""
        event = AuditEvent(
            event_id="test-event-123",
            timestamp="2024-01-01T12:00:00",
            event_type="access",
            outcome="success",
            user_id="user123",
            patient_id="patient456",
            operation="view_record",
            component="xml_parser",
            source_ip="192.168.1.1",
            data_elements=["medical_record", "patient_data"]
        )
        
        assert event.event_id == "test-event-123"
        assert event.event_type == "access"
        assert event.outcome == "success"
        assert event.user_id == "user123"
        assert event.patient_id == "patient456"
        assert event.operation == "view_record"
        assert event.component == "xml_parser"
        assert event.source_ip == "192.168.1.1"
        assert event.data_elements == ["medical_record", "patient_data"]
    
    def test_audit_event_to_dict(self):
        """Test audit event dictionary conversion."""
        event = AuditEvent(
            event_id="test-event-123",
            timestamp="2024-01-01T12:00:00",
            event_type="access",
            outcome="success",
            user_id="user123",
            patient_id="patient456",
            operation="view_record",
            component="xml_parser"
        )
        
        event_dict = event.to_dict()
        
        assert event_dict["event_id"] == "test-event-123"
        assert event_dict["event_type"] == "access"
        assert event_dict["outcome"] == "success"
        assert event_dict["user_id"] == "user123"
        assert event_dict["patient_id"] == "patient456"
    
    def test_audit_event_to_json(self):
        """Test audit event JSON conversion."""
        event = AuditEvent(
            event_id="test-event-123",
            timestamp="2024-01-01T12:00:00",
            event_type="access",
            outcome="success",
            user_id="user123",
            patient_id="patient456",
            operation="view_record",
            component="xml_parser"
        )
        
        json_str = event.to_json()
        parsed = json.loads(json_str)
        
        assert parsed["event_id"] == "test-event-123"
        assert parsed["event_type"] == "access"

class TestAuditLogger:
    """Test AuditLogger class."""
    
    @pytest.fixture
    def temp_audit_dir(self):
        """Create temporary audit directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def audit_logger(self, temp_audit_dir):
        """Create audit logger."""
        return AuditLogger(
            audit_log_dir=temp_audit_dir,
            enable_encryption=False,  # Disable for testing
            retention_days=30
        )
    
    def test_audit_logger_initialization(self, audit_logger, temp_audit_dir):
        """Test audit logger initialization."""
        assert audit_logger.audit_log_dir == Path(temp_audit_dir)
        assert audit_logger.enable_encryption is False
        assert audit_logger.retention_days == 30
        assert audit_logger.logger is not None
    
    def test_audit_directory_creation(self, temp_audit_dir):
        """Test audit directory creation."""
        audit_dir = Path(temp_audit_dir) / "custom_audit"
        assert not audit_dir.exists()
        
        AuditLogger(audit_log_dir=str(audit_dir))
        
        assert audit_dir.exists()
    
    def test_patient_id_hashing(self, audit_logger):
        """Test patient ID hashing for privacy."""
        patient_id = "PATIENT123"
        hashed_id = audit_logger._hash_patient_id(patient_id)
        
        assert hashed_id != patient_id
        assert len(hashed_id) == 16  # Truncated SHA-256
        
        # Same patient ID should produce same hash
        hashed_id2 = audit_logger._hash_patient_id(patient_id)
        assert hashed_id == hashed_id2
        
        # Different patient ID should produce different hash
        hashed_id3 = audit_logger._hash_patient_id("PATIENT456")
        assert hashed_id != hashed_id3
    
    def test_event_id_generation(self, audit_logger):
        """Test unique event ID generation."""
        event_id1 = audit_logger._generate_event_id()
        event_id2 = audit_logger._generate_event_id()
        
        assert event_id1 != event_id2
        assert len(event_id1) == 36  # UUID4 length
    
    def test_log_patient_access(self, audit_logger, temp_audit_dir):
        """Test logging patient data access."""
        audit_logger.log_patient_access(
            patient_id="PATIENT123",
            operation="view_medical_record",
            component="xml_parser",
            outcome=AuditOutcome.SUCCESS,
            user_id="user123",
            data_elements=["medical_record", "patient_demographics"]
        )
        
        # Check if audit log file was created
        log_files = list(Path(temp_audit_dir).glob("audit_*.log"))
        assert len(log_files) == 1
        
        # Check log content (audit logger writes JSON lines)
        with open(log_files[0], 'r') as f:
            lines = f.readlines()
            assert len(lines) >= 1
            log_data = json.loads(lines[-1].strip())  # Get the last log entry
            
            assert log_data["event_type"] == "access"
            assert log_data["outcome"] == "success"
            assert log_data["operation"] == "view_medical_record"
            assert log_data["component"] == "xml_parser"
            assert log_data["user_id"] == "user123"
            assert log_data["data_elements"] == ["medical_record", "patient_demographics"]
            # Patient ID should be hashed
            assert log_data["patient_id"] != "PATIENT123"
    
    def test_log_data_modification(self, audit_logger, temp_audit_dir):
        """Test logging data modification."""
        audit_logger.log_data_modification(
            patient_id="PATIENT123",
            operation="update_analysis",
            component="medical_summarizer",
            outcome=AuditOutcome.SUCCESS,
            user_id="user123",
            data_elements=["medical_summary"],
            additional_context={"analysis_type": "condition_extraction"}
        )
        
        log_files = list(Path(temp_audit_dir).glob("audit_*.log"))
        with open(log_files[0], 'r') as f:
            lines = f.readlines()
            assert len(lines) >= 1
            log_data = json.loads(lines[-1].strip())  # Get the last log entry
            
            assert log_data["event_type"] == "modification"
            assert log_data["additional_context"]["analysis_type"] == "condition_extraction"
    
    def test_log_report_creation(self, audit_logger, temp_audit_dir):
        """Test logging report creation."""
        audit_logger.log_report_creation(
            patient_id="PATIENT123",
            operation="generate_analysis_report",
            component="report_generator",
            outcome=AuditOutcome.SUCCESS,
            user_id="user123",
            report_type="comprehensive_analysis"
        )
        
        log_files = list(Path(temp_audit_dir).glob("audit_*.log"))
        with open(log_files[0], 'r') as f:
            lines = f.readlines()
            assert len(lines) >= 1
            log_data = json.loads(lines[-1].strip())  # Get the last log entry
            
            assert log_data["event_type"] == "creation"
            assert log_data["additional_context"]["report_type"] == "comprehensive_analysis"
            assert log_data["data_elements"] == ["analysis_report", "medical_summary"]
    
    def test_log_data_export(self, audit_logger, temp_audit_dir):
        """Test logging data export."""
        audit_logger.log_data_export(
            patient_id="PATIENT123",
            operation="export_report",
            component="s3_persister",
            export_destination="s3://medical-reports/bucket",
            outcome=AuditOutcome.SUCCESS,
            user_id="user123",
            data_elements=["analysis_report"]
        )
        
        log_files = list(Path(temp_audit_dir).glob("audit_*.log"))
        with open(log_files[0], 'r') as f:
            lines = f.readlines()
            assert len(lines) >= 1
            log_data = json.loads(lines[-1].strip())  # Get the last log entry
            
            assert log_data["event_type"] == "export"
            assert log_data["additional_context"]["export_destination"] == "s3://medical-reports/bucket"
    
    def test_log_authentication(self, audit_logger, temp_audit_dir):
        """Test logging authentication events."""
        audit_logger.log_authentication(
            user_id="user123",
            operation="user_login",
            outcome=AuditOutcome.SUCCESS,
            source_ip="192.168.1.100",
            user_agent="Mozilla/5.0 (Medical Analysis Client)"
        )
        
        log_files = list(Path(temp_audit_dir).glob("audit_*.log"))
        with open(log_files[0], 'r') as f:
            lines = f.readlines()
            assert len(lines) >= 1
            log_data = json.loads(lines[-1].strip())  # Get the last log entry
            
            assert log_data["event_type"] == "authentication"
            assert log_data["component"] == "authentication_system"
            assert log_data["source_ip"] == "192.168.1.100"
            assert log_data["user_agent"] == "Mozilla/5.0 (Medical Analysis Client)"
    
    def test_log_authorization(self, audit_logger, temp_audit_dir):
        """Test logging authorization events."""
        audit_logger.log_authorization(
            user_id="user123",
            operation="access_patient_record",
            resource_accessed="/api/patients/PATIENT123",
            outcome=AuditOutcome.SUCCESS,
            patient_id="PATIENT123"
        )
        
        log_files = list(Path(temp_audit_dir).glob("audit_*.log"))
        with open(log_files[0], 'r') as f:
            lines = f.readlines()
            assert len(lines) >= 1
            log_data = json.loads(lines[-1].strip())  # Get the last log entry
            
            assert log_data["event_type"] == "authorization"
            assert log_data["component"] == "authorization_system"
            assert log_data["resource_accessed"] == "/api/patients/PATIENT123"
    
    def test_log_error(self, audit_logger, temp_audit_dir):
        """Test logging error events."""
        error = ValueError("Test error message")
        
        audit_logger.log_error(
            operation="parse_xml",
            component="xml_parser",
            error=error,
            patient_id="PATIENT123",
            user_id="user123",
            additional_context={"file_path": "/path/to/file.xml"}
        )
        
        log_files = list(Path(temp_audit_dir).glob("audit_*.log"))
        with open(log_files[0], 'r') as f:
            lines = f.readlines()
            assert len(lines) >= 1
            log_data = json.loads(lines[-1].strip())  # Get the last log entry
            
            assert log_data["event_type"] == "error"
            assert log_data["outcome"] == "failure"
            assert log_data["additional_context"]["error_type"] == "ValueError"
            assert log_data["additional_context"]["error_message"] == "Test error message"
    
    def test_log_system_event(self, audit_logger, temp_audit_dir):
        """Test logging system events."""
        audit_logger.log_system_event(
            operation="system_startup",
            component="main_application",
            outcome=AuditOutcome.SUCCESS,
            additional_context={"version": "1.0.0", "environment": "production"}
        )
        
        log_files = list(Path(temp_audit_dir).glob("audit_*.log"))
        with open(log_files[0], 'r') as f:
            lines = f.readlines()
            assert len(lines) >= 1
            log_data = json.loads(lines[-1].strip())  # Get the last log entry
            
            assert log_data["event_type"] == "system_event"
            assert log_data["additional_context"]["version"] == "1.0.0"
    
    def test_multiple_events_logging(self, audit_logger, temp_audit_dir):
        """Test logging multiple events."""
        # Log multiple events
        audit_logger.log_patient_access("PATIENT123", "view_record", "xml_parser")
        audit_logger.log_data_modification("PATIENT123", "update_summary", "summarizer")
        audit_logger.log_report_creation("PATIENT123", "generate_report", "report_generator")
        
        log_files = list(Path(temp_audit_dir).glob("audit_*.log"))
        assert len(log_files) == 1
        
        # Check that all events are logged
        with open(log_files[0], 'r') as f:
            lines = f.read().strip().split('\n')
            assert len(lines) >= 3  # At least 3 events (plus initialization event)
            
            # Parse each line as JSON
            events = [json.loads(line) for line in lines if line.strip()]
            event_types = [event["event_type"] for event in events]
            
            assert "access" in event_types
            assert "modification" in event_types
            assert "creation" in event_types
    
    def test_audit_statistics(self, audit_logger):
        """Test audit statistics collection."""
        # Log some events
        audit_logger.log_patient_access("PATIENT123", "view_record", "xml_parser")
        audit_logger.log_data_modification("PATIENT123", "update_summary", "summarizer")
        audit_logger.log_error("parse_error", "xml_parser", ValueError("Test error"))
        
        stats = audit_logger.get_audit_statistics()
        
        assert "total_events" in stats
        assert "events_by_type" in stats
        assert "events_by_outcome" in stats
        assert "events_by_component" in stats
        assert "log_files" in stats
        
        assert stats["total_events"] >= 3
        assert "access" in stats["events_by_type"]
        assert "modification" in stats["events_by_type"]
        assert "error" in stats["events_by_type"]
    
    def test_daily_log_rotation(self, audit_logger, temp_audit_dir):
        """Test daily log file rotation."""
        # Log an event
        audit_logger.log_patient_access("PATIENT123", "view_record", "xml_parser")
        
        # Check current log file
        current_date = datetime.now().strftime('%Y%m%d')
        expected_file = Path(temp_audit_dir) / f"audit_{current_date}.log"
        assert expected_file.exists()
    
    @patch('src.utils.audit_logger.datetime')
    def test_log_cleanup(self, mock_datetime, audit_logger, temp_audit_dir):
        """Test old log cleanup."""
        # Create old log files
        old_date = "20230101"
        old_log = Path(temp_audit_dir) / f"audit_{old_date}.log"
        old_log.write_text("old log content")
        
        # Set old modification time
        import os
        old_timestamp = 1672531200  # Jan 1, 2023
        os.utime(old_log, (old_timestamp, old_timestamp))
        
        # Mock current time to be much later
        mock_now = Mock()
        mock_now.timestamp.return_value = 1704067200  # Jan 1, 2024
        mock_datetime.now.return_value = mock_now
        
        # Run cleanup
        deleted_files = audit_logger.cleanup_old_logs()
        
        assert old_log.name in deleted_files
        assert not old_log.exists()
    
    def test_audit_logging_failure_handling(self, audit_logger):
        """Test handling of audit logging failures."""
        # Mock logger to raise exception
        audit_logger.logger = Mock()
        audit_logger.logger.info.side_effect = Exception("Logging failed")
        
        # Should not raise exception, but print error
        with patch('builtins.print') as mock_print:
            audit_logger.log_patient_access("PATIENT123", "view_record", "xml_parser")
            mock_print.assert_called_once()
            assert "CRITICAL: Audit logging failed" in mock_print.call_args[0][0]

class TestAuditLoggerGlobalFunctions:
    """Test global audit logger functions."""
    
    def test_initialize_audit_logging(self):
        """Test global audit logging initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            logger = initialize_audit_logging(
                audit_log_dir=temp_dir,
                enable_encryption=False,
                retention_days=365
            )
            
            assert isinstance(logger, AuditLogger)
            assert get_audit_logger() is logger
            assert logger.retention_days == 365
    
    def test_get_audit_logger_without_initialization(self):
        """Test getting audit logger without initialization."""
        # Reset global audit logger
        import src.utils.audit_logger
        src.utils.audit_logger._audit_logger = None
        
        logger = get_audit_logger()
        assert logger is None

class TestAuditLoggerIntegration:
    """Test audit logger integration scenarios."""
    
    def test_hipaa_compliance_fields(self):
        """Test that all required HIPAA audit fields are present."""
        with tempfile.TemporaryDirectory() as temp_dir:
            audit_logger = AuditLogger(audit_log_dir=temp_dir)
            
            audit_logger.log_patient_access(
                patient_id="PATIENT123",
                operation="view_medical_record",
                component="xml_parser",
                user_id="user123"
            )
            
            log_files = list(Path(temp_dir).glob("audit_*.log"))
            with open(log_files[0], 'r') as f:
                lines = f.readlines()
                assert len(lines) >= 1
                log_data = json.loads(lines[-1].strip())  # Get the last log entry
                
                # Check required HIPAA fields
                required_fields = [
                    "event_id", "timestamp", "event_type", "outcome",
                    "user_id", "patient_id", "operation", "component"
                ]
                
                for field in required_fields:
                    assert field in log_data, f"Missing required field: {field}"
    
    def test_patient_privacy_protection(self):
        """Test patient privacy protection in audit logs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            audit_logger = AuditLogger(audit_log_dir=temp_dir)
            
            original_patient_id = "PATIENT123"
            audit_logger.log_patient_access(
                patient_id=original_patient_id,
                operation="view_record",
                component="xml_parser"
            )
            
            log_files = list(Path(temp_dir).glob("audit_*.log"))
            with open(log_files[0], 'r') as f:
                log_content = f.read()
                
                # Original patient ID should not appear in log
                assert original_patient_id not in log_content
                
                # But hashed version should be present
                lines = log_content.strip().split('\n')
                log_data = json.loads(lines[-1])  # Get the last log entry
                assert log_data["patient_id"] is not None
                assert log_data["patient_id"] != original_patient_id
    
    def test_comprehensive_audit_trail(self):
        """Test comprehensive audit trail for a complete workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            audit_logger = AuditLogger(audit_log_dir=temp_dir)
            
            patient_id = "PATIENT123"
            user_id = "user123"
            
            # Simulate complete workflow
            audit_logger.log_authentication(user_id, "login", AuditOutcome.SUCCESS)
            audit_logger.log_authorization(user_id, "access_patient", "/api/patients/PATIENT123", AuditOutcome.SUCCESS, patient_id)
            audit_logger.log_patient_access(patient_id, "view_record", "xml_parser", user_id=user_id)
            audit_logger.log_data_modification(patient_id, "extract_conditions", "condition_extractor", user_id=user_id)
            audit_logger.log_report_creation(patient_id, "generate_report", "report_generator", user_id=user_id)
            audit_logger.log_data_export(patient_id, "save_report", "s3_persister", "s3://bucket/reports", user_id=user_id)
            
            # Verify complete audit trail
            stats = audit_logger.get_audit_statistics()
            assert stats["total_events"] >= 6
            
            expected_event_types = ["authentication", "authorization", "access", "modification", "creation", "export"]
            for event_type in expected_event_types:
                assert event_type in stats["events_by_type"]