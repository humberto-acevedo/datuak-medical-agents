"""Integration tests for quality assurance system with main workflow."""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from src.workflow.main_workflow import MainWorkflow
from src.models import PatientData, MedicalSummary, ResearchAnalysis, AnalysisReport
from src.models.exceptions import ReportError, HallucinationDetectedError
from src.utils.quality_assurance import QualityLevel, ValidationSeverity
from src.utils.hallucination_prevention import HallucinationRiskLevel
from src.utils.audit_logger import AuditLogger

class TestQualityAssuranceIntegration:
    """Test quality assurance integration with main workflow."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.audit_logger = Mock(spec=AuditLogger)
        self.workflow = MainWorkflow(
            audit_logger=self.audit_logger,
            enable_enhanced_logging=False
        )
    
    def create_sample_analysis_report(self, quality_level: str = "good") -> AnalysisReport:
        """Create a sample analysis report with configurable quality."""
        patient_data = PatientData(
            name="John Doe",
            patient_id="P12345",
            age=45,
            gender="Male",
            date_of_birth="1978-01-15"
        )
        
        if quality_level == "good":
            medical_summary = MedicalSummary(
                summary_text="Patient has well-controlled type 2 diabetes and hypertension.",
                key_conditions=[
                    {"name": "Type 2 Diabetes", "confidence_score": 0.95},
                    {"name": "Hypertension", "confidence_score": 0.88}
                ],
                chronic_conditions=["diabetes", "hypertension"],
                medications=["metformin", "lisinopril"]
            )
            
            research_analysis = ResearchAnalysis(
                research_findings=[
                    {
                        "title": "Diabetes Management in Primary Care",
                        "journal": "Journal of Medical Research",
                        "publication_year": 2023,
                        "relevance_score": 0.92
                    }
                ],
                analysis_confidence=0.85,
                insights=["Early intervention improves outcomes"],
                recommendations=["Continue current medication regimen"]
            )
        
        elif quality_level == "poor":
            medical_summary = MedicalSummary(
                summary_text="",  # Empty summary - poor quality
                key_conditions=[
                    {"name": "", "confidence_score": 2.0}  # Invalid data
                ],
                chronic_conditions=[],
                medications=[]
            )
            
            research_analysis = ResearchAnalysis(
                research_findings=[],
                analysis_confidence=0.1,  # Very low confidence
                insights=[],
                recommendations=[]
            )
        
        elif quality_level == "hallucination":
            medical_summary = MedicalSummary(
                summary_text="Patient has fictional magical disease from Harry Potter with supernatural healing powers.",
                key_conditions=[
                    {"name": "Magical Disease", "confidence_score": 0.95}
                ],
                chronic_conditions=["fictional condition"],
                medications=["magical potion", "invented medicine"]
            )
            
            research_analysis = ResearchAnalysis(
                research_findings=[
                    {
                        "title": "Fictional Study from Star Wars",
                        "journal": "Imaginary Journal",
                        "publication_year": 2050,  # Future year
                        "relevance_score": 0.95
                    }
                ],
                analysis_confidence=0.95,
                insights=["Magical healing is very effective"],
                recommendations=["Use more fictional treatments"]
            )
        
        return AnalysisReport(
            report_id="R12345",
            patient_data=patient_data,
            medical_summary=medical_summary,
            research_analysis=research_analysis,
            generated_at=datetime.now()
        )
    
    @pytest.mark.asyncio
    async def test_quality_assurance_good_report(self):
        """Test quality assurance with a good quality report."""
        report = self.create_sample_analysis_report("good")
        
        # Execute quality assurance
        quality_result = await self.workflow._execute_quality_assurance(report)
        
        # Verify quality assessment passed
        assert quality_result is not None
        assert quality_result["quality_level"] in ["excellent", "good", "acceptable"]
        assert quality_result["overall_score"] > 0.5
        assert quality_result["hallucination_risk"] < 0.5
        
        # Verify metadata was added to report
        assert hasattr(report, 'processing_metadata')
        assert 'quality_assessment' in report.processing_metadata
    
    @pytest.mark.asyncio
    async def test_quality_assurance_poor_report(self):
        """Test quality assurance with a poor quality report."""
        report = self.create_sample_analysis_report("poor")
        
        # Quality assurance should raise ReportError for poor quality
        with pytest.raises(ReportError) as exc_info:
            await self.workflow._execute_quality_assurance(report)
        
        assert "quality" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_quality_assurance_hallucination_report(self):
        """Test quality assurance with hallucination content."""
        report = self.create_sample_analysis_report("hallucination")
        
        # Quality assurance should raise ReportError for hallucinations
        with pytest.raises(ReportError) as exc_info:
            await self.workflow._execute_quality_assurance(report)
        
        error_message = str(exc_info.value).lower()
        assert "hallucination" in error_message or "quality" in error_message
    
    @pytest.mark.asyncio
    async def test_quality_assurance_timeout(self):
        """Test quality assurance timeout handling."""
        report = self.create_sample_analysis_report("good")
        
        # Mock the QA engine to simulate timeout
        with patch.object(self.workflow.qa_engine, 'assess_analysis_quality') as mock_qa:
            mock_qa.side_effect = asyncio.TimeoutError()
            
            with pytest.raises(ReportError) as exc_info:
                await self.workflow._execute_quality_assurance(report)
            
            assert "timed out" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_quality_assurance_audit_logging(self):
        """Test that quality assurance events are properly logged."""
        report = self.create_sample_analysis_report("good")
        
        # Execute quality assurance
        await self.workflow._execute_quality_assurance(report)
        
        # Verify audit logging was called
        assert self.audit_logger.log_system_event.called
        
        # Check the logged event
        call_args = self.audit_logger.log_system_event.call_args
        assert call_args[1]["operation"] == "quality_assurance_passed"
        assert call_args[1]["component"] == "quality_assurance"
        assert "report_id" in call_args[1]["additional_context"]
        assert "quality_level" in call_args[1]["additional_context"]
    
    @pytest.mark.asyncio
    async def test_quality_assurance_critical_issues_logging(self):
        """Test logging of critical quality issues."""
        report = self.create_sample_analysis_report("poor")
        
        # Mock QA engine to return critical issues
        with patch.object(self.workflow.qa_engine, 'assess_analysis_quality') as mock_qa:
            from src.utils.quality_assurance import QualityAssessment, ValidationIssue
            
            critical_issue = ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                category="critical_test",
                message="Critical quality issue detected"
            )
            
            mock_assessment = QualityAssessment(
                overall_score=0.2,
                quality_level=QualityLevel.UNACCEPTABLE,
                data_completeness=0.3,
                consistency_score=0.2,
                accuracy_score=0.1,
                validation_issues=[critical_issue],
                hallucination_risk=0.1,
                confidence_metrics={},
                recommendations=["Fix critical issues"]
            )
            
            mock_qa.return_value = mock_assessment
            
            with pytest.raises(ReportError):
                await self.workflow._execute_quality_assurance(report)
            
            # Verify critical issues were logged
            assert self.audit_logger.log_system_event.called
            logged_calls = [call for call in self.audit_logger.log_system_event.call_args_list 
                          if call[1]["operation"] == "critical_quality_issues"]
            assert len(logged_calls) > 0
    
    def test_workflow_statistics_include_qa(self):
        """Test that workflow statistics include quality assurance data."""
        stats = self.workflow.get_workflow_statistics()
        
        # Verify QA statistics are included
        assert "quality_assurance_stats" in stats
        assert "hallucination_prevention_stats" in stats
        
        # Verify QA statistics structure
        qa_stats = stats["quality_assurance_stats"]
        assert "quality_thresholds" in qa_stats
        assert "hallucination_thresholds" in qa_stats
        assert "validator_info" in qa_stats
        
        # Verify hallucination prevention statistics structure
        hp_stats = stats["hallucination_prevention_stats"]
        assert "total_checks" in hp_stats
        assert "hallucination_rate" in hp_stats
        assert "by_risk_level" in hp_stats
    
    @pytest.mark.asyncio
    async def test_end_to_end_workflow_with_qa(self):
        """Test end-to-end workflow including quality assurance."""
        # Mock all the agents to return good data
        with patch.object(self.workflow, '_validate_patient_name', return_value="John Doe"), \
             patch.object(self.workflow, '_execute_xml_parsing') as mock_xml, \
             patch.object(self.workflow, '_execute_medical_summarization') as mock_med, \
             patch.object(self.workflow, '_execute_research_correlation') as mock_research, \
             patch.object(self.workflow, '_execute_report_generation') as mock_report, \
             patch.object(self.workflow, '_execute_report_persistence', return_value="s3://test/key"):
            
            # Set up mock returns
            patient_data = PatientData(
                name="John Doe",
                patient_id="P12345",
                age=45,
                gender="Male"
            )
            mock_xml.return_value = patient_data
            
            medical_summary = MedicalSummary(
                summary_text="Patient has well-controlled diabetes.",
                key_conditions=[{"name": "Diabetes", "confidence_score": 0.9}],
                medications=["metformin"]
            )
            mock_med.return_value = medical_summary
            
            research_analysis = ResearchAnalysis(
                research_findings=[{
                    "title": "Diabetes Study",
                    "journal": "Medical Journal",
                    "publication_year": 2023,
                    "relevance_score": 0.8
                }],
                analysis_confidence=0.8,
                insights=["Good diabetes management"],
                recommendations=["Continue treatment"]
            )
            mock_research.return_value = research_analysis
            
            analysis_report = AnalysisReport(
                report_id="R12345",
                patient_data=patient_data,
                medical_summary=medical_summary,
                research_analysis=research_analysis,
                generated_at=datetime.now()
            )
            mock_report.return_value = analysis_report
            
            # Execute complete workflow
            result = await self.workflow.execute_complete_analysis("John Doe")
            
            # Verify workflow completed successfully
            assert result is not None
            assert result.report_id == "R12345"
            
            # Verify quality assessment was added to metadata
            assert hasattr(result, 'processing_metadata')
            assert 'quality_assessment' in result.processing_metadata
            
            # Verify all steps were executed
            assert mock_xml.called
            assert mock_med.called
            assert mock_research.called
            assert mock_report.called
            
            # Verify workflow progress included QA step
            assert self.workflow.progress.total_steps == 7
            assert "Quality Assurance" in self.workflow.progress.step_names[5]
    
    @pytest.mark.asyncio
    async def test_workflow_qa_failure_stops_execution(self):
        """Test that QA failure stops workflow execution."""
        # Mock agents up to report generation
        with patch.object(self.workflow, '_validate_patient_name', return_value="John Doe"), \
             patch.object(self.workflow, '_execute_xml_parsing') as mock_xml, \
             patch.object(self.workflow, '_execute_medical_summarization') as mock_med, \
             patch.object(self.workflow, '_execute_research_correlation') as mock_research, \
             patch.object(self.workflow, '_execute_report_generation') as mock_report, \
             patch.object(self.workflow, '_execute_report_persistence') as mock_persist:
            
            # Set up mocks to return data that will fail QA
            patient_data = PatientData(name="John Doe", patient_id="P12345")
            mock_xml.return_value = patient_data
            
            medical_summary = MedicalSummary(
                summary_text="Patient has fictional magical disease from Harry Potter.",
                key_conditions=[{"name": "Magical Disease", "confidence_score": 0.9}],
                medications=["magical potion"]
            )
            mock_med.return_value = medical_summary
            
            research_analysis = ResearchAnalysis(
                research_findings=[],
                analysis_confidence=0.1,
                insights=["Magical healing works"],
                recommendations=["Use more magic"]
            )
            mock_research.return_value = research_analysis
            
            analysis_report = AnalysisReport(
                report_id="R12345",
                patient_data=patient_data,
                medical_summary=medical_summary,
                research_analysis=research_analysis,
                generated_at=datetime.now()
            )
            mock_report.return_value = analysis_report
            
            # Execute workflow - should fail at QA step
            with pytest.raises(ReportError) as exc_info:
                await self.workflow.execute_complete_analysis("John Doe")
            
            # Verify error is related to quality/hallucination
            error_message = str(exc_info.value).lower()
            assert "quality" in error_message or "hallucination" in error_message
            
            # Verify persistence was NOT called (workflow stopped at QA)
            assert not mock_persist.called
    
    def test_qa_system_initialization(self):
        """Test that QA systems are properly initialized in workflow."""
        # Verify QA engine is initialized
        assert self.workflow.qa_engine is not None
        assert hasattr(self.workflow.qa_engine, 'assess_analysis_quality')
        
        # Verify hallucination prevention is initialized
        assert self.workflow.hallucination_prevention is not None
        assert hasattr(self.workflow.hallucination_prevention, 'check_content')
        
        # Verify strict mode is enabled for medical safety
        assert self.workflow.hallucination_prevention.strict_mode is True
    
    def test_qa_system_configuration(self):
        """Test QA system configuration and thresholds."""
        # Get QA statistics to verify configuration
        qa_stats = self.workflow.qa_engine.get_quality_statistics()
        
        # Verify quality thresholds are properly configured
        assert "quality_thresholds" in qa_stats
        thresholds = qa_stats["quality_thresholds"]
        assert "excellent" in thresholds
        assert "good" in thresholds
        assert "acceptable" in thresholds
        assert "poor" in thresholds
        assert "unacceptable" in thresholds
        
        # Verify thresholds are in correct order
        assert thresholds["excellent"] > thresholds["good"]
        assert thresholds["good"] > thresholds["acceptable"]
        assert thresholds["acceptable"] > thresholds["poor"]
        assert thresholds["poor"] > thresholds["unacceptable"]
        
        # Get hallucination prevention statistics
        hp_stats = self.workflow.hallucination_prevention.get_prevention_statistics()
        
        # Verify prevention statistics structure
        assert "total_checks" in hp_stats
        assert "hallucination_rate" in hp_stats
        assert "by_risk_level" in hp_stats
        
        # Verify all risk levels are tracked
        risk_levels = hp_stats["by_risk_level"]
        expected_levels = ["minimal", "low", "medium", "high", "critical"]
        for level in expected_levels:
            assert level in risk_levels

if __name__ == "__main__":
    pytest.main([__file__])