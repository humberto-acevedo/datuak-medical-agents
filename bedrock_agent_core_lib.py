#!/usr/bin/env python3
"""
Bedrock Agent Core Library for Medical Record Analysis.
Minimal implementation for AWS Bedrock agent-core deployment.
"""

import json
import logging
from typing import Dict, Any
from datetime import datetime

# Add current directory to Python path for imports
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from bedrock_agentcore import BedrockAgentCoreApp
    from src.workflow.bedrock_workflow import BedrockWorkflow
    from src.utils.enhanced_logging import initialize_logging
    
    # Initialize logging with DEBUG level and S3 upload
    initialize_logging(log_dir="/tmp/logs", log_level="DEBUG")
    logger = logging.getLogger(__name__)
    logger.info("All imports successful")
    
except ImportError as e:
    # Fallback logging if enhanced logging fails
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    logger.error(f"Import failed: {e}", exc_info=True)
    raise
initialize_logging(log_level="DEBUG")
logger = logging.getLogger(__name__)

app = BedrockAgentCoreApp()

@app.entrypoint
def handle_request(payload: dict) -> dict:
    """
    Handle incoming requests for medical record analysis.
    
    Args:
        payload: Request payload containing patient information
        
    Returns:
        Analysis results as dictionary
    """
    try:
        logger.debug(f"Received payload: {payload}")
        
        # Extract patient name from payload
        patient_name = payload.get('patient_name') or payload.get('input', {}).get('patient_name')
        
        if not patient_name:
            logger.error("No patient name found in payload")
            return {
                'success': False,
                'error': 'Patient name is required',
                'timestamp': datetime.now().isoformat()
            }
        
        logger.info(f"Processing analysis request for patient: {patient_name}")
        
        # Initialize workflow
        logger.debug("Initializing BedrockWorkflow")
        workflow = BedrockWorkflow()
        logger.debug("BedrockWorkflow initialized successfully")
        
        # Execute analysis
        logger.debug("Starting workflow execution")
        results = workflow.execute_analysis(patient_name)
        logger.debug(f"Workflow execution completed: {type(results)}")
        
        # Return formatted response
        return {
            'success': True,
            'patient_name': patient_name,
            'analysis': results,
            'timestamp': datetime.now().isoformat()
        }
        
    except ImportError as e:
        logger.error(f"Import error: {str(e)}", exc_info=True)
        return {
            'success': False,
            'error': f'Import error: {str(e)}',
            'error_type': 'ImportError',
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__,
            'timestamp': datetime.now().isoformat()
        }

if __name__ == "__main__":
    logger.info("Starting Bedrock Agent Core application")
    app.run()
