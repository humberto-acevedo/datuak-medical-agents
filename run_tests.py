#!/usr/bin/env python3
"""
Comprehensive test runner for the Medical Record Analysis System.
This script runs various test scenarios to validate system functionality.
"""

import os
import sys
import asyncio
import time
from pathlib import Path
from unittest.mock import patch, Mock
import json

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
    os.environ.setdefault("WORKFLOW_TIMEOUT_SECONDS", "300")

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
        """Mock S3 get_object operation."""
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
    
    def mock_put_object(Bucket, Key, Body):
        """Mock S3 put_object operation."""
        return {'ETag': '"mock-etag-12345"'}
    
    mock_s3_client = Mock()
    mock_s3_client.get_object.side_effect = mock_get_object
    mock_s3_client.put_object.side_effect = mock_put_object
    
    return mock_s3_client

async def test_workflow_component(test_name, test_func):
    """Run a single test component with timing and error handling."""
    print(f"🧪 Running {test_name}...")
    start_time = time.time()
    
    try:
        result = await test_func()
        execution_time = time.time() - start_time
        
        if result:
            print(f"   ✅ {test_name} PASSED ({execution_time:.2f}s)")
            return True
        else:
            print(f"   ❌ {test_name} FAILED ({execution_time:.2f}s)")
            return False
            
    except Exception as e:
        execution_time = time.time() - start_time
        print(f"   ❌ {test_name} ERROR ({execution_time:.2f}s): {str(e)}")
        return False

async def test_xml_parser():
    """Test XML Parser Agent."""
    try:
        from src.agents.xml_parser_agent import XMLParserAgent
        
        with patch('src.agents.xml_parser_agent.boto3.client', return_value=create_mock_s3_client()):
            parser = XMLParserAgent()
            result = parser.parse_patient_record("John Doe")
            
            # Validate result
            assert result is not None
            assert result.patient_id == "TEST_P001"
            assert result.name == "John Doe"
            assert result.age == 45
            
            return True
            
    except Exception as e:
        print(f"      Error: {e}")
        return False

async def test_medical_summarizer():
    """Test Medical Summarization Agent."""
    try:
        from src.agents.medical_summarization_agent import MedicalSummarizationAgent
        from src.models import PatientData
        
        # Create test patient data
        patient_data = PatientData(
            name="John Doe",
            patient_id="TEST_P001",
            age=45,
            gender="Male",
            medical_history={
                "diagnoses": ["Type 2 diabetes", "Hypertension"],
                "medications": ["Metformin", "Lisinopril"],
                "procedures": ["Blood test", "ECG"]
            }
        )
        
        summarizer = MedicalSummarizationAgent()
        result = summarizer.generate_summary(patient_data)
        
        # Validate result
        assert result is not None
        assert len(result.summary_text) > 50
        assert len(result.key_conditions) > 0
        
        return True
        
    except Exception as e:
        print(f"      Error: {e}")
        return False

async def test_research_correlator():
    """Test Research Correlation Agent."""
    try:
        from src.agents.research_correlation_agent import ResearchCorrelationAgent
        from src.models import PatientData, MedicalSummary
        
        # Create test data
        patient_data = PatientData(name="John Doe", patient_id="TEST_P001")
        medical_summary = MedicalSummary(
            summary_text="Patient has diabetes and hypertension",
            key_conditions=[
                {"name": "Type 2 diabetes", "confidence_score": 0.9},
                {"name": "Hypertension", "confidence_score": 0.8}
            ],
            chronic_conditions=["diabetes", "hypertension"],
            medications=["metformin", "lisinopril"]
        )
        
        correlator = ResearchCorrelationAgent()
        result = correlator.correlate_research(patient_data, medical_summary)
        
        # Validate result
        assert result is not None
        assert result.analysis_confidence > 0
        assert len(result.insights) > 0
        
        return True
        
    except Exception as e:
        print(f"      Error: {e}")
        return False

async def test_quality_assurance():
    """Test Quality Assurance System."""
    try:
        from src.utils.quality_assurance import initialize_quality_assurance
        from src.models import PatientData, MedicalSummary, ResearchAnalysis, AnalysisReport
        from datetime import datetime
        
        # Initialize QA system
        qa_engine = initialize_quality_assurance()
        
        # Create test report
        patient_data = PatientData(name="John Doe", patient_id="TEST_P001", age=45)
        medical_summary = MedicalSummary(
            summary_text="Patient has well-controlled diabetes and hypertension",
            key_conditions=[
                {"name": "Type 2 Diabetes", "confidence_score": 0.95},
                {"name": "Hypertension", "confidence_score": 0.88}
            ],
            chronic_conditions=["diabetes", "hypertension"],
            medications=["metformin", "lisinopril"]
        )
        research_analysis = ResearchAnalysis(
            research_findings=[],
            analysis_confidence=0.8,
            insights=["Good disease management"],
            recommendations=["Continue current treatment"]
        )
        
        analysis_report = AnalysisReport(
            report_id="TEST_R001",
            patient_data=patient_data,
            medical_summary=medical_summary,
            research_analysis=research_analysis,
            generated_at=datetime.now()
        )
        
        # Assess quality
        assessment = qa_engine.assess_analysis_quality(analysis_report)
        
        # Validate assessment
        assert assessment is not None
        assert assessment.overall_score > 0.5
        assert assessment.quality_level.value in ['excellent', 'good', 'acceptable']
        
        return True
        
    except Exception as e:
        print(f"      Error: {e}")
        return False

