#!/bin/bash
# Helper script to run the prototype with AWS SSO credentials

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🏥 Medical Record Analysis System - AWS SSO Launcher${NC}"
echo "================================================================"
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI not found!${NC}"
    echo "Please install AWS CLI: https://aws.amazon.com/cli/"
    exit 1
fi

# Check if a profile is specified
if [ -z "$1" ]; then
    echo -e "${YELLOW}Usage: $0 <aws-profile-name>${NC}"
    echo ""
    echo "Available AWS profiles:"
    aws configure list-profiles 2>/dev/null || echo "  (none found)"
    echo ""
    echo "Example:"
    echo "  $0 default"
    echo "  $0 my-sso-profile"
    exit 1
fi

PROFILE_NAME="$1"

echo -e "${GREEN}📋 Using AWS Profile: ${PROFILE_NAME}${NC}"
echo ""

# Check if SSO session is valid
echo "🔍 Checking AWS SSO session..."
if ! aws sts get-caller-identity --profile "$PROFILE_NAME" &> /dev/null; then
    echo -e "${YELLOW}⚠️  AWS SSO session expired or not logged in${NC}"
    echo "Running: aws sso login --profile $PROFILE_NAME"
    echo ""
    aws sso login --profile "$PROFILE_NAME"
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ AWS SSO login failed${NC}"
        exit 1
    fi
    echo ""
fi

# Verify credentials work
echo "✅ AWS SSO session is valid"
echo ""
echo "🔍 AWS Identity:"
aws sts get-caller-identity --profile "$PROFILE_NAME" 2>/dev/null | grep -E "(UserId|Account|Arn)" || true
echo ""

# Set environment variables for boto3 to use SSO
export AWS_PROFILE="$PROFILE_NAME"
export AWS_SDK_LOAD_CONFIG="1"
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-us-east-1}"

echo -e "${GREEN}🚀 Launching prototype with AWS SSO credentials...${NC}"
echo "================================================================"
echo ""

# Run the prototype
python3 launch_prototype.py -v

exit $?
