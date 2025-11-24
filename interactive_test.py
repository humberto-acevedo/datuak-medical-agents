#!/usr/bin/env python3
"""
Interactive test script for the Medical Record Analysis System.
This allows you to test specific scenarios and see detailed outputs.
"""

import os
import sys
import asyncio
from pathlib import Path
from unittest.mock import patch, Mock

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def setup_test_environment():
    """Set up test environment variables."""
    os.environ.setdefault("AWS_ACCESS_KEY_ID", "test_access_key")
    os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test_secret_key")
    os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
    os.environ.setdefault("S3_BUCKET_NAME", "test-medical-records-bucket")
    os.environ.setdefault("LOG_LEVEL", "INFO")
    os.environ.setdefault("ENABLE_AUDIT_LOGGING", "true")
    os.environ.setdefault("QUALITY_ASSURANCE_STRICT_MODE", "false")

def create_mock_s3_client():
    """Create mock S3 client with test data."""
    from tests.fixtures.sample_patient_data import (
        SAMPLE_PATIENT_XML_GOOD, 
        SAMPLE_PATIENT_XML_COMPLEX, 
        SAMPLE_PATIENT_XML_MINIMAL
    )
    
    mock_patients = {
        "john_doe.xml": SAMPLE_PATIENT_XML_GOOD,
        "jane_smith.xml": SAMPLE_PATIENT_XML_COMPLEX,
        "bob_johnson.xml": SAMPLE_PATIENT_XML_MINIMAL,
        "test_patient.xml": SAMPLE_PATIENT_XML_GOOD,
    }
    
    def mock_get_object(Bucket, Key):
        filename = Key.split('/')[-1]
        if filename in mock_patients:
            xml_content = mock_patients[filename]
            return {
                'Body': Mock(read=Mock(return_value=xml_content.encode('utf-8')))
            }
        
        from botocore.exceptions import ClientError
        raise ClientError(
            error_response={'Error': {'Code': 'NoSuchKey', 'Message': 'Patient not found'}},
            operation_name='GetObject'
        )
    
    mock_s3_client = Mock()
    mock_s3_client.get_object.side_effect = mock_get_object
    mock_s3_client.put_object.return_value = {'ETag': '"mock-etag"'}
    
    return mock_s3_client

async def test_single_patient(patient_name):
    """Test analysis for a single patient."""
    print(f"\n🏥 Analyzing Patient: {patient_name}")
    print("=" * 50)
    
    try:
        from src.workflow.main_workflow import MainWorkflow
        
        with patch('src.agents.xml_parser_agent.boto3.client', return_value=create_mock_s3_client()):
            workflow = MainWorkflow(enable_enhanced_logging=False)
            
            with patch.object(workflow.s3_persister, 'save_analysis_report', return_value="s3://test/report.json"):
                # Execute analysis
                result = await workflow.execute_complete_analysis(patient_name)
                
                # Display results
                print(f"✅ Analysis completed successfully!")
                print(f"📋 Report ID: {result.report_id}")
                print(f"👤 Patient: {result.patient_data.name} (ID: {result.patient_data.patient_id})")
                print(f"📊 Age: {result.patient_data.age}, Gender: {result.patient_data.gender}")
                
                print(f"\n📝 Medical Summary:")
                print(f"   Summary Length: {len(result.medical_summary.summary_text)} characters")
                print(f"   Key Conditions: {len(result.medical_summary.key_conditions)}")
                print(f"   Medications: {len(result.medical_summary.medications)}")
                
                # Display conditions
                if result.medical_summary.key_conditions:
                    print(f"\n🔍 Key Conditions:")
                    for i, condition in enumerate(result.medical_summary.key_conditions[:3], 1):
                        if isinstance(condition, dict):
                            name = condition.get('name', 'Unknown')
                            confidence = condition.get('confidence_score', 0)
                            print(f"   {i}. {name} (confidence: {confidence:.2f})")
                        else:
                            print(f"   {i}. {condition}")
                
                # Display medications
                if result.medical_summary.medications:
                    print(f"\n💊 Medications:")
                    for i, med in enumerate(result.medical_summary.medications[:3], 1):
                        print(f"   {i}. {med}")
                
                print(f"\n🔬 Research Analysis:")
                print(f"   Research Findings: {len(result.research_analysis.research_findings)}")
                print(f"   Analysis Confidence: {result.research_analysis.analysis_confidence:.2f}")
                print(f"   Insights: {len(result.research_analysis.insights)}")
                print(f"   Recommendations: {len(result.research_analysis.recommendations)}")
                
                # Display quality assessment
                if 'quality_assessment' in result.processing_metadata:
                    qa_data = result.processing_metadata['quality_assessment']
                    print(f"\n🛡️ Quality Assessment:")
                    print(f"   Quality Level: {qa_data['quality_level']}")
                    print(f"   Overall Score: {qa_data['overall_score']:.3f}")
                    print(f"   Hallucination Risk: {qa_data['hallucination_risk']:.3f}")
                    print(f"   Validation Issues: {len(qa_data['validation_issues'])}")
                
                return True
                
    except Exception as e:
        print(f"❌ Analysis failed: {str(e)}")
        return False

