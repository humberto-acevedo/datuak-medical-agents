#!/bin/bash
# Setup Monitoring and Logging for Medical Record Analysis System

set -e

# Configuration
REGION="us-east-1"
ENVIRONMENT="${1:-production}"
STACK_NAME="medical-record-analysis-monitoring"
SNS_TOPIC_NAME="medical-record-analysis-alerts"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=============================================="
echo "Medical Record Analysis - Monitoring Setup"
echo "=============================================="
echo ""
echo "Environment: $ENVIRONMENT"
echo "Region: $REGION"
echo ""

# Check prerequisites
echo "Checking prerequisites..."
if ! command -v aws &> /dev/null; then
    echo -e "${RED}Error: AWS CLI is not installed${NC}"
    exit 1
fi

if ! command -v jq &> /dev/null; then
    echo -e "${YELLOW}Warning: jq is not installed. Some features may not work.${NC}"
fi

echo -e "${GREEN}✓ Prerequisites check passed${NC}"
echo ""

# Verify AWS credentials
echo "Verifying AWS credentials..."
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo -e "${GREEN}✓ AWS Account: $ACCOUNT_ID${NC}"
echo ""

# Create SNS Topic for Alerts
echo "Creating SNS topic for alerts..."
SNS_TOPIC_ARN=$(aws sns create-topic \
    --name $SNS_TOPIC_NAME \
    --region $REGION \
    --tags Key=Application,Value=MedicalRecordAnalysis Key=Environment,Value=$ENVIRONMENT \
    --query 'TopicArn' \
    --output text 2>/dev/null || \
    aws sns list-topics --region $REGION --query "Topics[?contains(TopicArn, '$SNS_TOPIC_NAME')].TopicArn" --output text)

echo -e "${GREEN}✓ SNS Topic: $SNS_TOPIC_ARN${NC}"
echo ""

# Subscribe email to SNS topic (optional)
read -p "Enter email address for alerts (or press Enter to skip): " EMAIL_ADDRESS
if [ ! -z "$EMAIL_ADDRESS" ]; then
    echo "Subscribing $EMAIL_ADDRESS to alerts..."
    aws sns subscribe \
        --topic-arn $SNS_TOPIC_ARN \
        --protocol email \
        --notification-endpoint $EMAIL_ADDRESS \
        --region $REGION
    echo -e "${YELLOW}⚠ Please check your email and confirm the subscription${NC}"
fi
echo ""

# Deploy CloudWatch Alarms
echo "Deploying CloudWatch alarms..."
aws cloudformation deploy \
    --template-file cloudwatch_alarms.yaml \
    --stack-name $STACK_NAME \
    --parameter-overrides \
        SNSTopicArn=$SNS_TOPIC_ARN \
        Environment=$ENVIRONMENT \
    --region $REGION \
    --no-fail-on-empty-changeset \
    --tags \
        Application=MedicalRecordAnalysis \
        Environment=$ENVIRONMENT

echo -e "${GREEN}✓ CloudWatch alarms deployed${NC}"
echo ""

# Create CloudWatch Dashboard
echo "Creating CloudWatch dashboard..."
DASHBOARD_BODY=$(cat cloudwatch_dashboard.json | jq -c '.dashboardBody')
aws cloudwatch put-dashboard \
    --dashboard-name "MedicalRecordAnalysis-${ENVIRONMENT}" \
    --dashboard-body "$DASHBOARD_BODY" \
    --region $REGION

echo -e "${GREEN}✓ CloudWatch dashboard created${NC}"
echo ""

# Enable CloudTrail for audit logging
echo "Checking CloudTrail configuration..."
TRAIL_NAME="medical-record-analysis-audit-trail"
TRAIL_BUCKET="medical-record-analysis-cloudtrail-${ACCOUNT_ID}"

