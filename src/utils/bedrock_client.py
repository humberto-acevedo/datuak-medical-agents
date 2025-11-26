"""AWS Bedrock client for Claude model interactions."""

import json
import logging
import os
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class BedrockClient:
    """Client for interacting with AWS Bedrock Claude models."""
    
    # Foundation Model IDs for Claude models
    CLAUDE_SONNET = "anthropic.claude-3-sonnet-20240229-v1:0"
    CLAUDE_HAIKU = "anthropic.claude-3-haiku-20240307-v1:0"
    CLAUDE_35_HAIKU = "anthropic.claude-3-haiku-20240307-v1:0"  # Use Claude 3 Haiku (already enabled)
    
    # Default cross-account role ARN
    DEFAULT_CROSS_ACCOUNT_ROLE = "arn:aws:iam::279259282911:role/BedrockCrossAccountRole"
    
    def __init__(self, region: str = "us-east-1", model_id: str = None):
        """
        Initialize Bedrock client.
        
        Args:
            region: AWS region (default: us-east-1 for HIPAA compliance)
            model_id: Claude model ID (default: Claude 3.5 Haiku)
        """
        self.region = region
        self.model_id = model_id or self.CLAUDE_35_HAIKU
        
        # Use cross-account role by default
        cross_account_role = os.environ.get('CROSS_ACCOUNT_ROLE_ARN', self.DEFAULT_CROSS_ACCOUNT_ROLE)
        
        try:
            logger.info(f"Assuming cross-account role: {cross_account_role}")
            sts = boto3.client('sts')
            assumed_role = sts.assume_role(
                RoleArn=cross_account_role,
                RoleSessionName='bedrock-prototype-session'
            )
            logger.info(f"Successfully assumed role. Account: {assumed_role['AssumedRoleUser']['Arn']}")
            
            self.bedrock_runtime = boto3.client(
                service_name='bedrock-runtime',
                region_name=region,
                aws_access_key_id=assumed_role['Credentials']['AccessKeyId'],
                aws_secret_access_key=assumed_role['Credentials']['SecretAccessKey'],
                aws_session_token=assumed_role['Credentials']['SessionToken']
            )
        except ClientError as e:
            logger.error(f"Failed to assume cross-account role: {e}")
            logger.warning("Falling back to default credentials (may not have Bedrock access)")
            self.bedrock_runtime = boto3.client(
                service_name='bedrock-runtime',
                region_name=region
            )
        
        logger.info(f"Bedrock client initialized with cross-account role")
        logger.info(f"Bedrock client initialized with model: {self.model_id}")
    
    def invoke_claude(self, 
                     prompt: str, 
                     system_prompt: Optional[str] = None,
                     max_tokens: int = 4096,
                     temperature: float = 0.7) -> Dict[str, Any]:
        """
        Invoke Claude model with a prompt.
        
        Args:
            prompt: User prompt/question
            system_prompt: Optional system prompt for context
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0-1)
            
        Returns:
            Dict containing response text and metadata
            
        Raises:
            ClientError: If Bedrock API call fails
        """
        try:
            # Prepare request body for Claude
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            # Add system prompt if provided
            if system_prompt:
                request_body["system"] = system_prompt
            
            # Log request (without full prompt for brevity)
            logger.info(f"Invoking Claude model: {self.model_id}")
            logger.debug(f"Prompt length: {len(prompt)} characters")
            
            # Invoke model
            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            
            # Extract text from response
            response_text = response_body['content'][0]['text']
            
            # Log response metadata
            logger.info(f"Claude response received: {len(response_text)} characters")
            logger.debug(f"Stop reason: {response_body.get('stop_reason')}")
            
            return {
                'text': response_text,
                'stop_reason': response_body.get('stop_reason'),
                'usage': response_body.get('usage', {}),
                'model_id': self.model_id
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"Bedrock API error ({error_code}): {error_message}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error invoking Claude: {str(e)}")
            raise
    
    def invoke_with_retry(self,
                         prompt: str,
                         system_prompt: Optional[str] = None,
                         max_retries: int = 3) -> Dict[str, Any]:
        """
        Invoke Claude with automatic retry on transient errors.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            max_retries: Maximum number of retry attempts
            
        Returns:
            Dict containing response text and metadata
        """
        import time
        
        for attempt in range(max_retries):
            try:
                return self.invoke_claude(prompt, system_prompt)
            except ClientError as e:
                error_code = e.response['Error']['Code']
                
                # Retry on throttling or transient errors
                if error_code in ['ThrottlingException', 'ServiceUnavailable'] and attempt < max_retries - 1:
                    wait_time = (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Retrying after {wait_time}s due to {error_code}")
                    time.sleep(wait_time)
                    continue
                else:
                    raise
        
        raise Exception(f"Failed after {max_retries} attempts")
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model."""
        # Determine model name from ID
        model_id_lower = self.model_id.lower()
        if 'sonnet' in model_id_lower:
            model_name = 'Claude 3 Sonnet'
        elif '3-5-haiku' in model_id_lower or '3.5-haiku' in model_id_lower:
            model_name = 'Claude 3.5 Haiku'
        elif 'haiku' in model_id_lower:
            model_name = 'Claude 3 Haiku'
        else:
            model_name = 'Claude'
        
        return {
            'model_id': self.model_id,
            'region': self.region,
            'provider': 'Anthropic',
            'model_name': model_name
        }
