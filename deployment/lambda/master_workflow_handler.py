"""
Lambda handler for Bedrock Agent Master Workflow action group.
This Lambda executes the complete medical analysis workflow.
"""

import json
import logging
import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    Lambda handler for Bedrock Agent action group.
    
    Event structure from Bedrock Agent:
    {
        "messageVersion": "1.0",
        "agent": {...},
        "inputText": "...",
        "sessionId": "...",
        "actionGroup": "...",
        "apiPath": "/analyze",
        "httpMethod": "POST",
        "parameters": [
            {"name": "patient_name", "type": "string", "value": "John Doe"}
        ]
    }
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Extract patient name from requestBody
        patient_name = None
        request_body = event.get('requestBody', {})
        
        # Handle both direct content and nested content structure
        if 'content' in request_body:
            content = request_body['content']
            if 'application/json' in content:
                body_data = json.loads(content['application/json'])
                patient_name = body_data.get('patient_name')
        elif 'patient_name' in request_body:
            patient_name = request_body['patient_name']
        
        # Fallback to parameters array (legacy support)
        if not patient_name:
            for param in event.get('parameters', []):
                if param['name'] == 'patient_name':
                    patient_name = param['value']
                    break
        
        if not patient_name:
            return format_error_response("Missing required parameter: patient_name")
        
        logger.info(f"Analyzing patient: {patient_name}")
        
        # Import and execute workflow
        from src.workflow.main_workflow import MainWorkflow
        from src.utils.audit_logger import initialize_audit_logging
        
        # Initialize workflow
        audit_logger = initialize_audit_logging()
        workflow = MainWorkflow(audit_logger=audit_logger)
        
        # Execute analysis (synchronous version)
        import asyncio
        result = asyncio.run(workflow.execute_complete_analysis(patient_name))
        
        # Convert result to JSON-serializable format
        response_body = {
            'patient_id': result.patient_data.patient_id,
            'patient_name': result.patient_data.name,
            'medical_summary': result.medical_summary.summary_text,
            'research_analysis': {
                'total_articles': len(result.research_analysis.articles),
                'key_findings': result.research_analysis.key_findings[:5]
            },
            'report_s3_key': result.report_s3_key,
            'processing_metadata': result.processing_metadata
        }
        
        logger.info("Analysis completed successfully")
        
        return format_success_response(response_body)
        
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}", exc_info=True)
        return format_error_response(str(e))


def format_success_response(body):
    """Format successful response for Bedrock Agent."""
    return {
        'messageVersion': '1.0',
        'response': {
            'actionGroup': 'MasterWorkflowActionGroup',
            'apiPath': '/analyze',
            'httpMethod': 'POST',
            'httpStatusCode': 200,
            'responseBody': {
                'application/json': {
                    'body': json.dumps(body, default=str)
                }
            }
        }
    }


def format_error_response(error_message):
    """Format error response for Bedrock Agent."""
    return {
        'messageVersion': '1.0',
        'response': {
            'actionGroup': 'MasterWorkflowActionGroup',
            'apiPath': '/analyze',
            'httpMethod': 'POST',
            'httpStatusCode': 500,
            'responseBody': {
                'application/json': {
                    'body': json.dumps({'error': error_message})
                }
            }
        }
    }
