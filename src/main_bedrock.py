#!/usr/bin/env python3
"""
Main entry point for Bedrock-based Medical Record Analysis System.

This version uses AWS Bedrock Claude models for medical summarization
and research analysis instead of the Python-based agents.
"""

import sys
import logging
import argparse
from datetime import datetime

from .workflow.bedrock_workflow import BedrockWorkflow
from .utils.enhanced_logging import initialize_logging
from .utils.audit_logger import initialize_audit_logging
from .cli import EnhancedCLI

# Initialize logging
initialize_logging()
logger = logging.getLogger(__name__)


def print_banner():
    """Print the application banner."""
    print("\n" + "=" * 80)
    print("🤖 MEDICAL RECORD ANALYSIS SYSTEM - BEDROCK CLAUDE AI")
    print("=" * 80)
    print("\nPowered by AWS Bedrock and Anthropic Claude AI")
    print("Advanced medical analysis with evidence-based recommendations")
    print("=" * 80 + "\n")


def print_results(results: dict):
    """Print analysis results using enhanced CLI."""
    cli = EnhancedCLI()
    cli.display_bedrock_results(results)


def analyze_patient(patient_name: str, verbose: bool = False) -> int:
    """Analyze a specific patient using Bedrock Claude AI."""
    try:
        if verbose:
            logging.getLogger().setLevel(logging.DEBUG)
        
        print(f"\n🔍 Analyzing medical records for: {patient_name}")
        print("⏳ This may take a minute...\n")
        
        # Initialize workflow
        workflow = BedrockWorkflow()
        
        # Execute analysis
        results = workflow.execute_analysis(patient_name)
        
        # Print results using enhanced CLI
        print_results(results)
        
        print("✅ Analysis completed successfully!\n")
        return 0
        
    except FileNotFoundError as e:
        print(f"\n❌ Error: Patient record not found - {str(e)}")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        logger.error(f"Analysis failed: {str(e)}", exc_info=True)
        return 1


def main():
    """Main entry point with command-line argument support."""
    parser = argparse.ArgumentParser(
        description="Medical Record Analysis System - Bedrock Claude AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.main_bedrock                    # Interactive mode
  python -m src.main_bedrock --patient "Jane Smith"  # Direct analysis
  python -m src.main_bedrock --patient "Jane Smith" --verbose  # With verbose logging
        """
    )
    
    parser.add_argument(
        '--patient', '-p',
        type=str,
        help='Patient name to analyze directly'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    try:
        print_banner()
        
        if args.patient:
            # Direct analysis mode
            return analyze_patient(args.patient, args.verbose)
        else:
            # Interactive mode
            patient_name = input("Enter patient name: ").strip()
            
            if not patient_name:
                print("❌ Error: Patient name cannot be empty")
                return 1
            
            return analyze_patient(patient_name, args.verbose)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Analysis cancelled by user")
        return 130
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        logger.error(f"Main function failed: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
