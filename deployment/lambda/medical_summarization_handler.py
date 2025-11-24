"""
AWS Lambda Handler for Medical Summarization Agent

This Lambda function handles requests to generate medical summaries from patient data.
It integrates with AWS Bedrock agents and provides proper error handling and logging.
"""

import json
import logging
import os
import sys
from typing import Dict, Any
from datetime import datetime

# Add src directory to path for imports
sys.path.insert(0, '/opt/python')  # Lambda layer path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from src.agents.medical_summarization_agent import MedicalSummarizationAgent
from src.models import PatientData
from src.models.exceptions import DataValidationError
from src.utils import setup_logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize agent (reused across invocations)
summarization_agent = None


def get_agent() -> MedicalSummarizationAgent:
    """Get or create Medical Summarization Agent instance (singleton pattern for Lambda)."""
    global summarization_agent
    if summarization_agent is None:
        setup_logging()
        summarization_agent = MedicalSummarizationAgent()
        logger.info("Medical Summarization Agent initialized")
    return summarization_agent


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler for Medical Summarization Agent.
    
    Expected event format:
    {
        "action": "generateSummary",
        "parameters": {
            "patientData": { ... }
        }
    }
    
    Or for API Gateway:
    {
        "body": "{\"patientData\": {...}}",
        "httpMethod": "POST",
        "path": "/generate-summary"
    }
    
    Args:
        event: Lambda event object
        context: Lambda context object
        
    Returns:
        Dict containing status code and response body
    """
    request_id = context.request_id if context else "local-test"
    logger.info(f"Request ID: {request_id}")
    
    try:
        # Parse input based on event source
        if 'body' in event:
            # API Gateway event
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
            patient_data_dict = body.get('patientData')
            action = event.get('path', '').split('/')[-1]
        elif 'parameters' in event:
            # Bedrock agent event
            patient_data_dict = event['parameters'].get('patientData')
            action = event.get('action', 'generateSummary')
        else:
            # Direct invocation
            patient_data_dict = event.get('patientData')
            action = event.get('action', 'generateSummary')
        
        # Validate input
        if not patient_data_dict:
            return create_error_response(
                400,
                "Missing required parameter: patientData",
                request_id
            )
        
        # Route to appropriate action
        if action in ['generateSummary', 'generate-summary']:
            return handle_generate_summary(patient_data_dict, request_id)
        elif action == 'analyzeConditionTrends':
            return handle_analyze_condition_trends(patient_data_dict, request_id)
        elif action == 'getConditionInsights':
            return handle_get_condition_insights(patient_data_dict, request_id)
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


def handle_generate_summary(patient_data_dict: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """Handle medical summary generation request."""
    try:
        logger.info(f"Generating medical summary for patient: {patient_data_dict.get('patient_id')}")
        
        # Convert dict to PatientData object
        patient_data = dict_to_patient_data(patient_data_dict)
        
        agent = get_agent()
        medical_summary = agent.generate_summary(patient_data)
        
        # Convert to dict for JSON serialization
        response_data = {
            'patient_id': medical_summary.patient_id,
            'summary_text': medical_summary.summary_text,
            'key_conditions': [
                {
                    'name': c.name,
                    'severity': c.severity,
                    'status': c.status,
                    'confidence_score': c.confidence_score,
                    'first_diagnosed': c.first_diagnosed,
                    'icd10_code': c.icd10_code,
                    'source': c.source
                }
                for c in medical_summary.key_conditions
            ],
            'medication_summary': medical_summary.medication_summary,
            'procedure_summary': medical_summary.procedure_summary,
            'chronological_events': [
                {
                    'date': event.date,
                    'event_type': event.event_type,
                    'description': event.description,
                    'significance': event.significance
                }
                for event in medical_summary.chronological_events
            ],
            'data_quality_score': medical_summary.data_quality_score,
            'missing_data_indicators': medical_summary.missing_data_indicators,
            'generated_timestamp': medical_summary.generated_timestamp.isoformat() if medical_summary.generated_timestamp else None
        }
        
        logger.info(f"Successfully generated medical summary with {len(medical_summary.key_conditions)} conditions")
        
        return create_success_response(response_data, request_id)
        
    except DataValidationError as e:
        logger.error(f"Data validation error: {str(e)}")
        return create_error_response(400, f"Invalid patient data: {str(e)}", request_id)
        
    except Exception as e:
        logger.error(f"Unexpected error generating summary: {str(e)}", exc_info=True)
        return create_error_response(500, f"Failed to generate summary: {str(e)}", request_id)


def handle_analyze_condition_trends(patient_data_dict: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """Handle condition trends analysis request."""
    try:
        patient_data = dict_to_patient_data(patient_data_dict)
        
        agent = get_agent()
        trends = agent.analyze_condition_trends(patient_data)
        
        return create_success_response(trends, request_id)
        
    except Exception as e:
        logger.error(f"Error analyzing condition trends: {str(e)}")
        return create_error_response(500, str(e), request_id)


def handle_get_condition_insights(patient_data_dict: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """Handle condition insights request."""
    try:
        patient_data = dict_to_patient_data(patient_data_dict)
        
        agent = get_agent()
        insights = agent.get_condition_insights(patient_data)
        
        return create_success_response(insights, request_id)
        
    except Exception as e:
        logger.error(f"Error getting condition insights: {str(e)}")
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


def dict_to_patient_data(data: Dict[str, Any]) -> PatientData:
    """Convert dictionary to PatientData object."""
    from src.models import Demographics, MedicalEvent, Medication, Procedure, Diagnosis
    
    # Parse demographics
    demographics_dict = data.get('demographics', {})
    demographics = Demographics(
        date_of_birth=demographics_dict.get('date_of_birth'),
        gender=demographics_dict.get('gender'),
        race=demographics_dict.get('race'),
        ethnicity=demographics_dict.get('ethnicity'),
        address=demographics_dict.get('address'),
        phone=demographics_dict.get('phone'),
        email=demographics_dict.get('email')
    )
    
    # Parse medical history
    medical_history = [
        MedicalEvent(
            date=event.get('date'),
            event_type=event.get('event_type'),
            description=event.get('description'),
            provider=event.get('provider'),
            location=event.get('location')
        )
        for event in data.get('medical_history', [])
    ]
    
    # Parse medications
    medications = [
        Medication(
            name=med.get('name'),
            dosage=med.get('dosage'),
            frequency=med.get('frequency'),
            start_date=med.get('start_date'),
            end_date=med.get('end_date'),
            prescribing_doctor=med.get('prescribing_doctor'),
            indication=med.get('indication'),
            status=med.get('status', 'active')
        )
        for med in data.get('medications', [])
    ]
    
    # Parse procedures
    procedures = [
        Procedure(
            name=proc.get('name'),
            date=proc.get('date'),
            provider=proc.get('provider'),
            location=proc.get('location'),
            indication=proc.get('indication'),
            outcome=proc.get('outcome')
        )
        for proc in data.get('procedures', [])
    ]
    
    # Parse diagnoses
    diagnoses = [
        Diagnosis(
            name=diag.get('name'),
            date=diag.get('date'),
            icd10_code=diag.get('icd10_code'),
            diagnosing_provider=diag.get('diagnosing_provider'),
            status=diag.get('status', 'active'),
            severity=diag.get('severity')
        )
        for diag in data.get('diagnoses', [])
    ]
    
    # Create PatientData object
    patient_data = PatientData(
        patient_id=data.get('patient_id'),
        name=data.get('name'),
        demographics=demographics,
        medical_history=medical_history,
        medications=medications,
        procedures=procedures,
        diagnoses=diagnoses,
        raw_xml=data.get('raw_xml', ''),
        data_quality_score=data.get('data_quality_score', 0.0),
        parsed_timestamp=datetime.fromisoformat(data['parsed_timestamp']) if data.get('parsed_timestamp') else None
    )
    
    return patient_data


def create_success_response(data: Any, request_id: str) -> Dict[str, Any]:
    """Create successful response."""
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'X-Request-ID': request_id,
            'Access-Control-Allow-Origin': '*'
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
            'Access-Control-Allow-Origin': '*'
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
        "patientData": {
            "patient_id": "P001",
            "name": "John Doe",
            "demographics": {},
            "medical_history": [],
            "medications": [],
            "procedures": [],
            "diagnoses": []
        },
        "action": "generateSummary"
    }
    
    class MockContext:
        request_id = "test-request-123"
    
    result = lambda_handler(test_event, MockContext())
    print(json.dumps(result, indent=2))
