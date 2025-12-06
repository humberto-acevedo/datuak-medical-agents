# CloudWatch Logging - Quick Reference

## Log Groups

| Function | Log Group | Retention |
|----------|-----------|-----------|
| XML Parser | `/aws/lambda/MedicalRecordXMLParser` | 30 days |
| Medical Summarization | `/aws/lambda/MedicalSummarization` | 30 days |
| Research Correlation | `/aws/lambda/ResearchCorrelation` | 30 days |
| Master Workflow | `/aws/lambda/MasterWorkflowHandler` | 30 days |

## Quick Commands

### View Real-Time Logs
```bash
# Master Workflow
aws logs tail /aws/lambda/MasterWorkflowHandler --follow

# All functions
aws logs tail /aws/lambda/MedicalRecordXMLParser --follow
aws logs tail /aws/lambda/MedicalSummarization --follow
aws logs tail /aws/lambda/ResearchCorrelation --follow
```

### Search Logs
```bash
# Find errors in last hour
aws logs filter-log-events \
  --log-group-name "/aws/lambda/MasterWorkflowHandler" \
  --filter-pattern "ERROR" \
  --start-time $(date -u -d '1 hour ago' +%s)000

# Find patient processing
aws logs filter-log-events \
  --log-group-name "/aws/lambda/MasterWorkflowHandler" \
  --filter-pattern "patient_id" \
  --start-time $(date -u -d '24 hours ago' +%s)000

# Find Bedrock calls
aws logs filter-log-events \
  --log-group-name "/aws/lambda/MasterWorkflowHandler" \
  --filter-pattern "Bedrock" \
  --start-time $(date -u -d '1 hour ago' +%s)000
```

### CloudWatch Insights Queries

**Error Analysis:**
```
fields @timestamp, @message, @logStream
| filter @message like /ERROR/
| sort @timestamp desc
| limit 100
```

**Performance Analysis:**
```
fields @timestamp, @duration, @billedDuration, @memorySize, @maxMemoryUsed
| filter @type = "REPORT"
| stats avg(@duration), max(@duration), pct(@duration, 95) by bin(5m)
```

**Patient Processing:**
```
fields @timestamp, @message
| filter @message like /patient_id/
| parse @message /patient_id[=:]\s*(?<patientId>[^\s,}]+)/
| stats count() by patientId
| sort count desc
```

**Bedrock Workflow:**
```
fields @timestamp, @message
| filter @message like /Bedrock/ or @message like /workflow/
| sort @timestamp desc
| limit 100
```

## Setup Commands

```bash
# Deploy monitoring
cd deployment/monitoring
./setup_monitoring.sh production

# Check Bedrock logs
./check_bedrock_logs.sh us-east-1
```

## Console Links

- **Logs:** https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:log-groups
- **Insights:** https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:logs-insights
- **Dashboard:** https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=MedicalRecordAnalysis-production

## What's Logged

### All Functions
- ✅ Request ID
- ✅ Patient identifiers
- ✅ Processing steps
- ✅ Success/error responses
- ✅ Exception stack traces

### Bedrock-Specific
- ✅ Model invocations
- ✅ Token usage
- ✅ Response lengths
- ✅ Model IDs
- ✅ Processing duration

### HIPAA Audit
- ✅ Patient access
- ✅ Data operations
- ✅ User actions
- ✅ Timestamps
- ✅ Error conditions

## Troubleshooting

**No logs appearing:**
1. Check function is deployed
2. Verify function has been invoked
3. Check IAM permissions for CloudWatch
4. Verify log group exists

**Retention not set:**
1. Re-run `setup_monitoring.sh`
2. Check IAM permissions
3. Manually set in Console

**Insights query fails:**
1. Verify log groups exist
2. Check query syntax
3. Ensure logs contain expected patterns
