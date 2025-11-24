#!/bin/bash
# Deploy CI/CD Pipeline for Medical Record Analysis System

set -e

# Configuration
STACK_NAME="medical-record-analysis-pipeline"
REGION="us-east-1"
TEMPLATE_FILE="pipeline.yaml"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=============================================="
echo "Medical Record Analysis - Pipeline Deployment"
echo "=============================================="
echo ""

# Check prerequisites
echo "Checking prerequisites..."
if ! command -v aws &> /dev/null; then
    echo -e "${RED}Error: AWS CLI is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Prerequisites check passed${NC}"
echo ""

# Verify AWS credentials
echo "Verifying AWS credentials..."
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo -e "${GREEN}✓ AWS Account: $ACCOUNT_ID${NC}"
echo ""

# Collect parameters
echo "Pipeline Configuration:"
echo ""

read -p "GitHub Repository Owner: " GITHUB_OWNER
read -p "GitHub Repository Name [medical-record-analysis]: " GITHUB_REPO
GITHUB_REPO=${GITHUB_REPO:-medical-record-analysis}

read -p "GitHub Branch [main]: " GITHUB_BRANCH
GITHUB_BRANCH=${GITHUB_BRANCH:-main}

read -sp "GitHub Personal Access Token: " GITHUB_TOKEN
echo ""

read -p "Environment [production]: " ENVIRONMENT
ENVIRONMENT=${ENVIRONMENT:-production}

echo ""
echo "Configuration Summary:"
echo "  Repository: $GITHUB_OWNER/$GITHUB_REPO"
echo "  Branch: $GITHUB_BRANCH"
echo "  Environment: $ENVIRONMENT"
echo "  Region: $REGION"
echo ""

read -p "Proceed with deployment? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "Deployment cancelled"
    exit 0
fi

echo ""
echo "Deploying pipeline..."

# Deploy CloudFormation stack
aws cloudformation deploy \
    --template-file $TEMPLATE_FILE \
    --stack-name $STACK_NAME \
    --parameter-overrides \
        GitHubOwner=$GITHUB_OWNER \
        GitHubRepo=$GITHUB_REPO \
        GitHubBranch=$GITHUB_BRANCH \
        GitHubToken=$GITHUB_TOKEN \
        Environment=$ENVIRONMENT \
    --capabilities CAPABILITY_NAMED_IAM \
    --region $REGION \
    --tags \
        Application=MedicalRecordAnalysis \
        Environment=$ENVIRONMENT

echo -e "${GREEN}✓ Pipeline deployed successfully${NC}"
echo ""

# Get outputs
PIPELINE_NAME=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`PipelineName`].OutputValue' \
    --output text)

PIPELINE_URL=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`PipelineUrl`].OutputValue' \
    --output text)

ARTIFACT_BUCKET=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`ArtifactBucketName`].OutputValue' \
    --output text)

DEPLOYMENT_BUCKET=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`DeploymentBucketName`].OutputValue' \
    --output text)

# Save configuration
cat > pipeline_config.json <<EOF
{
  "stackName": "$STACK_NAME",
  "pipelineName": "$PIPELINE_NAME",
  "region": "$REGION",
  "environment": "$ENVIRONMENT",
  "githubRepo": "$GITHUB_OWNER/$GITHUB_REPO",
  "githubBranch": "$GITHUB_BRANCH",
  "artifactBucket": "$ARTIFACT_BUCKET",
  "deploymentBucket": "$DEPLOYMENT_BUCKET",
  "pipelineUrl": "$PIPELINE_URL",
  "deploymentTimestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}
EOF

echo ""
echo "=============================================="
echo "Pipeline Deployment Complete!"
echo "=============================================="
echo ""
echo "Pipeline Details:"
echo "  Name: $PIPELINE_NAME"
echo "  URL: $PIPELINE_URL"
echo ""
echo "S3 Buckets:"
echo "  Artifacts: $ARTIFACT_BUCKET"
echo "  Deployments: $DEPLOYMENT_BUCKET"
echo ""
echo "Pipeline Stages:"
echo "  1. Source (GitHub)"
echo "  2. Build (CodeBuild)"
echo "  3. Deploy Development (Auto)"
echo "  4. Approve Staging (Manual)"
echo "  5. Deploy Staging"
echo "  6. Approve Production (Manual)"
echo "  7. Deploy Production"
echo ""
echo "Configuration saved to: pipeline_config.json"
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo "  1. Push code to trigger pipeline"
echo "  2. Monitor pipeline execution in AWS Console"
echo "  3. Approve staging deployment when ready"
echo "  4. Approve production deployment when ready"
echo ""
echo "View Pipeline:"
echo "  $PIPELINE_URL"
echo ""
