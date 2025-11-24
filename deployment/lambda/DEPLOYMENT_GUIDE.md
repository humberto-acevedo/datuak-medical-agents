# Lambda Deployment Quick Start Guide

## Overview

This guide provides a quick reference for deploying the Medical Record Analysis Lambda functions.

## Prerequisites Checklist

- [ ] AWS CLI installed and configured
- [ ] AWS SAM CLI installed (`python3 -m pip install aws-sam-cli`)
- [ ] Python 3.11+ installed
- [ ] Docker installed (for SAM build)
- [ ] AWS credentials configured for account 539247495490
- [ ] Access to us-east-1 region

## Quick Deployment (5 minutes)

```bash
# 1. Navigate to lambda directory
cd deployment/lambda

# 2. Run deployment script
./deploy.sh production

# 3. Save the API endpoint and key from output
```

That's it! The script handles everything automatically.

## What Gets Deployed

### Lambda Functions
1. **MedicalRecordXMLParser** - Parses patient XML records
2. **MedicalSummarization** - Generates medical summaries
3. **ResearchCorrelation** - Correlates medical research

### Supporting Resources
- Lambda execution IAM role with HIPAA-compliant policies
- Lambda layer with Python dependencies
- API Gateway with endpoints for each function
- API key and usage plan
- CloudWatch log groups (30-day retention)
- CloudWatch alarms for error monitoring

### Estimated Costs
- Lambda: ~$0.20 per 1M requests
- API Gateway: ~$3.50 per 1M requests
- CloudWatch Logs: ~$0.50/GB
- S3 (deployment): ~$0.023/GB

## Testing Your Deployment

```bash
# Get your API key
API_KEY=$(cat deployment_outputs.json | grep apiKeyValue | cut -d'"' -f4)

# Get your API endpoint
API_ENDPOINT=$(cat deployment_outputs.json | grep apiEndpoint | cut -d'"' -f4)

# Test XML Parser
curl -X POST $API_ENDPOINT/parse-patient-record \
  -H "x-api-key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"patientName": "John Doe"}'
```

## Common Issues

### Issue: "SAM CLI not found"
**Solution**: Install SAM CLI
```bash
python3 -m pip install aws-sam-cli
```

### Issue: "Docker not running"
**Solution**: Start Docker Desktop or Docker daemon

### Issue: "Access Denied" errors
**Solution**: Verify AWS credentials
```bash
aws sts get-caller-identity
```

### Issue: "Stack already exists"
**Solution**: Update existing stack
```bash
sam deploy --stack-name medical-record-analysis-lambda --no-fail-on-empty-changeset
```

## Integration with Bedrock

After deploying Lambda functions, update your Bedrock agent action groups:

```bash
# Get Lambda ARNs from CloudFormation outputs
aws cloudformation describe-stacks \
  --stack-name medical-record-analysis-lambda \
  --query 'Stacks[0].Outputs'

# Update each Bedrock agent action group with corresponding Lambda ARN
```

## Monitoring

### View Logs
```bash
# Real-time logs
aws logs tail /aws/lambda/MedicalRecordXMLParser --follow
```

### View Metrics
```bash
# Open CloudWatch console
open https://console.aws.amazon.com/cloudwatch/home?region=us-east-1
```

## Cleanup

To remove all deployed resources:

```bash
aws cloudformation delete-stack \
  --stack-name medical-record-analysis-lambda \
  --region us-east-1
```

## Next Steps

1. ✅ Lambda functions deployed
2. ⏭️ Update Bedrock agent action groups (Task 13.1)
3. ⏭️ Configure monitoring dashboards (Task 13.3)
4. ⏭️ Set up CI/CD pipeline (Task 14)

## Support

- **Logs**: Check CloudWatch Logs for detailed error messages
- **Metrics**: Monitor Lambda metrics in CloudWatch
- **Documentation**: See README.md for detailed information
- **AWS Support**: Contact AWS support for infrastructure issues
