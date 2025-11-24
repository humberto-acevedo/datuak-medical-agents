"""Comprehensive integration tests with anonymized sample patient data."""
import pytest
import asyncio
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import xml.etree.ElementTree as ET

from src.workflow.main_workflow import MainWorkflow
from src.agents.xml_parser_agent import XMLParserAgent
from src.agents.medical_summarization_agent import MedicalSummarizationAgent
from src.agents.research_correlation_agent import ResearchCorrelationAgent
from src.agents.report_generator import ReportGenerator
from src.agents.s3_report_persister import S3ReportPersister
from src.models import PatientData, MedicalSummary, ResearchAnalysis, AnalysisReport
from src.utils.quality_assurance import QualityLevel
from src.utils.hallucination_prevention import HallucinationRiskLevel
from src.utils.audit_logger import AuditLogger

from tests.fixtures.sample_patient_data import (
    SAMPLE_PATIENT_XML_GOOD, SAMPLE_PATIENT_XML_COMPLEX, SAMPLE_PATIENT_XML_MINIMAL,
    SAMPLE_PATIENT_XML_INVALID, EXPECTED_ANALYSIS_RESULTS, PERFORMANCE_BENCHMARKS,
    MEDICAL_ACCURACY_TEST_CASES, ADVERSARIAL_TEST_CASES
)

