#!/usr/bin/env python3
"""Test Bedrock access with updated IAM permissions."""

import sys
sys.path.insert(0, '/Users/humberto.acevedo/datuak-agents')

from src.utils.bedrock_client import BedrockClient

def test_bedrock_access():
    print("Testing Bedrock access with inference profile...")
    
    try:
        client = BedrockClient(region="us-east-1")
        print(f"✓ Bedrock client initialized with model: {client.model_id}")
        
        response = client.invoke_claude(
            prompt="Say 'Hello' in one word.",
            max_tokens=10
        )
        
        print(f"✓ Successfully invoked Bedrock!")
        print(f"Response: {response['text']}")
        print(f"Model: {response['model_id']}")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = test_bedrock_access()
    sys.exit(0 if success else 1)
