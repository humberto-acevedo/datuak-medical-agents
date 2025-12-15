# Bedrock Agent Lambda Permission Fix

## Problem Analysis

### Error Details
```
Access denied while invoking Lambda function 
arn:aws:lambda:us-east-1:539247495490:function:MedicalAnalysisMasterWorkflow
```

### Root Cause
The Bedrock Agent `LAA6HDZPAH` doesn't have permission to invoke the Lambda function `MedicalAnalysisMasterWorkflow`. This is an AWS IAM permissions issue.

## Solutions

### Option 1: Fix Lambda Permissions (Recommended)

#### 1.1 Add Resource-Based Policy to Lambda
```bash
aws lambda add-permission \
  --function-name MedicalAnalysisMasterWorkflow \
  --statement-id bedrock-agent-invoke \
  --action lambda:InvokeFunction \
  --principal bedrock.amazonaws.com \
  --source-arn "arn:aws:bedrock:us-east-1:539247495490:agent/LAA6HDZPAH"
```

#### 1.2 Update Bedrock Agent Execution Role
The Bedrock Agent's execution role needs these permissions:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "lambda:InvokeFunction"
            ],
            "Resource": [
                "arn:aws:lambda:us-east-1:539247495490:function:MedicalAnalysisMasterWorkflow"
            ]
        }
    ]
}
```

### Option 2: Use Direct Bedrock Models (Workaround)

Instead of using the Bedrock Agent, use the direct Claude models which we know work:

```bash
# Instead of this (broken):
python launch_prototype.py --bedrock-agent --agent-id LAA6HDZPAH --agent-alias-id TSTALIASID

# Use this (working):
python launch_prototype.py --bedrock
```

### Option 3: Add Fallback Logic

Let me add fallback logic to the system to gracefully handle this error.

## Implementation

### 3.1 Add Error Handling to Bedrock Workflow