#!/usr/bin/env python3
"""
Quick launch script for testing the Medical Record Analysis System prototype.
This script sets up a minimal test environment and launches the system.
"""

import os
import sys
import asyncio
import argparse
import json
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))
# Make boto3/botocore load shared config (so SSO profiles work like the AWS CLI)
os.environ.setdefault("AWS_SDK_LOAD_CONFIG", "1")

def setup_test_environment(verbose: bool = False):
    """Set up minimal test environment variables."""
    print("⚠️  Note: This prototype requires real AWS credentials and S3 bucket.")
    print("   For testing without AWS, use the test suite: pytest tests/")
    print()
    
    # Check if AWS credentials are configured via several supported sources
    from pathlib import Path as _Path

    has_env_creds = bool(os.environ.get("AWS_ACCESS_KEY_ID") and os.environ.get("AWS_SECRET_ACCESS_KEY"))
    has_profile = bool(os.environ.get("AWS_PROFILE") or os.environ.get("AWS_DEFAULT_PROFILE"))
    has_shared_files = _Path.home().joinpath('.aws', 'credentials').exists() or _Path.home().joinpath('.aws', 'config').exists()
    has_sso_cache = _Path.home().joinpath('.aws', 'sso', 'cache').exists()

    has_aws_creds = has_env_creds or has_profile or has_shared_files or has_sso_cache
    
    if not has_aws_creds:
        print("❌ AWS credentials not found!")
        print()
        print("To use this prototype, configure AWS credentials:")
        print("   export AWS_ACCESS_KEY_ID=your_access_key")
        print("   export AWS_SECRET_ACCESS_KEY=your_secret_key")
        print("   export AWS_DEFAULT_REGION=us-east-1")
        print("Or, if you use SSO/profile, set an AWS profile and enable SDK config loading:")
        print("   export AWS_PROFILE=your_profile")
        print("   export AWS_SDK_LOAD_CONFIG=1")
        print()
        print("Or run: aws configure")
        print()
        print("For testing without AWS, use: pytest tests/")
        return False

    # Auto-detect and set AWS_PROFILE if not set but default profile exists
    if not has_profile and has_shared_files:
        # Try to read default profile from config
        config_file = _Path.home().joinpath('.aws', 'config')
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    content = f.read()
                    if '[default]' in content or '[profile default]' in content:
                        os.environ.setdefault("AWS_PROFILE", "default")
                        print("🔍 Auto-detected AWS default profile")
                        has_profile = True
            except Exception:
                pass

    # If verbose, provide a credential source hint (non-sensitive)
    if verbose:
        cred_source = "unknown"
        if os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"):
            cred_source = "environment"
        elif os.getenv("AWS_PROFILE"):
            cred_source = f"profile:{os.getenv('AWS_PROFILE')}"
        else:
            from pathlib import Path as _Path
            if _Path.home().joinpath('.aws', 'credentials').exists():
                cred_source = "shared_credentials_file"
            else:
                cred_source = "role_or_imds"

        print(f"🔍 Credential source hint: {cred_source}")
    
    # Set system configuration
    os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
    os.environ.setdefault("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))
    os.environ.setdefault("S3_BUCKET_NAME", "patient-records-20251024")
    os.environ.setdefault("LOG_LEVEL", "INFO")
    os.environ.setdefault("ENABLE_AUDIT_LOGGING", "true")
    os.environ.setdefault("QUALITY_ASSURANCE_STRICT_MODE", "false")  # Relaxed for testing
    os.environ.setdefault("WORKFLOW_TIMEOUT_SECONDS", "300")
    
    print("✅ AWS credentials found")
    print("🔧 Test environment configured")
    print(f"   AWS Region: {os.environ['AWS_DEFAULT_REGION']}")
    print(f"   S3 Bucket: {os.environ['S3_BUCKET_NAME']}")
    if os.environ.get("AWS_PROFILE"):
        print(f"   AWS Profile: {os.environ['AWS_PROFILE']}")
    print(f"   Log Level: {os.environ['LOG_LEVEL']}")
    print()
    print("💡 Tip: Use --bedrock flag to use AWS Bedrock Claude AI")
    print("   Example: python launch_prototype.py --bedrock")
    print()
    return True

def check_dependencies():
    """Check if required dependencies are available."""
    required_modules = [
        "boto3", "lxml", "pydantic", "requests", "structlog", "pytest"
    ]
    
    missing_modules = []
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)
    
    if missing_modules:
        print("❌ Missing required dependencies:")
        for module in missing_modules:
            print(f"   - {module}")
        print("\nPlease install dependencies with:")
        print("   python3 -m venv venv")
        print("   source venv/bin/activate  # On macOS/Linux")
        print("   python3 -m pip install -r requirements.txt")
        return False
    
    print("✅ All required dependencies found")
    return True

