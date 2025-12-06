#!/bin/bash
# Check for Bedrock Agent CloudWatch Log Groups

set -e

REGION="${1:-us-east-1}"

echo "=============================================="
echo "Bedrock Agent Log Group Discovery"
echo "=============================================="
echo ""
echo "Region: $REGION"
echo ""

# Check for Bedrock Agent log groups
echo "Searching for Bedrock Agent log groups..."
echo ""

# Common patterns for Bedrock Agent logs
PATTERNS=(
    "/aws/bedrock"
    "/aws/bedrock-agent"
    "/aws/vendedlogs/bedrock"
    "bedrock"
    "BedrockAgent"
)

FOUND_GROUPS=()

for PATTERN in "${PATTERNS[@]}"; do
    echo "Checking pattern: $PATTERN"
    
    GROUPS=$(aws logs describe-log-groups \
        --region $REGION \
        --query "logGroups[?contains(logGroupName, '$PATTERN')].logGroupName" \
        --output text 2>/dev/null || echo "")
    
    if [ ! -z "$GROUPS" ]; then
        echo "  ✓ Found log groups:"
        for GROUP in $GROUPS; do
            echo "    - $GROUP"
            FOUND_GROUPS+=("$GROUP")
        done
    else
        echo "  - No log groups found"
    fi
    echo ""
done

# Check for Lambda log groups related to Bedrock
echo "Checking Lambda log groups..."
LAMBDA_GROUPS=$(aws logs describe-log-groups \
    --region $REGION \
    --log-group-name-prefix "/aws/lambda/" \
    --query "logGroups[].logGroupName" \
    --output text 2>/dev/null || echo "")

echo "Lambda log groups found:"
for GROUP in $LAMBDA_GROUPS; do
    echo "  - $GROUP"
done
echo ""

# Check if Master Workflow Lambda exists
if echo "$LAMBDA_GROUPS" | grep -q "MasterWorkflow"; then
    echo "✓ Master Workflow Lambda log group exists"
else
    echo "⚠ Master Workflow Lambda log group NOT found"
    echo "  Expected: /aws/lambda/MasterWorkflowHandler"
fi
echo ""

# Summary
echo "=============================================="
echo "Summary"
echo "=============================================="
echo ""

if [ ${#FOUND_GROUPS[@]} -gt 0 ]; then
    echo "Bedrock-related log groups found: ${#FOUND_GROUPS[@]}"
    for GROUP in "${FOUND_GROUPS[@]}"; do
        echo "  - $GROUP"
    done
    echo ""
    echo "Action Required:"
    echo "  1. Add these log groups to monitoring setup"
    echo "  2. Set 30-day retention policy"
    echo "  3. Include in CloudWatch Insights queries"
else
    echo "No Bedrock-specific log groups found."
    echo ""
    echo "This is expected if:"
    echo "  - Bedrock Agents log to Lambda function log groups"
    echo "  - Bedrock Agent has not been invoked yet"
    echo "  - Bedrock Agent logging is not enabled"
fi
echo ""

# Check Bedrock Agent configuration
echo "Checking Bedrock Agent configuration..."
AGENTS=$(aws bedrock-agent list-agents \
    --region $REGION \
    --query "agentSummaries[].agentId" \
    --output text 2>/dev/null || echo "")

if [ ! -z "$AGENTS" ]; then
    echo "Bedrock Agents found:"
    for AGENT_ID in $AGENTS; do
        echo "  - Agent ID: $AGENT_ID"
        
        # Get agent details
        AGENT_NAME=$(aws bedrock-agent get-agent \
            --agent-id $AGENT_ID \
            --region $REGION \
            --query "agent.agentName" \
            --output text 2>/dev/null || echo "Unknown")
        
        echo "    Name: $AGENT_NAME"
        
        # Check if agent has CloudWatch logging enabled
        # Note: This may not be available in all regions/versions
    done
else
    echo "No Bedrock Agents found in region $REGION"
fi
echo ""

echo "=============================================="
echo "Recommendations"
echo "=============================================="
echo ""
echo "1. Ensure Master Workflow Lambda is deployed"
echo "2. Invoke Bedrock Agent to generate logs"
echo "3. Re-run this script after invocation"
echo "4. Update monitoring setup with any new log groups"
echo ""
