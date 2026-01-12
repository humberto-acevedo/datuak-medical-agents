# Bedrock Agent Function Call Format Fix

## Problem

The Bedrock Agent was returning an error:
```
"Unfortunately, I am not able to execute the complete workflow to analyze the medical records 
for patient Jane Smith due to an issue with the function call format."
```

## Root Cause

The OpenAPI schema for the master workflow action group incorrectly defined `patient_name` as a **query parameter** instead of in the **request body**. For POST requests, Bedrock Agents expect parameters in the request body.

**Incorrect (before):**
```json
"parameters": [
  {
    "name": "patient_name",
    "in": "query",
    "required": true,
    "schema": {"type": "string"}
  }
]
```

**Correct (after):**
```json
"requestBody": {
  "required": true,
  "content": {
    "application/json": {
      "schema": {
        "type": "object",
        "required": ["patient_name"],
        "properties": {
          "patient_name": {
            "type": "string",
            "description": "Name of the patient to analyze"
          }
        }
      }
    }
  }
}
```

## Files Changed

1. **deployment/bedrock/action_groups/master_workflow_actions.json**
   - Changed from query parameters to requestBody

2. **deployment/lambda/master_workflow_handler.py**
   - Updated to extract `patient_name` from requestBody
   - Added fallback to parameters array for backward compatibility

3. **update_bedrock_agent.py** (new)
   - Script to update the deployed Bedrock Agent with corrected schema

## How to Apply the Fix

### Step 1: Set Environment Variables

```bash
# Set your Lambda function ARN
export MASTER_WORKFLOW_LAMBDA_ARN="arn:aws:lambda:us-east-1:YOUR_ACCOUNT:function:master-workflow"

# Optional: Set cross-account role (defaults to MemberCrossAccountRole)
export CROSS_ACCOUNT_ROLE_ARN="arn:aws:iam::539247495490:role/MemberCrossAccountRole"
```

### Step 2: Update the Lambda Function

```bash
# Navigate to Lambda directory
cd deployment/lambda

# Package and deploy the updated handler
zip -r function.zip master_workflow_handler.py

aws lambda update-function-code \
  --function-name master-workflow \
  --zip-file fileb://function.zip \
  --region us-east-1
```

### Step 3: Update the Bedrock Agent

```bash
# Run the update script with your agent ID
python update_bedrock_agent.py YOUR_AGENT_ID
```

Example:
```bash
python update_bedrock_agent.py ABCD1234
```

### Step 4: Test the Fix

```bash
python launch_prototype.py --bedrock-agent \
  --agent-id YOUR_AGENT_ID \
  --agent-alias-id YOUR_ALIAS_ID
```

## Alternative: Manual Update via AWS Console

If you prefer to update manually:

1. **Update Lambda:**
   - Go to AWS Lambda Console
   - Find your `master-workflow` function
   - Update the code with the new `master_workflow_handler.py`

2. **Update Bedrock Agent:**
   - Go to AWS Bedrock Console → Agents
   - Select your agent
   - Go to Action Groups → MasterWorkflowActionGroup
   - Edit the API Schema
   - Replace with contents of `deployment/bedrock/action_groups/master_workflow_actions.json`
   - Save and Prepare the agent

## Verification

After applying the fix, the agent should successfully:
1. Parse the patient name from the request
2. Execute the complete workflow
3. Return a structured JSON response with analysis results

Expected response format:
```json
{
  "patient_id": "P12345",
  "patient_name": "Jane Smith",
  "medical_summary": "...",
  "research_analysis": {...},
  "report_s3_key": "s3://bucket/path/to/report.json"
}
```

## Technical Details

### OpenAPI 3.0 Best Practices for Bedrock Agents

- **GET requests**: Use query parameters
- **POST/PUT requests**: Use requestBody
- **Required fields**: Mark in both `required` array and individual property definitions
- **Schema validation**: Bedrock validates against the OpenAPI schema before invoking Lambda

### Lambda Event Structure

With the fix, the Lambda receives:
```json
{
  "requestBody": {
    "content": {
      "application/json": "{\"patient_name\": \"Jane Smith\"}"
    }
  }
}
```

The handler now correctly extracts `patient_name` from this structure.

## Troubleshooting

### Issue: "Missing required parameter: patient_name"

**Cause:** Lambda not receiving the parameter correctly

**Solution:** Check CloudWatch Logs for the Lambda function to see the actual event structure

### Issue: "Agent preparation failed"

**Cause:** Invalid OpenAPI schema

**Solution:** Validate the schema at https://editor.swagger.io/

### Issue: "Access denied" when updating agent

**Cause:** Insufficient IAM permissions

**Solution:** Ensure your role has `bedrock:UpdateAgentActionGroup` and `bedrock:PrepareAgent` permissions

## References

- [AWS Bedrock Agents Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
- [OpenAPI 3.0 Specification](https://swagger.io/specification/)
- [Bedrock Agent Action Groups](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-action-groups.html)
