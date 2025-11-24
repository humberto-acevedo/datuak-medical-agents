#!/usr/bin/env python3
"""
Setup test data for the Medical Record Analysis System prototype.
This script creates mock S3 data and patient records for testing.
"""

import os
import sys
import json
from pathlib import Path
from unittest.mock import patch, Mock

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def create_mock_s3_data():
    """Create mock S3 data for testing."""
    from tests.fixtures.sample_patient_data import (
        SAMPLE_PATIENT_XML_GOOD, 
        SAMPLE_PATIENT_XML_COMPLEX, 
        SAMPLE_PATIENT_XML_MINIMAL
    )
    
    # Mock patient data mapping
    mock_patients = {
        "john doe": SAMPLE_PATIENT_XML_GOOD,
        "jane smith": SAMPLE_PATIENT_XML_COMPLEX,
        "bob johnson": SAMPLE_PATIENT_XML_MINIMAL,
        "test patient": SAMPLE_PATIENT_XML_GOOD,
        "demo patient": SAMPLE_PATIENT_XML_GOOD,
    }
    
    return mock_patients

def setup_mock_s3_operations():
    """Setup mock S3 operations for testing."""
    mock_patients = create_mock_s3_data()
    
    def mock_get_object(Bucket, Key):
        """Mock S3 get_object operation."""
        # Extract patient name from key (assuming format: patients/{name}.xml)
        if 'patients/' in Key:
            patient_name = Key.split('patients/')[-1].replace('.xml', '').replace('_', ' ').lower()
            
            if patient_name in mock_patients:
                xml_content = mock_patients[patient_name]
                return {
                    'Body': Mock(read=Mock(return_value=xml_content.encode('utf-8')))
                }
        
        # If patient not found, raise exception
        from botocore.exceptions import ClientError
        raise ClientError(
            error_response={'Error': {'Code': 'NoSuchKey', 'Message': 'The specified key does not exist.'}},
            operation_name='GetObject'
        )
    
    def mock_put_object(Bucket, Key, Body):
        """Mock S3 put_object operation."""
        print(f"📄 Mock S3: Saving report to {Key}")
        return {'ETag': '"mock-etag-12345"'}
    
    # Create mock S3 client
    mock_s3_client = Mock()
    mock_s3_client.get_object.side_effect = mock_get_object
    mock_s3_client.put_object.side_effect = mock_put_object
    
    return mock_s3_client

def display_available_patients():
    """Display available test patients."""
    mock_patients = create_mock_s3_data()
    
    print("📋 Available Test Patients:")
    print("-" * 40)
    
    patient_info = {
        "john doe": "45-year-old male with diabetes and hypertension",
        "jane smith": "58-year-old female with breast cancer history",
        "bob johnson": "33-year-old male with asthma",
        "test patient": "Sample patient for testing",
        "demo patient": "Demo patient for demonstrations"
    }
    
    for name, description in patient_info.items():
        print(f"  • {name.title()}: {description}")
    
    print("\n💡 Tip: Enter any of these names when prompted by the system")
    print("🔍 The system will find and analyze their medical records")
    print()

def main():
    """Main setup function."""
    print("🏥 Medical Record Analysis System - Test Data Setup")
    print("=" * 60)
    
    # Display available patients
    display_available_patients()
    
    print("✅ Test data setup complete!")
    print("🚀 You can now run the prototype with: python launch_prototype.py")
    print()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())