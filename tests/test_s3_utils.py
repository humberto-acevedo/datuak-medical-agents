"""Unit tests for S3 utilities."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError, NoCredentialsError
from datetime import datetime

from src.utils.s3_client import S3Client, create_s3_client
from src.utils.patient_resolver import PatientResolver
from src.models.exceptions import S3Error, PatientNotFoundError


class TestS3Client:
    """Test S3Client functionality."""
    
    @patch('src.utils.s3_client.config')
    @patch('src.utils.s3_client.Session')
    def test_s3_client_initialization_success(self, mock_session, mock_config):
        """Test successful S3 client initialization."""
        # Mock configuration
        mock_config.aws.region = "us-east-1"
        mock_config.aws.s3_bucket = "test-bucket"
        mock_config.aws.access_key_id = "test-key"
        mock_config.aws.secret_access_key = "test-secret"
        mock_config.aws.s3_endpoint_url = None
        
        # Mock AWS session and client
        mock_s3_client = Mock()
        mock_session_instance = Mock()
        mock_session_instance.client.return_value = mock_s3_client
        mock_session.return_value = mock_session_instance
        
        # Mock bucket validation
        mock_s3_client.get_bucket_location.return_value = {'LocationConstraint': None}
        mock_s3_client.get_bucket_encryption.return_value = {'ServerSideEncryptionConfiguration': {}}
        
        # Create S3 client
        s3_client = S3Client()
        
        assert s3_client.bucket_name == "test-bucket"
        assert s3_client.s3_client == mock_s3_client
        mock_s3_client.get_bucket_location.assert_called_once()
    
    @patch('src.utils.s3_client.config')
    def test_s3_client_hipaa_region_validation(self, mock_config):
        """Test HIPAA region validation."""
        mock_config.aws.region = "eu-west-1"  # Non-US region
        
        with pytest.raises(S3Error, match="HIPAA Compliance Error"):
            S3Client()
    
    @patch('src.utils.s3_client.config')
    @patch('boto3.session.Session')
    def test_s3_client_bucket_validation_failure(self, mock_session, mock_config):
        """Test bucket validation failure."""
        mock_config.aws.region = "us-east-1"
        mock_config.aws.s3_bucket = "nonexistent-bucket"
        mock_config.aws.access_key_id = "test-key"
        mock_config.aws.secret_access_key = "test-secret"
        mock_config.aws.s3_endpoint_url = None
        
        mock_s3_client = Mock()
        mock_session_instance = Mock()
        mock_session_instance.client.return_value = mock_s3_client
        mock_session.return_value = mock_session_instance
        
        # Mock bucket not found
        error_response = {'Error': {'Code': 'NoSuchBucket'}}
        mock_s3_client.get_bucket_location.side_effect = ClientError(error_response, 'GetBucketLocation')
        
        with pytest.raises(S3Error, match="does not exist"):
            S3Client()
    
    @patch('src.utils.s3_client.config')
    @patch('src.utils.s3_client.Session')
    def test_get_object_success(self, mock_session, mock_config):
        """Test successful object retrieval."""
        # Setup mocks
        mock_config.aws.region = "us-east-1"
        mock_config.aws.s3_bucket = "test-bucket"
        mock_config.aws.access_key_id = "test-key"
        mock_config.aws.secret_access_key = "test-secret"
        mock_config.aws.s3_endpoint_url = None
        
        mock_s3_client = Mock()
        mock_session_instance = Mock()
        mock_session_instance.client.return_value = mock_s3_client
        mock_session.return_value = mock_session_instance
        
        # Mock successful operations
        mock_s3_client.get_bucket_location.return_value = {'LocationConstraint': None}
        mock_s3_client.get_bucket_encryption.return_value = {'ServerSideEncryptionConfiguration': {}}
        
        # Mock get_object response
        mock_body = Mock()
        mock_body.read.return_value = b"test content"
        mock_s3_client.get_object.return_value = {'Body': mock_body}
        
        # Test
        s3_client = S3Client()
        content = s3_client.get_object("test-key")
        
        assert content == b"test content"
        mock_s3_client.get_object.assert_called_once_with(Bucket="test-bucket", Key="test-key")
    
    @patch('src.utils.s3_client.config')
    @patch('src.utils.s3_client.Session')
    def test_get_object_retry_logic(self, mock_session, mock_config):
        """Test retry logic for get_object."""
        # Setup mocks
        mock_config.aws.region = "us-east-1"
        mock_config.aws.s3_bucket = "test-bucket"
        mock_config.aws.access_key_id = "test-key"
        mock_config.aws.secret_access_key = "test-secret"
        mock_config.aws.s3_endpoint_url = None
        
        mock_s3_client = Mock()
        mock_session_instance = Mock()
        mock_session_instance.client.return_value = mock_s3_client
        mock_session.return_value = mock_session_instance
        
        # Mock successful operations for initialization
        mock_s3_client.get_bucket_location.return_value = {'LocationConstraint': None}
        mock_s3_client.get_bucket_encryption.return_value = {'ServerSideEncryptionConfiguration': {}}
        
        # Mock get_object to fail twice then succeed
        error_response = {'Error': {'Code': 'InternalError'}}
        mock_body = Mock()
        mock_body.read.return_value = b"test content"
        
        mock_s3_client.get_object.side_effect = [
            ClientError(error_response, 'GetObject'),  # First attempt fails
            ClientError(error_response, 'GetObject'),  # Second attempt fails
            {'Body': mock_body}  # Third attempt succeeds
        ]
        
        # Test with short retry delay
        s3_client = S3Client(retry_delay=0.1)
        
        with patch('time.sleep'):  # Mock sleep to speed up test
            content = s3_client.get_object("test-key")
        
        assert content == b"test content"
        assert mock_s3_client.get_object.call_count == 3
    
    @patch('src.utils.s3_client.config')
    @patch('src.utils.s3_client.Session')
    def test_put_object_with_encryption(self, mock_session, mock_config):
        """Test object storage with encryption."""
        # Setup mocks
        mock_config.aws.region = "us-east-1"
        mock_config.aws.s3_bucket = "test-bucket"
        mock_config.aws.access_key_id = "test-key"
        mock_config.aws.secret_access_key = "test-secret"
        mock_config.aws.s3_endpoint_url = None
        
        mock_s3_client = Mock()
        mock_session_instance = Mock()
        mock_session_instance.client.return_value = mock_s3_client
        mock_session.return_value = mock_session_instance
        
        # Mock successful operations
        mock_s3_client.get_bucket_location.return_value = {'LocationConstraint': None}
        mock_s3_client.get_bucket_encryption.return_value = {'ServerSideEncryptionConfiguration': {}}
        mock_s3_client.put_object.return_value = {}
        
        # Test
        s3_client = S3Client()
        s3_client.put_object("test-key", b"test content", {"custom": "metadata"})
        
        # Verify put_object was called with encryption
        mock_s3_client.put_object.assert_called_once()
        call_args = mock_s3_client.put_object.call_args[1]
        
        assert call_args['Bucket'] == "test-bucket"
        assert call_args['Key'] == "test-key"
        assert call_args['Body'] == b"test content"
        assert call_args['ServerSideEncryption'] == 'AES256'
        assert call_args['Metadata'] == {"custom": "metadata"}
    
    @patch('src.utils.s3_client.config')
    @patch('src.utils.s3_client.Session')
    def test_object_exists(self, mock_session, mock_config):
        """Test object existence check."""
        # Setup mocks
        mock_config.aws.region = "us-east-1"
        mock_config.aws.s3_bucket = "test-bucket"
        mock_config.aws.access_key_id = "test-key"
        mock_config.aws.secret_access_key = "test-secret"
        mock_config.aws.s3_endpoint_url = None
        
        mock_s3_client = Mock()
        mock_session_instance = Mock()
        mock_session_instance.client.return_value = mock_s3_client
        mock_session.return_value = mock_session_instance
        
        # Mock successful operations
        mock_s3_client.get_bucket_location.return_value = {'LocationConstraint': None}
        mock_s3_client.get_bucket_encryption.return_value = {'ServerSideEncryptionConfiguration': {}}
        
        # Test existing object
        mock_s3_client.head_object.return_value = {}
        s3_client = S3Client()
        assert s3_client.object_exists("existing-key") is True
        
        # Test non-existing object
        error_response = {'Error': {'Code': 'NoSuchKey'}}
        mock_s3_client.head_object.side_effect = ClientError(error_response, 'HeadObject')
        assert s3_client.object_exists("nonexistent-key") is False


class TestPatientResolver:
    """Test PatientResolver functionality."""
    
    def test_normalize_patient_name(self):
        """Test patient name normalization."""
        mock_s3_client = Mock()
        resolver = PatientResolver(mock_s3_client)
        
        # Test basic normalization
        assert resolver._normalize_patient_name("jane smith") == "JaneSmith"
        assert resolver._normalize_patient_name("  JOHN   DOE  ") == "JohnDoe"
        assert resolver._normalize_patient_name("Mary-Jane O'Connor") == "MaryJaneOConnor"
        assert resolver._normalize_patient_name("Dr. Smith Jr.") == "DrSmithJr"
    
    def test_names_similar(self):
        """Test name similarity checking."""
        mock_s3_client = Mock()
        resolver = PatientResolver(mock_s3_client)
        
        # Test exact matches
        assert resolver._names_similar("johnsmith", "johnsmith") is True
        
        # Test partial matches
        assert resolver._names_similar("john", "johnsmith") is True
        assert resolver._names_similar("johnsmith", "john") is True
        
        # Test dissimilar names
        assert resolver._names_similar("john", "mary") is False
        
        # Test empty names
        assert resolver._names_similar("", "john") is False
        assert resolver._names_similar("john", "") is False
    
    def test_find_patient_record_exact_match(self):
        """Test finding patient record with exact name match."""
        mock_s3_client = Mock()
        mock_s3_client.list_objects.return_value = [
            "01995eed-3135-733a-b8eb-a6ff8eaa39dd/JaneSmith.xml",
            "02995eed-3135-733a-b8eb-a6ff8eaa39dd/JohnDoe.xml",
            "metadata/index.json"
        ]
        
        resolver = PatientResolver(mock_s3_client)
        
        # Test exact match
        result = resolver._find_patient_record("JaneSmith")
        assert result == "01995eed-3135-733a-b8eb-a6ff8eaa39dd/JaneSmith.xml"
        
        # Test case insensitive match
        result = resolver._find_patient_record("janesmith")
        assert result == "01995eed-3135-733a-b8eb-a6ff8eaa39dd/JaneSmith.xml"
    
    def test_find_patient_record_not_found(self):
        """Test patient record not found scenario."""
        mock_s3_client = Mock()
        mock_s3_client.list_objects.return_value = [
            "01995eed-3135-733a-b8eb-a6ff8eaa39dd/JaneSmith.xml",
            "metadata/index.json"
        ]
        
        resolver = PatientResolver(mock_s3_client)
        
        result = resolver._find_patient_record("NonExistentPatient")
        assert result is None
    
    def test_construct_patient_path_success(self):
        """Test successful patient path construction."""
        mock_s3_client = Mock()
        mock_s3_client.list_objects.return_value = [
            "01995eed-3135-733a-b8eb-a6ff8eaa39dd/JaneSmith.xml"
        ]
        
        resolver = PatientResolver(mock_s3_client)
        
        result = resolver.construct_patient_path("Jane Smith")
        assert result == "01995eed-3135-733a-b8eb-a6ff8eaa39dd/JaneSmith.xml"
    
    def test_construct_patient_path_not_found(self):
        """Test patient path construction when patient not found."""
        mock_s3_client = Mock()
        mock_s3_client.list_objects.return_value = []
        
        resolver = PatientResolver(mock_s3_client)
        
        with pytest.raises(PatientNotFoundError, match="No record found for patient"):
            resolver.construct_patient_path("Nonexistent Patient")
    
    def test_extract_patient_id_from_path(self):
        """Test patient ID extraction from file path."""
        mock_s3_client = Mock()
        resolver = PatientResolver(mock_s3_client)
        
        # Test standard path format
        patient_id = resolver.extract_patient_id_from_path(
            "01995eed-3135-733a-b8eb-a6ff8eaa39dd/JaneSmith.xml"
        )
        assert patient_id == "01995eed-3135-733a-b8eb-a6ff8eaa39dd"
        
        # Test fallback to filename
        patient_id = resolver.extract_patient_id_from_path("JaneSmith.xml")
        assert patient_id == "JaneSmith"
    
    def test_construct_analysis_path(self):
        """Test analysis report path construction."""
        mock_s3_client = Mock()
        resolver = PatientResolver(mock_s3_client)
        
        # Test with specific timestamp
        timestamp = datetime(2023, 11, 1, 14, 30, 0)
        path = resolver.construct_analysis_path("patient-123", timestamp)
        assert path == "patient-123/analysis-20231101_143000.json"
        
        # Test with current timestamp (just check format)
        path = resolver.construct_analysis_path("patient-123")
        assert path.startswith("patient-123/analysis-")
        assert path.endswith(".json")
    
    def test_list_patient_analyses(self):
        """Test listing patient analysis reports."""
        mock_s3_client = Mock()
        mock_s3_client.list_objects.return_value = [
            "patient-123/analysis-20231101_143000.json",
            "patient-123/analysis-20231102_090000.json",
            "patient-123/analysis-20231103_160000.json"
        ]
        
        resolver = PatientResolver(mock_s3_client)
        
        analyses = resolver.list_patient_analyses("patient-123")
        
        # Should be sorted newest first
        assert len(analyses) == 3
        assert analyses[0] == "patient-123/analysis-20231103_160000.json"
        assert analyses[2] == "patient-123/analysis-20231101_143000.json"


def test_create_s3_client_factory():
    """Test S3 client factory function."""
    with patch('src.utils.s3_client.S3Client') as mock_s3_client_class:
        mock_instance = Mock()
        mock_s3_client_class.return_value = mock_instance
        
        result = create_s3_client("test-bucket", "http://localhost:4566")
        
        mock_s3_client_class.assert_called_once_with(
            bucket_name="test-bucket",
            endpoint_url="http://localhost:4566"
        )
        assert result == mock_instance