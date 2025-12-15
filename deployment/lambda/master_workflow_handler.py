"""
Lambda handler for Bedrock Agent Master Workflow action group.
This Lambda executes the complete medical analysis workflow.
"""

import json
import logging
import sys
import os
import boto3
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
s3_client = boto3.client('s3', region_name='us-east-1')


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
        
        # Extract patient name from various possible locations in the event
        patient_name = None
        
        # Method 1: From inputText (most common for Bedrock Agent)
        input_text = event.get('inputText', '')
        if input_text and 'patient:' in input_text.lower():
            # Extract patient name from "Analyze medical records for patient: Jane Smith"
            parts = input_text.split('patient:')
            if len(parts) > 1:
                patient_name = parts[1].strip()
        
        # Method 2: From requestBody
        if not patient_name:
            request_body = event.get('requestBody', {})
            
            # Handle nested content structure
            if 'content' in request_body:
                content = request_body['content']
                if 'application/json' in content:
                    try:
                        body_data = json.loads(content['application/json'])
                        patient_name = body_data.get('patient_name')
                    except json.JSONDecodeError:
                        pass
            elif 'patient_name' in request_body:
                patient_name = request_body['patient_name']
        
        # Method 3: From parameters array (legacy support)
        if not patient_name:
            for param in event.get('parameters', []):
                if param.get('name') == 'patient_name':
                    patient_name = param.get('value')
                    break
        
        # Method 4: Default for testing
        if not patient_name:
            patient_name = "Jane Smith"  # Default for testing
            logger.warning("No patient name found in event, using default: Jane Smith")
        
        logger.info(f"Extracted patient name: {patient_name}")
        
        logger.info(f"Analyzing patient: {patient_name}")
        
        # Execute simplified Bedrock-based analysis
        try:
            # Step 1: Get patient XML from S3
            bucket_name = os.environ.get('S3_BUCKET_NAME', 'patient-records-20251024')
            xml_key = f"patient-records/{patient_name}.xml"
            
            logger.info(f"Fetching patient XML from s3://{bucket_name}/{xml_key}")
            
            try:
                xml_response = s3_client.get_object(Bucket=bucket_name, Key=xml_key)
                xml_content = xml_response['Body'].read().decode('utf-8')
                logger.info(f"Retrieved XML content: {len(xml_content)} characters")
            except Exception as e:
                logger.error(f"Failed to retrieve patient XML: {str(e)}")
                return format_error_response(f"Patient record not found: {patient_name}")
            
            # Step 2: Generate medical summary using Bedrock Claude
            logger.info("Generating medical summary with Claude...")
            
            summary_prompt = f"""
            Please analyze the following patient medical record and provide a comprehensive medical summary:

            Patient: {patient_name}
            
            Medical Record (XML):
            {xml_content[:4000]}  # Limit to avoid token limits
            
            Please provide:
            1. Patient demographics and basic information
            2. Current medical conditions and diagnoses
            3. Current medications and treatments
            4. Recent procedures and test results
            5. Clinical recommendations and next steps
            
            Format your response as a clear, professional medical summary.
            """
            
            medical_summary = invoke_claude_model(summary_prompt)
            
            # Step 3: Generate research analysis
            logger.info("Generating research analysis with Claude...")
            
            research_prompt = f"""
            Based on the medical summary below, provide evidence-based research analysis and clinical recommendations:

            Medical Summary:
            {medical_summary}
            
            Please provide:
            1. Current evidence-based treatment guidelines
            2. Recent research findings relevant to the patient's conditions
            3. Clinical recommendations based on current medical literature
            4. Potential drug interactions or contraindications
            5. Preventive care recommendations
            
            Focus on actionable, evidence-based recommendations.
            """
            
            research_analysis = invoke_claude_model(research_prompt)
            
            # Step 4: Save report to S3
            report_id = f"RPT_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{patient_name.replace(' ', '_')}"
            report_key = f"analysis-reports/{patient_name.replace(' ', '_')}/bedrock-agent-{report_id}.json"
            
            report_data = {
                'report_id': report_id,
                'patient_name': patient_name,
                'generated_at': datetime.now().isoformat(),
                'medical_summary': medical_summary,
                'research_analysis': research_analysis,
                'workflow_type': 'bedrock_agent_lambda',
                'model_info': {
                    'model_name': 'Claude 3.5 Haiku',
                    'provider': 'Anthropic',
                    'region': 'us-east-1'
                }
            }
            
            s3_client.put_object(
                Bucket=bucket_name,
                Key=report_key,
                Body=json.dumps(report_data, indent=2),
                ContentType='application/json'
            )
            
            logger.info(f"Report saved to s3://{bucket_name}/{report_key}")
            
            # Convert result to JSON-serializable format
            response_body = {
                'patient_name': patient_name,
                'medical_summary': medical_summary,
                'research_analysis': research_analysis,
                'report_s3_key': report_key,
                'report_id': report_id,
                'workflow_type': 'bedrock_agent_lambda',
                'generated_at': datetime.now().isoformat(),
                'model_info': {
                    'model_name': 'Claude 3.5 Haiku',
                    'provider': 'Anthropic',
                    'region': 'us-east-1'
                }
            }
            
        except Exception as workflow_error:
            logger.error(f"Workflow execution failed: {str(workflow_error)}", exc_info=True)
            return format_error_response(f"Analysis workflow failed: {str(workflow_error)}")
        
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


def invoke_claude_model(prompt: str) -> str:
    """Invoke Claude model via Bedrock."""
    try:
        model_id = "anthropic.claude-3-haiku-20240307-v1:0"
        
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4000,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        response = bedrock_client.invoke_model(
            modelId=model_id,
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(response['body'].read())
        return response_body['content'][0]['text']
        
    except Exception as e:
        logger.error(f"Failed to invoke Claude model: {str(e)}")
        raise Exception(f"Claude model invocation failed: {str(e)}")


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
