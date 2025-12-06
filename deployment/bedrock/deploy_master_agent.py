#!/usr/bin/env python3
"""Deploy Master Bedrock Agent with workflow Lambda."""

import json
import boto3
import time
from pathlib import Path

AWS_REGION = "us-east-1"
AWS_ACCOUNT_ID = "539247495490"
LAMBDA_ROLE_NAME = "MedicalAnalysisLambdaRole"


def create_lambda_role(iam_client):
    """Create IAM role for Lambda."""
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }
    
    try:
        response = iam_client.create_role(
            RoleName=LAMBDA_ROLE_NAME,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description="Role for Medical Analysis Lambda functions"
        )
        role_arn = response['Role']['Arn']
        print(f"✓ Created Lambda role: {role_arn}")
    except iam_client.exceptions.EntityAlreadyExistsException:
        role_arn = f"arn:aws:iam::{AWS_ACCOUNT_ID}:role/{LAMBDA_ROLE_NAME}"
        print(f"✓ Lambda role exists: {role_arn}")
    
    # Attach policies
    iam_client.attach_role_policy(
        RoleName=LAMBDA_ROLE_NAME,
        PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
    )
    iam_client.attach_role_policy(
        RoleName=LAMBDA_ROLE_NAME,
        PolicyArn="arn:aws:iam::aws:policy/AmazonS3FullAccess"
    )
    
    time.sleep(10)  # Wait for role propagation
    return role_arn


def deploy_lambda(lambda_client, role_arn):
    """Deploy Lambda function."""
    import zipfile
    import io
    
    function_name = "MedicalAnalysisMasterWorkflow"
    
    # Create proper ZIP file
    handler_path = Path(__file__).parent.parent / "lambda" / "master_workflow_handler.py"
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.write(handler_path, 'master_workflow_handler.py')
    code_content = zip_buffer.getvalue()
    
    try:
        response = lambda_client.create_function(
            FunctionName=function_name,
            Runtime='python3.11',
            Role=role_arn,
            Handler='master_workflow_handler.lambda_handler',
            Code={'ZipFile': code_content},
            Timeout=300,
            MemorySize=1024,
            Environment={
                'Variables': {
                    'S3_BUCKET_NAME': 'patient-records-20251024'
                }
            }
        )
        function_arn = response['FunctionArn']
        print(f"✓ Created Lambda: {function_arn}")
    except lambda_client.exceptions.ResourceConflictException:
        response = lambda_client.get_function(FunctionName=function_name)
        function_arn = response['Configuration']['FunctionArn']
        print(f"✓ Lambda exists: {function_arn}")
    
    return function_arn


def deploy_bedrock_agent(bedrock_client, lambda_arn):
    """Deploy Bedrock Agent."""
    config_path = Path(__file__).parent / "master_agent_config.json"
    with open(config_path) as f:
        config = json.load(f)
    
    # Create agent
    try:
        response = bedrock_client.create_agent(**config)
        agent_id = response['agent']['agentId']
        print(f"✓ Created agent: {agent_id}")
    except Exception as e:
        print(f"Agent may exist, checking... {e}")
        # List and find existing agent
        agents = bedrock_client.list_agents()
        for agent in agents.get('agentSummaries', []):
            if agent['agentName'] == config['agentName']:
                agent_id = agent['agentId']
                print(f"✓ Found existing agent: {agent_id}")
                break
        else:
            raise
    
    # Create action group
    action_schema_path = Path(__file__).parent / "action_groups" / "master_workflow_actions.json"
    with open(action_schema_path) as f:
        action_schema = json.load(f)
    
    try:
        bedrock_client.create_agent_action_group(
            agentId=agent_id,
            agentVersion='DRAFT',
            actionGroupName='MasterWorkflowActionGroup',
            actionGroupExecutor={'lambda': lambda_arn},
            apiSchema={'payload': json.dumps(action_schema)}
        )
        print("✓ Created action group")
    except bedrock_client.exceptions.ConflictException:
        print("✓ Action group already exists")
    except Exception as e:
        print(f"✗ Failed to create action group: {e}")
        raise
    
    # Prepare agent
    bedrock_client.prepare_agent(agentId=agent_id)
    print("✓ Preparing agent...")
    time.sleep(30)
    
    # Create alias
    try:
        alias_response = bedrock_client.create_agent_alias(
            agentId=agent_id,
            agentAliasName='production'
        )
        alias_id = alias_response['agentAlias']['agentAliasId']
        print(f"✓ Created alias: {alias_id}")
    except Exception as e:
        print(f"Alias may exist: {e}")
        aliases = bedrock_client.list_agent_aliases(agentId=agent_id)
        alias_id = aliases['agentAliasSummaries'][0]['agentAliasId']
    
    return agent_id, alias_id


def main():
    print("🚀 Deploying Master Bedrock Agent")
    print("=" * 60)
    
    iam_client = boto3.client('iam')
    lambda_client = boto3.client('lambda', region_name=AWS_REGION)
    bedrock_client = boto3.client('bedrock-agent', region_name=AWS_REGION)
    
    # Deploy components
    role_arn = create_lambda_role(iam_client)
    lambda_arn = deploy_lambda(lambda_client, role_arn)
    agent_id, alias_id = deploy_bedrock_agent(bedrock_client, lambda_arn)
    
    # Save deployment info
    deployment_info = {
        'agent_id': agent_id,
        'agent_alias_id': alias_id,
        'lambda_arn': lambda_arn,
        'region': AWS_REGION
    }
    
    output_path = Path(__file__).parent / "master_agent_deployment.json"
    with open(output_path, 'w') as f:
        json.dump(deployment_info, f, indent=2)
    
    print("\n" + "=" * 60)
    print("✅ Deployment Complete!")
    print("=" * 60)
    print(f"\nAgent ID: {agent_id}")
    print(f"Alias ID: {alias_id}")
    print(f"\nTo use with CLI:")
    print(f"python launch_prototype.py --bedrock-agent --agent-id {agent_id} --agent-alias-id {alias_id}")
    print(f"\nDeployment info saved to: {output_path}")


if __name__ == "__main__":
    main()
