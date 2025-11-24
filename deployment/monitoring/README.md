# Production Monitoring and Logging

This directory contains monitoring and logging configurations for the Medical Record Analysis System.

## Overview

Comprehensive monitoring solution with:
- CloudWatch Dashboards for real-time visibility
- CloudWatch Alarms for proactive alerting
- CloudWatch Logs with structured logging
- CloudWatch Insights for log analysis
- CloudTrail for HIPAA-compliant audit logging
- Custom metrics for business KPIs

## Quick Setup

```bash
# Run automated setup
./setup_monitoring.sh production

# Or for staging
./setup_monitoring.sh staging
```

This creates all monitoring resources in ~5 minutes.

## Components

### 1. CloudWatch Dashboard

**File**: `cloudwatch_dashboard.json`

**Widgets**:
- Lambda invocations (all functions)
- Lambda errors with threshold annotations
- Lambda duration (avg and p99)
- Concurrent executions
- API Gateway requests and errors
- API Gateway latency
- S3 storage metrics
- Recent errors log widget
- Patient processing rate
- Function duration statistics
- Lambda throttles
- CloudWatch Logs volume

**Access**:
```bash
# View dashboard
open "https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=MedicalRecordAnalysis-production"
```

### 2. CloudWatch Alarms

**File**: `cloudwatch_alarms.yaml`

**Alarms Created**:

#### Lambda Error Alarms
- `XMLParser-HighErrorRate` - >10 errors in 5 minutes
- `MedicalSummarization-HighErrorRate` - >10 errors in 5 minutes
- `ResearchCorrelation-HighErrorRate` - >10 errors in 5 minutes

#### Lambda Duration Alarms
- `XMLParser-HighDuration` - Avg duration >270s (90% of timeout)
- `MedicalSummarization-HighDuration` - Avg duration >270s
- `ResearchCorrelation-HighDuration` - Avg duration >270s

#### Lambda Throttle Alarms
- `XMLParser-Throttles` - >5 throttles in 5 minutes
- `MedicalSummarization-Throttles` - >5 throttles in 5 minutes
- `ResearchCorrelation-Throttles` - >5 throttles in 5 minutes

#### API Gateway Alarms
- `APIGateway-HighErrorRate` - >10 5XX errors in 5 minutes
- `APIGateway-HighLatency` - Avg latency >5 seconds

#### Custom Metric Alarms
- `HighPatientProcessingFailureRate` - >5 failures in 5 minutes
- `LowDataQualityScore` - Avg quality score <0.5

#### Composite Alarm
- `SystemHealth-Critical` - Triggers if any critical alarm fires

**SNS Integration**:
All alarms send notifications to SNS topic for email/SMS/PagerDuty integration.

### 3. CloudWatch Logs

**Log Groups**:
- `/aws/lambda/MedicalRecordXMLParser`
- `/aws/lambda/MedicalSummarization`
- `/aws/lambda/ResearchCorrelation`

**Configuration**:
- Retention: 30 days (HIPAA compliance)
- Encryption: Enabled
- Log format: JSON structured logging

**Log Levels**:
- ERROR: Critical errors requiring immediate attention
- WARNING: Issues that don't stop processing
- INFO: Normal operational messages
- DEBUG: Detailed diagnostic information

### 4. CloudWatch Insights Queries

**File**: `cloudwatch_insights_queries.json`

**Saved Queries**:

1. **ErrorAnalysis** - Analyze all errors with error types and patient IDs
2. **PerformanceAnalysis** - Duration, memory usage, percentiles
3. **PatientProcessing** - Track patient record processing success/failure
4. **AuditTrail** - HIPAA audit trail for data access
5. **DataQualityMetrics** - Monitor data quality scores over time
6. **ResearchCorrelation** - Track research paper correlation metrics
7. **S3Operations** - Monitor S3 access patterns
8. **ColdStarts** - Identify Lambda cold starts
9. **TimeoutWarnings** - Functions approaching timeout
10. **MemoryUsage** - Analyze memory usage patterns

**Usage**:
```bash
# Run a query
aws logs start-query \
  --log-group-names "/aws/lambda/MedicalRecordXMLParser" \
  --start-time $(date -u -d '1 hour ago' +%s) \
  --end-time $(date -u +%s) \
  --query-string "fields @timestamp, @message | filter @message like /ERROR/ | limit 20"
```

