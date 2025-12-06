# Bedrock Agent Deployment Guide

This guide explains how to deploy and use the Master Bedrock Agent that orchestrates the complete medical analysis workflow.

## Architecture Overview

```
CLI (--bedrock-agent flag)
    ↓
Bedrock Agent Runtime API
    ↓
Master Bedrock Agent (Claude + Instructions)
    ↓
Action Group: "analyzePatient"
    ↓
Lambda: MasterWorkflowLambda
    ↓
MainWorkflow (your existing Python code)
    ↓
  - XMLParserAgent
  - MedicalSummarizationAgent
  - ResearchCorrelationAgent
  - ReportGenerator
  - S3ReportPersister
    ↓
Returns complete analysis to Agent
    ↓
Agent formats response for user
```

## Key Differences from Direct Model Invocation

### Current `--bedrock` flag:
- Your code orchestrates everything
- Direct Claude API calls
- Predictable, sequential workflow

### New `--bedrock-agent` flag:
- Bedrock Agent orchestrates via Lambda
- Agent decides when to call workflow
- More flexible but requires deployment

## Prerequisites

1. AWS CLI configured with credentials
2. IAM permissions for:
   - Lambda (create functions, roles)
   - Bedrock Agent (create agents, action groups)
   - S3 (read/write patient records)
3. Python 3.11+ runtime available in Lambda

## Deployment Steps

### Step 1: Deploy Master Agent

```bash
cd deployment/bedrock
python deploy_master_agent.py
```

This script will:
1. Create IAM role for Lambda
2. Deploy Lambda function with your workflow code
3. Create Bedrock Agent
4. Create action group linking agent to Lambda
5. Create production alias
6. Save deployment info to `master_agent_deployment.json`

### Step 2: Note Agent IDs

After deployment, you'll see:
```
Agent ID: ABCD1234
Alias ID: EFGH5678
```

Save these for CLI usage.

### Step 3: Test with CLI

```bash
# Using deployed agent
python launch_prototype.py --bedrock-agent \
  --agent-id ABCD1234 \
  --agent-alias-id EFGH5678
```

## Lambda Function Details

### Handler: `master_workflow_handler.py`

The Lambda function:
1. Receives event from Bedrock Agent
2. Extracts patient_name parameter
3. Imports and executes MainWorkflow
4. Returns JSON response to agent

### Environment Variables

Set in Lambda:
- `S3_BUCKET_NAME`: patient-records-20251024
- `AWS_REGION`: us-east-1

### Timeout & Memory

- Timeout: 300 seconds (5 minutes)
- Memory: 1024 MB
- Runtime: Python 3.11

## Lambda Deployment Package

For production, create a proper deployment package:

```bash
# Create deployment package
cd /Users/humberto.acevedo/datuak-agents
mkdir -p lambda_package
pip install -r requirements.txt -t lambda_package/
cp -r src lambda_package/
cp deployment/lambda/master_workflow_handler.py lambda_package/

# Create ZIP
cd lambda_package
zip -r ../master_workflow_lambda.zip .

# Upload to Lambda
aws lambda update-function-code \
  --function-name MedicalAnalysisMasterWorkflow \
  --zip-file fileb://../master_workflow_lambda.zip \
  --region us-east-1
```

## CLI Usage

### Option 1: Python Agents (default)
```bash
python launch_prototype.py
```

### Option 2: Direct Bedrock Models
```bash
python launch_prototype.py --bedrock
```

### Option 3: Bedrock Agent (new)
```bash
python launch_prototype.py --bedrock-agent \
  --agent-id YOUR_AGENT_ID \
  --agent-alias-id YOUR_ALIAS_ID
```

## Configuration File

After deployment, agent IDs are saved to:
```
deployment/bedrock/master_agent_deployment.json
```

You can load these automatically:

```python
import json
with open('deployment/bedrock/master_agent_deployment.json') as f:
    config = json.load(f)
    agent_id = config['agent_id']
    agent_alias_id = config['agent_alias_id']
```

## Monitoring

### CloudWatch Logs

Lambda logs:
```
/aws/lambda/MedicalAnalysisMasterWorkflow
```

Agent logs:
```
/aws/bedrock/agents/MedicalRecordAnalysisMasterAgent
```

### View Logs

```bash
# Lambda logs
aws logs tail /aws/lambda/MedicalAnalysisMasterWorkflow --follow

# Agent logs
aws logs tail /aws/bedrock/agents/MedicalRecordAnalysisMasterAgent --follow
```

## Troubleshooting

### Lambda Timeout
If analysis takes > 5 minutes:
```bash
aws lambda update-function-configuration \
  --function-name MedicalAnalysisMasterWorkflow \
  --timeout 600
```

### Import Errors in Lambda
Ensure all dependencies are in deployment package:
```bash
pip install -r requirements.txt -t lambda_package/
```

### Agent Not Found
Verify agent exists:
```bash
aws bedrock-agent list-agents --region us-east-1
```

### Permission Errors
Check Lambda role has S3 access:
```bash
aws iam get-role-policy \
  --role-name MedicalAnalysisLambdaRole \
  --policy-name S3Access
```

## Cost Comparison

### Direct Model (`--bedrock`):
- 2 Claude API calls per analysis
- ~$0.001 per analysis

### Bedrock Agent (`--bedrock-agent`):
- 1 Agent invocation (includes Claude)
- 1 Lambda execution
- ~$0.002 per analysis

## When to Use Each Option

### Use `--bedrock` (Direct Models):
- ✅ Lower cost
- ✅ Faster (no Lambda cold start)
- ✅ More predictable
- ✅ Easier debugging

### Use `--bedrock-agent`:
- ✅ Agent can handle complex queries
- ✅ More flexible (agent decides workflow)
- ✅ Better for conversational interfaces
- ✅ Scalable (Lambda auto-scales)

## Next Steps

1. Deploy the agent: `python deploy_master_agent.py`
2. Test with CLI: `python launch_prototype.py --bedrock-agent ...`
3. Monitor CloudWatch logs
4. Optimize Lambda memory/timeout based on usage
5. Set up CloudWatch alarms for errors

## Support

For issues:
- Check CloudWatch logs
- Verify IAM permissions
- Ensure S3 bucket access
- Test Lambda function directly