async def test_hallucination_prevention():
    """Test Hallucination Prevention System."""
    try:
        from src.utils.hallucination_prevention import initialize_hallucination_prevention
        
        # Initialize prevention system
        prevention_system = initialize_hallucination_prevention(strict_mode=False)
        
        # Test clean medical content
        clean_result = prevention_system.check_content(
            "Patient has diabetes and takes metformin 500mg twice daily",
            "medication"
        )
        
        # Test suspicious content
        suspicious_result = prevention_system.check_content(
            "Patient has magical healing powers from Harry Potter",
            "general"
        )
        
        # Validate results
        assert clean_result.risk_level.value in ['minimal', 'low']
        assert suspicious_result.risk_level.value in ['medium', 'high', 'critical']
        assert len(suspicious_result.detected_patterns) > 0
        
        return True
        
    except Exception as e:
        print(f"      Error: {e}")
        return False

async def test_complete_workflow():
    """Test complete end-to-end workflow."""
    try:
        from src.workflow.main_workflow import MainWorkflow
        
        # Mock S3 operations
        with patch('src.agents.xml_parser_agent.boto3.client', return_value=create_mock_s3_client()):
            # Initialize workflow
            workflow = MainWorkflow(enable_enhanced_logging=False)
            
            # Mock S3 persistence
            with patch.object(workflow.s3_persister, 'save_analysis_report', return_value="s3://test/report.json"):
                # Execute complete analysis
                result = await workflow.execute_complete_analysis("John Doe")
                
                # Validate complete workflow result
                assert result is not None
                assert result.patient_data.patient_id == "TEST_P001"
                assert result.medical_summary is not None
                assert result.research_analysis is not None
                assert 'quality_assessment' in result.processing_metadata
                
                # Validate quality assessment
                qa_data = result.processing_metadata['quality_assessment']
                assert qa_data['quality_level'] in ['excellent', 'good', 'acceptable']
                assert qa_data['overall_score'] > 0.5
                
                return True
        
    except Exception as e:
        print(f"      Error: {e}")
        return False

async def test_error_handling():
    """Test error handling scenarios."""
    try:
        from src.workflow.main_workflow import MainWorkflow
        from src.models.exceptions import XMLParsingError
        
        # Mock S3 to return error
        def mock_get_object_error(Bucket, Key):
            from botocore.exceptions import ClientError
            raise ClientError(
                error_response={'Error': {'Code': 'NoSuchKey', 'Message': 'Patient not found'}},
                operation_name='GetObject'
            )
        
        mock_s3_client = Mock()
        mock_s3_client.get_object.side_effect = mock_get_object_error
        
        with patch('src.agents.xml_parser_agent.boto3.client', return_value=mock_s3_client):
            workflow = MainWorkflow(enable_enhanced_logging=False)
            
            # This should raise an error
            try:
                await workflow.execute_complete_analysis("Nonexistent Patient")
                return False  # Should not reach here
            except Exception:
                return True  # Expected error
        
    except Exception as e:
        print(f"      Error: {e}")
        return False

async def run_performance_test():
    """Run performance test with timing."""
    try:
        from src.workflow.main_workflow import MainWorkflow
        
        with patch('src.agents.xml_parser_agent.boto3.client', return_value=create_mock_s3_client()):
            workflow = MainWorkflow(enable_enhanced_logging=False)
            
            with patch.object(workflow.s3_persister, 'save_analysis_report', return_value="s3://test/report.json"):
                start_time = time.time()
                result = await workflow.execute_complete_analysis("John Doe")
                execution_time = time.time() - start_time
                
                # Performance validation
                assert execution_time < 60  # Should complete within 60 seconds
                assert result is not None
                
                print(f"      Performance: {execution_time:.2f}s (target: <60s)")
                return True
        
    except Exception as e:
        print(f"      Error: {e}")
        return False

async def main():
    """Main test runner."""
    print("🏥 Medical Record Analysis System - Comprehensive Testing")
    print("=" * 70)
    
    # Setup test environment
    setup_test_environment()
    print("🔧 Test environment configured")
    print()
    
    # Define test suite
    test_suite = [
        ("XML Parser Agent", test_xml_parser),
        ("Medical Summarization Agent", test_medical_summarizer),
        ("Research Correlation Agent", test_research_correlator),
        ("Quality Assurance System", test_quality_assurance),
        ("Hallucination Prevention", test_hallucination_prevention),
        ("Complete Workflow", test_complete_workflow),
        ("Error Handling", test_error_handling),
        ("Performance Test", run_performance_test),
    ]
    
    # Run tests
    results = []
    total_start_time = time.time()
    
    print("🧪 Running Test Suite:")
    print("-" * 40)
    
    for test_name, test_func in test_suite:
        result = await test_workflow_component(test_name, test_func)
        results.append((test_name, result))
    
    total_execution_time = time.time() - total_start_time
    
    # Display results summary
    print()
    print("📊 Test Results Summary:")
    print("=" * 40)
    
    passed_tests = sum(1 for _, result in results if result)
    total_tests = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} {test_name}")
    
    print()
    print(f"📈 Overall Results:")
    print(f"   Tests Passed: {passed_tests}/{total_tests} ({passed_tests/total_tests*100:.1f}%)")
    print(f"   Total Time: {total_execution_time:.2f}s")
    
    if passed_tests == total_tests:
        print("🎉 ALL TESTS PASSED! System is ready for use.")
        return 0
    else:
        print("⚠️  Some tests failed. Please review the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))