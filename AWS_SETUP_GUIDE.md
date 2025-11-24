# AWS Setup Guide

## Overview

The Medical Record Analysis System requires AWS services for production use. This guide explains how to set up AWS for different scenarios.

## Testing vs Production

### Testing (No AWS Required)

For testing and development without AWS:

```bash
# Run tests with mocked AWS services
pytest tests/

# All tests use moto to mock S3, Lambda, etc.
# No real AWS credentials needed
```

### Prototype (AWS Required)

The prototype launcher requires real AWS:

```bash
# Requires configured AWS credentials
python launch_prototype.py
```

### Production (AWS Required)

Production deployment requires:
- AWS Account
- S3 bucket for patient records
- Lambda functions (optional)
- Bedrock agents (optional)

## AWS Credentials Setup

### Method 1: AWS CLI (Recommended)

```bash
# Install AWS CLI
python3 -m pip install awscli

# Configure credentials
aws configure

# You'll be prompted for:
# - AWS Access Key ID
# - AWS Secret Access Key  
# - Default region (use: us-east-1)
# - Default output format (use: json)

# Verify configuration
aws sts get-caller-identity
```

### Method 2: Environment Variables

```bash
# Set credentials
export AWS_ACCESS_KEY_ID=your_access_key_here
export AWS_SECRET_ACCESS_KEY=your_secret_key_here
export AWS_DEFAULT_REGION=us-east-1

# Verify
aws sts get-caller-identity
```

### Method 3: AWS Credentials File

Create `~/.aws/credentials`:
```ini
[default]
aws_access_key_id = your_access_key_here
aws_secret_access_key = your_secret_key_here
```

Create `~/.aws/config`:
```ini
[default]
region = us-east-1
output = json
```

## Getting AWS Credentials

### For AWS Account Owners

1. Sign in to AWS Console
2. Go to IAM → Users → Your User
3. Security Credentials tab
4. Create Access Key
5. Download and save the credentials

### For Team Members

Ask your AWS administrator to:
1. Create an IAM user for you
2. Attach appropriate policies (S3, Lambda, Bedrock)
3. Generate access keys
4. Share credentials securely

## Required AWS Permissions

### Minimum Permissions for Testing

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::patient-records-20251024",
        "arn:aws:s3:::patient-records-20251024/*"
      ]
    }
  ]
}
```

### Full Permissions for Production

See `deployment/bedrock/iam_policy.json` for complete policy.

## S3 Bucket Setup

### Create S3 Bucket

```bash
# Create bucket
aws s3 mb s3://patient-records-20251024 --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket patient-records-20251024 \
  --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket patient-records-20251024 \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'
```

### Upload Test Data

```bash
# Upload patient XML files
aws s3 cp tests/fixtures/patient_records/ \
  s3://patient-records-20251024/ \
  --recursive
```

## Troubleshooting

### Error: Unable to locate credentials

**Problem**: AWS credentials not configured

**Solution**:
```bash
aws configure
# Or set environment variables
```

### Error: InvalidAccessKeyId

**Problem**: Invalid or expired credentials

**Solution**:
```bash
# Verify credentials
aws sts get-caller-identity

# If invalid, reconfigure
aws configure
```

### Error: Access Denied

**Problem**: Insufficient IAM permissions

**Solution**:
1. Check IAM user permissions
2. Verify bucket policy
3. Ensure correct region (us-east-1)

### Error: Bucket does not exist

**Problem**: S3 bucket not created

**Solution**:
```bash
# Create bucket
aws s3 mb s3://patient-records-20251024 --region us-east-1

# Verify
aws s3 ls s3://patient-records-20251024/
```

## Security Best Practices

### 1. Never Commit Credentials

```bash
# Add to .gitignore
echo ".env" >> .gitignore
echo "*.pem" >> .gitignore
echo "credentials" >> .gitignore
```

### 2. Use IAM Roles (Production)

For Lambda and EC2, use IAM roles instead of access keys.

### 3. Rotate Credentials Regularly

```bash
# Create new access key
aws iam create-access-key --user-name your-username

# Delete old access key
aws iam delete-access-key \
  --user-name your-username \
  --access-key-id OLD_KEY_ID
```

### 4. Use Least Privilege

Only grant permissions actually needed.

### 5. Enable MFA

Enable multi-factor authentication for AWS console access.

## Testing Without AWS

For development and testing without AWS:

```bash
# Run all tests (uses mocked AWS)
pytest tests/

# Run specific test
pytest tests/test_xml_parser.py

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

Tests use `moto` library to mock AWS services:
- No real AWS credentials needed
- No charges incurred
- Fast execution
- Isolated from production

## Cost Considerations

### Free Tier

AWS Free Tier includes:
- S3: 5GB storage, 20,000 GET requests, 2,000 PUT requests
- Lambda: 1M requests, 400,000 GB-seconds compute
- CloudWatch: 10 custom metrics, 10 alarms

### Estimated Costs (Beyond Free Tier)

- S3 Storage: ~$0.023/GB/month
- S3 Requests: ~$0.0004/1000 GET, ~$0.005/1000 PUT
- Lambda: ~$0.20 per 1M requests
- CloudWatch Logs: ~$0.50/GB ingested

### Cost Optimization

1. Use S3 lifecycle policies to archive old data
2. Enable S3 Intelligent-Tiering
3. Monitor usage with AWS Cost Explorer
4. Set up billing alerts

## Regional Considerations

### HIPAA Compliance

For HIPAA compliance, all resources must be in US regions:
- Primary: us-east-1 (N. Virginia)
- Backup: us-west-2 (Oregon)

### Configuration

```bash
# Set region
export AWS_DEFAULT_REGION=us-east-1

# Or in AWS CLI config
aws configure set region us-east-1
```

## Support

### AWS Documentation

- [AWS CLI Configuration](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html)
- [S3 User Guide](https://docs.aws.amazon.com/s3/)
- [IAM Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)

### Project Documentation

- `TROUBLESHOOTING.md` - Common issues and solutions
- `deployment/bedrock/README.md` - Bedrock deployment
- `deployment/lambda/README.md` - Lambda deployment
- `deployment/monitoring/README.md` - Monitoring setup

### Getting Help

1. Check `TROUBLESHOOTING.md`
2. Review AWS CloudWatch logs
3. Verify IAM permissions
4. Check AWS service status
5. Contact AWS Support (if needed)
