#!/usr/bin/env python3
"""Fix Bedrock Agent Lambda permissions."""

import json
import boto3
from pathlib import Path

AWS_REGION = "us-east-1"
BEDROCK_ROLE_NAME = "MedicalRecordAnalysisBedrockAgentRole"
POLICY_NAME = "MedicalRecordAnalysisBedrockPolicy"


def update_bedrock_agent_policy():
    """Update the Bedrock Agent IAM policy to include Lambda invoke permissions."""
    iam_client = boto3.client('iam')
    
    # Read the updated policy
    policy_path = Path("deployment/bedrock/iam_policy.json")
    with open(policy_path) as f:
        policy_document = json.load(f)
    
    try:
        # Get existing policy version
        response = iam_client.get_role_policy(
            RoleName=BEDROCK_ROLE_NAME,
            PolicyName=POLICY_NAME
        )
        print(f"✓ Found existing policy: {POLICY_NAME}")
        
        # Update the policy
        iam_client.put_role_policy(
            RoleName=BEDROCK_ROLE_NAME,
            PolicyName=POLICY_NAME,
            PolicyDocument=json.dumps(policy_document)
        )
        print(f"✓ Updated policy with Lambda invoke permissions")
        
    except iam_client.exceptions.NoSuchEntityException:
        print(f"✗ Role or policy not found: {BEDROCK_ROLE_NAME}/{POLICY_NAME}")
        print("Creating new policy...")
        
        # Create the policy
        iam_client.put_role_policy(
            RoleName=BEDROCK_ROLE_NAME,
            PolicyName=POLICY_NAME,
            PolicyDocument=json.dumps(policy_document)
        )
        print(f"✓ Created new policy: {POLICY_NAME}")
    
    # Verify the policy was updated
    response = iam_client.get_role_policy(
        RoleName=BEDROCK_ROLE_NAME,
        PolicyName=POLICY_NAME
    )
    
    # PolicyDocument is already a dict when returned from AWS
    updated_policy = response['PolicyDocument']
    lambda_permissions = [
        stmt for stmt in updated_policy['Statement'] 
        if stmt.get('Sid') == 'LambdaInvokePermission'
    ]
    
    if lambda_permissions:
        print("✅ Lambda invoke permissions successfully added!")
        print(f"   Resources: {lambda_permissions[0]['Resource']}")
    else:
        print("❌ Lambda permissions not found in updated policy")
        return False
    
    return True


def add_lambda_resource_policy():
    """Add resource-based policy to Lambda function to allow Bedrock Agent invocation."""
    lambda_client = boto3.client('lambda', region_name=AWS_REGION)
    
    # Get the Lambda function ARN from the error message
    function_name = "medical-record-lambda-simpl-MasterWorkflowFunction-yN3fosVGxUsV"
    
    try:
        # Check if function exists
        response = lambda_client.get_function(FunctionName=function_name)
        function_arn = response['Configuration']['FunctionArn']
        print(f"✓ Found Lambda function: {function_arn}")
        
        # Add permission for Bedrock Agent to invoke the function
        try:
            lambda_client.add_permission(
                FunctionName=function_name,
                StatementId='bedrock-agent-invoke-permission',
                Action='lambda:InvokeFunction',
                Principal='bedrock.amazonaws.com',
                SourceAccount='539247495490'
            )
            print("✓ Added Bedrock Agent invoke permission to Lambda function")
        except lambda_client.exceptions.ResourceConflictException:
            print("✓ Bedrock Agent permission already exists on Lambda function")
        
        return True
        
    except lambda_client.exceptions.ResourceNotFoundException:
        print(f"✗ Lambda function not found: {function_name}")
        print("Please check the function name and ensure it's deployed correctly.")
        return False


def main():
    print("🔧 Fixing Bedrock Agent Lambda Permissions")
    print("=" * 60)
    
    success = True
    
    # Step 1: Update Bedrock Agent IAM role policy
    print("\n[Step 1/2] Updating Bedrock Agent IAM policy...")
    if not update_bedrock_agent_policy():
        success = False
    
    # Step 2: Add resource-based policy to Lambda function
    print("\n[Step 2/2] Adding Lambda resource-based policy...")
    if not add_lambda_resource_policy():
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("✅ Permission Fix Complete!")
        print("\nThe Bedrock Agent should now be able to invoke the Lambda function.")
        print("Try running your medical analysis again.")
    else:
        print("❌ Some permission fixes failed.")
        print("Please check the error messages above and resolve manually.")
    print("=" * 60)


if __name__ == "__main__":
    main()