### 5. CloudTrail Audit Logging

**Trail Name**: `medical-record-analysis-audit-trail`

**Configuration**:
- Multi-region trail
- Log file validation enabled
- S3 bucket encryption enabled
- Logs all API calls for HIPAA compliance

**Events Logged**:
- Lambda invocations
- S3 object access
- IAM role assumptions
- API Gateway requests
- CloudWatch operations

**Access Logs**:
```bash
# Query CloudTrail logs
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceName,AttributeValue=MedicalRecordXMLParser \
  --max-results 10
```

## Monitoring Best Practices

### 1. Dashboard Review

Review dashboard daily:
- Check error rates
- Monitor latency trends
- Verify processing volumes
- Review resource utilization

### 2. Alarm Response

When alarms trigger:
1. Check CloudWatch dashboard for context
2. Review CloudWatch Logs for errors
3. Check CloudTrail for unusual activity
4. Investigate root cause
5. Implement fix
6. Document incident

### 3. Log Analysis

Regular log analysis:
- Weekly error pattern review
- Monthly performance analysis
- Quarterly audit trail review
- Annual compliance audit

### 4. Capacity Planning

Monitor trends for:
- Request volume growth
- Processing duration increases
- Memory usage patterns
- Storage growth

## HIPAA Compliance

### Audit Requirements

The monitoring system meets HIPAA requirements:

✅ **Access Logging**: CloudTrail logs all data access  
✅ **Audit Trail**: 30-day log retention minimum  
✅ **Encryption**: All logs encrypted at rest  
✅ **Integrity**: CloudTrail log file validation  
✅ **Monitoring**: Real-time alerting on anomalies  
✅ **Reporting**: Audit reports available on demand

### Audit Reports

Generate audit reports:

```bash
# Patient access report
aws logs filter-log-events \
  --log-group-name "/aws/lambda/MedicalRecordXMLParser" \
  --filter-pattern "patient_id" \
  --start-time $(date -u -d '30 days ago' +%s)000 \
  --end-time $(date -u +%s)000 \
  > patient_access_report.json

# Error report
aws logs filter-log-events \
  --log-group-name "/aws/lambda/MedicalRecordXMLParser" \
  --filter-pattern "ERROR" \
  --start-time $(date -u -d '30 days ago' +%s)000 \
  --end-time $(date -u +%s)000 \
  > error_report.json
```

## Custom Metrics

### Publishing Custom Metrics

```python
import boto3

cloudwatch = boto3.client('cloudwatch', region_name='us-east-1')

# Publish patient processing metric
cloudwatch.put_metric_data(
    Namespace='MedicalRecordAnalysis',
    MetricData=[
        {
            'MetricName': 'PatientProcessingSuccess',
            'Value': 1,
            'Unit': 'Count',
            'Dimensions': [
                {'Name': 'Environment', 'Value': 'production'},
                {'Name': 'Function', 'Value': 'XMLParser'}
            ]
        }
    ]
)

# Publish data quality metric
cloudwatch.put_metric_data(
    Namespace='MedicalRecordAnalysis',
    MetricData=[
        {
            'MetricName': 'DataQualityScore',
            'Value': 0.85,
            'Unit': 'None',
            'Dimensions': [
                {'Name': 'Environment', 'Value': 'production'},
                {'Name': 'PatientId', 'Value': 'P001'}
            ]
        }
    ]
)
```

### Available Custom Metrics

- `PatientProcessingSuccess` - Successful patient record processing
- `PatientProcessingFailures` - Failed patient record processing
- `DataQualityScore` - Average data quality score
- `ResearchPapersFound` - Number of research papers found
- `ConditionsIdentified` - Number of conditions identified
- `ProcessingDuration` - End-to-end processing duration

## Alerting Integrations

### Email Alerts

Configured during setup:
```bash
./setup_monitoring.sh production
# Enter email when prompted
```

### Slack Integration

Add Slack webhook to SNS:
```bash
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:ACCOUNT_ID:medical-record-analysis-alerts \
  --protocol https \
  --notification-endpoint https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

### PagerDuty Integration

Add PagerDuty email to SNS:
```bash
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:ACCOUNT_ID:medical-record-analysis-alerts \
  --protocol email \
  --notification-endpoint your-service@your-account.pagerduty.com
