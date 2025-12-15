# SAM Deployment S3 Upload Fix

## Problem Analysis

The error shows:
```
Error: Unable to upload artifact XMLParserFunction referenced by CodeUri parameter of XMLParserFunction resource.
Could not connect to the endpoint URL: "https://medical-record-analysis-deployment.s3.amazonaws.com/..."
```

But the bucket exists:
```bash
aws s3 ls s3://medical-record-analysis-deployment/
2025-12-11 13:03:24   31983574 a2edf05c10869377b70acea34565ca54
```

## Root Causes

1. **Region Mismatch**: Bucket might be in different region than expected
2. **Partial Upload**: Previous upload was interrupted, leaving incomplete multipart upload
3. **Bucket Policy**: Bucket might have restrictive policies
4. **Network Issues**: Temporary connectivity problems

## Solutions

### Solution 1: Check Bucket Region and Clean Up

```bash
# Check bucket region
aws s3api get-bucket-location --bucket medical-record-analysis-deployment

# Clean up incomplete multipart uploads
aws s3api list-multipart-uploads --bucket medical-record-analysis-deployment
aws s3api abort-multipart-upload --bucket medical-record-analysis-deployment --key d4bb01e47a831147123a001974f69eac --upload-id uyathDH0W1Zw5ya64lbIcJoBfv8Jt5Z4nwWanQr.sZcwZ2ht6SzIk5XZ0uZ27Zw1wISJBnwp1KGo3HSHVlz96qKsuDVDP6JnnX02akoLIXBQYSp..1CWhTOHaRnDiLg806TLPv.BxMMM.hlnLRxPLQ--
```

### Solution 2: Use Different Bucket Name

```bash
# Use account-specific bucket name to avoid conflicts
export S3_BUCKET="medical-record-analysis-deployment-$(aws sts get-caller-identity --query Account --output text)"
echo $S3_BUCKET

# Update deployment script to use this bucket
```

### Solution 3: Manual Bucket Recreation

```bash
# Delete and recreate bucket (if safe to do so)
aws s3 rb s3://medical-record-analysis-deployment --force
aws s3 mb s3://medical-record-analysis-deployment --region us-east-1

# Enable encryption
aws s3api put-bucket-encryption \
    --bucket medical-record-analysis-deployment \
    --server-side-encryption-configuration '{
        "Rules": [{
            "ApplyServerSideEncryptionByDefault": {
                "SSEAlgorithm": "AES256"
            }
        }]
    }'
```

### Solution 4: Use SAM's Managed Bucket

```bash
# Let SAM create and manage the bucket automatically
sam deploy --guided --stack-name medical-record-analysis-lambda
```

## Quick Fix Commands

### Option A: Clean and Retry
```bash
cd deployment/lambda

# Clean up any incomplete uploads
aws s3api list-multipart-uploads --bucket medical-record-analysis-deployment --query 'Uploads[].{Key:Key,UploadId:UploadId}' --output table

# If any incomplete uploads exist, abort them
# aws s3api abort-multipart-upload --bucket medical-record-analysis-deployment --key <KEY> --upload-id <UPLOAD_ID>

# Retry deployment
./deploy.sh production
```

### Option B: Use Account-Specific Bucket
```bash
cd deployment/lambda

# Create account-specific bucket name
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
NEW_BUCKET="medical-record-analysis-deployment-$ACCOUNT_ID"

# Update deploy.sh to use new bucket name
sed -i.bak "s/medical-record-analysis-deployment/$NEW_BUCKET/g" deploy.sh

# Run deployment
./deploy.sh production
```

### Option C: Manual SAM Deploy
```bash
cd deployment/lambda

# Build
sam build

# Deploy with guided setup (will create bucket automatically)
sam deploy --guided --stack-name medical-record-analysis-lambda --capabilities CAPABILITY_NAMED_IAM
```

## Prevention

Update the deployment script to be more robust:

```bash
# Better bucket creation logic
create_deployment_bucket() {
    local bucket_name=$1
    local region=$2
    
    echo "Checking deployment S3 bucket: $bucket_name"
    
    # Check if bucket exists and is accessible
    if aws s3api head-bucket --bucket "$bucket_name" 2>/dev/null; then
        echo "✓ Bucket exists and is accessible"
        
        # Clean up any incomplete multipart uploads
        echo "Cleaning up incomplete uploads..."
        aws s3api list-multipart-uploads --bucket "$bucket_name" --query 'Uploads[].{Key:Key,UploadId:UploadId}' --output text | \
        while read key upload_id; do
            if [ ! -z "$key" ] && [ ! -z "$upload_id" ]; then
                echo "Aborting incomplete upload: $key"
                aws s3api abort-multipart-upload --bucket "$bucket_name" --key "$key" --upload-id "$upload_id"
            fi
        done
    else
        echo "Creating deployment bucket: $bucket_name"
        aws s3 mb "s3://$bucket_name" --region "$region"
        
        # Enable encryption
        aws s3api put-bucket-encryption \
            --bucket "$bucket_name" \
            --server-side-encryption-configuration '{
                "Rules": [{
                    "ApplyServerSideEncryptionByDefault": {
                        "SSEAlgorithm": "AES256"
                    }
                }]
            }'
    fi
}
```

## Recommended Action

Try **Option A** first (clean and retry), then **Option C** (manual SAM deploy) if that fails.