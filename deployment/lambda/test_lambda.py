#!/usr/bin/env python3
"""
Test script for the MedicalAnalysisMasterWorkflow Lambda function.
"""

import json
import boto3
from datetime import datetime

def test_lambda_function():
    """Test the Lambda function directly."""
    
    # Initialize Lambda client
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Create test event (simulating Bedrock Agent input)
    test_event = {
        "messageVersion": "1.0",
        "inputText": "Analyze medical records for patient: Jane Smith",
        "sessionId": "test-session-123",
        "actionGroup": "MasterWorkflowActionGroup",
        "apiPath": "/analyze",
        "httpMethod": "POST",
        "parameters": [
            {"name": "patient_name", "type": "string", "value": "Jane Smith"}
        ]
    }
    
    print("Testing MedicalAnalysisMasterWorkflow Lambda function...")
    print(f"Test event: {json.dumps(test_event, indent=2)}")
    print()
    
    try:
        # Invoke Lambda function
        response = lambda_client.invoke(
            FunctionName='MedicalAnalysisMasterWorkflow',
            InvocationType='RequestResponse',
            Payload=json.dumps(test_event)
        )
        
        # Parse response
        response_payload = json.loads(response['Payload'].read())
        
        print("✅ Lambda function invoked successfully!")
        print(f"Status Code: {response['StatusCode']}")
        print(f"Response: {json.dumps(response_payload, indent=2)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Lambda function test failed: {str(e)}")
        return False

def test_lambda_logs():
    """Check recent Lambda function logs."""
    
    logs_client = boto3.client('logs', region_name='us-east-1')
    
    try:
        # Get log streams
        log_group = '/aws/lambda/MedicalAnalysisMasterWorkflow'
        
        streams_response = logs_client.describe_log_streams(
            logGroupName=log_group,
            orderBy='LastEventTime',
            descending=True,
            limit=1
        )
        
        if not streams_response['logStreams']:
            print("No log streams found")
            return
        
        latest_stream = streams_response['logStreams'][0]['logStreamName']
        
        # Get recent log events
        events_response = logs_client.get_log_events(
            logGroupName=log_group,
            logStreamName=latest_stream,
            limit=20
        )
        
        print(f"\n📋 Recent logs from {log_group}:")
        print("=" * 80)
        
        for event in events_response['events'][-10:]:  # Last 10 events
            timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
            message = event['message'].strip()
            print(f"{timestamp}: {message}")
        
    except Exception as e:
        print(f"❌ Failed to retrieve logs: {str(e)}")

if __name__ == "__main__":
    print("🧪 Testing MedicalAnalysisMasterWorkflow Lambda Function")
    print("=" * 60)
    
    # Test 1: Direct Lambda invocation
    success = test_lambda_function()
    
    # Test 2: Check logs
    test_lambda_logs()
    
    if success:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Tests failed - check logs for details")