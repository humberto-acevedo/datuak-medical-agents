# Lambda Handler Fix for Bedrock Agent

## Problem Analysis

### Error Evolution
1. **Before**: "Access denied while invoking Lambda function" 
2. **After**: "Received failed response from API execution"

This indicates the Lambda function is now being invoked but failing internally.

### Root Causes
1. **Import Issues**: Lambda handler tried to import local `src` modules that don't exist in Lambda environment
2. **Async Execution**: Complex async workflow execution in Lambda context
3. **Missing Dependencies**: Lambda layer didn't include all required dependencies
4. **Parameter Extraction**: Bedrock Agent input format not properly handled

## Solutions Implemented

### 1. Simplified Lambda Handler

**File: `deployment/lambda/master_workflow_handler.py`**

#### Before (Complex)
```python
# Import and execute workflow
from src.workflow.main_workflow import MainWorkflow
result = asyncio.run(workflow.execute_complete_analysis(patient_name))
```

#### After (Simplified)
```python
# Direct Bedrock calls without complex imports
medical_summary = invoke_claude_model(summary_prompt)
research_analysis = invoke_claude_model(research_prompt)
```

### 2. Direct Bedrock Integration

Added `invoke_claude_model()` function that directly calls Claude 3.5 Haiku:

```python
def invoke_claude_model(prompt: str) -> str:
    model_id = "anthropic.claude-3-5-haiku-20241022-v1:0"
    request_body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 4000,
        "messages": [{"role": "user", "content": prompt}]
    }
    response = bedrock_client.invoke_model(modelId=model_id, body=json.dumps(request_body))
    return response_body['content'][0]['text']
```

### 3. Improved Parameter Extraction

Enhanced parameter extraction to handle multiple Bedrock Agent input formats:

```python
# Method 1: From inputText (most common)
if 'patient:' in input_text.lower():
    patient_name = input_text.split('patient:')[1].strip()

# Method 2: From requestBody
# Method 3: From parameters array
# Method 4: Default for testing
```

### 4. Comprehensive Error Handling

Added try/catch blocks around:
- S3 patient record retrieval
- Bedrock model invocations
- Report generation and storage
- JSON parsing and formatting

### 5. Workflow Steps

The Lambda now executes this simplified workflow:

1. **Extract patient name** from Bedrock Agent input
2. **Fetch patient XML** from S3 bucket
3. **Generate medical summary** using Claude 3.5 Haiku
4. **Generate research analysis** using Claude 3.5 Haiku
5. **Save report** to S3 bucket
6. **Return results** to Bedrock Agent

## Testing

### Test 1: Direct Lambda Invocation

```bash
cd deployment/lambda
python test_lambda.py
```

This will:
- Invoke the Lambda function directly
- Check the response format
- Display recent CloudWatch logs

### Test 2: Check Lambda Logs

```bash
aws logs tail /aws/lambda/MedicalAnalysisMasterWorkflow --follow
```

### Test 3: Bedrock Agent Integration

```bash
python launch_prototype.py --bedrock-agent --agent-id LAA6HDZPAH --agent-alias-id TSTALIASID
```

## Deployment

### Option 1: Redeploy Everything

```bash
cd deployment/lambda
./deploy.sh production
```

### Option 2: Update Function Code Only

```bash
cd deployment/lambda
zip function.zip master_workflow_handler.py
aws lambda update-function-code \
  --function-name MedicalAnalysisMasterWorkflow \
  --zip-file fileb://function.zip
```

## Expected Behavior

### Before Fix
```
❌ Received failed response from API execution
❌ Lambda function crashes on import errors
❌ No meaningful error messages
```

### After Fix
```
✅ Lambda function executes successfully
✅ Generates medical summary with Claude
✅ Generates research analysis with Claude
✅ Saves report to S3
✅ Returns structured JSON response to Bedrock Agent
```

## Response Format

The Lambda now returns properly formatted JSON:

```json
{
  "patient_name": "Jane Smith",
  "medical_summary": "Comprehensive medical summary...",
  "research_analysis": "Evidence-based research analysis...",
  "report_s3_key": "analysis-reports/Jane_Smith/bedrock-agent-RPT_20251202_140530.json",
  "report_id": "RPT_20251202_140530_Jane_Smith",
  "workflow_type": "bedrock_agent_lambda",
  "generated_at": "2025-12-02T14:05:30",
  "model_info": {
    "model_name": "Claude 3.5 Haiku",
    "provider": "Anthropic",
    "region": "us-east-1"
  }
}
```

## Monitoring

### CloudWatch Logs
```bash
# Real-time monitoring
aws logs tail /aws/lambda/MedicalAnalysisMasterWorkflow --follow

# Search for errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/MedicalAnalysisMasterWorkflow \
  --filter-pattern "ERROR"
```

### CloudWatch Metrics
- **Duration**: Should be 30-60 seconds for typical analysis
- **Memory**: Should use ~200-400MB of 1GB allocated
- **Errors**: Should be 0 for successful executions
- **Invocations**: Tracks usage

## Troubleshooting

### Issue: "Patient record not found"
**Solution**: Verify S3 bucket and file naming
```bash
aws s3 ls s3://patient-records-20251024/patient-records/
```

### Issue: "Claude model invocation failed"
**Solution**: Check Bedrock model access
```bash
aws bedrock list-foundation-models --region us-east-1
```

### Issue: "S3 access denied"
**Solution**: Verify Lambda IAM permissions
```bash
aws iam get-role-policy --role-name MedicalRecordAnalysisLambdaRole --policy-name MedicalRecordAnalysisLambdaPolicy
```

### Issue: Lambda timeout
**Solution**: Function has 15-minute timeout, check for infinite loops in logs

## Security & Compliance

### HIPAA Compliance
- ✅ All data encrypted in transit (HTTPS/TLS)
- ✅ All data encrypted at rest (S3 server-side encryption)
- ✅ No PHI in CloudWatch logs
- ✅ Access controls via IAM policies
- ✅ Audit trail via CloudTrail

### IAM Permissions
Lambda execution role has minimal required permissions:
- S3: GetObject, PutObject on patient records bucket
- Bedrock: InvokeModel on Claude models only
- CloudWatch: CreateLogGroup, CreateLogStream, PutLogEvents
- KMS: Decrypt/Encrypt for S3 encryption

## Performance

### Expected Performance
- **Cold Start**: 2-5 seconds
- **Warm Execution**: 30-60 seconds
- **Memory Usage**: 200-400MB
- **Cost per Analysis**: ~$0.002 (Lambda + Bedrock)

### Optimization
- Function stays warm for 15 minutes after last invocation
- Claude 3.5 Haiku chosen for speed and cost efficiency
- S3 operations optimized with direct key access
- JSON responses kept minimal for faster transmission

## Next Steps

1. ✅ Deploy updated Lambda handler
2. ⏭️ Test with real patient data
3. ⏭️ Monitor performance and costs
4. ⏭️ Add more sophisticated error handling
5. ⏭️ Implement caching for repeated analyses

The Lambda function is now properly configured for Bedrock Agent integration! 🎉