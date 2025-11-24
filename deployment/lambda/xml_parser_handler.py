"""
AWS Lambda Handler for XML Parser Agent

This Lambda function handles requests to parse patient XML records from S3.
It integrates with AWS Bedrock agents and provides proper error handling and logging.
"""

import json
import logging
import os
import sys
from typing import Dict, Any

# Add src directory to path for imports
sys.path.insert(0, '/opt/python')  # Lambda layer path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from src.agents.xml_parser_agent import XMLParserAgent
from src.models.exceptions import PatientNotFoundError, XMLParsingError, S3Error
from src.utils import setup_logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize agent (reused across invocations)
xml_parser_agent = None


def get_agent() -> XMLParserAgent:
    """Get or create XML Parser Agent instance (singleton pattern for Lambda)."""
    global xml_parser_agent
    if xml_parser_agent is None:
        setup_logging()
        xml_parser_agent = XMLParserAgent()
        logger.info("XML Parser Agent initialized")
    return xml_parser_agent


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler for XML Parser Agent.
    
    Expected event format:
    {
        "action": "parsePatientRecord",
        "parameters": {
            "patientName": "John Doe"
        }
    }
    
    Or for API Gateway:
    {
        "body": "{\"patientName\": \"John Doe\"}",
        "httpMethod": "POST",
        "path": "/parse-patient-record"
    }
    
    Args:
        event: Lambda event object
        context: Lambda context object
        
    Returns:
        Dict containing status code and response body
    """
    request_id = context.request_id if context else "local-test"
    logger.info(f"Request ID: {request_id}")
    logger.info(f"Event: {json.dumps(event)}")
    
    try:
        # Parse input based on event source
        if 'body' in event:
            # API Gateway event
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
            patient_name = body.get('patientName')
            action = event.get('path', '').split('/')[-1]
        elif 'parameters' in event:
            # Bedrock agent event
            patient_name = event['parameters'].get('patientName')
            action = event.get('action', 'parsePatientRecord')
        else:
            # Direct invocation
            patient_name = event.get('patientName')
            action = event.get('action', 'parsePatientRecord')
        
        # Validate input
        if not patient_name:
            return create_error_response(
                400,
                "Missing required parameter: patientName",
                request_id
            )
        
        # Route to appropriate action
        if action in ['parsePatientRecord', 'parse-patient-record']:
            return handle_parse_patient_record(patient_name, request_id)
        elif action == 'validatePatientExists':
            return handle_validate_patient_exists(patient_name, request_id)
        elif action == 'getPatientMetadata':
            return handle_get_patient_metadata(patient_name, request_id)
        elif action == 'listPatients':
            return handle_list_patients(request_id)
        elif action == 'healthCheck':
            return handle_health_check(request_id)
        else:
            return create_error_response(
                400,
                f"Unknown action: {action}",
                request_id
            )
            
    except Exception as e:
        logger.error(f"Unexpected error in lambda_handler: {str(e)}", exc_info=True)
        return create_error_response(
            500,
            f"Internal server error: {str(e)}",
            request_id
        )


def handle_parse_patient_record(patient_name: str, request_id: str) -> Dict[str, Any]:
    """Handle patient record parsing request."""
    try:
        logger.info(f"Parsing patient record for: {patient_name}")
        
        agent = get_agent()
        patient_data = agent.parse_patient_record(patient_name)
        
        # Convert to dict for JSON serialization
        response_data = {
            'patient_id': patient_data.patient_id,
            'name': patient_data.name,
            'demographics': patient_data.demographics.__dict__ if patient_data.demographics else {},
            'medical_history': [event.__dict__ for event in patient_data.medical_history],
            'medications': [med.__dict__ for med in patient_data.medications],
            'procedures': [proc.__dict__ for proc in patient_data.procedures],
            'diagnoses': [diag.__dict__ for diag in patient_data.diagnoses],
            'data_quality_score': patient_data.data_quality_score,
            'parsed_timestamp': patient_data.parsed_timestamp.isoformat() if patient_data.parsed_timestamp else None
        }
        
        logger.info(f"Successfully parsed patient record: {patient_data.patient_id}")
        
        return create_success_response(response_data, request_id)
        
    except PatientNotFoundError as e:
        logger.warning(f"Patient not found: {patient_name}")
        return create_error_response(404, str(e), request_id)
        
    except XMLParsingError as e:
        logger.error(f"XML parsing error: {str(e)}")
        return create_error_response(400, f"XML parsing failed: {str(e)}", request_id)
        
    except S3Error as e:
        logger.error(f"S3 error: {str(e)}")
        return create_error_response(500, f"S3 operation failed: {str(e)}", request_id)
        
    except Exception as e:
        logger.error(f"Unexpected error parsing patient record: {str(e)}", exc_info=True)
        return create_error_response(500, f"Failed to parse patient record: {str(e)}", request_id)


def handle_validate_patient_exists(patient_name: str, request_id: str) -> Dict[str, Any]:
    """Handle patient existence validation request."""
    try:
        agent = get_agent()
        exists = agent.validate_patient_exists(patient_name)
        
        return create_success_response({
            'patientName': patient_name,
            'exists': exists
        }, request_id)
        
    except Exception as e:
        logger.error(f"Error validating patient existence: {str(e)}")
        return create_error_response(500, str(e), request_id)


def handle_get_patient_metadata(patient_name: str, request_id: str) -> Dict[str, Any]:
    """Handle patient metadata retrieval request."""
    try:
        agent = get_agent()
        metadata = agent.get_patient_metadata(patient_name)
        
        # Convert datetime objects to ISO format
        if 'last_modified' in metadata:
            metadata['last_modified'] = metadata['last_modified'].isoformat()
        
        return create_success_response(metadata, request_id)
        
    except PatientNotFoundError as e:
        return create_error_response(404, str(e), request_id)
        
    except Exception as e:
        logger.error(f"Error getting patient metadata: {str(e)}")
        return create_error_response(500, str(e), request_id)


def handle_list_patients(request_id: str, limit: int = 100) -> Dict[str, Any]:
    """Handle list patients request."""
    try:
        agent = get_agent()
        patients = agent.list_available_patients(limit=limit)
        
        # Convert datetime objects to ISO format
        for patient in patients:
            if 'last_modified' in patient:
                patient['last_modified'] = patient['last_modified'].isoformat()
        
        return create_success_response({
            'patients': patients,
            'count': len(patients)
        }, request_id)
        
    except Exception as e:
        logger.error(f"Error listing patients: {str(e)}")
        return create_error_response(500, str(e), request_id)


def handle_health_check(request_id: str) -> Dict[str, Any]:
    """Handle health check request."""
    try:
        agent = get_agent()
        status = agent.get_agent_status()
        
        return create_success_response(status, request_id)
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return create_error_response(500, str(e), request_id)


def create_success_response(data: Any, request_id: str) -> Dict[str, Any]:
    """Create successful response."""
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'X-Request-ID': request_id,
            'Access-Control-Allow-Origin': '*'  # Configure appropriately for production
        },
        'body': json.dumps({
            'success': True,
            'data': data,
            'requestId': request_id
        })
    }


def create_error_response(status_code: int, error_message: str, request_id: str) -> Dict[str, Any]:
    """Create error response."""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'X-Request-ID': request_id,
            'Access-Control-Allow-Origin': '*'  # Configure appropriately for production
        },
        'body': json.dumps({
            'success': False,
            'error': error_message,
            'requestId': request_id
        })
    }


# For local testing
if __name__ == "__main__":
    test_event = {
        "patientName": "John Doe",
        "action": "parsePatientRecord"
    }
    
    class MockContext:
        request_id = "test-request-123"
    
    result = lambda_handler(test_event, MockContext())
    print(json.dumps(result, indent=2))