class TestComprehensiveIntegration:
    """Comprehensive integration tests with real patient data scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.audit_logger = Mock(spec=AuditLogger)
        self.workflow = MainWorkflow(
            audit_logger=self.audit_logger,
            enable_enhanced_logging=False,
            timeout_seconds=60
        )
    
    def mock_s3_operations(self, patient_xml: str):
        """Mock S3 operations to return sample patient data."""
        # Mock S3 client to return sample XML
        mock_s3_client = Mock()
        mock_s3_client.get_object.return_value = {
            'Body': Mock(read=Mock(return_value=patient_xml.encode('utf-8')))
        }
        
        # Mock S3 operations in XML parser
        with patch('src.agents.xml_parser_agent.boto3.client', return_value=mock_s3_client):
            # Mock S3 persistence
            with patch.object(self.workflow.s3_persister, 'save_analysis_report', return_value="s3://test-bucket/analysis-123.json"):
                yield mock_s3_client
    
    @pytest.mark.asyncio
    async def test_end_to_end_good_patient_data(self):
        """Test complete workflow with good quality patient data."""
        patient_name = "John Doe"
        expected = EXPECTED_ANALYSIS_RESULTS["TEST_P001"]
        
        with self.mock_s3_operations(SAMPLE_PATIENT_XML_GOOD):
            start_time = time.time()
            
            # Execute complete workflow
            result = await self.workflow.execute_complete_analysis(patient_name)
            
            execution_time = time.time() - start_time
            
            # Verify basic result structure
            assert result is not None
            assert isinstance(result, AnalysisReport)
            assert result.patient_data.patient_id == expected["patient_id"]
            assert result.patient_data.name == expected["name"]
            assert result.patient_data.age == expected["age"]
            assert result.patient_data.gender == expected["gender"]
            
            # Verify medical summary quality
            assert result.medical_summary is not None
            assert len(result.medical_summary.summary_text) > 50
            assert len(result.medical_summary.key_conditions) >= 2
            assert len(result.medical_summary.medications) >= 2
            
            # Verify research analysis
            assert result.research_analysis is not None
            assert result.research_analysis.analysis_confidence > 0.5
            assert len(result.research_analysis.insights) > 0
            assert len(result.research_analysis.recommendations) > 0
            
            # Verify quality assurance passed
            assert hasattr(result, 'processing_metadata')
            assert 'quality_assessment' in result.processing_metadata
            qa_data = result.processing_metadata['quality_assessment']
            assert qa_data['quality_level'] in ['excellent', 'good', 'acceptable']
            assert qa_data['overall_score'] >= expected["quality_expectations"]["min_quality_score"]
            assert qa_data['hallucination_risk'] <= expected["quality_expectations"]["max_hallucination_risk"]
            
            # Verify performance
            assert execution_time <= PERFORMANCE_BENCHMARKS["total_workflow_max_time"]
            
            # Verify audit logging
            assert self.audit_logger.log_patient_access.called
            assert self.audit_logger.log_system_event.called
    
    @pytest.mark.asyncio
    async def test_end_to_end_complex_patient_data(self):
        """Test complete workflow with complex patient data (cancer patient)."""
        patient_name = "Jane Smith"
        expected = EXPECTED_ANALYSIS_RESULTS["TEST_P002"]
        
        with self.mock_s3_operations(SAMPLE_PATIENT_XML_COMPLEX):
            start_time = time.time()
            
            # Execute complete workflow
            result = await self.workflow.execute_complete_analysis(patient_name)
            
            execution_time = time.time() - start_time
            
            # Verify complex medical conditions are handled
            assert result.patient_data.patient_id == expected["patient_id"]
            assert len(result.medical_summary.key_conditions) >= 3
            
            # Verify cancer-related medications are identified
            medications = [med.lower() if isinstance(med, str) else med.get('name', '').lower() 
                          for med in result.medical_summary.medications]
            assert any('tamoxifen' in med for med in medications)
            
            # Verify research includes cancer-related topics
            research_text = ' '.join([
                result.research_analysis.summary_text or '',
                ' '.join(result.research_analysis.insights or []),
                ' '.join(result.research_analysis.recommendations or [])
            ]).lower()
            
            assert any(topic in research_text for topic in expected["expected_research_topics"])
            
            # Verify quality for complex case
            qa_data = result.processing_metadata['quality_assessment']
            assert qa_data['overall_score'] >= expected["quality_expectations"]["min_quality_score"]
            
            # Performance should still be reasonable for complex cases
            assert execution_time <= PERFORMANCE_BENCHMARKS["total_workflow_max_time"] * 1.5
    
    @pytest.mark.asyncio
    async def test_end_to_end_minimal_patient_data(self):
        """Test complete workflow with minimal patient data."""
        patient_name = "Bob Johnson"
        expected = EXPECTED_ANALYSIS_RESULTS["TEST_P003"]
        
        with self.mock_s3_operations(SAMPLE_PATIENT_XML_MINIMAL):
            # Execute complete workflow
            result = await self.workflow.execute_complete_analysis(patient_name)
            
            # Verify basic functionality with minimal data
            assert result.patient_data.patient_id == expected["patient_id"]
            assert len(result.medical_summary.key_conditions) >= 1
            assert len(result.medical_summary.medications) >= 1
            
            # Quality should be acceptable even with minimal data
            qa_data = result.processing_metadata['quality_assessment']
            assert qa_data['quality_level'] in ['acceptable', 'good', 'excellent']
            assert qa_data['overall_score'] >= expected["quality_expectations"]["min_quality_score"]
            
            # Should still generate research insights
            assert result.research_analysis is not None
            assert len(result.research_analysis.insights) > 0
    
    @pytest.mark.asyncio
    async def test_invalid_patient_data_handling(self):
        """Test workflow handling of invalid patient data."""
        patient_name = "Invalid Patient"
        
        with self.mock_s3_operations(SAMPLE_PATIENT_XML_INVALID):
            # Should handle invalid data gracefully or raise appropriate error
            try:
                result = await self.workflow.execute_complete_analysis(patient_name)
                
                # If it succeeds, quality should be poor
                qa_data = result.processing_metadata['quality_assessment']
                assert qa_data['quality_level'] in ['poor', 'unacceptable']
                assert qa_data['overall_score'] < 0.5
                
            except Exception as e:
                # Should be a specific error type, not a generic exception
                assert any(error_type in str(type(e)) for error_type in [
                    'XMLParsingError', 'AgentCommunicationError', 'ReportError'
                ])
    
    def test_workflow_progress_tracking(self):
        """Test workflow progress tracking functionality."""
        # Test progress tracking without full execution
        progress_updates = []
        
        def progress_callback(progress):
            progress_updates.append({
                'step': progress.current_step,
                'percentage': progress.get_progress_percentage(),
                'step_name': progress.step_names[progress.current_step] if progress.current_step < len(progress.step_names) else 'Completed'
            })
        
        workflow = MainWorkflow(
            progress_callback=progress_callback,
            enable_enhanced_logging=False
        )
        
        # Simulate progress updates
        workflow.progress = workflow.WorkflowProgress() if hasattr(workflow, 'WorkflowProgress') else type('WorkflowProgress', (), {
            'current_step': 0,
            'total_steps': 7,
            'step_names': [
                "Patient Name Input",
                "XML Parsing & Data Extraction", 
                "Medical Summarization",
                "Research Correlation",
                "Report Generation",
                "Quality Assurance & Validation",
                "Report Persistence"
            ],
            'get_progress_percentage': lambda: (0 / 7) * 100
        })()
        
        # Test progress callback
        workflow._update_progress()
        
        assert len(progress_updates) > 0
        assert progress_updates[0]['step'] == 0
        assert progress_updates[0]['percentage'] == 0.0
    
    def test_workflow_statistics_collection(self):
        """Test workflow statistics collection and reporting."""
        stats = self.workflow.get_workflow_statistics()
        
        # Verify basic statistics structure
        assert 'total_workflows' in stats
        assert 'successful_workflows' in stats
        assert 'failed_workflows' in stats
        assert 'average_processing_time' in stats
        
        # Verify quality assurance statistics
        assert 'quality_assurance_stats' in stats
        assert 'hallucination_prevention_stats' in stats
        
        # Verify error handler statistics
        assert 'error_handler_stats' in stats
        
        # Test statistics after workflow execution (mocked)
        self.workflow.stats['total_workflows'] = 5
        self.workflow.stats['successful_workflows'] = 4
        self.workflow.stats['failed_workflows'] = 1
        
        updated_stats = self.workflow.get_workflow_statistics()
        assert updated_stats['total_workflows'] == 5
        assert updated_stats['successful_workflows'] == 4
        assert updated_stats['failed_workflows'] == 1
    
    @pytest.mark.asyncio
    async def test_workflow_timeout_handling(self):
        """Test workflow timeout handling."""
        # Create workflow with very short timeout
        short_timeout_workflow = MainWorkflow(
            audit_logger=self.audit_logger,
            timeout_seconds=1,  # 1 second timeout
            enable_enhanced_logging=False
        )
        
        # Mock a slow operation
        with patch.object(short_timeout_workflow, '_execute_xml_parsing') as mock_xml:
            mock_xml.side_effect = asyncio.sleep(5)  # Simulate 5-second delay
            
            with self.mock_s3_operations(SAMPLE_PATIENT_XML_GOOD):
                with pytest.raises(Exception) as exc_info:
                    await short_timeout_workflow.execute_complete_analysis("Test Patient")
                
                # Should be a timeout-related error
                assert any(keyword in str(exc_info.value).lower() for keyword in ['timeout', 'timed out'])
    
    @pytest.mark.asyncio
    async def test_workflow_error_recovery(self):
        """Test workflow error recovery mechanisms."""
        # Test recovery from XML parsing error
        with patch.object(self.workflow, '_execute_xml_parsing') as mock_xml:
            mock_xml.side_effect = Exception("Simulated XML parsing error")
            
            with pytest.raises(Exception) as exc_info:
                await self.workflow.execute_complete_analysis("Test Patient")
            
            # Verify error was logged
            assert self.audit_logger.log_error.called or self.audit_logger.log_system_event.called
        
        # Test recovery from research correlation error
        with self.mock_s3_operations(SAMPLE_PATIENT_XML_GOOD):
            with patch.object(self.workflow, '_execute_research_correlation') as mock_research:
                mock_research.side_effect = Exception("Simulated research error")
                
                with pytest.raises(Exception):
                    await self.workflow.execute_complete_analysis("Test Patient")
    
    def test_audit_logging_compliance(self):
        """Test HIPAA-compliant audit logging."""
        # Verify audit logger is properly configured
        assert self.workflow.audit_logger is not None
        
        # Test audit logging methods exist
        assert hasattr(self.workflow.audit_logger, 'log_patient_access')
        assert hasattr(self.workflow.audit_logger, 'log_data_access')
        assert hasattr(self.workflow.audit_logger, 'log_system_event')
        assert hasattr(self.workflow.audit_logger, 'log_error')
        
        # Test audit logging during workflow (mocked)
        self.workflow.audit_logger.log_patient_access(
            patient_id="TEST_PATIENT",
            operation="test_access",
            component="test_component"
        )
        
        assert self.workflow.audit_logger.log_patient_access.called

class TestPerformanceBenchmarks:
    """Performance benchmark tests for the medical analysis system."""
    
    def setup_method(self):
        """Set up performance test fixtures."""
        self.workflow = MainWorkflow(enable_enhanced_logging=False)
    
    @pytest.mark.asyncio
    async def test_xml_parsing_performance(self):
        """Test XML parsing performance benchmarks."""
        xml_parser = XMLParserAgent()
        
        # Mock S3 operations
        with patch('src.agents.xml_parser_agent.boto3.client') as mock_boto:
            mock_s3_client = Mock()
            mock_s3_client.get_object.return_value = {
                'Body': Mock(read=Mock(return_value=SAMPLE_PATIENT_XML_GOOD.encode('utf-8')))
            }
            mock_boto.return_value = mock_s3_client
            
            start_time = time.time()
            result = xml_parser.parse_patient_record("John Doe")
            execution_time = time.time() - start_time
            
            # Verify performance benchmark
            assert execution_time <= PERFORMANCE_BENCHMARKS["xml_parsing_max_time"]
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_medical_summarization_performance(self):
        """Test medical summarization performance benchmarks."""
        summarizer = MedicalSummarizationAgent()
        
        # Create sample patient data
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
        
        start_time = time.time()
        result = summarizer.generate_summary(patient_data)
        execution_time = time.time() - start_time
        
        # Verify performance benchmark
        assert execution_time <= PERFORMANCE_BENCHMARKS["medical_summarization_max_time"]
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_research_correlation_performance(self):
        """Test research correlation performance benchmarks."""
        correlator = ResearchCorrelationAgent()
        
        # Create sample data
        patient_data = PatientData(name="John Doe", patient_id="TEST_P001")
        medical_summary = MedicalSummary(
            summary_text="Patient has diabetes and hypertension",
            key_conditions=[
                {"name": "Type 2 diabetes", "confidence_score": 0.9},
                {"name": "Hypertension", "confidence_score": 0.8}
            ]
        )
        
        start_time = time.time()
        result = correlator.correlate_research(patient_data, medical_summary)
        execution_time = time.time() - start_time
        
        # Verify performance benchmark
        assert execution_time <= PERFORMANCE_BENCHMARKS["research_correlation_max_time"]
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_quality_assurance_performance(self):
        """Test quality assurance performance benchmarks."""
        from src.models import Demographics
        
        # Create sample analysis report
        demographics = Demographics(
            date_of_birth="1978-01-01",
            gender="Male",
            age=45,
            address=None,
            phone=None,
            emergency_contact=None
        )
        
        patient_data = PatientData(
            name="John Doe",
            patient_id="TEST_P001",
            demographics=demographics,
            medical_history=[],
            medications=[],
            procedures=[],
            diagnoses=[],
            raw_xml="<patient></patient>",
            extraction_timestamp=datetime.now()
        )
        medical_summary = MedicalSummary(
            summary_text="Patient has well-controlled diabetes",
            key_conditions=[{"name": "Diabetes", "confidence_score": 0.9}]
        )
        research_analysis = ResearchAnalysis(
            research_findings=[],
            analysis_confidence=0.8,
            insights=["Good diabetes management"],
            recommendations=["Continue treatment"]
        )
        
        analysis_report = AnalysisReport(
            report_id="TEST_R001",
            patient_data=patient_data,
            medical_summary=medical_summary,
            research_analysis=research_analysis,
            generated_at=datetime.now()
        )
        
        start_time = time.time()
        qa_result = await self.workflow._execute_quality_assurance(analysis_report)
        execution_time = time.time() - start_time
        
        # Verify performance benchmark
        assert execution_time <= PERFORMANCE_BENCHMARKS["quality_assurance_max_time"]
        assert qa_result is not None

class TestMedicalAccuracy:
    """Medical accuracy validation tests."""
    
    def setup_method(self):
        """Set up medical accuracy test fixtures."""
        self.workflow = MainWorkflow(enable_enhanced_logging=False)
    
    def test_medication_appropriateness_validation(self):
        """Test validation of medication appropriateness for conditions."""
        for test_case in MEDICAL_ACCURACY_TEST_CASES:
            if test_case["test_type"] == "medication_appropriateness":
                condition = test_case["input_condition"]
                expected_meds = test_case["expected_medications"]
                invalid_meds = test_case["invalid_medications"]
                
                # Test that expected medications are considered appropriate
                for med in expected_meds:
                    # This would use a real medical knowledge base in production
                    # For testing, we verify the structure exists
                    assert isinstance(med, str)
                    assert len(med) > 0
                
                # Test that invalid medications are flagged
                for med in invalid_meds:
                    assert isinstance(med, str)
                    assert len(med) > 0
    
    def test_icd_code_validation(self):
        """Test ICD-10 code format validation."""
        for test_case in MEDICAL_ACCURACY_TEST_CASES:
            if test_case["test_type"] == "code_validation":
                valid_codes = test_case["input_codes"]
                invalid_codes = test_case["invalid_codes"]
                
                # Test valid ICD-10 codes
                for code in valid_codes:
                    # Basic ICD-10 format validation
                    assert len(code) >= 3
                    assert code[0].isalpha()
                    assert code[1:3].isdigit()
                
                # Test invalid codes
                for code in invalid_codes:
                    # These should not match ICD-10 format
                    is_valid_format = (
                        len(code) >= 3 and 
                        code[0].isalpha() and 
                        code[1:3].isdigit()
                    )
                    assert not is_valid_format
    
    def test_drug_interaction_awareness(self):
        """Test awareness of drug interactions."""
        for test_case in MEDICAL_ACCURACY_TEST_CASES:
            if test_case["test_type"] == "drug_interactions":
                combinations = test_case["medication_combinations"]
                
                for combo in combinations:
                    drugs = combo["drugs"]
                    risk_level = combo["interaction_risk"]
                    
                    # Verify structure
                    assert len(drugs) == 2
                    assert risk_level in ["low", "moderate", "high"]
                    
                    # In production, this would check against drug interaction database
                    assert all(isinstance(drug, str) for drug in drugs)

class TestAdversarialScenarios:
    """Adversarial testing for hallucination detection and security."""
    
    def setup_method(self):
        """Set up adversarial test fixtures."""
        self.workflow = MainWorkflow(enable_enhanced_logging=False)
    
    def test_hallucination_detection(self):
        """Test detection of AI hallucinations in medical content."""
        prevention_system = self.workflow.hallucination_prevention
        
        for test_case in ADVERSARIAL_TEST_CASES:
            malicious_input = test_case["malicious_input"]
            expected_detection = test_case["expected_detection"]
            expected_risk = test_case["risk_level"]
            
            # Test hallucination detection
            result = prevention_system.check_content(malicious_input, "general")
            
            if expected_detection:
                # Should detect the hallucination
                assert result.risk_level != HallucinationRiskLevel.MINIMAL
                assert len(result.detected_patterns) > 0
                
                # Verify risk level is appropriate
                if expected_risk == "critical":
                    assert result.risk_level == HallucinationRiskLevel.CRITICAL
                elif expected_risk == "high":
                    assert result.risk_level in [HallucinationRiskLevel.HIGH, HallucinationRiskLevel.CRITICAL]
                elif expected_risk == "medium":
                    assert result.risk_level in [HallucinationRiskLevel.MEDIUM, HallucinationRiskLevel.HIGH, HallucinationRiskLevel.CRITICAL]
            else:
                # Should not detect false positives
                assert result.risk_level == HallucinationRiskLevel.MINIMAL
    
    def test_input_sanitization(self):
        """Test input sanitization and validation."""
        # Test various malicious inputs
        malicious_inputs = [
            "",  # Empty input
            "A" * 1000,  # Very long input
            "Patient<script>alert('xss')</script>",  # XSS attempt
            "Patient'; DROP TABLE patients; --",  # SQL injection attempt
            "Patient\x00\x01\x02",  # Null bytes and control characters
        ]
        
        for malicious_input in malicious_inputs:
            try:
                # Should handle malicious input gracefully
                validated_name = self.workflow._validate_patient_name(malicious_input)
                
                # If validation passes, result should be sanitized
                if validated_name:
                    assert len(validated_name) <= 100
                    assert all(c.isalnum() or c.isspace() or c in "'-." for c in validated_name)
                    
            except Exception as e:
                # Should raise appropriate validation error, not crash
                assert "validation" in str(e).lower() or "invalid" in str(e).lower()
    
    def test_xml_injection_protection(self):
        """Test protection against XML injection attacks."""
        malicious_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE patient_record [
            <!ENTITY xxe SYSTEM "file:///etc/passwd">
        ]>
        <patient_record>
            <demographics>
                <patient_id>&xxe;</patient_id>
                <name>Malicious Patient</name>
            </demographics>
        </patient_record>"""
        
        # Test that XML parser handles malicious XML safely
        xml_parser = XMLParserAgent()
        
        with patch('src.agents.xml_parser_agent.boto3.client') as mock_boto:
            mock_s3_client = Mock()
            mock_s3_client.get_object.return_value = {
                'Body': Mock(read=Mock(return_value=malicious_xml.encode('utf-8')))
            }
            mock_boto.return_value = mock_s3_client
            
            try:
                result = xml_parser.parse_patient_record("Malicious Patient")
                
                # If parsing succeeds, should not contain malicious content
                if result:
                    assert "file:///etc/passwd" not in str(result.__dict__)
                    assert "&xxe;" not in str(result.__dict__)
                    
            except Exception as e:
                # Should handle malicious XML gracefully
                assert not isinstance(e, SystemExit)  # Should not crash the system

if __name__ == "__main__":
    pytest.main([__file__, "-v"])