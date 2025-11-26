#!/usr/bin/env python3
"""
Main entry point for Bedrock-based Medical Record Analysis System.

This version uses AWS Bedrock Claude models for medical summarization
and research analysis instead of the Python-based agents.
"""

import sys
import logging
from datetime import datetime

from .workflow.bedrock_workflow import BedrockWorkflow
from .utils.enhanced_logging import initialize_logging

# Initialize logging
initialize_logging()
logger = logging.getLogger(__name__)


def print_banner():
    """Print application banner."""
    print("\n" + "=" * 80)
    print("  MEDICAL RECORD ANALYSIS SYSTEM")
    print("  Powered by AWS Bedrock & Claude AI")
    print("=" * 80 + "\n")


def print_results(results: dict):
    """Print analysis results in a formatted way."""
    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    
    print(f"\n📋 Patient Information:")
    print(f"   Name: {results['patient_name']}")
    print(f"   ID: {results['patient_id']}")
    
    print(f"\n⏱️  Processing Time: {results['duration_seconds']:.2f} seconds")
    print(f"🤖 AI Model: {results['model_info']['model_name']}")
    print(f"📍 Region: {results['model_info']['region']}")
    
    print(f"\n" + "-" * 80)
    print("MEDICAL SUMMARY")
    print("-" * 80)
    print(results['medical_summary'])
    
    print(f"\n" + "-" * 80)
    print("RESEARCH-BASED ANALYSIS")
    print("-" * 80)
    print(results['research_analysis'])
    
    print(f"\n" + "-" * 80)
    print(f"📄 Report saved to S3: {results['s3_key']}")
    print(f"🆔 Report ID: {results['report']['report_id']}")
    print("-" * 80 + "\n")


def main():
    """Main entry point."""
    try:
        print_banner()
        
        # Get patient name from user
        patient_name = input("Enter patient name: ").strip()
        
        if not patient_name:
            print("❌ Error: Patient name cannot be empty")
            return 1
        
        print(f"\n🔍 Analyzing medical records for: {patient_name}")
        print("⏳ This may take a minute...\n")
        
        # Initialize workflow
        workflow = BedrockWorkflow()
        
        # Execute analysis
        results = workflow.execute_analysis(patient_name)
        
        # Print results
        print_results(results)
        
        print("✅ Analysis completed successfully!\n")
        return 0
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Analysis cancelled by user")
        return 130
    except FileNotFoundError as e:
        print(f"\n❌ Error: Patient record not found - {str(e)}")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        logger.error(f"Analysis failed: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
