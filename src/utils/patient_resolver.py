"""Patient record path resolution utilities."""

import logging
import re
from typing import Optional, Tuple
from datetime import datetime

from ..models.exceptions import PatientNotFoundError


logger = logging.getLogger(__name__)


class PatientResolver:
    """Resolves patient names to S3 paths and handles patient record location."""
    
    def __init__(self, s3_client):
        """
        Initialize patient resolver.
        
        Args:
            s3_client: S3Client instance for file operations
        """
        self.s3_client = s3_client
    
    def construct_patient_path(self, patient_name: str) -> str:
        """
        Construct S3 path for patient XML file based on patient name.
        
        Based on the example: s3://patient-records-20251024/01995eed-3135-733a-b8eb-a6ff8eaa39dd/JaneSmith.xml
        
        Args:
            patient_name: Patient name (e.g., "Jane Smith")
            
        Returns:
            S3 key path for the patient XML file
            
        Raises:
            PatientNotFoundError: If patient record cannot be located
        """
        # Normalize patient name (remove spaces, handle case)
        normalized_name = self._normalize_patient_name(patient_name)
        
        logger.info(f"Searching for patient record: {patient_name} (normalized: {normalized_name})")
        
        # Search for patient record in all patient directories
        patient_key = self._find_patient_record(normalized_name)
        
        if not patient_key:
            raise PatientNotFoundError(f"No record found for patient: {patient_name}")
        
        logger.info(f"Found patient record at: {patient_key}")
        return patient_key
    
    def _normalize_patient_name(self, patient_name: str) -> str:
        """
        Normalize patient name for file searching.
        
        Args:
            patient_name: Raw patient name input
            
        Returns:
            Normalized patient name for file matching
        """
        # Remove extra spaces and convert to title case
        normalized = re.sub(r'\s+', '', patient_name.strip().title())
        
        # Handle common name variations
        normalized = normalized.replace("'", "").replace("-", "").replace(".", "")
        
        return normalized
    
    def _find_patient_record(self, normalized_name: str) -> Optional[str]:
        """
        Search for patient record across all patient directories.
        
        Args:
            normalized_name: Normalized patient name
            
        Returns:
            S3 key path if found, None otherwise
        """
        try:
            # List all objects in the bucket to find patient directories
            all_objects = self.s3_client.list_objects(prefix="", max_keys=10000)
            
            # Look for XML files matching the patient name pattern
            for obj_key in all_objects:
                if obj_key.endswith('.xml'):
                    # Extract filename from path
                    filename = obj_key.split('/')[-1]
                    file_basename = filename.replace('.xml', '')
                    
                    # Normalize the filename for comparison
                    normalized_filename = self._normalize_patient_name(file_basename)
                    
                    if normalized_filename.lower() == normalized_name.lower():
                        return obj_key
            
            # If exact match not found, try partial matching
            for obj_key in all_objects:
                if obj_key.endswith('.xml'):
                    filename = obj_key.split('/')[-1]
                    file_basename = filename.replace('.xml', '')
                    normalized_filename = self._normalize_patient_name(file_basename)
                    
                    # Check if names are similar (for typos or variations)
                    if self._names_similar(normalized_name.lower(), normalized_filename.lower()):
                        logger.warning(f"Found similar patient name: {filename} for search: {normalized_name}")
                        return obj_key
            
            return None
            
        except Exception as e:
            logger.error(f"Error searching for patient record: {str(e)}")
            raise PatientNotFoundError(f"Failed to search for patient record: {str(e)}")
    
    def _names_similar(self, name1: str, name2: str, threshold: float = 0.8) -> bool:
        """
        Check if two names are similar using simple string similarity.
        
        Args:
            name1: First name to compare
            name2: Second name to compare
            threshold: Similarity threshold (0.0 to 1.0)
            
        Returns:
            True if names are similar enough
        """
        # Simple similarity check based on common characters
        if len(name1) == 0 or len(name2) == 0:
            return False
        
        # Check if one name contains the other
        if name1 in name2 or name2 in name1:
            return True
        
        # Calculate character overlap
        set1 = set(name1.lower())
        set2 = set(name2.lower())
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        similarity = intersection / union if union > 0 else 0
        return similarity >= threshold
    
    def construct_analysis_path(self, patient_id: str, timestamp: Optional[datetime] = None) -> str:
        """
        Construct S3 path for analysis report based on patient ID and timestamp.
        
        Args:
            patient_id: Patient identifier
            timestamp: Analysis timestamp (defaults to current time)
            
        Returns:
            S3 key path for the analysis report
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        # Format: {patient-id}/analysis-{timestamp}.json
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
        analysis_key = f"{patient_id}/analysis-{timestamp_str}.json"
        
        logger.info(f"Analysis report path: {analysis_key}")
        return analysis_key
    
    def extract_patient_id_from_path(self, patient_path: str) -> str:
        """
        Extract patient ID from the patient XML file path.
        
        Args:
            patient_path: S3 path to patient XML file
            
        Returns:
            Patient ID extracted from the path
        """
        # Extract patient ID from path like: 01995eed-3135-733a-b8eb-a6ff8eaa39dd/JaneSmith.xml
        path_parts = patient_path.split('/')
        if len(path_parts) >= 2:
            patient_id = path_parts[-2]  # Directory name before filename
            logger.info(f"Extracted patient ID: {patient_id}")
            return patient_id
        else:
            # Fallback: use filename without extension
            filename = patient_path.split('/')[-1]
            patient_id = filename.replace('.xml', '')
            logger.warning(f"Using filename as patient ID: {patient_id}")
            return patient_id
    
    def list_patient_analyses(self, patient_id: str) -> list:
        """
        List all analysis reports for a given patient.
        
        Args:
            patient_id: Patient identifier
            
        Returns:
            List of analysis report S3 keys for the patient
        """
        try:
            prefix = f"{patient_id}/analysis-"
            analysis_keys = self.s3_client.list_objects(prefix=prefix)
            
            # Sort by timestamp (newest first)
            analysis_keys.sort(reverse=True)
            
            logger.info(f"Found {len(analysis_keys)} analysis reports for patient {patient_id}")
            return analysis_keys
            
        except Exception as e:
            logger.error(f"Failed to list patient analyses: {str(e)}")
            return []