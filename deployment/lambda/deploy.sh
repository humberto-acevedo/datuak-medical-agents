#!/bin/bash
# AWS Lambda Deployment Script for Medical Record Analysis System

set -e  # Exit on error

# Configuration
STACK_NAME="medical-record-analysis-lambda"
REGION="us-east-1"
S3_BUCKET="medical-record-analysis-deployment"
ENVIRONMENT="${1:-production}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "Medical Record Analysis Lambda Deployment"
echo "=========================================="
echo ""
echo "Environment: $ENVIRONMENT"
echo "Region: $REGION"
echo "Stack Name: $STACK_NAME"
echo ""

# Check prerequisites
echo "Checking prerequisites..."

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo -e "${RED}Error: AWS CLI is not installed${NC}"
    exit 1
fi

# Check SAM CLI
if ! command -v sam &> /dev/null; then
    echo -e "${RED}Error: AWS SAM CLI is not installed${NC}"
    echo "Install with: python3 -m pip install aws-sam-cli"
    exit 1
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Prerequisites check passed${NC}"
echo ""

# Verify AWS credentials
echo "Verifying AWS credentials..."
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}Error: AWS credentials not configured${NC}"
    echo "Run: aws configure"
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo -e "${GREEN}✓ AWS Account: $ACCOUNT_ID${NC}"
echo ""

# Create deployment bucket if it doesn't exist
echo "Checking deployment S3 bucket..."
if ! aws s3 ls "s3://$S3_BUCKET" 2>&1 > /dev/null; then
    echo "Creating deployment bucket: $S3_BUCKET"
    aws s3 mb "s3://$S3_BUCKET" --region $REGION
    
    # Enable encryption
    aws s3api put-bucket-encryption \
        --bucket $S3_BUCKET \
        --server-side-encryption-configuration '{
            "Rules": [{
                "ApplyServerSideEncryptionByDefault": {
                    "SSEAlgorithm": "AES256"
                }
            }]
        }'
    
    echo -e "${GREEN}✓ Created deployment bucket${NC}"
else
    echo -e "${GREEN}✓ Deployment bucket exists${NC}"
fi
echo ""

# Prepare Lambda layer
echo "Preparing Lambda layer with dependencies..."
mkdir -p layer/python
python3 -m pip install -r ../../requirements.txt -t layer/python/ --upgrade
echo -e "${GREEN}✓ Lambda layer prepared${NC}"
echo ""

# Build SAM application
echo "Building SAM application..."
sam build --template-file template.yaml --use-container
echo -e "${GREEN}✓ SAM build complete${NC}"
echo ""

# Package SAM application
echo "Packaging SAM application..."
sam package \
    --template-file .aws-sam/build/template.yaml \
    --s3-bucket $S3_BUCKET \
    --output-template-file packaged.yaml \
    --region $REGION
echo -e "${GREEN}✓ SAM package complete${NC}"
echo ""

# Deploy SAM application
echo "Deploying SAM application..."
sam deploy \
    --template-file packaged.yaml \
    --stack-name $STACK_NAME \
    --capabilities CAPABILITY_NAMED_IAM \
    --region $REGION \
    --parameter-overrides \
        Environment=$ENVIRONMENT \
        S3BucketName=patient-records-20251024 \
    --no-fail-on-empty-changeset \
    --tags \
        Application=MedicalRecordAnalysis \
        Compliance=HIPAA \
        Environment=$ENVIRONMENT

echo -e "${GREEN}✓ SAM deployment complete${NC}"
echo ""

# Get outputs
echo "Retrieving deployment outputs..."
API_ENDPOINT=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`APIEndpoint`].OutputValue' \
    --output text)

API_KEY_ID=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`APIKey`].OutputValue' \
    --output text)

# Get API Key value
API_KEY_VALUE=$(aws apigateway get-api-key \
    --api-key $API_KEY_ID \
    --include-value \
    --region $REGION \
    --query 'value' \
    --output text)

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""
echo "API Endpoint: $API_ENDPOINT"
echo "API Key ID: $API_KEY_ID"
echo ""
echo "Lambda Functions:"
echo "  - MedicalRecordXMLParser"
echo "  - MedicalSummarization"
echo "  - ResearchCorrelation"
echo ""
echo "To test the API:"
echo "  curl -X POST $API_ENDPOINT/parse-patient-record \\"
echo "    -H 'x-api-key: $API_KEY_VALUE' \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"patientName\": \"John Doe\"}'"
echo ""
echo "API Key has been saved to: deployment_outputs.json"
echo ""

# Save outputs to file
cat > deployment_outputs.json <<EOF
{
  "stackName": "$STACK_NAME",
  "region": "$REGION",
  "environment": "$ENVIRONMENT",
  "apiEndpoint": "$API_ENDPOINT",
  "apiKeyId": "$API_KEY_ID",
  "apiKeyValue": "$API_KEY_VALUE",
  "accountId": "$ACCOUNT_ID",
  "deploymentTimestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}
EOF

echo -e "${GREEN}✓ Deployment outputs saved to deployment_outputs.json${NC}"
echo ""
echo "Next steps:"
echo "  1. Update Bedrock agent action groups with Lambda ARNs"
echo "  2. Test Lambda functions with sample data"
echo "  3. Configure CloudWatch dashboards and alarms"
echo "  4. Review and update API Gateway CORS settings for production"
echo ""
