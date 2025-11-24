# Quick Start with AWS SSO

## TL;DR - Run This

```bash
# 1. Login to AWS SSO
aws sso login --profile default

# 2. Run the prototype with SSO
./run_with_sso.sh default
```

That's it! The script handles everything else.

## What the Script Does

The `run_with_sso.sh` script automatically:
1. ✅ Checks if AWS CLI is installed
2. ✅ Verifies your SSO session is valid
3. ✅ Runs `aws sso login` if needed
4. ✅ Sets `AWS_PROFILE` environment variable
5. ✅ Sets `AWS_SDK_LOAD_CONFIG=1` for boto3
6. ✅ Launches the prototype with proper credentials

## If You Get Errors

### "Invalid AWS Access Key ID"

Your SSO session expired. Just re-login:
```bash
aws sso login --profile default
./run_with_sso.sh default
```

### "No such profile"

List your available profiles:
```bash
aws configure list-profiles
```

Then use the correct profile name:
```bash
./run_with_sso.sh your-profile-name
```

### "AWS CLI not found"

Install AWS CLI:
- macOS: `brew install awscli`
- Linux: `pip install awscli`
- Windows: Download from https://aws.amazon.com/cli/

## Manual Method (If Script Doesn't Work)

```bash
# 1. Login
aws sso login --profile default

# 2. Set environment variables
export AWS_PROFILE=default
export AWS_SDK_LOAD_CONFIG=1
export AWS_DEFAULT_REGION=us-east-1

# 3. Run prototype
python3 launch_prototype.py -v
```

## Need More Help?

See the detailed guide: [AWS_SSO_SETUP.md](AWS_SSO_SETUP.md)