```

## Troubleshooting

### No Data in Dashboard

**Issue**: Dashboard shows no data

**Solutions**:
1. Verify Lambda functions are deployed
2. Check Lambda functions have been invoked
3. Verify CloudWatch Logs are being created
4. Check IAM permissions for CloudWatch

### Alarms Not Triggering

**Issue**: Alarms don't trigger when expected

**Solutions**:
1. Verify alarm thresholds are appropriate
2. Check alarm state in CloudWatch console
3. Verify SNS topic subscription is confirmed
4. Check alarm evaluation periods

### Missing Logs

**Issue**: Logs not appearing in CloudWatch

**Solutions**:
1. Verify Lambda execution role has CloudWatch Logs permissions
2. Check log group exists
3. Verify log retention policy
4. Check Lambda function is actually executing

### High Costs

**Issue**: CloudWatch costs are high

**Solutions**:
1. Reduce log retention period
2. Filter logs before ingestion
3. Use log sampling for high-volume logs
4. Archive old logs to S3
5. Review custom metric usage

## Cost Optimization

### Estimated Monthly Costs

- CloudWatch Logs: $0.50/GB ingested
- CloudWatch Metrics: $0.30 per custom metric
- CloudWatch Alarms: $0.10 per alarm
- CloudWatch Dashboards: $3.00 per dashboard
- CloudTrail: $2.00 per 100,000 events

**Typical Monthly Cost**: $20-50 for production workload

### Cost Reduction Tips

1. **Log Filtering**: Filter verbose logs before ingestion
2. **Metric Aggregation**: Aggregate metrics before publishing
3. **Alarm Consolidation**: Use composite alarms
4. **Dashboard Optimization**: Remove unused widgets
5. **Log Archival**: Archive old logs to S3 Glacier

## Maintenance

### Weekly Tasks

- [ ] Review error trends
- [ ] Check alarm history
- [ ] Verify backup logs
- [ ] Review performance metrics

### Monthly Tasks

- [ ] Analyze cost trends
- [ ] Review and update alarms
- [ ] Optimize dashboard widgets
- [ ] Generate compliance reports
- [ ] Review capacity planning

### Quarterly Tasks

- [ ] Comprehensive audit review
- [ ] Update monitoring documentation
- [ ] Review and update alert thresholds
- [ ] Capacity planning review
- [ ] Disaster recovery testing

## Support

### Viewing Logs

```bash
# Real-time logs
aws logs tail /aws/lambda/MedicalRecordXMLParser --follow

# Recent errors
aws logs filter-log-events \
  --log-group-name "/aws/lambda/MedicalRecordXMLParser" \
  --filter-pattern "ERROR" \
  --max-items 20
```

### Querying Metrics

```bash
# Get metric statistics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=MedicalRecordXMLParser \
  --start-time $(date -u -d '1 hour ago' --iso-8601=seconds) \
  --end-time $(date -u --iso-8601=seconds) \
  --period 300 \
  --statistics Sum
```

### Alarm Management

```bash
# List alarms
aws cloudwatch describe-alarms \
  --alarm-name-prefix "MedicalRecord"

# Disable alarm
aws cloudwatch disable-alarm-actions \
  --alarm-names "MedicalRecord-production-XMLParser-HighErrorRate"

# Enable alarm
aws cloudwatch enable-alarm-actions \
  --alarm-names "MedicalRecord-production-XMLParser-HighErrorRate"
```

## Next Steps

After setting up monitoring:

1. ✅ Monitoring infrastructure deployed
2. ⏭️ Configure alert recipients
3. ⏭️ Test alarms with sample errors
4. ⏭️ Create runbooks for common issues
5. ⏭️ Set up CI/CD pipeline (Task 14)

## Resources

- [CloudWatch Documentation](https://docs.aws.amazon.com/cloudwatch/)
- [CloudWatch Logs Insights](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AnalyzingLogData.html)
- [CloudTrail Documentation](https://docs.aws.amazon.com/cloudtrail/)
- [HIPAA Compliance Guide](https://aws.amazon.com/compliance/hipaa-compliance/)
