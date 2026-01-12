"""Workflow orchestration for medical record analysis system."""

# Import only what we need for the bedrock workflow
from .bedrock_workflow import BedrockWorkflow

__all__ = ["BedrockWorkflow"]