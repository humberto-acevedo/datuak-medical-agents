"""Integration tests for XML Parser Agent."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.agents.xml_parser_agent import XMLParserAgent
from src.models.exceptions import PatientNotFoundError, XMLParsingError, S3Error


class TestXMLParserAgent:
    """Test XML Parser Agent integration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_s3_client = Mock()
        self.mock_audit_logger = Mock()
        
        # Create agent with mocked dependencies
        with patch('src.agents.xml_parser_agent.S3Client'), \
             patch('src.agents.xml_parser_agent.setup_logging'):
            self.agent = XMLParserAgent(
                s3_client=self.mock_s3_client,
                audit_logger=self.mock_audit_logger
            )
    
    def test_parse_patient_record_success(self):
        """Test successful complete workflow."""
        # Mock patient resolution
        self.mock_s3_client.list_objects.return_value = [
            "01995eed-3135-733a-b8eb-a6ff8eaa39dd/JaneSmith.xml"
        ]
        
        # Mock S3 retrieval
        sample_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <patient>
            <id>P001</id>
            <name>Jane Smith</name>
            <age>45</age>
            <gender>F</gender>
            <medications>
                <medication>
                    <name>Lisinopril</name>
                    <dosage>10mg</dosage>
                    <frequency>daily</frequency>
                </medication>
            </medications>
        </patient>"""
        
        self.mock_s3_client.get_object.return_value = sample_xml.encode('utf-8')
        
        # Execute
        result = self.agent.parse_patient_record("Jane Smith")
        
        # Verify result
        assert result.patient_id == "P001"
        assert result.name == "Jane Smith"
        assert result.demographics.age == 45
        assert len(result.medications) == 1
        assert result.medications[0].name == "Lisinopril"
        
        # Verify S3 operations
        self.mock_s3_client.list_objects.assert_called_once()
        self.mock_s3_client.get_object.assert_called_once_with(
            "01995eed-3135-733a-b8eb-a6ff8eaa39dd/JaneSmith.xml"
        )
        
        # Verify audit logging
        assert self.mock_audit_logger.log_processing_start.called
        assert self.mock_audit_logger.log_data_access.called
        assert self.mock_audit_logger.log_processing_complete.called
    
    def test_parse_patient_record_patient_not_found(self):
        """Test handling when patient is not found."""
        # Mock empty S3 response
        self.mock_s3_client.list_objects.return_value = []
        
        # Execute and verify exception
        with pytest.raises(PatientNotFoundError):
            self.agent.parse_patient_record("Nonexistent Patient")
        
        # Verify error logging
        self.mock_audit_logger.log_error.assert_called_once()
        error_call = self.mock_audit_logger.log_error.call_args
        assert error_call[1]['operation'] == 'patient_resolution'
    
    def test_parse_patient_record_s3_error(self):
        """Test handling S3 retrieval errors."""
        # Mock patient resolution success
        self.mock_s3_client.list_objects.return_value = [
            "01995eed-3135-733a-b8eb-a6ff8eaa39dd/JaneSmith.xml"
        ]
        
        # Mock S3 retrieval failure
        self.mock_s3_client.get_object.side_effect = S3Error("S3 connection failed")
        
        # Execute and verify exception
        with pytest.raises(S3Error):
            self.agent.parse_patient_record("Jane Smith")
        
        # Verify error logging
        self.mock_audit_logger.log_error.assert_called_once()
        error_call = self.mock_audit_logger.log_error.call_args
        assert error_call[1]['operation'] == 's3_retrieval'
    
    def test_parse_patient_record_xml_parsing_error(self):
        """Test handling XML parsing errors."""
        # Mock patient resolution and S3 retrieval
        self.mock_s3_client.list_objects.return_value = [
            "01995eed-3135-733a-b8eb-a6ff8eaa39dd/JaneSmith.xml"
        ]
        
        # Invalid XML content
        invalid_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <patient>
            <name>Jane Smith</name>
            <unclosed_tag>
        </patient>"""
        
        self.mock_s3_client.get_object.return_value = invalid_xml.encode('utf-8')
        
        # Execute and verify exception
        with pytest.raises(XMLParsingError):
            self.agent.parse_patient_record("Jane Smith")
        
        # Verify error logging
        self.mock_audit_logger.log_error.assert_called_once()
        error_call = self.mock_audit_logger.log_error.call_args
        assert error_call[1]['operation'] == 'xml_parsing'
    
    def test_validate_patient_exists_true(self):
        """Test patient existence validation - patient exists."""
        # Mock patient found
        self.mock_s3_client.list_objects.return_value = [
            "01995eed-3135-733a-b8eb-a6ff8eaa39dd/JaneSmith.xml"
        ]
        self.mock_s3_client.object_exists.return_value = True
        
        result = self.agent.validate_patient_exists("Jane Smith")
        assert result is True
    
    def test_validate_patient_exists_false(self):
        """Test patient existence validation - patient not found."""
        # Mock patient not found
        self.mock_s3_client.list_objects.return_value = []
        
        result = self.agent.validate_patient_exists("Nonexistent Patient")
        assert result is False
    
    def test_get_patient_metadata(self):
        """Test getting patient metadata."""
        # Mock patient resolution - need to set up side_effect for multiple calls
        self.mock_s3_client.list_objects.side_effect = [
            # First call for patient resolution
            ["01995eed-3135-733a-b8eb-a6ff8eaa39dd/JaneSmith.xml"],
            # Second call for analyses list
            ["01995eed-3135-733a-b8eb-a6ff8eaa39dd/analysis-20231101_120000.json"]
        ]
        
        # Mock S3 metadata
        self.mock_s3_client.get_object_metadata.return_value = {
            'size': 2048,
            'last_modified': datetime(2023, 11, 1, 12, 0, 0),
            'server_side_encryption': 'AES256'
        }
        
        result = self.agent.get_patient_metadata("Jane Smith")
        
        assert result['patient_name'] == "Jane Smith"
        assert result['patient_id'] == "01995eed-3135-733a-b8eb-a6ff8eaa39dd"
        assert result['file_size'] == 2048
        assert result['encrypted'] is True
        assert result['existing_analyses'] == 1
    
    def test_list_available_patients(self):
        """Test listing available patients."""
        # Mock S3 objects
        self.mock_s3_client.list_objects.return_value = [
            "01995eed-3135-733a-b8eb-a6ff8eaa39dd/JaneSmith.xml",
            "02995eed-3135-733a-b8eb-a6ff8eaa39dd/JohnDoe.xml",
            "metadata/index.json",  # Should be filtered out
            "logs/system.log"       # Should be filtered out
        ]
        
        # Mock metadata for each patient
        def mock_metadata(path):
            return {
                'size': 1024,
                'last_modified': datetime(2023, 11, 1, 12, 0, 0)
            }
        
        self.mock_s3_client.get_object_metadata.side_effect = mock_metadata
        
        result = self.agent.list_available_patients()
        
        assert len(result) == 2
        assert result[0]['patient_name'] == "JaneSmith"
        assert result[1]['patient_name'] == "JohnDoe"
        assert all('patient_id' in patient for patient in result)
        assert all('file_size' in patient for patient in result)
    
    def test_list_available_patients_with_limit(self):
        """Test listing patients with limit."""
        # Mock many patients
        patients = [f"patient{i:03d}/Patient{i:03d}.xml" for i in range(50)]
        self.mock_s3_client.list_objects.return_value = patients
        
        # Mock metadata
        self.mock_s3_client.get_object_metadata.return_value = {
            'size': 1024,
            'last_modified': datetime(2023, 11, 1, 12, 0, 0)
        }
        
        result = self.agent.list_available_patients(limit=10)
        
        assert len(result) == 10
        # Verify limit was applied
        self.mock_s3_client.list_objects.assert_called_once_with(prefix="", max_keys=20)
    
    def test_get_agent_status_healthy(self):
        """Test agent status when healthy."""
        # Mock successful S3 connectivity test
        self.mock_s3_client.list_objects.return_value = []
        self.mock_s3_client.bucket_name = "test-bucket"
        
        result = self.agent.get_agent_status()
        
        assert result['agent_name'] == 'XML Parser Agent'
        assert result['status'] == 'healthy'
        assert result['s3_connectivity'] is True
        assert result['bucket_name'] == "test-bucket"
        assert result['region'] == 'us-east-1'
    
    def test_get_agent_status_degraded(self):
        """Test agent status when S3 connectivity fails."""
        # Mock S3 connectivity failure
        self.mock_s3_client.list_objects.side_effect = Exception("Connection failed")
        self.mock_s3_client.bucket_name = "test-bucket"
        
        result = self.agent.get_agent_status()
        
        assert result['agent_name'] == 'XML Parser Agent'
        assert result['status'] == 'degraded'
        assert result['s3_connectivity'] is False
    
    def test_complex_patient_record_parsing(self):
        """Test parsing a complex patient record with multiple data types."""
        # Mock patient resolution - need to match the normalized name
        self.mock_s3_client.list_objects.return_value = [
            "complex-patient-id/MaryJohnson.xml"  # Normalized name without spaces
        ]
        
        # Complex XML with multiple sections
        complex_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <patient>
            <id>COMPLEX001</id>
            <name>
                <firstName>Mary</firstName>
                <lastName>Johnson</lastName>
            </name>
            <age>67</age>
            <gender>F</gender>
            <dateOfBirth>1956-03-15</dateOfBirth>
            <medications>
                <medication>
                    <id>M001</id>
                    <name>Metformin</name>
                    <dosage>500mg</dosage>
                    <frequency>twice daily</frequency>
                    <indication>Type 2 Diabetes</indication>
                    <startDate>2020-01-15</startDate>
                </medication>
                <medication>
                    <id>M002</id>
                    <name>Lisinopril</name>
                    <dosage>10mg</dosage>
                    <frequency>daily</frequency>
                    <indication>Hypertension</indication>
                </medication>
            </medications>
            <diagnoses>
                <diagnosis>
                    <id>D001</id>
                    <condition>Type 2 Diabetes Mellitus</condition>
                    <dateDiagnosed>2020-01-15</dateDiagnosed>
                    <icd10Code>E11.9</icd10Code>
                    <status>active</status>
                </diagnosis>
                <diagnosis>
                    <id>D002</id>
                    <condition>Essential Hypertension</condition>
                    <dateDiagnosed>2018-06-20</dateDiagnosed>
                    <icd10Code>I10</icd10Code>
                    <status>active</status>
                </diagnosis>
            </diagnoses>
            <procedures>
                <procedure>
                    <id>P001</id>
                    <name>Annual Physical Exam</name>
                    <date>2023-10-15</date>
                    <provider>Dr. Smith</provider>
                    <outcome>Normal findings</outcome>
                </procedure>
            </procedures>
            <medicalHistory>
                <event>
                    <id>E001</id>
                    <date>2023-10-15</date>
                    <type>visit</type>
                    <description>Annual checkup with lab work</description>
                    <provider>Dr. Smith</provider>
                </event>
            </medicalHistory>
        </patient>"""
        
        self.mock_s3_client.get_object.return_value = complex_xml.encode('utf-8')
        
        # Execute
        result = self.agent.parse_patient_record("Mary Johnson")
        
        # Verify comprehensive parsing
        assert result.patient_id == "COMPLEX001"
        assert result.name == "Mary Johnson"
        assert result.demographics.age == 67
        assert result.demographics.gender == "F"
        assert result.demographics.date_of_birth == "1956-03-15"
        
        # Verify medications
        assert len(result.medications) == 2
        metformin = next(med for med in result.medications if med.name == "Metformin")
        assert metformin.indication == "Type 2 Diabetes"
        assert metformin.start_date == "2020-01-15"
        
        # Verify diagnoses
        assert len(result.diagnoses) == 2
        diabetes = next(diag for diag in result.diagnoses if "Diabetes" in diag.condition)
        assert diabetes.icd_10_code == "E11.9"
        
        # Verify procedures
        assert len(result.procedures) == 1
        assert result.procedures[0].name == "Annual Physical Exam"
        
        # Verify medical history
        assert len(result.medical_history) == 1
        assert result.medical_history[0].description == "Annual checkup with lab work"
    
    def test_audit_trail_completeness(self):
        """Test that complete audit trail is generated."""
        # Mock successful workflow
        self.mock_s3_client.list_objects.return_value = [
            "patient-id/TestPatient.xml"
        ]
        
        simple_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <patient>
            <id>TEST001</id>
            <name>Test Patient</name>
        </patient>"""
        
        self.mock_s3_client.get_object.return_value = simple_xml.encode('utf-8')
        
        # Execute
        self.agent.parse_patient_record("Test Patient")
        
        # Verify complete audit trail
        assert self.mock_audit_logger.log_processing_start.called
        assert self.mock_audit_logger.log_data_access.called
        assert self.mock_audit_logger.log_processing_complete.called
        
        # Verify audit log details
        start_call = self.mock_audit_logger.log_processing_start.call_args
        assert start_call[1]['workflow_type'] == 'xml_parsing'
        
        # Check that we have at least one data access call (there are multiple)
        assert self.mock_audit_logger.log_data_access.call_count >= 1
        
        complete_call = self.mock_audit_logger.log_processing_complete.call_args
        assert complete_call[1]['workflow_type'] == 'xml_parsing'
        assert 'duration_seconds' in complete_call[1]