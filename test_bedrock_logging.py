#!/usr/bin/env python3
"""Test script to verify Bedrock logging is working."""

import logging
import sys
from src.utils.bedrock_client import BedrockClient

# Configure logging to see INFO level
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def test_bedrock_logging():
    """Test that Bedrock client logs model calls properly."""
    
    logger.info("=" * 80)
    logger.info("TESTING BEDROCK LOGGING")
    logger.info("=" * 80)
    
    try:
        # Initialize Bedrock client
        logger.info("\n1. Initializing Bedrock client...")
        client = BedrockClient()
        
        # Test simple prompt
        logger.info("\n2. Testing simple model call...")
        prompt = "What is the capital of France? Answer in one word."
        
        response = client.invoke_claude(
            prompt=prompt,
            system_prompt="You are a helpful assistant.",
            max_tokens=100,
            temperature=0.7
        )
        
        logger.info("\n3. Response received:")
        logger.info(f"   Text: {response['text'][:100]}...")
        logger.info(f"   Model: {response['model_id']}")
        logger.info(f"   Usage: {response['usage']}")
        
        logger.info("\n" + "=" * 80)
        logger.info("✓ BEDROCK LOGGING TEST PASSED")
        logger.info("=" * 80)
        
        return True
        
    except Exception as e:
        logger.error(f"\n✗ BEDROCK LOGGING TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_bedrock_logging()
    sys.exit(0 if success else 1)
