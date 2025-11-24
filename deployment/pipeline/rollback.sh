#!/bin/bash
# Rollback script for Medical Record Analysis System

set -e

# Configuration
REGION="us-east-1"
ENVIRONMENT="${1:-production}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=============================================="
echo "Medical Record Analysis - Rollback"
echo "=============================================="
echo ""
echo "Environment: $ENVIRONMENT"
echo "Region: $REGION"
echo ""

# Verify AWS credentials
echo "Verifying AWS credentials..."
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo -e "${GREEN}✓ AWS Account: $ACCOUNT_ID${NC}"
echo ""

# Stack name
STACK_NAME="medical-record-analysis-lambda-${ENVIRONMENT}"

# Check if stack exists
if ! aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION &> /dev/null; then
    echo -e "${RED}Error: Stack $STACK_NAME does not exist${NC}"
    exit 1
fi

# Get current stack status
CURRENT_STATUS=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].StackStatus' \
    --output text)

echo "Current stack status: $CURRENT_STATUS"
echo ""

# List recent stack events
echo "Recent stack events:"
aws cloudformation describe-stack-events \
    --stack-name $STACK_NAME \
    --region $REGION \
    --max-items 10 \
    --query 'StackEvents[*].[Timestamp,ResourceStatus,ResourceType,LogicalResourceId]' \
    --output table

echo ""

# Get stack change sets
echo "Available change sets:"
CHANGE_SETS=$(aws cloudformation list-change-sets \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Summaries[*].[ChangeSetName,Status,CreationTime]' \
    --output table)

if [ -z "$CHANGE_SETS" ]; then
    echo "No change sets available"
else
    echo "$CHANGE_SETS"
fi

echo ""

# Rollback options
echo "Rollback Options:"
echo "  1. Rollback to previous version (CloudFormation rollback)"
echo "  2. Rollback to specific Lambda version"
echo "  3. Cancel current update"
echo "  4. Exit"
echo ""

read -p "Select option (1-4): " OPTION

case $OPTION in
    1)
        echo ""
        echo -e "${YELLOW}Warning: This will rollback the entire stack to the previous version${NC}"
        read -p "Are you sure? (yes/no): " CONFIRM
        
        if [ "$CONFIRM" != "yes" ]; then
            echo "Rollback cancelled"
            exit 0
        fi
        
        echo "Initiating stack rollback..."
        aws cloudformation rollback-stack \
            --stack-name $STACK_NAME \
            --region $REGION
        
        echo "Waiting for rollback to complete..."
        aws cloudformation wait stack-rollback-complete \
            --stack-name $STACK_NAME \
            --region $REGION
        
        echo -e "${GREEN}✓ Stack rollback completed${NC}"
        ;;
    
    2)
        echo ""
        echo "Lambda Functions:"
        FUNCTIONS=(
            "MedicalRecordXMLParser"
            "MedicalSummarization"
            "ResearchCorrelation"
        )
        
        for i in "${!FUNCTIONS[@]}"; do
            echo "  $((i+1)). ${FUNCTIONS[$i]}"
        done
        
        echo ""
        read -p "Select function (1-3): " FUNC_INDEX
        FUNC_INDEX=$((FUNC_INDEX-1))
        
        if [ $FUNC_INDEX -lt 0 ] || [ $FUNC_INDEX -ge ${#FUNCTIONS[@]} ]; then
            echo -e "${RED}Invalid selection${NC}"
            exit 1
        fi
        
        FUNCTION_NAME="${FUNCTIONS[$FUNC_INDEX]}"
        
        echo ""
        echo "Available versions for $FUNCTION_NAME:"
        aws lambda list-versions-by-function \
            --function-name $FUNCTION_NAME \
            --region $REGION \
            --query 'Versions[*].[Version,LastModified,Description]' \
            --output table
        
        echo ""
        read -p "Enter version number to rollback to: " VERSION
        
        echo ""
        echo -e "${YELLOW}Warning: This will update the function alias to point to version $VERSION${NC}"
        read -p "Are you sure? (yes/no): " CONFIRM
        
        if [ "$CONFIRM" != "yes" ]; then
            echo "Rollback cancelled"
            exit 0
        fi
        
        echo "Rolling back $FUNCTION_NAME to version $VERSION..."
        
        # Update production alias
        aws lambda update-alias \
            --function-name $FUNCTION_NAME \
            --name production \
            --function-version $VERSION \
            --region $REGION
        
        echo -e "${GREEN}✓ Function rolled back to version $VERSION${NC}"
        ;;
    
    3)
        echo ""
        echo -e "${YELLOW}Warning: This will cancel the current stack update${NC}"
        read -p "Are you sure? (yes/no): " CONFIRM
        
        if [ "$CONFIRM" != "yes" ]; then
            echo "Operation cancelled"
            exit 0
        fi
        
        echo "Cancelling stack update..."
        aws cloudformation cancel-update-stack \
            --stack-name $STACK_NAME \
            --region $REGION
        
        echo -e "${GREEN}✓ Stack update cancelled${NC}"
        ;;
    
    4)
        echo "Exiting..."
        exit 0
        ;;
    
    *)
        echo -e "${RED}Invalid option${NC}"
        exit 1
        ;;
esac

echo ""
echo "=============================================="
echo "Rollback Complete!"
echo "=============================================="
echo ""
echo "Current Stack Status:"
aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].[StackName,StackStatus,LastUpdatedTime]' \
    --output table

echo ""
echo "Verify the rollback:"
echo "  1. Check CloudWatch Logs for errors"
echo "  2. Test Lambda functions"
echo "  3. Monitor CloudWatch metrics"
echo "  4. Review CloudTrail logs"
echo ""
echo "If issues persist:"
echo "  - Review CloudFormation events"
echo "  - Check Lambda function logs"
echo "  - Contact AWS Support if needed"
echo ""