async def run_prototype_test(use_bedrock: bool = False, use_bedrock_agent: bool = False, 
                            agent_id: str = None, agent_alias_id: str = None):
    """Run a quick prototype test."""
    if use_bedrock_agent:
        print("🚀 Starting Medical Record Analysis System - Bedrock Agent Version")
    elif use_bedrock:
        print("🚀 Starting Medical Record Analysis System - Bedrock Claude Version")
    else:
        print("🚀 Starting Medical Record Analysis System - Python Agents Version")
    print("=" * 60)
    
    try:
        if use_bedrock_agent:
            # Import Bedrock Agent workflow
            from src.workflow.bedrock_workflow import BedrockWorkflow
            
            print("📋 Bedrock Agent components loaded successfully")
            print(f"🤖 Using AWS Bedrock Agent: {agent_id}")
            print("🏥 Launching Medical Record Analysis System...")
            print()
            
            # Get patient name interactively
            patient_name = input("Enter patient name: ").strip()
            
            if not patient_name:
                print("❌ Error: Patient name cannot be empty")
                return 1
            
            # Initialize workflow with Bedrock Agent
            workflow = BedrockWorkflow(
                use_bedrock_agent=True,
                agent_id=agent_id,
                agent_alias_id=agent_alias_id
            )
            
            # Execute analysis
            result = workflow.execute_analysis(patient_name)
            
            # Display results
            print("\n" + "=" * 80)
            print("✅ ANALYSIS COMPLETE")
            print("=" * 80)
            print(json.dumps(result, indent=2, default=str))
            
            return 0
            
        elif use_bedrock:
            # Import Bedrock components (not main, to avoid argument parsing conflict)
            from src.main_bedrock import print_banner, analyze_patient
            
            print("📋 Bedrock components loaded successfully")
            print("🤖 Using AWS Bedrock Claude AI for analysis")
            print("🏥 Launching Medical Record Analysis System...")
            print()
            
            # Show banner
            print_banner()
            
            # Get patient name interactively
            patient_name = input("Enter patient name: ").strip()
            
            if not patient_name:
                print("❌ Error: Patient name cannot be empty")
                return 1
            
            # Run the Bedrock analysis (synchronous)
            result = analyze_patient(patient_name, verbose=False)
            return result
        else:
            # Import original main components
            from src.main import main_async
            
            print("📋 System components loaded successfully")
            print("🐍 Using Python-based agents for analysis")
            print("🏥 Launching Medical Record Analysis System...")
            print()
            
            # Run the main application
            result = await main_async()
            return result
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're running from the project root directory")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

def main():
    """Main entry point for prototype testing."""
    print("🏥 Medical Record Analysis System - Prototype Launcher")
    print("=" * 60)
    
    parser = argparse.ArgumentParser(description="Launch prototype tests")
    parser.add_argument('-v', '--verbose', action='store_true', help='Show credential diagnostics')
    parser.add_argument('--bedrock', action='store_true', 
                       help='Use AWS Bedrock Claude AI instead of Python agents')
    parser.add_argument('--bedrock-agent', action='store_true',
                       help='Use AWS Bedrock Agent (requires deployed agent)')
    parser.add_argument('--agent-id', type=str,
                       help='Bedrock Agent ID (required with --bedrock-agent)')
    parser.add_argument('--agent-alias-id', type=str,
                       help='Bedrock Agent Alias ID (required with --bedrock-agent)')
    parser.add_argument('--python', action='store_true',
                       help='Use Python-based agents (default)')
    args = parser.parse_args()

    # Determine which version to use
    use_bedrock = args.bedrock
    use_bedrock_agent = args.bedrock_agent
    
    # Validate bedrock-agent requirements
    if use_bedrock_agent and (not args.agent_id or not args.agent_alias_id):
        print("❌ Error: --bedrock-agent requires --agent-id and --agent-alias-id")
        print("   Example: python launch_prototype.py --bedrock-agent --agent-id AGENT123 --agent-alias-id ALIAS456")
        return 1
    
    # Check dependencies
    if not check_dependencies():
        return 1
    
    # Setup test environment
    if not setup_test_environment(verbose=args.verbose):
        return 1
    
    # Show version info
    if use_bedrock_agent:
        print("🤖 Mode: AWS Bedrock Agent")
        print(f"   - Agent ID: {args.agent_id}")
        print(f"   - Agent Alias: {args.agent_alias_id}")
        print("   - Agent orchestrates full workflow via Lambda")
        print()
    elif use_bedrock:
        print("🤖 Mode: AWS Bedrock Claude AI")
        print("   - Medical summarization: Claude 3.5 Haiku")
        print("   - Research analysis: Claude 3.5 Haiku")
        print("   - Cost: ~$0.001 per analysis (very affordable!)")
        print()
    else:
        print("🐍 Mode: Python-based Agents")
        print("   - Medical summarization: Python algorithms")
        print("   - Research correlation: Simulated research database")
        print()
    
    # Run prototype
    try:
        # Both versions now run through asyncio for consistency
        return asyncio.run(run_prototype_test(
            use_bedrock=use_bedrock,
            use_bedrock_agent=use_bedrock_agent,
            agent_id=args.agent_id,
            agent_alias_id=args.agent_alias_id
        ))
    except KeyboardInterrupt:
        print("\n\n👋 Prototype test interrupted by user")
        return 0
    except Exception as e:
        print(f"\n❌ Prototype test failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())