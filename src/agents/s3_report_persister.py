"""S3 persistence functionality for analysis reports."""
import logging
import json
import os
import re
from typing import Optional, List, Dict, Any
from datetime import datetime
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from ..models import AnalysisReport, S3Error
from ..utils import AuditLogger
from ..config import get_config

logger = logging.getLogger(__name__)

class S3ReportPersister:
    """
    Persists analysis reports to S3 with HIPAA-compliant storage and retrieval.
    
    This class handles saving analysis reports to S3 buckets with proper
    encryption, access controls, and audit logging for HIPAA compliance.
    """
    
    def __init__(self, audit_logger: Optional[AuditLogger] = None):
        """
        Initialize S3 report persister.
        
        Args:
            audit_logger: Optional audit logger for HIPAA compliance
        """
        self.audit_logger = audit_logger
        self.config = get_config()
        
        # Initialize S3 client with HIPAA-compliant settings
        self.s3_client = boto3.client(
            's3',
            region_name=self.config.aws.region,
            aws_access_key_id=self.config.aws.access_key_id,
            aws_secret_access_key=self.config.aws.secret_access_key,
            endpoint_url=self.config.aws.s3_endpoint_url
        )
        
        self.bucket_name = self.config.aws.s3_bucket
        self.reports_prefix = "analysis-reports/"
        self.encryption_key_id = os.getenv("S3_KMS_KEY_ID", "alias/aws/s3")  # Default KMS key
        
        logger.info("S3 report persister initialized")
    
    @staticmethod
    def _sanitize_tag_value(value: str) -> str:
        """
        Sanitize a value for use as an S3 tag value.
        
        AWS S3 tag values must:
        - Be UTF-8 encoded
        - Not exceed 256 characters
        - Only contain letters, numbers, spaces, and certain special characters
        
        Args:
            value: The value to sanitize
            
        Returns:
            str: Sanitized value safe for S3 tags
        """
        if not value:
            return "unknown"
        
        # Replace invalid characters with underscores
        # S3 allows: letters, numbers, spaces, and +-=._:/
        sanitized = re.sub(r'[^a-zA-Z0-9\s+\-=._:/]', '_', str(value))
        
        # Trim to max length (256 chars for tag values)
        sanitized = sanitized[:256]
        
        # Remove leading/trailing whitespace
        sanitized = sanitized.strip()
        
        return sanitized if sanitized else "unknown"
    
    def save_analysis_report(self, report: AnalysisReport) -> str:
        """
        Save analysis report to S3 with HIPAA-compliant encryption.
        
        Args:
            report: Analysis report to save
            
        Returns:
            str: S3 key where report was saved
            
        Raises:
            S3Error: If S3 operations fail
        """
        logger.info(f"Saving analysis report {report.report_id} to S3")
        
        try:
            # Log report save start
            if self.audit_logger:
                self.audit_logger.log_data_access(
                    patient_id=report.patient_data.patient_id,
                    operation="report_save_start",
                    details={
                        "report_id": report.report_id,
                        "s3_bucket": self.bucket_name,
                        "save_timestamp": datetime.now().isoformat()
                    }
                )
            
            # Generate S3 key with timestamp-based filename
            s3_key = self._generate_s3_key(report)
            
            # Serialize report to JSON
            report_json = self._serialize_report(report)
            
            # Upload to S3 with encryption
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=report_json,
                ContentType='application/json',
                ServerSideEncryption='aws:kms',
                SSEKMSKeyId=self.encryption_key_id,
                Metadata={
                    'patient-id': report.patient_data.patient_id,
                    'report-id': report.report_id,
                    'report-version': getattr(report, 'report_version', '1.0'),
                    'generated-timestamp': report.generated_timestamp.isoformat(),
                    'content-type': 'medical-analysis-report'
                },
                Tagging=f"PatientID={self._sanitize_tag_value(report.patient_data.patient_id)}&ReportType=MedicalAnalysis&Confidential=true"
            )
            
            # Log successful save
            if self.audit_logger:
                self.audit_logger.log_data_access(
                    patient_id=report.patient_data.patient_id,
                    operation="report_save_complete",
                    details={
                        "report_id": report.report_id,
                        "s3_key": s3_key,
                        "report_size_bytes": len(report_json),
                        "encryption_enabled": True
                    }
                )
            
            logger.info(f"Analysis report saved successfully: {s3_key}")
            return s3_key
            
        except ClientError as e:
            error_msg = f"S3 client error saving report {report.report_id}: {str(e)}"
            logger.error(error_msg)
            
            if self.audit_logger:
                self.audit_logger.log_error(
                    patient_id=report.patient_data.patient_id,
                    operation="report_save",
                    error=e
                )
            
            raise S3Error(error_msg)
            
        except Exception as e:
            error_msg = f"Failed to save report {report.report_id}: {str(e)}"
            logger.error(error_msg)
            
            if self.audit_logger:
                self.audit_logger.log_error(
                    patient_id=report.patient_data.patient_id,
                    operation="report_save",
                    error=e
                )
            
            raise S3Error(error_msg)
    
    def retrieve_analysis_report(self, report_id: str, patient_id: str) -> AnalysisReport:
        """
        Retrieve analysis report from S3.
        
        Args:
            report_id: Report ID to retrieve
            patient_id: Patient ID for audit logging and validation
            
        Returns:
            AnalysisReport: Retrieved analysis report
            
        Raises:
            S3Error: If S3 operations fail or report not found
        """
        logger.info(f"Retrieving analysis report {report_id} from S3")
        
        try:
            # Log report retrieval start
            if self.audit_logger:
                self.audit_logger.log_data_access(
                    patient_id=patient_id,
                    operation="report_retrieve_start",
                    details={
                        "report_id": report_id,
                        "s3_bucket": self.bucket_name,
                        "retrieve_timestamp": datetime.now().isoformat()
                    }
                )
            
            # Find report by ID (search through possible keys)
            s3_key = self._find_report_key(report_id, patient_id)
            
            # Retrieve from S3
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            # Deserialize report
            report_json = response['Body'].read().decode('utf-8')
            report = self._deserialize_report(report_json)
            
            # Validate patient ID matches
            if report.patient_data.patient_id != patient_id:
                raise S3Error(f"Patient ID mismatch: expected {patient_id}, got {report.patient_data.patient_id}")
            
            # Log successful retrieval
            if self.audit_logger:
                self.audit_logger.log_data_access(
                    patient_id=patient_id,
                    operation="report_retrieve_complete",
                    details={
                        "report_id": report_id,
                        "s3_key": s3_key,
                        "report_size_bytes": len(report_json)
                    }
                )
            
            logger.info(f"Analysis report retrieved successfully: {report_id}")
            return report
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                error_msg = f"Report {report_id} not found in S3"
            else:
                error_msg = f"S3 client error retrieving report {report_id}: {str(e)}"
            
            logger.error(error_msg)
            
            if self.audit_logger:
                self.audit_logger.log_error(
                    patient_id=patient_id,
                    operation="report_retrieve",
                    error=e
                )
            
            raise S3Error(error_msg)
            
        except Exception as e:
            error_msg = f"Failed to retrieve report {report_id}: {str(e)}"
            logger.error(error_msg)
            
            if self.audit_logger:
                self.audit_logger.log_error(
                    patient_id=patient_id,
                    operation="report_retrieve",
                    error=e
                )
            
            raise S3Error(error_msg)
    
    def list_patient_reports(self, patient_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        List analysis reports for a specific patient.
        
        Args:
            patient_id: Patient ID to list reports for
            limit: Maximum number of reports to return
            
        Returns:
            List[Dict[str, Any]]: List of report metadata
            
        Raises:
            S3Error: If S3 operations fail
        """
        logger.info(f"Listing analysis reports for patient {patient_id}")
        
        try:
            # Log report listing start
            if self.audit_logger:
                self.audit_logger.log_data_access(
                    patient_id=patient_id,
                    operation="report_list_start",
                    details={
                        "s3_bucket": self.bucket_name,
                        "list_timestamp": datetime.now().isoformat()
                    }
                )
            
            # List objects with patient ID prefix
            patient_prefix = f"{self.reports_prefix}patient-{patient_id}/"
            
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=patient_prefix,
                MaxKeys=limit
            )
            
            reports = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    # Get object metadata
                    head_response = self.s3_client.head_object(
                        Bucket=self.bucket_name,
                        Key=obj['Key']
                    )
                    
                    metadata = head_response.get('Metadata', {})
                    
                    report_info = {
                        's3_key': obj['Key'],
                        'report_id': metadata.get('report-id', 'unknown'),
                        'generated_timestamp': metadata.get('generated-timestamp', obj['LastModified'].isoformat()),
                        'size_bytes': obj['Size'],
                        'last_modified': obj['LastModified'].isoformat(),
                        'report_version': metadata.get('report-version', '1.0')
                    }
                    reports.append(report_info)
            
            # Sort by generation timestamp (newest first)
            reports.sort(key=lambda x: x['generated_timestamp'], reverse=True)
            
            # Log successful listing
            if self.audit_logger:
                self.audit_logger.log_data_access(
                    patient_id=patient_id,
                    operation="report_list_complete",
                    details={
                        "reports_found": len(reports),
                        "search_prefix": patient_prefix
                    }
                )
            
            logger.info(f"Found {len(reports)} reports for patient {patient_id}")
            return reports
            
        except ClientError as e:
            error_msg = f"S3 client error listing reports for patient {patient_id}: {str(e)}"
            logger.error(error_msg)
            
            if self.audit_logger:
                self.audit_logger.log_error(
                    patient_id=patient_id,
                    operation="report_list",
                    error=e
                )
            
            raise S3Error(error_msg)
            
        except Exception as e:
            error_msg = f"Failed to list reports for patient {patient_id}: {str(e)}"
            logger.error(error_msg)
            
            if self.audit_logger:
                self.audit_logger.log_error(
                    patient_id=patient_id,
                    operation="report_list",
                    error=e
                )
            
            raise S3Error(error_msg)
    
    def delete_analysis_report(self, report_id: str, patient_id: str) -> bool:
        """
        Delete analysis report from S3 (for data retention compliance).
        
        Args:
            report_id: Report ID to delete
            patient_id: Patient ID for audit logging and validation
            
        Returns:
            bool: True if successfully deleted
            
        Raises:
            S3Error: If S3 operations fail
        """
        logger.info(f"Deleting analysis report {report_id} from S3")
        
        try:
            # Log report deletion start
            if self.audit_logger:
                self.audit_logger.log_data_access(
                    patient_id=patient_id,
                    operation="report_delete_start",
                    details={
                        "report_id": report_id,
                        "s3_bucket": self.bucket_name,
                        "delete_timestamp": datetime.now().isoformat()
                    }
                )
            
            # Find report key
            s3_key = self._find_report_key(report_id, patient_id)
            
            # Delete from S3
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            # Log successful deletion
            if self.audit_logger:
                self.audit_logger.log_data_access(
                    patient_id=patient_id,
                    operation="report_delete_complete",
                    details={
                        "report_id": report_id,
                        "s3_key": s3_key,
                        "deletion_confirmed": True
                    }
                )
            
            logger.info(f"Analysis report deleted successfully: {report_id}")
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.warning(f"Report {report_id} not found for deletion")
                return False
            
            error_msg = f"S3 client error deleting report {report_id}: {str(e)}"
            logger.error(error_msg)
            
            if self.audit_logger:
                self.audit_logger.log_error(
                    patient_id=patient_id,
                    operation="report_delete",
                    error=e
                )
            
            raise S3Error(error_msg)
            
        except Exception as e:
            error_msg = f"Failed to delete report {report_id}: {str(e)}"
            logger.error(error_msg)
            
            if self.audit_logger:
                self.audit_logger.log_error(
                    patient_id=patient_id,
                    operation="report_delete",
                    error=e
                )
            
            raise S3Error(error_msg)
    
    def _generate_s3_key(self, report: AnalysisReport) -> str:
        """Generate S3 key for analysis report with timestamp-based filename."""
        timestamp = report.generated_timestamp.strftime("%Y%m%d_%H%M%S")
        patient_id = report.patient_data.patient_id
        report_id = report.report_id
        
        # Format: analysis-reports/patient-{patient_id}/analysis-{timestamp}-{report_id}.json
        return f"{self.reports_prefix}patient-{patient_id}/analysis-{timestamp}-{report_id}.json"
    
    def _find_report_key(self, report_id: str, patient_id: str) -> str:
        """Find S3 key for a report by searching patient's reports."""
        patient_prefix = f"{self.reports_prefix}patient-{patient_id}/"
        
        # List objects to find the report
        response = self.s3_client.list_objects_v2(
            Bucket=self.bucket_name,
            Prefix=patient_prefix
        )
        
        if 'Contents' not in response:
            raise S3Error(f"No reports found for patient {patient_id}")
        
        # Search for report by ID in filename or metadata
        for obj in response['Contents']:
            if report_id in obj['Key']:
                return obj['Key']
            
            # Check metadata if filename doesn't contain report ID
            try:
                head_response = self.s3_client.head_object(
                    Bucket=self.bucket_name,
                    Key=obj['Key']
                )
                metadata = head_response.get('Metadata', {})
                if metadata.get('report-id') == report_id:
                    return obj['Key']
            except ClientError:
                continue
        
        raise S3Error(f"Report {report_id} not found for patient {patient_id}")
    
    def _serialize_report(self, report: AnalysisReport) -> str:
        """Serialize analysis report to JSON string."""
        try:
            # Convert report to dictionary
            report_dict = report.to_dict()
            
            # Serialize to JSON with proper formatting
            return json.dumps(report_dict, indent=2, default=str, ensure_ascii=False)
            
        except Exception as e:
            raise S3Error(f"Failed to serialize report: {str(e)}")
    
    def _deserialize_report(self, report_json: str) -> AnalysisReport:
        """Deserialize JSON string to analysis report."""
        try:
            # Parse JSON
            report_dict = json.loads(report_json)
            
            # Convert back to AnalysisReport object
            return AnalysisReport.from_dict(report_dict)
            
        except Exception as e:
            raise S3Error(f"Failed to deserialize report: {str(e)}")
    
    def get_storage_statistics(self, patient_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get storage statistics for reports.
        
        Args:
            patient_id: Optional patient ID to get statistics for specific patient
            
        Returns:
            Dict[str, Any]: Storage statistics
        """
        try:
            if patient_id:
                prefix = f"{self.reports_prefix}patient-{patient_id}/"
            else:
                prefix = self.reports_prefix
            
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            if 'Contents' not in response:
                return {
                    "total_reports": 0,
                    "total_size_bytes": 0,
                    "oldest_report": None,
                    "newest_report": None
                }
            
            objects = response['Contents']
            total_size = sum(obj['Size'] for obj in objects)
            
            # Sort by last modified
            objects.sort(key=lambda x: x['LastModified'])
            
            return {
                "total_reports": len(objects),
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "oldest_report": objects[0]['LastModified'].isoformat() if objects else None,
                "newest_report": objects[-1]['LastModified'].isoformat() if objects else None,
                "average_size_bytes": round(total_size / len(objects)) if objects else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get storage statistics: {str(e)}")
            return {"error": str(e)}