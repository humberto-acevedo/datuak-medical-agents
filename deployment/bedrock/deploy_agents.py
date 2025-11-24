#!/usr/bin/env python3
"""
AWS Bedrock Agent Deployment Script

This script deploys the three medical record analysis agents to AWS Bedrock:
1. XML Parser Agent
2. Medical Summarization Agent
3. Research Correlation Agent

Prerequisites:
- AWS CLI configured with appropriate credentials
- boto3 installed
- IAM role created with proper permissions
"""

import json
import boto3
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional

# AWS Configuration
AWS_REGION = "us-east-1"
AWS_ACCOUNT_ID = "539247495490"
IAM_ROLE_NAME = "MedicalRecordAnalysisBedrockAgentRole"

class BedrockAgentDeployer:
    def __init__(self, region: str = AWS_REGION):
        self.region = region
        self.bedrock_agent_client = boto3.client('bedrock-agent', region_name=region)
        self.iam_client = boto3.client('iam', region_name=region)
        self.deployment_dir = Path(__file__).parent
        
    def load_json_config(self, filename: str) -> Dict[str, Any]:
        """Load JSON configuration file"""
        config_path = self.deployment_dir / filename
        with open(config_path, 'r') as f:
            return json.load(f)
    
    def create_or_update_iam_role(self) -> str:
        """Create or update IAM role for Bedrock agents"""
        print(f"Creating/updating IAM role: {IAM_ROLE_NAME}")
        
        trust_policy = self.load_json_config('trust_policy.json')
        iam_policy = self.load_json_config('iam_policy.json')
        
        role_arn = f"arn:aws:iam::{AWS_ACCOUNT_ID}:role/{IAM_ROLE_NAME}"
        
        try:
            # Try to create the role
            response = self.iam_client.create_role(
                RoleName=IAM_ROLE_NAME,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description="IAM role for Medical Record Analysis Bedrock Agents with HIPAA compliance",
                Tags=[
                    {'Key': 'Application', 'Value': 'MedicalRecordAnalysis'},
                    {'Key': 'Compliance', 'Value': 'HIPAA'},
                    {'Key': 'Environment', 'Value': 'Production'}
                ]
            )
            print(f"✓ Created IAM role: {role_arn}")
        except self.iam_client.exceptions.EntityAlreadyExistsException:
            print(f"✓ IAM role already exists: {role_arn}")
            # Update trust policy
            self.iam_client.update_assume_role_policy(
                RoleName=IAM_ROLE_NAME,
                PolicyDocument=json.dumps(trust_policy)
            )
        
        # Create or update inline policy
        policy_name = "MedicalRecordAnalysisBedrockPolicy"
        self.iam_client.put_role_policy(
            RoleName=IAM_ROLE_NAME,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(iam_policy)
        )
        print(f"✓ Updated IAM policy: {policy_name}")
        
        # Wait for role to be available
        print("Waiting for IAM role to propagate...")
        time.sleep(10)
        
        return role_arn
    
    def create_or_update_agent(self, config_file: str, action_group_file: Optional[str] = None) -> Dict[str, Any]:
        """Create or update a Bedrock agent"""
        config = self.load_json_config(config_file)
        agent_name = config['agentName']
        
        print(f"\nDeploying agent: {agent_name}")
        
        # Check if agent already exists
        existing_agent = self.find_agent_by_name(agent_name)
        
        agent_params = {
            'agentName': config['agentName'],
            'agentResourceRoleArn': config['agentResourceRoleArn'],
            'foundationModel': config['foundationModel'],
            'instruction': config['instruction'],
            'description': config.get('description', ''),
            'idleSessionTTLInSeconds': config.get('idleSessionTTLInSeconds', 600)
        }
        
        if existing_agent:
            # Update existing agent
            print(f"Updating existing agent: {agent_name}")
            response = self.bedrock_agent_client.update_agent(
                agentId=existing_agent['agentId'],
                **agent_params
            )
            agent_id = existing_agent['agentId']
        else:
            # Create new agent
            print(f"Creating new agent: {agent_name}")
            response = self.bedrock_agent_client.create_agent(**agent_params)
            agent_id = response['agent']['agentId']
        
        print(f"✓ Agent ID: {agent_id}")
        
        # Prepare the agent (required before creating alias)
        print(f"Preparing agent: {agent_name}")
        self.bedrock_agent_client.prepare_agent(agentId=agent_id)
        
        # Wait for agent to be prepared
        self.wait_for_agent_status(agent_id, 'PREPARED')
        
        # Create or update action group if specified
        if action_group_file:
            self.create_or_update_action_group(agent_id, action_group_file)
        
        # Create or update agent alias
        alias_name = "production"
        alias_id = self.create_or_update_alias(agent_id, alias_name)
        
        return {
            'agentId': agent_id,
            'agentName': agent_name,
            'aliasId': alias_id,
            'aliasName': alias_name,
            'status': 'DEPLOYED'
        }
    
    def find_agent_by_name(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Find an agent by name"""
        try:
            response = self.bedrock_agent_client.list_agents(maxResults=100)
            for agent in response.get('agentSummaries', []):
                if agent['agentName'] == agent_name:
                    return agent
        except Exception as e:
            print(f"Error finding agent: {e}")
        return None
    
    def wait_for_agent_status(self, agent_id: str, target_status: str, timeout: int = 300):
        """Wait for agent to reach target status"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            response = self.bedrock_agent_client.get_agent(agentId=agent_id)
            status = response['agent']['agentStatus']
            
            if status == target_status:
                print(f"✓ Agent reached status: {target_status}")
                return
            elif status == 'FAILED':
                raise Exception(f"Agent preparation failed")
            
            print(f"  Agent status: {status}, waiting...")
            time.sleep(5)
        
        raise TimeoutError(f"Agent did not reach {target_status} within {timeout} seconds")
    
    def create_or_update_action_group(self, agent_id: str, action_group_file: str):
        """Create or update action group for an agent"""
        action_group_config = self.load_json_config(action_group_file)
        action_group_name = action_group_config['actionGroupName']
        
        print(f"Creating/updating action group: {action_group_name}")
        
        # List existing action groups
        try:
            response = self.bedrock_agent_client.list_agent_action_groups(
                agentId=agent_id,
                agentVersion='DRAFT'
            )
            
            existing_group = None
            for group in response.get('actionGroupSummaries', []):
                if group['actionGroupName'] == action_group_name:
                    existing_group = group
                    break
            
            action_group_params = {
                'agentId': agent_id,
                'agentVersion': 'DRAFT',
                'actionGroupName': action_group_name,
                'description': action_group_config['description'],
                'actionGroupExecutor': action_group_config['actionGroupExecutor'],
                'apiSchema': action_group_config['apiSchema']
            }
            
            if existing_group:
                # Update existing action group
                self.bedrock_agent_client.update_agent_action_group(
                    actionGroupId=existing_group['actionGroupId'],
                    **action_group_params
                )
                print(f"✓ Updated action group: {action_group_name}")
            else:
                # Create new action group
                self.bedrock_agent_client.create_agent_action_group(**action_group_params)
                print(f"✓ Created action group: {action_group_name}")
                
        except Exception as e:
            print(f"Warning: Could not create/update action group: {e}")
    
    def create_or_update_alias(self, agent_id: str, alias_name: str) -> str:
        """Create or update agent alias"""
        print(f"Creating/updating alias: {alias_name}")
        
        try:
            # List existing aliases
            response = self.bedrock_agent_client.list_agent_aliases(
                agentId=agent_id,
                maxResults=100
            )
            
            existing_alias = None
            for alias in response.get('agentAliasSummaries', []):
                if alias['agentAliasName'] == alias_name:
                    existing_alias = alias
                    break
            
            if existing_alias:
                # Update existing alias
                response = self.bedrock_agent_client.update_agent_alias(
                    agentId=agent_id,
                    agentAliasId=existing_alias['agentAliasId'],
                    agentAliasName=alias_name,
                    description=f"Production alias for {agent_id}"
                )
                alias_id = existing_alias['agentAliasId']
                print(f"✓ Updated alias: {alias_name}")
            else:
                # Create new alias
                response = self.bedrock_agent_client.create_agent_alias(
                    agentId=agent_id,
                    agentAliasName=alias_name,
                    description=f"Production alias for {agent_id}"
                )
                alias_id = response['agentAlias']['agentAliasId']
                print(f"✓ Created alias: {alias_name}")
            
            return alias_id
            
        except Exception as e:
            print(f"Error creating/updating alias: {e}")
            raise
    
    def deploy_all_agents(self) -> Dict[str, Any]:
        """Deploy all three medical record analysis agents"""
        print("=" * 80)
        print("AWS Bedrock Agent Deployment")
        print("Medical Record Analysis System")
        print("=" * 80)
        
        # Step 1: Create/update IAM role
        role_arn = self.create_or_update_iam_role()
        
        # Step 2: Deploy XML Parser Agent
        xml_parser_result = self.create_or_update_agent(
            'xml_parser_agent_config.json',
            'action_groups/xml_parser_actions.json'
        )
        
        # Step 3: Deploy Medical Summarization Agent
        summarization_result = self.create_or_update_agent(
            'medical_summarization_agent_config.json',
            'action_groups/medical_summarization_actions.json'
        )
        
        # Step 4: Deploy Research Correlation Agent
        research_result = self.create_or_update_agent(
            'research_correlation_agent_config.json',
            'action_groups/research_correlation_actions.json'
        )
        
        results = {
            'iamRole': role_arn,
            'agents': {
                'xmlParser': xml_parser_result,
                'medicalSummarization': summarization_result,
                'researchCorrelation': research_result
            }
        }
        
        # Save deployment results
        output_file = self.deployment_dir / 'deployment_results.json'
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print("\n" + "=" * 80)
        print("✓ Deployment Complete!")
        print("=" * 80)
        print(f"\nDeployment results saved to: {output_file}")
        print("\nAgent Details:")
        for agent_type, agent_info in results['agents'].items():
            print(f"\n{agent_type}:")
            print(f"  Agent ID: {agent_info['agentId']}")
            print(f"  Alias ID: {agent_info['aliasId']}")
            print(f"  Status: {agent_info['status']}")
        
        return results

def main():
    """Main deployment function"""
    try:
        deployer = BedrockAgentDeployer()
        results = deployer.deploy_all_agents()
        return 0
    except Exception as e:
        print(f"\n❌ Deployment failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
