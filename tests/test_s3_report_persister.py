"""Tests for S3 Report Persister."""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import json
from botocore.exceptions import ClientError

from src.agents.s3_report_persister import S3ReportPersister
from src.models import (
    AnalysisReport, PatientData, Demographics, MedicalSummary, 
    ResearchAnalysis, S3Error
)
from src.utils import AuditLogger


class TestS3ReportPersister:
    """Test cases for S3 Report Persister."""
    
    @pytest.fixture
    def mock_audit_logger(self):
        """Create mock audit logger."""
        return Mock(spec=AuditLogger)
    
    @pytest.fixture
    def mock_s3_client(self):
        """Create mock S3 client."""
        return Mock()
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock()
        config.aws = Mock()
        config.aws.region = "us-east-1"
        config.aws.access_key_id = "test_key"
        config.aws.secret_access_key = "test_secret"
        config.aws.s3_bucket = "test-medical-reports"
        config.aws.s3_endpoint_url = None
        return config
    
    @pytest.fixture
    def sample_analysis_report(self):
        """Create sample analysis report."""
        patient_data = PatientData(
            patient_id="S3_TEST_123",
            name="Bob Wilson",
            demographics=Demographics(age=45, gender="M"),
            medical_history=[],
            medications=[],
            procedures=[],
            diagnoses=[],
            raw_xml="<patient>test</patient>",
            extraction_timestamp=datetime.now()
        )
        
        medical_summary = MedicalSummary(
            patient_id="S3_TEST_123",
            summary_text="Test medical summary",
            key_conditions=[],
            medication_summary="No medications",
            procedure_summary="No procedures",
            chronological_events=[],
            generated_timestamp=datetime.now(),
            data_quality_score=0.8,
            missing_data_indicators=[]
        )
        
        research_analysis = ResearchAnalysis(
            patient_id="S3_TEST_123",
            analysis_timestamp=datetime.now(),
            conditions_analyzed=[],
            research_findings=[],
            condition_research_correlations={},
            categorized_findings={},
            research_insights=["Test insight"],
            clinical_recommendations=["Test recommendation"],
            analysis_confidence=0.7,
            total_papers_reviewed=5,
            relevant_papers_found=2
        )
        
        report = AnalysisReport(
            report_id="RPT_TEST_S3_001",
            patient_data=patient_data,
            medical_summary=medical_summary,
            research_analysis=research_analysis,
            generated_timestamp=datetime.now(),
            processing_time_seconds=1.5,
            agent_versions={"test": "1.0"},
            quality_metrics={"overall_quality_score": 0.8}
        )
        
        # Add additional attributes
        report.executive_summary = "Test executive summary"
        report.key_findings = ["Test finding"]
        report.recommendations = ["Test recommendation"]
        report.data_sources = ["Test source"]
        report.report_version = "1.0"
        
        return report
    
    @patch('src.agents.s3_report_persister.get_config')
    @patch('src.agents.s3_report_persister.boto3.client')
    def test_persister_initialization(self, mock_boto3_client, mock_get_config, 
                                    mock_config, mock_audit_logger):
        """Test S3 report persister initialization."""
        mock_get_config.return_value = mock_config
        mock_s3_client = Mock()
        mock_boto3_client.return_value = mock_s3_client
        
        persister = S3ReportPersister(audit_logger=mock_audit_logger)
        
        assert persister.audit_logger == mock_audit_logger
        assert persister.bucket_name == "test-medical-reports"
        assert persister.reports_prefix == "analysis-reports/"
        assert persister.encryption_key_id == "alias/aws/s3"  # Default KMS key
        
        # Verify S3 client was created with correct parameters
        mock_boto3_client.assert_called_once_with(
            's3',
            region_name="us-east-1",
            aws_access_key_id="test_key",
            aws_secret_access_key="test_secret",
            endpoint_url=None
        )
    
    @patch('src.agents.s3_report_persister.get_config')
    @patch('src.agents.s3_report_persister.boto3.client')
    def test_save_analysis_report_success(self, mock_boto3_client, mock_get_config,
                                        mock_config, sample_analysis_report, 
                                        mock_audit_logger):
        """Test successful analysis report saving."""
        mock_get_config.return_value = mock_config
        mock_s3_client = Mock()
        mock_boto3_client.return_value = mock_s3_client
        
        persister = S3ReportPersister(audit_logger=mock_audit_logger)
        persister.s3_client = mock_s3_client
        
        # Execute save
        s3_key = persister.save_analysis_report(sample_analysis_report)
        
        # Verify S3 put_object was called
        mock_s3_client.put_object.assert_called_once()
        call_args = mock_s3_client.put_object.call_args
        
        assert call_args[1]['Bucket'] == "test-medical-reports"
        assert call_args[1]['ContentType'] == 'application/json'
        assert call_args[1]['ServerSideEncryption'] == 'aws:kms'
        assert call_args[1]['SSEKMSKeyId'] == "alias/aws/s3"
        
        # Verify metadata
        metadata = call_args[1]['Metadata']
        assert metadata['patient-id'] == "S3_TEST_123"
        assert metadata['report-id'] == "RPT_TEST_S3_001"
        assert metadata['content-type'] == 'medical-analysis-report'
        
        # Verify tagging
        assert "PatientID=S3_TEST_123" in call_args[1]['Tagging']
        assert "Confidential=true" in call_args[1]['Tagging']
        
        # Verify S3 key format
        assert s3_key.startswith("analysis-reports/patient-S3_TEST_123/analysis-")
        assert s3_key.endswith("-RPT_TEST_S3_001.json")
        
        # Verify audit logging
        mock_audit_logger.log_data_access.assert_called()
    
    @patch('src.agents.s3_report_persister.get_config')
    @patch('src.agents.s3_report_persister.boto3.client')
    def test_save_analysis_report_s3_error(self, mock_boto3_client, mock_get_config,
                                         mock_config, sample_analysis_report,
                                         mock_audit_logger):
        """Test analysis report saving with S3 error."""
        mock_get_config.return_value = mock_config
        mock_s3_client = Mock()
        mock_boto3_client.return_value = mock_s3_client
        
        # Configure S3 client to raise error
        mock_s3_client.put_object.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
            'PutObject'
        )
        
        persister = S3ReportPersister(audit_logger=mock_audit_logger)
        persister.s3_client = mock_s3_client
        
        # Execute and verify exception
        with pytest.raises(S3Error) as exc_info:
            persister.save_analysis_report(sample_analysis_report)
        
        assert "S3 client error" in str(exc_info.value)
        mock_audit_logger.log_error.assert_called_once()
    
    @patch('src.agents.s3_report_persister.get_config')
    @patch('src.agents.s3_report_persister.boto3.client')
    def test_retrieve_analysis_report_success(self, mock_boto3_client, mock_get_config,
                                             mock_config, sample_analysis_report,
                                             mock_audit_logger):
        """Test successful analysis report retrieval."""
        mock_get_config.return_value = mock_config
        mock_s3_client = Mock()
        mock_boto3_client.return_value = mock_s3_client
        
        # Mock list_objects_v2 response
        mock_s3_client.list_objects_v2.return_value = {
            'Contents': [{
                'Key': 'analysis-reports/patient-S3_TEST_123/analysis-20241101_120000-RPT_TEST_S3_001.json',
                'Size': 1024,
                'LastModified': datetime.now()
            }]
        }
        
        # Mock get_object response
        report_json = json.dumps(sample_analysis_report.to_dict(), default=str)
        mock_response = Mock()
        mock_response.read.return_value = report_json.encode('utf-8')
        mock_s3_client.get_object.return_value = {'Body': mock_response}
        
        persister = S3ReportPersister(audit_logger=mock_audit_logger)
        persister.s3_client = mock_s3_client
        
        # Execute retrieval
        retrieved_report = persister.retrieve_analysis_report("RPT_TEST_S3_001", "S3_TEST_123")
        
        # Verify result
        assert isinstance(retrieved_report, AnalysisReport)
        assert retrieved_report.report_id == "RPT_TEST_S3_001"
        assert retrieved_report.patient_data.patient_id == "S3_TEST_123"
        
        # Verify S3 calls
        mock_s3_client.list_objects_v2.assert_called_once()
        mock_s3_client.get_object.assert_called_once()
        
        # Verify audit logging
        mock_audit_logger.log_data_access.assert_called()
    
    @patch('src.agents.s3_report_persister.get_config')
    @patch('src.agents.s3_report_persister.boto3.client')
    def test_retrieve_analysis_report_not_found(self, mock_boto3_client, mock_get_config,
                                               mock_config, mock_audit_logger):
        """Test analysis report retrieval when report not found."""
        mock_get_config.return_value = mock_config
        mock_s3_client = Mock()
        mock_boto3_client.return_value = mock_s3_client
        
        # Mock empty list_objects_v2 response
        mock_s3_client.list_objects_v2.return_value = {}
        
        persister = S3ReportPersister(audit_logger=mock_audit_logger)
        persister.s3_client = mock_s3_client
        
        # Execute and verify exception
        with pytest.raises(S3Error) as exc_info:
            persister.retrieve_analysis_report("NONEXISTENT", "S3_TEST_123")
        
        assert "No reports found" in str(exc_info.value)
        mock_audit_logger.log_error.assert_called_once()
    
    @patch('src.agents.s3_report_persister.get_config')
    @patch('src.agents.s3_report_persister.boto3.client')
    def test_list_patient_reports_success(self, mock_boto3_client, mock_get_config,
                                        mock_config, mock_audit_logger):
        """Test successful patient reports listing."""
        mock_get_config.return_value = mock_config
        mock_s3_client = Mock()
        mock_boto3_client.return_value = mock_s3_client
        
        # Mock list_objects_v2 response
        mock_s3_client.list_objects_v2.return_value = {
            'Contents': [
                {
                    'Key': 'analysis-reports/patient-S3_TEST_123/analysis-20241101_120000-RPT_001.json',
                    'Size': 1024,
                    'LastModified': datetime(2024, 11, 1, 12, 0, 0)
                },
                {
                    'Key': 'analysis-reports/patient-S3_TEST_123/analysis-20241102_130000-RPT_002.json',
                    'Size': 2048,
                    'LastModified': datetime(2024, 11, 2, 13, 0, 0)
                }
            ]
        }
        
        # Mock head_object responses
        def mock_head_object(Bucket, Key):
            if "RPT_001" in Key:
                return {
                    'Metadata': {
                        'report-id': 'RPT_001',
                        'generated-timestamp': '2024-11-01T12:00:00',
                        'report-version': '1.0'
                    }
                }
            else:
                return {
                    'Metadata': {
                        'report-id': 'RPT_002',
                        'generated-timestamp': '2024-11-02T13:00:00',
                        'report-version': '1.0'
                    }
                }
        
        mock_s3_client.head_object.side_effect = mock_head_object
        
        persister = S3ReportPersister(audit_logger=mock_audit_logger)
        persister.s3_client = mock_s3_client
        
        # Execute listing
        reports = persister.list_patient_reports("S3_TEST_123")
        
        # Verify results
        assert len(reports) == 2
        assert reports[0]['report_id'] == 'RPT_002'  # Newest first
        assert reports[1]['report_id'] == 'RPT_001'
        
        # Verify report structure
        for report in reports:
            assert 's3_key' in report
            assert 'report_id' in report
            assert 'generated_timestamp' in report
            assert 'size_bytes' in report
            assert 'last_modified' in report
        
        # Verify audit logging
        mock_audit_logger.log_data_access.assert_called()
    
    @patch('src.agents.s3_report_persister.get_config')
    @patch('src.agents.s3_report_persister.boto3.client')
    def test_delete_analysis_report_success(self, mock_boto3_client, mock_get_config,
                                          mock_config, mock_audit_logger):
        """Test successful analysis report deletion."""
        mock_get_config.return_value = mock_config
        mock_s3_client = Mock()
        mock_boto3_client.return_value = mock_s3_client
        
        # Mock list_objects_v2 response
        mock_s3_client.list_objects_v2.return_value = {
            'Contents': [{
                'Key': 'analysis-reports/patient-S3_TEST_123/analysis-20241101_120000-RPT_TEST_S3_001.json',
                'Size': 1024,
                'LastModified': datetime.now()
            }]
        }
        
        persister = S3ReportPersister(audit_logger=mock_audit_logger)
        persister.s3_client = mock_s3_client
        
        # Execute deletion
        result = persister.delete_analysis_report("RPT_TEST_S3_001", "S3_TEST_123")
        
        # Verify result
        assert result is True
        
        # Verify S3 delete_object was called
        mock_s3_client.delete_object.assert_called_once()
        call_args = mock_s3_client.delete_object.call_args
        assert call_args[1]['Bucket'] == "test-medical-reports"
        assert "RPT_TEST_S3_001" in call_args[1]['Key']
        
        # Verify audit logging
        mock_audit_logger.log_data_access.assert_called()
    
    def test_generate_s3_key(self, sample_analysis_report):
        """Test S3 key generation."""
        persister = S3ReportPersister()
        persister.reports_prefix = "analysis-reports/"
        
        s3_key = persister._generate_s3_key(sample_analysis_report)
        
        # Verify format
        assert s3_key.startswith("analysis-reports/patient-S3_TEST_123/analysis-")
        assert s3_key.endswith("-RPT_TEST_S3_001.json")
        
        # Verify timestamp format
        parts = s3_key.split("/")[-1]  # Get filename
        assert "analysis-" in parts
        assert "-RPT_TEST_S3_001.json" in parts
    
    def test_serialize_report(self, sample_analysis_report):
        """Test report serialization."""
        persister = S3ReportPersister()
        
        report_json = persister._serialize_report(sample_analysis_report)
        
        # Verify JSON format
        assert isinstance(report_json, str)
        assert len(report_json) > 100
        
        # Verify it's valid JSON
        parsed = json.loads(report_json)
        assert parsed['report_id'] == "RPT_TEST_S3_001"
        assert parsed['patient_data']['patient_id'] == "S3_TEST_123"
    
    def test_deserialize_report(self, sample_analysis_report):
        """Test report deserialization."""
        persister = S3ReportPersister()
        
        # Serialize then deserialize
        report_json = persister._serialize_report(sample_analysis_report)
        deserialized_report = persister._deserialize_report(report_json)
        
        # Verify deserialization
        assert isinstance(deserialized_report, AnalysisReport)
        assert deserialized_report.report_id == sample_analysis_report.report_id
        assert deserialized_report.patient_data.patient_id == sample_analysis_report.patient_data.patient_id
    
    @patch('src.agents.s3_report_persister.get_config')
    @patch('src.agents.s3_report_persister.boto3.client')
    def test_get_storage_statistics_success(self, mock_boto3_client, mock_get_config,
                                          mock_config):
        """Test storage statistics retrieval."""
        mock_get_config.return_value = mock_config
        mock_s3_client = Mock()
        mock_boto3_client.return_value = mock_s3_client
        
        # Mock list_objects_v2 response
        mock_s3_client.list_objects_v2.return_value = {
            'Contents': [
                {
                    'Key': 'analysis-reports/patient-123/report1.json',
                    'Size': 1024,
                    'LastModified': datetime(2024, 11, 1, 12, 0, 0)
                },
                {
                    'Key': 'analysis-reports/patient-456/report2.json',
                    'Size': 2048,
                    'LastModified': datetime(2024, 11, 2, 13, 0, 0)
                }
            ]
        }
        
        persister = S3ReportPersister()
        persister.s3_client = mock_s3_client
        
        # Execute statistics retrieval
        stats = persister.get_storage_statistics()
        
        # Verify statistics
        assert stats['total_reports'] == 2
        assert stats['total_size_bytes'] == 3072
        assert stats['total_size_mb'] == 0.0  # Small files
        assert stats['average_size_bytes'] == 1536
        assert stats['oldest_report'] == '2024-11-01T12:00:00'
        assert stats['newest_report'] == '2024-11-02T13:00:00'
    
    @patch('src.agents.s3_report_persister.get_config')
    @patch('src.agents.s3_report_persister.boto3.client')
    def test_get_storage_statistics_patient_specific(self, mock_boto3_client, mock_get_config,
                                                   mock_config):
        """Test storage statistics for specific patient."""
        mock_get_config.return_value = mock_config
        mock_s3_client = Mock()
        mock_boto3_client.return_value = mock_s3_client
        
        # Mock list_objects_v2 response for specific patient
        mock_s3_client.list_objects_v2.return_value = {
            'Contents': [
                {
                    'Key': 'analysis-reports/patient-S3_TEST_123/report1.json',
                    'Size': 1024,
                    'LastModified': datetime(2024, 11, 1, 12, 0, 0)
                }
            ]
        }
        
        persister = S3ReportPersister()
        persister.s3_client = mock_s3_client
        
        # Execute statistics retrieval for specific patient
        stats = persister.get_storage_statistics(patient_id="S3_TEST_123")
        
        # Verify statistics
        assert stats['total_reports'] == 1
        assert stats['total_size_bytes'] == 1024
        
        # Verify correct prefix was used
        mock_s3_client.list_objects_v2.assert_called_once()
        call_args = mock_s3_client.list_objects_v2.call_args
        assert call_args[1]['Prefix'] == "analysis-reports/patient-S3_TEST_123/"
    
    @patch('src.agents.s3_report_persister.get_config')
    @patch('src.agents.s3_report_persister.boto3.client')
    def test_get_storage_statistics_no_reports(self, mock_boto3_client, mock_get_config,
                                             mock_config):
        """Test storage statistics when no reports exist."""
        mock_get_config.return_value = mock_config
        mock_s3_client = Mock()
        mock_boto3_client.return_value = mock_s3_client
        
        # Mock empty list_objects_v2 response
        mock_s3_client.list_objects_v2.return_value = {}
        
        persister = S3ReportPersister()
        persister.s3_client = mock_s3_client
        
        # Execute statistics retrieval
        stats = persister.get_storage_statistics()
        
        # Verify empty statistics
        assert stats['total_reports'] == 0
        assert stats['total_size_bytes'] == 0
        assert stats['oldest_report'] is None
        assert stats['newest_report'] is None