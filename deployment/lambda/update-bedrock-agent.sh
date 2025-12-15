#!/bin/bash

# Update Bedrock Agent Configuration Script
# This script updates the Bedrock agent action groups with new Lambda ARNs

set -e

# Configuration
REGION="us-east-1"
MASTER_AGENT_ID="LAA6HDZPAH"
ACTION_GROUP_ID="DRKURWNKFM"

# Get the new Lambda ARN from CloudFormation stack
echo "Getting Lambda ARN from CloudFormation stack..."
LAMBDA_ARN=$(aws cloudformation describe-stacks \
  --stack-name medical-record-lambda-simple \
  --region $REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`MasterWorkflowFunctionArn`].OutputValue' \
  --output text)

if [ -z "$LAMBDA_ARN" ]; then
  echo "Error: Could not retrieve Lambda ARN from CloudFormation stack"
  exit 1
fi

echo "New Lambda ARN: $LAMBDA_ARN"

# Update the action group
echo "Updating Bedrock agent action group..."
aws bedrock-agent update-agent-action-group \
  --agent-id $MASTER_AGENT_ID \
  --agent-version DRAFT \
  --action-group-id $ACTION_GROUP_ID \
  --action-group-name "MasterWorkflowActionGroup" \
  --description "Execute complete medical analysis workflow" \
  --action-group-executor lambda=$LAMBDA_ARN \
  --api-schema payload='{"openapi":"3.0.0","info":{"title":"Master Medical Analysis Workflow API","version":"1.0.0","description":"API for executing complete medical record analysis workflow"},"paths":{"/analyze":{"post":{"summary":"Analyze patient medical records","description":"Execute complete medical analysis workflow including XML parsing, medical summarization, research correlation, and report generation","operationId":"analyzePatient","requestBody":{"required":true,"content":{"application/json":{"schema":{"type":"object","required":["patient_name"],"properties":{"patient_name":{"type":"string","description":"Name of the patient to analyze"}}}}}},"responses":{"200":{"description":"Successful analysis","content":{"application/json":{"schema":{"type":"object","properties":{"patient_id":{"type":"string","description":"Patient identifier"},"patient_name":{"type":"string","description":"Patient name"},"medical_summary":{"type":"string","description":"Comprehensive medical summary"},"research_analysis":{"type":"object","description":"Research correlation results"},"report_s3_key":{"type":"string","description":"S3 key where report is stored"}}}}}},"500":{"description":"Analysis failed","content":{"application/json":{"schema":{"type":"object","properties":{"error":{"type":"string"}}}}}}}}}}' \
  --region $REGION

echo "Preparing agent..."
aws bedrock-agent prepare-agent \
  --agent-id $MASTER_AGENT_ID \
  --region $REGION

echo "✅ Bedrock agent updated successfully!"
echo "Agent ID: $MASTER_AGENT_ID"
echo "Lambda ARN: $LAMBDA_ARN"
echo ""
echo "The agent is now configured to use the new Lambda function."
