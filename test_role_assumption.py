#!/usr/bin/env python3
import boto3
import os

os.environ.setdefault("AWS_SDK_LOAD_CONFIG", "1")

print("Testing role assumption...")
print(f"AWS_PROFILE: {os.environ.get('AWS_PROFILE', 'not set')}")
print(f"AWS_SDK_LOAD_CONFIG: {os.environ.get('AWS_SDK_LOAD_CONFIG', 'not set')}")

# Check current identity
sts = boto3.client('sts')
identity = sts.get_caller_identity()
print(f"\nCurrent identity: {identity['Arn']}")
print(f"Account: {identity['Account']}")

# Try to assume role
role_arn = "arn:aws:iam::279259282911:role/BedrockCrossAccountRole"
print(f"\nAttempting to assume role: {role_arn}")

try:
    response = sts.assume_role(
        RoleArn=role_arn,
        RoleSessionName='test-session'
    )
    print(f"✓ Successfully assumed role!")
    print(f"  AssumedRoleUser: {response['AssumedRoleUser']['Arn']}")
    print(f"  Expiration: {response['Credentials']['Expiration']}")
except Exception as e:
    print(f"✗ Failed to assume role: {e}")
