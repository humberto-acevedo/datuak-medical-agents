# Monitoring Quick Start Guide

## 5-Minute Setup

```bash
cd deployment/monitoring
./setup_monitoring.sh production
```

Enter your email when prompted to receive alerts.

## What You Get

### Real-Time Dashboard
- Lambda performance metrics
- Error rates and trends
- API Gateway statistics
- S3 storage metrics
- Live log analysis

**Access**: [CloudWatch Dashboard](https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:)

### Proactive Alerts
- 15 CloudWatch alarms
- Email/SMS notifications
- Composite system health alarm
- Custom business metrics

### Audit Logging
- CloudTrail for all API calls
- 30-day log retention
- HIPAA-compliant audit trail
- Log file validation

### Log Analysis
- 10 pre-built Insights queries
- Error pattern analysis
- Performance monitoring
- Patient processing tracking

## Daily Monitoring Checklist

- [ ] Check dashboard for anomalies
- [ ] Review any triggered alarms
- [ ] Scan error logs
- [ ] Verify processing volumes

## Key Metrics to Watch

| Metric | Healthy Range | Action Threshold |
|--------|---------------|------------------|
| Error Rate | <1% | >5 errors/5min |
| Latency | <2s | >5s |
| Duration | <30s | >270s |
| Data Quality | >0.7 | <0.5 |

## Common Queries

### View Recent Errors
```bash
aws logs tail /aws/lambda/MedicalRecordXMLParser --follow --filter-pattern "ERROR"
```

### Check Processing Stats
```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=MedicalRecordXMLParser \
  --start-time $(date -u -d '1 hour ago' --iso-8601=seconds) \
  --end-time $(date -u --iso-8601=seconds) \
  --period 300 \
  --statistics Sum
```

### Generate Audit Report
```bash
aws logs filter-log-events \
  --log-group-name "/aws/lambda/MedicalRecordXMLParser" \
  --filter-pattern "patient_id" \
  --start-time $(date -u -d '7 days ago' +%s)000 \
  > weekly_audit_report.json
```

## Alarm Response

When you receive an alert:

1. **Check Dashboard** - Get overall system context
2. **Review Logs** - Find specific error messages
3. **Check CloudTrail** - Look for unusual activity
4. **Investigate** - Determine root cause
5. **Fix** - Implement solution
6. **Document** - Record incident and resolution

## HIPAA Compliance

✅ All patient data access is logged  
✅ Logs retained for 30 days minimum  
✅ Audit trail with file validation  
✅ Encrypted logs at rest  
✅ Real-time anomaly detection

## Cost Estimate

**Monthly**: $20-50 for typical production workload

- CloudWatch Logs: ~$10
- CloudWatch Metrics: ~$5
- CloudWatch Alarms: ~$2
- CloudWatch Dashboards: ~$3
- CloudTrail: ~$5

## Troubleshooting

### Dashboard shows no data
→ Verify Lambda functions are deployed and invoked

### Alarms not triggering
→ Check SNS subscription is confirmed

### Missing logs
→ Verify Lambda execution role has CloudWatch permissions

### High costs
→ Reduce log retention or use log filtering

## Support

- **Documentation**: See README.md for detailed information
- **AWS Support**: Contact AWS support for infrastructure issues
- **Logs**: Check CloudWatch Logs for error details
- **Metrics**: Monitor CloudWatch metrics for trends

## Next Steps

1. ✅ Monitoring setup complete
2. ⏭️ Confirm SNS email subscription
3. ⏭️ Review dashboard and familiarize yourself
4. ⏭️ Test alarms with sample errors
5. ⏭️ Set up CI/CD pipeline (Task 14)
