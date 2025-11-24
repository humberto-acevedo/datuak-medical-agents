"""
AWS Lambda Handler for Research Correlation Agent

This Lambda function handles requests to correlate medical research with patient conditions.
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

from src.agents.research_correlation_agent import ResearchCorrelationAgent
from src.models import PatientData, MedicalSummary, Condition
from src.models.exceptions import ResearchError
from src.utils import setup_logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize agent (reused across invocations)
research_agent = None


def get_agent() -> ResearchCorrelationAgent:
    """Get or create Research Correlation Agent instance (singleton pattern for Lambda)."""
    global research_agent
    if research_agent is None:
        setup_logging()
        research_agent = ResearchCorrelationAgent()
        logger.info("Research Correlation Agent initialized")
    return research_agent


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler for Research Correlation Agent.
    
    Expected event format:
    {
        "action": "correlateResearch",
        "parameters": {
            "patientData": { ... },
            "medicalSummary": { ... }
        }
    }
    
    Or for API Gateway:
    {
        "body": "{\"patientData\": {...}, \"medicalSummary\": {...}}",
        "httpMethod": "POST",
        "path": "/correlate-research"
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
            medical_summary_dict = body.get('medicalSummary')
            action = event.get('path', '').split('/')[-1]
        elif 'parameters' in event:
            # Bedrock agent event
            patient_data_dict = event['parameters'].get('patientData')
            medical_summary_dict = event['parameters'].get('medicalSummary')
            action = event.get('action', 'correlateResearch')
        else:
            # Direct invocation
            patient_data_dict = event.get('patientData')
            medical_summary_dict = event.get('medicalSummary')
            action = event.get('action', 'correlateResearch')
        
        # Validate input
        if not patient_data_dict or not medical_summary_dict:
            return create_error_response(
                400,
                "Missing required parameters: patientData and medicalSummary",
                request_id
            )
        
        # Route to appropriate action
        if action in ['correlateResearch', 'correlate-research']:
            return handle_correlate_research(patient_data_dict, medical_summary_dict, request_id)
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


def handle_correlate_research(patient_data_dict: Dict[str, Any], 
                             medical_summary_dict: Dict[str, Any],
                             request_id: str) -> Dict[str, Any]:
    """Handle research correlation request."""
    try:
        logger.info(f"Correlating research for patient: {patient_data_dict.get('patient_id')}")
        
        # Convert dicts to objects
        patient_data = dict_to_patient_data(patient_data_dict)
        medical_summary = dict_to_medical_summary(medical_summary_dict)
        
        agent = get_agent()
        research_analysis = agent.analyze_patient_research(patient_data, medical_summary)
        
        # Convert to dict for JSON serialization
        response_data = {
            'patient_id': research_analysis.patient_id,
            'analysis_timestamp': research_analysis.analysis_timestamp.isoformat(),
            'conditions_analyzed': [
                {
                    'name': c.name,
                    'severity': c.severity,
                    'confidence_score': c.confidence_score
                }
                for c in research_analysis.conditions_analyzed
            ],
            'research_findings': [
                {
                    'title': f.title,
                    'authors': f.authors,
                    'publication_date': f.publication_date,
                    'journal': f.journal,
                    'doi': f.doi,
                    'relevance_score': f.relevance_score,
                    'key_findings': f.key_findings,
                    'citation': f.citation,
                    'study_type': f.study_type,
                    'peer_reviewed': f.peer_reviewed
                }
                for f in research_analysis.research_findings
            ],
            'condition_research_correlations': {
                condition: [
                    {
                        'title': f.title,
                        'relevance_score': f.relevance_score,
                        'doi': f.doi
                    }
                    for f in findings
                ]
                for condition, findings in research_analysis.condition_research_correlations.items()
            },
            'research_insights': research_analysis.research_insights,
            'clinical_recommendations': research_analysis.clinical_recommendations,
            'analysis_confidence': research_analysis.analysis_confidence,
            'total_papers_reviewed': research_analysis.total_papers_reviewed,
            'relevant_papers_found': research_analysis.relevant_papers_found
        }
        
        logger.info(f"Successfully correlated {len(research_analysis.research_findings)} research papers")
        
        return create_success_response(response_data, request_id)
        
    except ResearchError as e:
        logger.error(f"Research correlation error: {str(e)}")
        return create_error_response(500, f"Research correlation failed: {str(e)}", request_id)
        
    except Exception as e:
        logger.error(f"Unexpected error correlating research: {str(e)}", exc_info=True)
        return create_error_response(500, f"Failed to correlate research: {str(e)}", request_id)


def handle_health_check(request_id: str) -> Dict[str, Any]:
    """Handle health check request."""
    try:
        return create_success_response({
            'agent_name': 'Research Correlation Agent',
            'status': 'healthy',
            'timestamp': datetime.now().isoformat()
        }, request_id)
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return create_error_response(500, str(e), request_id)


def dict_to_patient_data(data: Dict[str, Any]) -> PatientData:
    """Convert dictionary to PatientData object."""
    from src.models import Demographics, MedicalEvent, Medication, Procedure, Diagnosis
    
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
    
    return PatientData(
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


def dict_to_medical_summary(data: Dict[str, Any]) -> MedicalSummary:
    """Convert dictionary to MedicalSummary object."""
    from src.models import ChronologicalEvent
    
    key_conditions = [
        Condition(
            name=c.get('name'),
            severity=c.get('severity'),
            status=c.get('status'),
            confidence_score=c.get('confidence_score', 0.0),
            first_diagnosed=c.get('first_diagnosed'),
            icd10_code=c.get('icd10_code'),
            source=c.get('source')
        )
        for c in data.get('key_conditions', [])
    ]
    
    chronological_events = [
        ChronologicalEvent(
            date=event.get('date'),
            event_type=event.get('event_type'),
            description=event.get('description'),
            significance=event.get('significance')
        )
        for event in data.get('chronological_events', [])
    ]
    
    return MedicalSummary(
        patient_id=data.get('patient_id'),
        summary_text=data.get('summary_text', ''),
        key_conditions=key_conditions,
        medication_summary=data.get('medication_summary', ''),
        procedure_summary=data.get('procedure_summary', ''),
        chronological_events=chronological_events,
        data_quality_score=data.get('data_quality_score', 0.0),
        missing_data_indicators=data.get('missing_data_indicators', []),
        generated_timestamp=datetime.fromisoformat(data['generated_timestamp']) if data.get('generated_timestamp') else None
    )


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
        "medicalSummary": {
            "patient_id": "P001",
            "summary_text": "Test summary",
            "key_conditions": [],
            "medication_summary": "",
            "procedure_summary": "",
            "chronological_events": []
        },
        "action": "correlateResearch"
    }
    
    class MockContext:
        request_id = "test-request-123"
    
    result = lambda_handler(test_event, MockContext())
    print(json.dumps(result, indent=2))