async def test_quality_assurance_demo():
    """Demonstrate quality assurance features."""
    print(f"\n🛡️ Quality Assurance Demonstration")
    print("=" * 50)
    
    try:
        from src.utils.hallucination_prevention import initialize_hallucination_prevention
        
        prevention_system = initialize_hallucination_prevention(strict_mode=False)
        
        test_cases = [
            ("Clean Medical Content", "Patient has diabetes and takes metformin 500mg twice daily"),
            ("Suspicious Content", "Patient has magical healing powers from Harry Potter"),
            ("Invalid Medication", "Patient prescribed fictionaldrugname 100mg daily"),
            ("Contradictory Statement", "Patient is asymptomatic but has severe chronic pain"),
        ]
        
        for test_name, content in test_cases:
            print(f"\n🧪 Testing: {test_name}")
            print(f"   Content: {content}")
            
            result = prevention_system.check_content(content, "general")
            
            print(f"   Risk Level: {result.risk_level.value}")
            print(f"   Confidence: {result.confidence:.3f}")
            print(f"   Requires Review: {result.requires_human_review}")
            
            if result.detected_patterns:
                print(f"   Detected Issues:")
                for pattern in result.detected_patterns[:2]:
                    print(f"     - {pattern}")
        
        return True
        
    except Exception as e:
        print(f"❌ Quality assurance demo failed: {str(e)}")
        return False

async def test_performance_demo():
    """Demonstrate system performance."""
    print(f"\n⚡ Performance Demonstration")
    print("=" * 50)
    
    try:
        import time
        from src.workflow.main_workflow import MainWorkflow
        
        with patch('src.agents.xml_parser_agent.boto3.client', return_value=create_mock_s3_client()):
            workflow = MainWorkflow(enable_enhanced_logging=False)
            
            with patch.object(workflow.s3_persister, 'save_analysis_report', return_value="s3://test/report.json"):
                
                # Test multiple patients for performance
                patients = ["John Doe", "Jane Smith", "Bob Johnson"]
                
                for patient in patients:
                    print(f"\n🏃 Processing {patient}...")
                    start_time = time.time()
                    
                    result = await workflow.execute_complete_analysis(patient)
                    
                    execution_time = time.time() - start_time
                    print(f"   ✅ Completed in {execution_time:.2f}s")
                    print(f"   📊 Quality Score: {result.processing_metadata['quality_assessment']['overall_score']:.3f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Performance demo failed: {str(e)}")
        return False

def display_menu():
    """Display interactive menu."""
    print("\n🏥 Medical Record Analysis System - Interactive Testing")
    print("=" * 60)
    print("Available Test Options:")
    print("1. Test John Doe (Diabetes patient)")
    print("2. Test Jane Smith (Cancer patient)")
    print("3. Test Bob Johnson (Asthma patient)")
    print("4. Quality Assurance Demo")
    print("5. Performance Demo")
    print("6. Run All Tests")
    print("0. Exit")
    print()

async def main():
    """Main interactive testing function."""
    setup_test_environment()
    
    while True:
        display_menu()
        
        try:
            choice = input("Select test option (0-6): ").strip()
            
            if choice == "0":
                print("\n👋 Goodbye!")
                break
            elif choice == "1":
                await test_single_patient("John Doe")
            elif choice == "2":
                await test_single_patient("Jane Smith")
            elif choice == "3":
                await test_single_patient("Bob Johnson")
            elif choice == "4":
                await test_quality_assurance_demo()
            elif choice == "5":
                await test_performance_demo()
            elif choice == "6":
                print("\n🧪 Running comprehensive tests...")
                os.system("python run_tests.py")
            else:
                print("❌ Invalid option. Please select 0-6.")
            
            input("\nPress Enter to continue...")
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            input("Press Enter to continue...")

if __name__ == "__main__":
    asyncio.run(main())