# Create S3 bucket for CloudTrail
if ! aws s3 ls "s3://$TRAIL_BUCKET" 2>&1 > /dev/null; then
    echo "Creating CloudTrail S3 bucket..."
    aws s3 mb "s3://$TRAIL_BUCKET" --region $REGION
    
    # Apply bucket policy for CloudTrail
    cat > /tmp/cloudtrail-bucket-policy.json <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AWSCloudTrailAclCheck",
            "Effect": "Allow",
            "Principal": {
                "Service": "cloudtrail.amazonaws.com"
            },
            "Action": "s3:GetBucketAcl",
            "Resource": "arn:aws:s3:::$TRAIL_BUCKET"
        },
        {
            "Sid": "AWSCloudTrailWrite",
            "Effect": "Allow",
            "Principal": {
                "Service": "cloudtrail.amazonaws.com"
            },
            "Action": "s3:PutObject",
            "Resource": "arn:aws:s3:::$TRAIL_BUCKET/AWSLogs/${ACCOUNT_ID}/*",
            "Condition": {
                "StringEquals": {
                    "s3:x-amz-acl": "bucket-owner-full-control"
                }
            }
        }
    ]
}
EOF
    
    aws s3api put-bucket-policy \
        --bucket $TRAIL_BUCKET \
        --policy file:///tmp/cloudtrail-bucket-policy.json
    
    # Enable encryption
    aws s3api put-bucket-encryption \
        --bucket $TRAIL_BUCKET \
        --server-side-encryption-configuration '{
            "Rules": [{
                "ApplyServerSideEncryptionByDefault": {
                    "SSEAlgorithm": "AES256"
                }
            }]
        }'
    
    echo -e "${GREEN}✓ CloudTrail S3 bucket created${NC}"
else
    echo -e "${GREEN}✓ CloudTrail S3 bucket exists${NC}"
fi

# Create or update CloudTrail
if ! aws cloudtrail describe-trails --region $REGION --query "trailList[?Name=='$TRAIL_NAME']" --output text | grep -q "$TRAIL_NAME"; then
    echo "Creating CloudTrail..."
    aws cloudtrail create-trail \
        --name $TRAIL_NAME \
        --s3-bucket-name $TRAIL_BUCKET \
        --is-multi-region-trail \
        --enable-log-file-validation \
        --region $REGION \
        --tags-list Key=Application,Value=MedicalRecordAnalysis Key=Compliance,Value=HIPAA
    
    aws cloudtrail start-logging \
        --name $TRAIL_NAME \
        --region $REGION
    
    echo -e "${GREEN}✓ CloudTrail created and started${NC}"
else
    echo -e "${GREEN}✓ CloudTrail already exists${NC}"
fi
echo ""

# Configure CloudWatch Logs retention
echo "Configuring CloudWatch Logs retention..."
LOG_GROUPS=(
    "/aws/lambda/MedicalRecordXMLParser"
    "/aws/lambda/MedicalSummarization"
    "/aws/lambda/ResearchCorrelation"
    "/aws/lambda/MasterWorkflowHandler"
)

for LOG_GROUP in "${LOG_GROUPS[@]}"; do
    if aws logs describe-log-groups --log-group-name-prefix "$LOG_GROUP" --region $REGION | grep -q "$LOG_GROUP"; then
        aws logs put-retention-policy \
            --log-group-name "$LOG_GROUP" \
            --retention-in-days 30 \
            --region $REGION 2>/dev/null || true
        echo -e "${GREEN}✓ Set retention for $LOG_GROUP${NC}"
    fi
done
echo ""

# Create custom metrics namespace
echo "Creating custom metrics namespace..."
aws cloudwatch put-metric-data \
    --namespace MedicalRecordAnalysis \
    --metric-name SystemInitialized \
    --value 1 \
    --region $REGION \
    --dimensions Environment=$ENVIRONMENT

echo -e "${GREEN}✓ Custom metrics namespace created${NC}"
echo ""

# Create CloudWatch Insights queries
echo "Creating CloudWatch Insights saved queries..."

# Error analysis query
aws logs put-query-definition \
    --name "MedicalRecord-ErrorAnalysis" \
    --query-string "fields @timestamp, @message, @logStream
