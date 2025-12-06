#!/usr/bin/env python3
"""Update Bedrock Agent with corrected action group schema."""

import boto3
import json
import sys
import os

def update_agent_action_group(agent_id: str, agent_version: str = "DRAFT"):
    """Update the master workflow action group with corrected schema."""
    
    # Load the corrected schema
    schema_path = "deployment/bedrock/action_groups/master_workflow_actions.json"
    with open(schema_path, 'r') as f:
        schema = json.load(f)
    
    # Get Lambda ARN from environment or use default
    lambda_arn = os.environ.get('MASTER_WORKFLOW_LAMBDA_ARN')
    if not lambda_arn:
        print("Error: MASTER_WORKFLOW_LAMBDA_ARN environment variable not set")
        print("Set it with: export MASTER_WORKFLOW_LAMBDA_ARN=arn:aws:lambda:...")
        return False
    
    # Use shell AWS credentials
    client = boto3.client('bedrock-agent', region_name='us-east-1')
    
    try:
        # List existing action groups
        print(f"\nListing action groups for agent {agent_id}...")
        response = client.list_agent_action_groups(
            agentId=agent_id,
            agentVersion=agent_version
        )
        
        action_group_id = None
        for ag in response.get('actionGroupSummaries', []):
            if ag['actionGroupName'] == 'MasterWorkflowActionGroup':
                action_group_id = ag['actionGroupId']
                print(f"Found action group: {action_group_id}")
                break
        
        if not action_group_id:
            print("Error: MasterWorkflowActionGroup not found")
            return False
        
        # Update the action group
        print(f"\nUpdating action group with corrected schema...")
        client.update_agent_action_group(
            agentId=agent_id,
            agentVersion=agent_version,
            actionGroupId=action_group_id,
            actionGroupName='MasterWorkflowActionGroup',
            description='Execute complete medical analysis workflow',
            actionGroupExecutor={
                'lambda': lambda_arn
            },
            apiSchema={
                'payload': json.dumps(schema)
            },
            actionGroupState='ENABLED'
        )
        
        print("✓ Action group updated successfully")
        
        # Prepare the agent
        print(f"\nPreparing agent {agent_id}...")
        prepare_response = client.prepare_agent(agentId=agent_id)
        print(f"✓ Agent prepared: {prepare_response['agentStatus']}")
        
        return True
        
    except Exception as e:
        print(f"Error updating agent: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python update_bedrock_agent.py <agent_id>")
        print("\nExample:")
        print("  export MASTER_WORKFLOW_LAMBDA_ARN=arn:aws:lambda:us-east-1:123456789012:function:master-workflow")
        print("  python update_bedrock_agent.py ABCD1234")
        sys.exit(1)
    
    agent_id = sys.argv[1]
    success = update_agent_action_group(agent_id)
    sys.exit(0 if success else 1)
