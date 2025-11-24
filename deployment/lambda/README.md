# AWS Lambda Deployment

This directory contains Lambda function handlers and deployment configurations for the Medical Record Analysis System.

## Overview

The system deploys three Lambda functions that serve as the execution layer for AWS Bedrock agents:

1. **XML Parser Lambda** - Parses patient XML records from S3
2. **Medical Summarization Lambda** - Generates medical summaries
3. **Research Correlation Lambda** - Correlates medical research

## Architecture

```
┌─────────────────┐
│  Bedrock Agent  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────┐
│  API Gateway    │◄────►│ Lambda Layer │
└────────┬────────┘      └──────────────┘
         │
         ▼
┌─────────────────┐
│ Lambda Function │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   S3 Bucket     │
└─────────────────┘
```

## Prerequisites

### Required Tools
- AWS CLI (configured with credentials)
- AWS SAM CLI (`python3 -m pip install aws-sam-cli`)
- Python 3.11+
- Docker (for SAM build)

### AWS Requirements
- AWS Account ID: 539247495490
- Region: us-east-1 (HIPAA compliance)
- IAM permissions for Lambda, API Gateway, CloudFormation, S3, IAM

### Installation

```bash
# Install AWS SAM CLI
python3 -m pip install aws-sam-cli

# Verify installation
sam --version

# Configure AWS credentials
aws configure
```

## Directory Structure

```
deployment/lambda/
├── README.md                              # This file
├── template.yaml                          # SAM CloudFormation template
├── deploy.sh                              # Deployment script
├── xml_parser_handler.py                  # XML Parser Lambda handler
├── medical_summarization_handler.py       # Summarization Lambda handler
├── research_correlation_handler.py        # Research Lambda handler
├── layer/                                 # Lambda layer (generated)
│   └── python/                            # Python dependencies
├── packaged.yaml                          # Generated package template
└── deployment_outputs.json                # Generated deployment info
```

## Lambda Functions

### 1. XML Parser Lambda

**Handler**: `xml_parser_handler.lambda_handler`

**Actions**:
- `parsePatientRecord` - Parse patient XML from S3
- `validatePatientExists` - Check if patient record exists
- `getPatientMetadata` - Get patient record metadata
- `listPatients` - List available patient records
- `healthCheck` - Health check endpoint

**Event Format**:
```json
{
  "action": "parsePatientRecord",
  "parameters": {
    "patientName": "John Doe"
  }
}
```

### 2. Medical Summarization Lambda

**Handler**: `medical_summarization_handler.lambda_handler`

**Actions**:
- `generateSummary` - Generate medical summary
- `analyzeConditionTrends` - Analyze condition trends
- `getConditionInsights` - Get condition insights
- `healthCheck` - Health check endpoint

**Event Format**:
```json
{
  "action": "generateSummary",
  "parameters": {
    "patientData": { ... }
  }
}
```

### 3. Research Correlation Lambda

**Handler**: `research_correlation_handler.lambda_handler`

**Actions**:
- `correlateResearch` - Correlate medical research
- `healthCheck` - Health check endpoint

**Event Format**:
```json
{
  "action": "correlateResearch",
  "parameters": {
    "patientData": { ... },
    "medicalSummary": { ... }
  }
}
```

## Deployment

### Quick Deployment

```bash
# Deploy to production
./deploy.sh production

# Deploy to staging
./deploy.sh staging

# Deploy to development
./deploy.sh development
```

### Manual Deployment Steps

#### Step 1: Prepare Lambda Layer

```bash
# Create layer directory
mkdir -p layer/python

# Install dependencies
python3 -m pip install -r ../../requirements.txt -t layer/python/ --upgrade
```

#### Step 2: Build SAM Application

```bash
# Build with Docker
sam build --template-file template.yaml --use-container

# Or build locally
sam build --template-file template.yaml
```

#### Step 3: Package Application

```bash
# Create S3 bucket for deployment artifacts
aws s3 mb s3://medical-record-analysis-deployment --region us-east-1

# Package application
sam package \
  --template-file .aws-sam/build/template.yaml \
  --s3-bucket medical-record-analysis-deployment \
  --output-template-file packaged.yaml \
  --region us-east-1
```

#### Step 4: Deploy Application

```bash
# Deploy with SAM
sam deploy \
  --template-file packaged.yaml \
  --stack-name medical-record-analysis-lambda \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1 \
  --parameter-overrides \
      Environment=production \
      S3BucketName=patient-records-20251024
```

#### Step 5: Get Deployment Outputs

```bash
# Get API endpoint
aws cloudformation describe-stacks \
  --stack-name medical-record-analysis-lambda \
  --region us-east-1 \
  --query 'Stacks[0].Outputs'
```

## Configuration

### Environment Variables

All Lambda functions have these environment variables:

- `ENVIRONMENT` - Deployment environment (production/staging/development)
- `S3_BUCKET_NAME` - S3 bucket for patient records
- `AWS_REGION` - AWS region (us-east-1)
- `LOG_LEVEL` - Logging level (INFO/DEBUG/ERROR)
- `FUNCTION_NAME` - Specific function identifier

### Lambda Configuration

- **Runtime**: Python 3.11
- **Timeout**: 300 seconds (5 minutes)
- **Memory**: 512 MB
- **Architecture**: x86_64

### API Gateway Configuration

- **Stage**: Based on environment parameter
- **Authentication**: API Key required
- **CORS**: Enabled (configure for production)
- **Throttling**: 50 requests/second, 100 burst
- **Quota**: 10,000 requests/day

## Testing

### Local Testing