| filter @message like /ERROR/
| sort @timestamp desc
| limit 100" \
    --log-group-names \
        "/aws/lambda/MedicalRecordXMLParser" \
        "/aws/lambda/MedicalSummarization" \
        "/aws/lambda/ResearchCorrelation" \
        "/aws/lambda/MasterWorkflowHandler" \
    --region $REGION 2>/dev/null || true

# Performance analysis query
aws logs put-query-definition \
    --name "MedicalRecord-PerformanceAnalysis" \
    --query-string "fields @timestamp, @duration, @billedDuration, @memorySize, @maxMemoryUsed
| filter @type = \"REPORT\"
| stats avg(@duration), max(@duration), pct(@duration, 95) by bin(5m)" \
    --log-group-names \
        "/aws/lambda/MedicalRecordXMLParser" \
        "/aws/lambda/MedicalSummarization" \
        "/aws/lambda/ResearchCorrelation" \
        "/aws/lambda/MasterWorkflowHandler" \
    --region $REGION 2>/dev/null || true

# Patient processing query
aws logs put-query-definition \
    --name "MedicalRecord-PatientProcessing" \
    --query-string "fields @timestamp, @message
| filter @message like /patient_id/
| parse @message /patient_id[=:]\\s*(?<patientId>[^\\s,}]+)/
| stats count() by patientId
| sort count desc" \
    --log-group-names \
        "/aws/lambda/MedicalRecordXMLParser" \
        "/aws/lambda/MedicalSummarization" \
        "/aws/lambda/ResearchCorrelation" \
        "/aws/lambda/MasterWorkflowHandler" \
    --region $REGION 2>/dev/null || true

# Bedrock workflow query
aws logs put-query-definition \
    --name "MedicalRecord-BedrockWorkflow" \
    --query-string "fields @timestamp, @message
| filter @message like /Bedrock/ or @message like /workflow/
| sort @timestamp desc
| limit 100" \
    --log-group-names \
        "/aws/lambda/MasterWorkflowHandler" \
    --region $REGION 2>/dev/null || true

echo -e "${GREEN}✓ CloudWatch Insights queries created${NC}"
echo ""

# Save configuration
cat > monitoring_config.json <<EOF
{
  "environment": "$ENVIRONMENT",
  "region": "$REGION",
  "snsTopicArn": "$SNS_TOPIC_ARN",
  "cloudTrailName": "$TRAIL_NAME",
  "cloudTrailBucket": "$TRAIL_BUCKET",
  "dashboardName": "MedicalRecordAnalysis-${ENVIRONMENT}",
  "alarmStackName": "$STACK_NAME",
  "setupTimestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}
EOF

echo ""
echo "=============================================="
echo "Monitoring Setup Complete!"
echo "=============================================="
echo ""
echo "Resources Created:"
echo "  ✓ SNS Topic: $SNS_TOPIC_ARN"
echo "  ✓ CloudWatch Dashboard: MedicalRecordAnalysis-${ENVIRONMENT}"
echo "  ✓ CloudWatch Alarms: $STACK_NAME"
echo "  ✓ CloudTrail: $TRAIL_NAME"
echo "  ✓ CloudWatch Logs Retention: 30 days"
echo "  ✓ CloudWatch Insights Queries: 4 saved queries"
echo ""
echo "View Dashboard:"
echo "  https://console.aws.amazon.com/cloudwatch/home?region=$REGION#dashboards:name=MedicalRecordAnalysis-${ENVIRONMENT}"
echo ""
echo "View Alarms:"
echo "  https://console.aws.amazon.com/cloudwatch/home?region=$REGION#alarmsV2:"
echo ""
echo "View Logs:"
echo "  https://console.aws.amazon.com/cloudwatch/home?region=$REGION#logsV2:log-groups"
echo ""
echo "Configuration saved to: monitoring_config.json"
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo "  1. Confirm SNS email subscription (if provided)"
echo "  2. Review CloudWatch dashboard"
echo "  3. Test alarms with sample errors"
echo "  4. Configure additional alert recipients"
echo "  5. Set up PagerDuty/Slack integration (optional)"
echo ""
