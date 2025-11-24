# AWS SSO Setup Guide for Medical Record Analysis System

## Problem

When running `launch_prototype.py` with AWS SSO credentials, you may encounter:
```
Invalid AWS Access Key ID. Check your AWS credentials and try again.
```

This happens because:
1. AWS SSO credentials are temporary and stored differently than standard credentials
2. boto3 needs specific environment variables to find and use SSO credentials
3. The session token from SSO must be properly passed to boto3

## Solution

### Option 1: Use the Helper Script (Recommended)

We've created a helper script that handles all the AWS SSO configuration automatically:

```bash
# Make the script executable (first time only)
chmod +x run_with_sso.sh

# Run with your AWS profile name
./run_with_sso.sh default

# Or with a specific SSO profile
./run_with_sso.sh my-sso-profile
```

The script will:
- Check if your SSO session is valid
- Run `aws sso login` if needed
- Set all required environment variables
- Launch the prototype with proper credentials

### Option 2: Manual Setup

If you prefer to set up manually:

#### Step 1: Login to AWS SSO

```bash
# Login with your profile
aws sso login --profile default

# Or with a specific profile
aws sso login --profile my-sso-profile
```

#### Step 2: Set Environment Variables

```bash
# Set the AWS profile to use
export AWS_PROFILE=default  # or your profile name

# Enable boto3 to load AWS config file (required for SSO)
export AWS_SDK_LOAD_CONFIG=1

# Set the region (optional, defaults to us-east-1)
export AWS_DEFAULT_REGION=us-east-1
```

#### Step 3: Run the Prototype

```bash
python3 launch_prototype.py -v
```

### Option 3: Use Environment Variables Directly

If you have temporary credentials from SSO, you can export them directly:

```bash
# Get credentials from AWS SSO
aws configure export-credentials --profile default

# This will output something like:
# {
#   "AccessKeyId": "ASIA...",
#   "SecretAccessKey": "...",
#   "SessionToken": "...",
#   "Expiration": "..."
# }

# Export them as environment variables
export AWS_ACCESS_KEY_ID=ASIA...
export AWS_SECRET_ACCESS_KEY=...
export AWS_SESSION_TOKEN=...  # Important for SSO!
export AWS_DEFAULT_REGION=us-east-1

# Run the prototype
python3 launch_prototype.py
```

## Verification

To verify your AWS credentials are working:

```bash
# Check your AWS identity
aws sts get-caller-identity --profile default

# Should output something like:
# {
#     "UserId": "AIDA...",
#     "Account": "123456789012",
#     "Arn": "arn:aws:iam::123456789012:user/your-user"
# }
```

## Troubleshooting

### Error: "Invalid AWS Access Key ID"

**Cause**: SSO session expired or session token not being passed to boto3

**Solution**:
```bash
# Re-login to AWS SSO
aws sso login --profile default

# Ensure AWS_SDK_LOAD_CONFIG is set
export AWS_SDK_LOAD_CONFIG=1

# Run with the helper script
./run_with_sso.sh default
```

### Error: "No AWS credentials found"

**Cause**: AWS_PROFILE not set or boto3 can't find the config file

**Solution**:
```bash
# Check if your AWS config exists
ls -la ~/.aws/config
ls -la ~/.aws/credentials

# Set the profile explicitly
export AWS_PROFILE=default
export AWS_SDK_LOAD_CONFIG=1

# Verify it works
aws sts get-caller-identity --profile default
```

### Error: "Token has expired"

**Cause**: SSO session expired (typically after 8-12 hours)

**Solution**:
```bash
# Simply re-login
aws sso login --profile default

# Then run the prototype again
./run_with_sso.sh default
```

### Error: "session_token_present=False" in logs

**Cause**: Session token not being properly retrieved from SSO cache

**Solution**:
```bash
# Clear SSO cache and re-login
rm -rf ~/.aws/sso/cache/*
aws sso login --profile default

# Ensure SDK config loading is enabled
export AWS_SDK_LOAD_CONFIG=1

# Run the prototype
./run_with_sso.sh default
```

## AWS Profile Configuration

Your AWS config file (`~/.aws/config`) should look like this for SSO:

```ini
[default]
sso_start_url = https://your-org.awsapps.com/start
sso_region = us-east-1
sso_account_id = 123456789012
sso_role_name = YourRoleName
region = us-east-1
output = json
```

Or for a named profile:

```ini
[profile my-sso-profile]
sso_start_url = https://your-org.awsapps.com/start
sso_region = us-east-1
sso_account_id = 123456789012
sso_role_name = YourRoleName
region = us-east-1
output = json
```

## Quick Reference

### Check SSO Status
```bash
aws sts get-caller-identity --profile default
```

### Login to SSO
```bash
aws sso login --profile default
```

### List Available Profiles
```bash
aws configure list-profiles
```

### Run Prototype with SSO
```bash
./run_with_sso.sh default
```

### Environment Variables Needed
```bash
export AWS_PROFILE=default
export AWS_SDK_LOAD_CONFIG=1
export AWS_DEFAULT_REGION=us-east-1
```

## Additional Resources

- [AWS SSO Documentation](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html)
- [Boto3 Credentials Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html)
- [AWS CLI Configuration](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html)