```bash
# Test XML Parser locally
python xml_parser_handler.py

# Test with SAM local
sam local invoke XMLParserFunction \
  --event test_events/parse_patient.json

# Start local API
sam local start-api
```

### Test Events

Create `test_events/parse_patient.json`:
```json
{
  "patientName": "John Doe",
  "action": "parsePatientRecord"
}
```

### API Testing

```bash
# Get API key
API_KEY=$(aws apigateway get-api-key \
  --api-key <API_KEY_ID> \
  --include-value \
  --query 'value' \
  --output text)

# Test XML Parser
curl -X POST https://<API_ID>.execute-api.us-east-1.amazonaws.com/production/parse-patient-record \
  -H "x-api-key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"patientName": "John Doe"}'

# Test Medical Summarization
curl -X POST https://<API_ID>.execute-api.us-east-1.amazonaws.com/production/generate-summary \
  -H "x-api-key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d @test_data/patient_data.json

# Test Research Correlation
curl -X POST https://<API_ID>.execute-api.us-east-1.amazonaws.com/production/correlate-research \
  -H "x-api-key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d @test_data/research_request.json
```

## Monitoring

### CloudWatch Logs

View logs for each function:

```bash
# XML Parser logs
aws logs tail /aws/lambda/MedicalRecordXMLParser --follow

# Medical Summarization logs
aws logs tail /aws/lambda/MedicalSummarization --follow

# Research Correlation logs
aws logs tail /aws/lambda/ResearchCorrelation --follow
```

### CloudWatch Metrics

Key metrics to monitor:
- Invocations
- Errors
- Duration
- Throttles
- Concurrent Executions

### CloudWatch Alarms

The deployment creates alarms for:
- Error rate > 5 errors in 5 minutes
- Duration approaching timeout
- Throttling events

## Integration with Bedrock Agents

### Update Bedrock Agent Action Groups

After deploying Lambda functions, update the Bedrock agent action groups with the Lambda ARNs:

```bash
# Get Lambda ARNs
XML_PARSER_ARN=$(aws cloudformation describe-stacks \
  --stack-name medical-record-analysis-lambda \
  --query 'Stacks[0].Outputs[?OutputKey==`XMLParserFunctionArn`].OutputValue' \
  --output text)

# Update Bedrock agent action group
aws bedrock-agent update-agent-action-group \
  --agent-id <AGENT_ID> \
  --agent-version DRAFT \
  --action-group-id <ACTION_GROUP_ID> \
  --action-group-executor lambda=$XML_PARSER_ARN
```

## Troubleshooting

### Lambda Timeout Issues

If functions timeout:
1. Increase timeout in `template.yaml`
2. Optimize code for performance
3. Check S3 access latency
4. Review CloudWatch logs for bottlenecks

### Permission Issues

If Lambda can't access S3:
1. Verify IAM role has S3 permissions
2. Check S3 bucket policy
3. Verify KMS key permissions
4. Review CloudTrail logs

### Import Errors

If Lambda can't import modules:
1. Verify layer is built correctly
2. Check Python version compatibility
3. Rebuild layer with `--upgrade` flag
4. Test locally with SAM

### API Gateway 403 Errors

If API returns 403:
1. Verify API key is included in request
2. Check usage plan configuration
3. Verify API key is enabled
4. Check CORS configuration

## Performance Optimization

### Cold Start Optimization

- Use Lambda layers for dependencies
- Minimize package size
- Use provisioned concurrency for critical functions
- Implement connection pooling

### Memory Optimization

- Monitor memory usage in CloudWatch
- Adjust memory allocation based on usage
- Consider memory vs. duration tradeoffs

### Cost Optimization

- Use appropriate memory allocation
- Implement caching where possible
- Monitor invocation patterns
- Consider Reserved Concurrency

## Security

### HIPAA Compliance

- All data encrypted in transit and at rest
- CloudWatch logs retention: 30 days
- API Gateway requires API key
- Lambda execution role follows least privilege
- All resources in us-east-1 region

### Best Practices

- Rotate API keys regularly
- Use AWS Secrets Manager for sensitive data
- Enable CloudTrail for audit logging
- Implement request validation
- Use VPC endpoints for S3 access

## Updating Functions

### Update Function Code

```bash
# Rebuild and redeploy
sam build
sam deploy
```

### Update Function Configuration

```bash
# Update environment variables
aws lambda update-function-configuration \
  --function-name MedicalRecordXMLParser \
  --environment Variables={LOG_LEVEL=DEBUG}

# Update timeout
aws lambda update-function-configuration \
  --function-name MedicalRecordXMLParser \
  --timeout 600
```

## Cleanup

### Delete Stack

```bash
# Delete CloudFormation stack
aws cloudformation delete-stack \
  --stack-name medical-record-analysis-lambda \
  --region us-east-1

# Delete deployment bucket
aws s3 rb s3://medical-record-analysis-deployment --force
```

## Support

For issues or questions:
- Review CloudWatch logs
- Check AWS Lambda documentation
- Verify IAM permissions
- Test locally with SAM
- Review API Gateway logs

## Next Steps

After deploying Lambda functions:

1. **Update Bedrock Agents** (Task 13.1)
   - Update action group Lambda ARNs
   - Test agent invocations
   - Verify end-to-end workflow

2. **Configure Monitoring** (Task 13.3)
   - Set up CloudWatch dashboards
   - Configure additional alarms
   - Enable X-Ray tracing

3. **Production Hardening**
   - Configure VPC for Lambda functions
   - Implement request throttling
   - Set up WAF rules for API Gateway
   - Enable detailed monitoring
