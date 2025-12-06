"""AWS Bedrock Agent runtime client."""

import json
import logging
import boto3
import uuid
import os
from typing import Dict, Any

logger = logging.getLogger(__name__)


class BedrockAgentClient:
    """Client for invoking AWS Bedrock Agents."""
    
    DEFAULT_CROSS_ACCOUNT_ROLE = "arn:aws:iam::539247495490:role/MemberCrossAccountRole"
    
    def __init__(self, agent_id: str, agent_alias_id: str, region: str = "us-east-1"):
        self.agent_id = agent_id
        self.agent_alias_id = agent_alias_id
        self.region = region
        
        cross_account_role = os.environ.get('CROSS_ACCOUNT_ROLE_ARN', self.DEFAULT_CROSS_ACCOUNT_ROLE)
        
        logger.info(f"Assuming cross-account role: {cross_account_role}")
        sts = boto3.client('sts')
        assumed_role = sts.assume_role(
            RoleArn=cross_account_role,
            RoleSessionName='bedrock-agent-session'
        )
        
        self.client = boto3.client(
            'bedrock-agent-runtime',
            region_name=region,
            aws_access_key_id=assumed_role['Credentials']['AccessKeyId'],
            aws_secret_access_key=assumed_role['Credentials']['SecretAccessKey'],
            aws_session_token=assumed_role['Credentials']['SessionToken']
        )
        logger.info(f"Bedrock Agent client initialized with assumed role: {agent_id}")
    
    def invoke_agent(self, input_text: str, session_id: str = None) -> str:
        """Invoke Bedrock Agent and return response."""
        session_id = session_id or str(uuid.uuid4())
        
        logger.info(f"=" * 60)
        logger.info(f"BEDROCK AGENT CALL")
        logger.info(f"Agent ID: {self.agent_id}")
        logger.info(f"Alias ID: {self.agent_alias_id}")
        logger.info(f"Session ID: {session_id}")
        logger.info(f"Input: {input_text[:100]}...")
        logger.info(f"-" * 60)
        
        try:
            response = self.client.invoke_agent(
                agentId=self.agent_id,
                agentAliasId=self.agent_alias_id,
                sessionId=session_id,
                inputText=input_text
            )
            
            # Parse streaming response
            completion = ""
            for event in response.get('completion', []):
                if 'chunk' in event:
                    chunk = event['chunk']
                    if 'bytes' in chunk:
                        completion += chunk['bytes'].decode('utf-8')
            
            logger.info(f"BEDROCK AGENT RESPONSE")
            logger.info(f"Response length: {len(completion)} characters")
            logger.info(f"=" * 60)
            
            return completion
            
        except Exception as e:
            logger.error(f"Failed to invoke agent: {e}")
            raise
