"""S3 client utilities with HIPAA compliance and error handling."""

import logging
import time
from typing import Optional, Dict, Any
from botocore.exceptions import ClientError, NoCredentialsError, BotoCoreError, TokenRetrievalError
import boto3
from boto3.session import Session

from ..config import config
from ..models.exceptions import S3Error


logger = logging.getLogger(__name__)


class S3Client:
    """S3 client with HIPAA compliance, retry logic, and connection pooling."""
    
    def __init__(self, 
                 bucket_name: Optional[str] = None,
                 endpoint_url: Optional[str] = None,
                 max_retries: int = 3,
                 retry_delay: float = 1.0):
        """
        Initialize S3 client with HIPAA compliance validation.
        
        Args:
            bucket_name: S3 bucket name (defaults to config)
            endpoint_url: S3 endpoint URL (for LocalStack testing)
            max_retries: Maximum number of retry attempts
            retry_delay: Initial delay between retries (exponential backoff)
        """
        self.bucket_name = bucket_name or config.aws.s3_bucket
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # HIPAA Compliance: Ensure US-East-1 region
        if config.aws.region != "us-east-1":
            raise S3Error(f"HIPAA Compliance Error: Region must be us-east-1, got {config.aws.region}")
        
        # Initialize AWS session
        # If an AWS profile is set, prefer creating a session with that profile
        import os
        profile_name = os.getenv("AWS_PROFILE") or os.getenv("AWS_DEFAULT_PROFILE")
        if profile_name:
            # Ensure botocore loads shared config (SSO support)
            os.environ.setdefault("AWS_SDK_LOAD_CONFIG", "1")
            logger.info(f"Using AWS profile for session: {profile_name} (overrides env creds)")
            self.session = Session(profile_name=profile_name, region_name=config.aws.region)
        else:
            self.session = Session(
                aws_access_key_id=config.aws.access_key_id,
                aws_secret_access_key=config.aws.secret_access_key,
                region_name=config.aws.region
            )

        # Ensure credentials are available from the session or environment
        try:
            resolved_creds = self.session.get_credentials()
            has_access_key = bool(resolved_creds and getattr(resolved_creds, "access_key", None))

            # Determine a non-sensitive credential source hint for diagnostics
            import os
            cred_source = "unknown"
            if os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"):
                cred_source = "environment"
            elif os.getenv("AWS_PROFILE"):
                cred_source = f"profile:{os.getenv('AWS_PROFILE')}"
            else:
                # Check for shared credentials file presence
                try:
                    from pathlib import Path
                    if Path.home().joinpath('.aws', 'credentials').exists():
                        cred_source = "shared_credentials_file"
                    else:
                        cred_source = "role_or_imds"
                except Exception:
                    cred_source = "unknown"

            logger.info(f"Resolved AWS credential source hint: {cred_source}")

            # Log non-sensitive credential details for diagnostic purposes
            try:
                frozen = resolved_creds.get_frozen_credentials() if resolved_creds else None
                access_key_id = getattr(frozen, 'access_key', None)
                token_present = bool(getattr(frozen, 'token', None)) if frozen else False
                expiry = getattr(frozen, 'expiry_time', None) if frozen else None
                logger.info(
                    f"AWS credential diagnostic - access_key_id={access_key_id}, "
                    f"session_token_present={token_present}, expiry={expiry}"
                )
            except Exception:
                # Never log secrets; this is best-effort diagnostic only
                logger.debug("Unable to fetch frozen credentials for diagnostics")

            if not has_access_key:
                if not (os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY")):
                    raise S3Error(
                        "No AWS credentials found. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY, "
                        "or configure a profile with `aws configure`."
                    )
        except S3Error:
            raise
        except TokenRetrievalError:
            # SSO token refresh failed (expired or invalid refresh token)
            profile = os.getenv("AWS_PROFILE") or os.getenv("AWS_DEFAULT_PROFILE") or "<your-profile>"
            raise S3Error(
                "SSO token refresh failed or token expired. Please run: \n"
                f"   aws sso login --profile {profile}\n"
                "or re-authenticate with your SSO provider and try again."
            )
        except Exception:
            # If we cannot resolve credentials for any reason, raise a clear error
            raise S3Error(
                "Unable to resolve AWS credentials. Ensure environment variables or AWS profile are configured."
            )
        
        # Create S3 client with endpoint override for LocalStack
        client_config = {
            'region_name': config.aws.region,
            'config': boto3.session.Config(
                retries={'max_attempts': 0},  # We handle retries manually
                max_pool_connections=50  # Connection pooling
            )
        }
        
        if endpoint_url or config.aws.s3_endpoint_url:
            client_config['endpoint_url'] = endpoint_url or config.aws.s3_endpoint_url
            logger.info(f"Using custom S3 endpoint: {client_config['endpoint_url']}")
        
        try:
            self.s3_client = self.session.client('s3', **client_config)
            logger.info(f"S3 client initialized for bucket: {self.bucket_name}")
            
            # Validate bucket access and HIPAA compliance
            self._validate_bucket_compliance()
            
        except NoCredentialsError as e:
            raise S3Error("No AWS credentials available: configure AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
        except ClientError as e:
            # Surface common credential-related errors with actionable guidance
            error_code = e.response.get('Error', {}).get('Code')
            if error_code == 'InvalidAccessKeyId':
                raise S3Error(
                    "Invalid AWS Access Key ID provided. Verify AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY or profile."
                )
            elif error_code == 'SignatureDoesNotMatch':
                raise S3Error(
                    "AWS secret key signature mismatch. Verify AWS_SECRET_ACCESS_KEY and system clock."
                )
            else:
                raise S3Error(f"Failed to initialize S3 client: {str(e)}")
    
    def _validate_bucket_compliance(self) -> None:
        """Validate bucket exists and meets HIPAA compliance requirements."""
        try:
            # Check bucket location
            response = self.s3_client.get_bucket_location(Bucket=self.bucket_name)
            bucket_region = response.get('LocationConstraint') or 'us-east-1'
            
            if bucket_region != 'us-east-1':
                raise S3Error(f"HIPAA Compliance Error: Bucket {self.bucket_name} is in {bucket_region}, must be us-east-1")
            
            # Check encryption
            try:
                encryption = self.s3_client.get_bucket_encryption(Bucket=self.bucket_name)
                logger.info("Bucket encryption verified")
            except ClientError as e:
                if e.response['Error']['Code'] == 'ServerSideEncryptionConfigurationNotFoundError':
                    logger.warning(f"Bucket {self.bucket_name} does not have encryption enabled - HIPAA compliance risk")
                else:
                    raise
            
            logger.info(f"Bucket {self.bucket_name} HIPAA compliance validated")
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code')
            if error_code == 'NoSuchBucket':
                raise S3Error(f"Bucket {self.bucket_name} does not exist")
            elif error_code == 'AccessDenied':
                raise S3Error(f"Access denied to bucket {self.bucket_name}")
            elif error_code == 'InvalidAccessKeyId':
                raise S3Error(
                    "Failed to validate bucket compliance: Invalid AWS Access Key ID. "
                    "Check your AWS credentials and try again."
                )
            elif error_code == 'SignatureDoesNotMatch':
                raise S3Error(
                    "Failed to validate bucket compliance: AWS secret key signature mismatch. "
                    "Verify AWS_SECRET_ACCESS_KEY and system time."
                )
            else:
                raise S3Error(f"Failed to validate bucket compliance: {str(e)}")
    
    def _retry_with_backoff(self, operation, *args, **kwargs):
        """Execute operation with exponential backoff retry logic."""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return operation(*args, **kwargs)
            except ClientError as e:
                last_exception = e
                error_code = e.response['Error']['Code']
                
                # Don't retry on certain errors
                if error_code in ['NoSuchBucket', 'NoSuchKey', 'AccessDenied']:
                    raise S3Error(f"S3 operation failed: {str(e)}")
                
                if attempt < self.max_retries:
                    delay = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"S3 operation failed (attempt {attempt + 1}/{self.max_retries + 1}), "
                                 f"retrying in {delay}s: {str(e)}")
                    time.sleep(delay)
                else:
                    logger.error(f"S3 operation failed after {self.max_retries + 1} attempts")
            except BotoCoreError as e:
                last_exception = e
                if attempt < self.max_retries:
                    delay = self.retry_delay * (2 ** attempt)
                    logger.warning(f"S3 connection error (attempt {attempt + 1}/{self.max_retries + 1}), "
                                 f"retrying in {delay}s: {str(e)}")
                    time.sleep(delay)
                else:
                    logger.error(f"S3 connection failed after {self.max_retries + 1} attempts")
        
        raise S3Error(f"S3 operation failed after {self.max_retries + 1} attempts: {str(last_exception)}")
    
    def get_object(self, key: str) -> bytes:
        """
        Retrieve object from S3 with retry logic.
        
        Args:
            key: S3 object key
            
        Returns:
            Object content as bytes
            
        Raises:
            S3Error: If object retrieval fails
        """
        logger.info(f"Retrieving object: s3://{self.bucket_name}/{key}")
        
        def _get_operation():
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            return response['Body'].read()
        
        try:
            content = self._retry_with_backoff(_get_operation)
            logger.info(f"Successfully retrieved object {key} ({len(content)} bytes)")
            return content
        except Exception as e:
            logger.error(f"Failed to retrieve object {key}: {str(e)}")
            raise
    
    def put_object(self, key: str, content: bytes, metadata: Optional[Dict[str, str]] = None) -> None:
        """
        Store object in S3 with retry logic and HIPAA compliance.
        
        Args:
            key: S3 object key
            content: Object content as bytes
            metadata: Optional metadata dictionary
            
        Raises:
            S3Error: If object storage fails
        """
        logger.info(f"Storing object: s3://{self.bucket_name}/{key} ({len(content)} bytes)")
        
        # HIPAA Compliance: Ensure server-side encryption
        put_kwargs = {
            'Bucket': self.bucket_name,
            'Key': key,
            'Body': content,
            'ServerSideEncryption': 'AES256'  # Ensure encryption
        }
        
        if metadata:
            put_kwargs['Metadata'] = metadata
        
        def _put_operation():
            return self.s3_client.put_object(**put_kwargs)
        
        try:
            self._retry_with_backoff(_put_operation)
            logger.info(f"Successfully stored object {key}")
        except Exception as e:
            logger.error(f"Failed to store object {key}: {str(e)}")
            raise
    
    def object_exists(self, key: str) -> bool:
        """
        Check if object exists in S3.
        
        Args:
            key: S3 object key
            
        Returns:
            True if object exists, False otherwise
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return False
            else:
                raise S3Error(f"Failed to check object existence: {str(e)}")
    
    def list_objects(self, prefix: str = "", max_keys: int = 1000) -> list:
        """
        List objects in S3 bucket with given prefix.
        
        Args:
            prefix: Object key prefix to filter by
            max_keys: Maximum number of keys to return
            
        Returns:
            List of object keys
        """
        logger.info(f"Listing objects with prefix: {prefix}")
        
        def _list_operation():
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys
            )
            return [obj['Key'] for obj in response.get('Contents', [])]
        
        try:
            keys = self._retry_with_backoff(_list_operation)
            logger.info(f"Found {len(keys)} objects with prefix {prefix}")
            return keys
        except Exception as e:
            logger.error(f"Failed to list objects: {str(e)}")
            raise
    
    def get_object_metadata(self, key: str) -> Dict[str, Any]:
        """
        Get object metadata from S3.
        
        Args:
            key: S3 object key
            
        Returns:
            Dictionary containing object metadata
        """
        try:
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return {
                'size': response.get('ContentLength', 0),
                'last_modified': response.get('LastModified'),
                'etag': response.get('ETag', '').strip('"'),
                'metadata': response.get('Metadata', {}),
                'server_side_encryption': response.get('ServerSideEncryption')
            }
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                raise S3Error(f"Object {key} does not exist")
            else:
                raise S3Error(f"Failed to get object metadata: {str(e)}")


def create_s3_client(bucket_name: Optional[str] = None, 
                    endpoint_url: Optional[str] = None) -> S3Client:
    """
    Factory function to create S3 client with default configuration.
    
    Args:
        bucket_name: Optional bucket name override
        endpoint_url: Optional endpoint URL for testing
        
    Returns:
        Configured S3Client instance
    """
    return S3Client(bucket_name=bucket_name, endpoint_url=endpoint_url)