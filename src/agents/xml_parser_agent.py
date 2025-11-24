"""XML Parser Agent - Complete integration of S3, patient resolution, and XML parsing."""

import logging
from typing import Optional
from datetime import datetime

from ..models import PatientData
from ..models.exceptions import XMLParsingError, PatientNotFoundError, S3Error
from ..utils import S3Client, PatientResolver, AuditLogger, setup_logging
from .xml_parser import XMLParser
from .xml_parser_cda import CDAXMLParser


logger = logging.getLogger(__name__)


class XMLParserAgent:
    """
    Complete XML Parser Agent that handles the full workflow:
    1. Accept patient name input
    2. Resolve patient name to S3 path
    3. Retrieve XML file from S3
    4. Parse XML and extract medical data
    5. Return structured PatientData
    """
    
    def __init__(self, 
                 s3_client: Optional[S3Client] = None,
                 audit_logger: Optional[AuditLogger] = None):
        """
        Initialize XML Parser Agent.
        
        Args:
            s3_client: Optional S3 client (will create default if not provided)
            audit_logger: Optional audit logger (will create default if not provided)
        """
        self.s3_client = s3_client or S3Client()
        self.audit_logger = audit_logger or setup_logging()
        self.patient_resolver = PatientResolver(self.s3_client)
        self.generic_parser = XMLParser(self.audit_logger)
        self.cda_parser = CDAXMLParser(self.audit_logger)
        
        logger.info("XML Parser Agent initialized with CDA support")
    
    def parse_patient_record(self, patient_name: str) -> PatientData:
        """
        Complete workflow to parse patient record from name to structured data.
        
        Args:
            patient_name: Name of the patient to retrieve and parse
            
        Returns:
            PatientData: Structured patient medical data
            
        Raises:
            PatientNotFoundError: If patient record cannot be found
            XMLParsingError: If XML parsing fails
            S3Error: If S3 operations fail
        """
        request_id = self._generate_request_id()
        start_time = datetime.now()
        
        try:
            # Log workflow start
            self.audit_logger.log_processing_start(
                patient_id=f"search_{patient_name.replace(' ', '_')}",
                workflow_type="xml_parsing",
                request_id=request_id
            )
            
            logger.info(f"Starting patient record parsing for: {patient_name}")
            
            # Step 1: Resolve patient name to S3 path
            logger.info("Resolving patient name to S3 path...")
            patient_path = self.patient_resolver.construct_patient_path(patient_name)
            logger.info(f"Patient record located at: {patient_path}")
            
            # Step 2: Extract patient ID from path for audit logging
            patient_id = self.patient_resolver.extract_patient_id_from_path(patient_path)
            
            # Step 3: Retrieve XML content from S3
            logger.info("Retrieving XML content from S3...")
            xml_content = self.s3_client.get_object(patient_path)
            xml_string = xml_content.decode('utf-8')
            
            # Log data access
            self.audit_logger.log_data_access(
                patient_id=patient_id,
                operation="s3_retrieve",
                details={
                    "s3_path": patient_path,
                    "content_size": len(xml_content)
                },
                request_id=request_id
            )
            
            # Step 4: Parse XML content (auto-detect CDA vs generic)
            logger.info("Parsing XML content...")
            if self._is_cda_document(xml_string):
                logger.info(f"Detected HL7 CDA document for {patient_name}")
                patient_data = self.cda_parser.parse_patient_xml(xml_string, patient_name)
            else:
                logger.info(f"Using generic XML parser for {patient_name}")
                patient_data = self.generic_parser.parse_patient_xml(xml_string, patient_name)
            
            # Step 5: Validate and log success
            processing_time = (datetime.now() - start_time).total_seconds()
            
            self.audit_logger.log_processing_complete(
                patient_id=patient_data.patient_id,
                workflow_type="xml_parsing",
                duration_seconds=processing_time,
                request_id=request_id
            )
            
            logger.info(f"Successfully parsed patient record for {patient_name} "
                       f"(ID: {patient_data.patient_id}) in {processing_time:.2f}s")
            
            return patient_data
            
        except PatientNotFoundError as e:
            error_msg = f"Patient not found: {patient_name}"
            logger.error(error_msg)
            self.audit_logger.log_error(
                patient_id=f"search_{patient_name.replace(' ', '_')}",
                operation="patient_resolution",
                error=e,
                request_id=request_id
            )
            raise
            
        except S3Error as e:
            error_msg = f"S3 error while retrieving patient record: {str(e)}"
            logger.error(error_msg)
            self.audit_logger.log_error(
                patient_id=patient_id if 'patient_id' in locals() else "unknown",
                operation="s3_retrieval",
                error=e,
                request_id=request_id
            )
            raise
            
        except XMLParsingError as e:
            error_msg = f"XML parsing error for patient {patient_name}: {str(e)}"
            logger.error(error_msg)
            self.audit_logger.log_error(
                patient_id=patient_id if 'patient_id' in locals() else "unknown",
                operation="xml_parsing",
                error=e,
                request_id=request_id
            )
            raise
            
        except Exception as e:
            error_msg = f"Unexpected error parsing patient record for {patient_name}: {str(e)}"
            logger.error(error_msg)
            self.audit_logger.log_error(
                patient_id=patient_id if 'patient_id' in locals() else "unknown",
                operation="xml_parsing_workflow",
                error=e,
                request_id=request_id
            )
            raise XMLParsingError(error_msg)
    
    def validate_patient_exists(self, patient_name: str) -> bool:
        """
        Check if a patient record exists without parsing it.
        
        Args:
            patient_name: Name of the patient to check
            
        Returns:
            bool: True if patient record exists, False otherwise
        """
        try:
            patient_path = self.patient_resolver.construct_patient_path(patient_name)
            return self.s3_client.object_exists(patient_path)
        except PatientNotFoundError:
            return False
        except Exception as e:
            logger.warning(f"Error checking patient existence: {str(e)}")
            return False
    
    def get_patient_metadata(self, patient_name: str) -> dict:
        """
        Get metadata about a patient record without parsing the full XML.
        
        Args:
            patient_name: Name of the patient
            
        Returns:
            dict: Metadata about the patient record
            
        Raises:
            PatientNotFoundError: If patient record cannot be found
        """
        try:
            patient_path = self.patient_resolver.construct_patient_path(patient_name)
            patient_id = self.patient_resolver.extract_patient_id_from_path(patient_path)
            
            # Get S3 object metadata
            s3_metadata = self.s3_client.get_object_metadata(patient_path)
            
            # Get list of existing analyses
            analyses = self.patient_resolver.list_patient_analyses(patient_id)
            
            return {
                'patient_name': patient_name,
                'patient_id': patient_id,
                's3_path': patient_path,
                'file_size': s3_metadata['size'],
                'last_modified': s3_metadata['last_modified'],
                'encrypted': bool(s3_metadata.get('server_side_encryption')),
                'existing_analyses': len(analyses),
                'latest_analysis': analyses[0] if analyses else None
            }
            
        except Exception as e:
            logger.error(f"Error getting patient metadata: {str(e)}")
            raise
    
    def list_available_patients(self, limit: int = 100) -> list:
        """
        List available patient records in the S3 bucket.
        
        Args:
            limit: Maximum number of patients to return
            
        Returns:
            list: List of patient information dictionaries
        """
        try:
            # Get all XML files
            all_objects = self.s3_client.list_objects(prefix="", max_keys=limit * 2)
            xml_files = [obj for obj in all_objects if obj.endswith('.xml')]
            
            patients = []
            for xml_file in xml_files[:limit]:
                try:
                    # Extract patient name from filename
                    filename = xml_file.split('/')[-1]
                    patient_name = filename.replace('.xml', '').replace('_', ' ')
                    
                    # Get basic metadata
                    metadata = self.s3_client.get_object_metadata(xml_file)
                    patient_id = self.patient_resolver.extract_patient_id_from_path(xml_file)
                    
                    patients.append({
                        'patient_name': patient_name,
                        'patient_id': patient_id,
                        's3_path': xml_file,
                        'file_size': metadata['size'],
                        'last_modified': metadata['last_modified']
                    })
                    
                except Exception as e:
                    logger.warning(f"Error processing patient file {xml_file}: {str(e)}")
                    continue
            
            logger.info(f"Found {len(patients)} patient records")
            return patients
            
        except Exception as e:
            logger.error(f"Error listing patients: {str(e)}")
            return []
    
    def _is_cda_document(self, xml_content: str) -> bool:
        """
        Detect if XML content is an HL7 CDA document.
        
        Args:
            xml_content: Raw XML content as string
            
        Returns:
            bool: True if CDA document, False otherwise
        """
        # Check for CDA-specific elements
        cda_indicators = [
            '<ClinicalDocument',
            'xmlns="urn:hl7-org:v3"',
            'ClinicalDocument xmlns',
        ]
        
        for indicator in cda_indicators:
            if indicator in xml_content:
                return True
        
        return False
    
    def _generate_request_id(self) -> str:
        """Generate unique request ID for audit trail."""
        import uuid
        return str(uuid.uuid4())
    
    def get_agent_status(self) -> dict:
        """
        Get current status and health of the XML Parser Agent.
        
        Returns:
            dict: Agent status information
        """
        try:
            # Test S3 connectivity
            s3_healthy = True
            try:
                self.s3_client.list_objects(prefix="", max_keys=1)
            except Exception:
                s3_healthy = False
            
            return {
                'agent_name': 'XML Parser Agent',
                'status': 'healthy' if s3_healthy else 'degraded',
                's3_connectivity': s3_healthy,
                'bucket_name': self.s3_client.bucket_name,
                'region': 'us-east-1',
                'initialized_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'agent_name': 'XML Parser Agent',
                'status': 'error',
                'error': str(e),
                'initialized_at': datetime.now().isoformat()
            }