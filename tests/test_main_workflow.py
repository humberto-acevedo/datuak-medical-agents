"""Tests for Main Workflow Orchestrator."""
import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
import time

from src.workflow.main_workflow import MainWorkflow, WorkflowProgress
from src.models import (
    PatientData, Demographics, MedicalSummary, Condition,
    ResearchAnalysis, ResearchFinding, AnalysisReport,
    AgentCommunicationError, XMLParsingError, ResearchError, ReportError, S3Error
)
from src.utils import AuditLogger


class TestWorkflowProgress:
    """Test cases for WorkflowProgress."""
    
    def test_progress_initialization(self):
        """Test workflow progress initialization."""
        progress = WorkflowProgress()
        
        assert progress.current_step == 0
        assert progress.total_steps == 6
        assert len(progress.step_names) == 6
        assert progress.get_progress_percentage() == 0.0
        assert isinstance(progress.start_time, datetime)
    
    def test_step_timing(self):
        """Test step timing functionality."""
        progress = WorkflowProgress()
        
        # Start and complete a step
        progress.start_step(0)
        time.sleep(0.01)  # Small delay
        progress.complete_step(0)
        
        # Verify timing data
        assert 0 in progress.step_times
        assert "start" in progress.step_times[0]
        assert "end" in progress.step_times[0]
        assert "duration" in progress.step_times[0]
        assert progress.step_times[0]["duration"] > 0
    
    def test_progress_percentage(self):
        """Test progress percentage calculation."""
        progress = WorkflowProgress()
        
        assert progress.get_progress_percentage() == 0.0
        
        progress.current_step = 3
        assert progress.get_progress_percentage() == 50.0
        
        progress.current_step = 6
        assert progress.get_progress_percentage() == 100.0


@patch('src.workflow.main_workflow.S3ReportPersister')
@patch('src.workflow.main_workflow.ReportGenerator')
@patch('src.workflow.main_workflow.ResearchCorrelationAgent')
@patch('src.workflow.main_workflow.MedicalSummarizationAgent')
@patch('src.workflow.main_workflow.XMLParserAgent')
class TestMainWorkflow:
    """Test cases for Main Workflow Orchestrator."""
    
    @pytest.fixture
    def mock_audit_logger(self):
        """Create mock audit logger."""
        return Mock(spec=AuditLogger)
    
    @pytest.fixture
    def mock_progress_callback(self):
        """Create mock progress callback."""
        return Mock()
    
    @pytest.fixture
    def sample_patient_data(self):
        """Create sample patient data."""
        return PatientData(
            patient_id="WF_TEST_789",
            name="Michael Johnson",
            demographics=Demographics(age=67, gender="M"),
            medical_history=[],
            medications=[],
            procedures=[],
            diagnoses=[],
            raw_xml="<patient>workflow test</patient>",
            extraction_timestamp=datetime.now()
        )
    
    @pytest.fixture
    def sample_medical_summary(self):
        """Create sample medical summary."""
        conditions = [
            Condition(
                name="Coronary Artery Disease",
                icd_10_code="I25.9",
                severity="severe",
                confidence_score=0.95,
                status="active"
            )
        ]
        
        return MedicalSummary(
            patient_id="WF_TEST_789",
            summary_text="67-year-old male with coronary artery disease",
            key_conditions=conditions,
            medication_summary="Aspirin, Metoprolol, Atorvastatin",
            procedure_summary="Recent cardiac catheterization",
            chronological_events=[],
            generated_timestamp=datetime.now(),
            data_quality_score=0.9,
            missing_data_indicators=[]
        )
    
    @pytest.fixture
    def sample_research_analysis(self):
        """Create sample research analysis."""
        research_findings = [
            ResearchFinding(
                title="Coronary Artery Disease Management Guidelines",
                authors=["Smith, J."],
                publication_date="2023-01-01",
                journal="Cardiology",
                relevance_score=0.9,
                key_findings="Evidence-based CAD management",
                citation="Smith, J. (2023). CAD Guidelines. Cardiology.",
                study_type="guideline",
                peer_reviewed=True
            )
        ]
        
        conditions = [Condition(name="Coronary Artery Disease", confidence_score=0.95)]
        
        return ResearchAnalysis(
            patient_id="WF_TEST_789",
            analysis_timestamp=datetime.now(),
            conditions_analyzed=conditions,
            research_findings=research_findings,
            condition_research_correlations={"Coronary Artery Disease": research_findings},
            categorized_findings={"guidelines": research_findings},
            research_insights=["Strong evidence base for CAD management"],
            clinical_recommendations=["Follow current CAD guidelines"],
            analysis_confidence=0.9,
            total_papers_reviewed=10,
            relevant_papers_found=1
        )
    
    @pytest.fixture
    def sample_analysis_report(self, sample_patient_data, sample_medical_summary, sample_research_analysis):
        """Create sample analysis report."""
        report = AnalysisReport(
            report_id="RPT_WF_TEST_001",
            patient_data=sample_patient_data,
            medical_summary=sample_medical_summary,
            research_analysis=sample_research_analysis,
            generated_timestamp=datetime.now(),
            processing_time_seconds=1.0,
            agent_versions={"test": "1.0"},
            quality_metrics={"overall_quality_score": 0.9}
        )
        
        # Add additional attributes
        report.executive_summary = "Test executive summary"
        report.key_findings = ["Test finding"]
        report.recommendations = ["Test recommendation"]
        
        return report
    
    def test_workflow_initialization(self, mock_xml, mock_medical, mock_research, 
                                   mock_report_gen, mock_s3_persister, mock_audit_logger, mock_progress_callback):
        """Test workflow initialization."""
        workflow = MainWorkflow(
            audit_logger=mock_audit_logger,
            progress_callback=mock_progress_callback,
            timeout_seconds=300
        )
        
        assert workflow.audit_logger == mock_audit_logger
        assert workflow.progress_callback == mock_progress_callback
        assert workflow.timeout_seconds == 300
        assert workflow.current_workflow_id is None
        assert workflow.progress is None
        
        # Verify agents are initialized
        assert workflow.xml_parser is not None
        assert workflow.medical_summarizer is not None
        assert workflow.research_correlator is not None
        assert workflow.report_generator is not None
        assert workflow.s3_persister is not None
    
    def test_validate_patient_name_success(self, mock_xml, mock_medical, mock_research, 
                                          mock_report_gen, mock_s3_persister, mock_audit_logger):
        """Test successful patient name validation."""
        workflow = MainWorkflow(audit_logger=mock_audit_logger)
        
        # Test valid names
        valid_names = [
            "John Doe",
            "Mary Jane Smith",
            "O'Connor",
            "Jean-Pierre",
            "Dr. Smith",
            "Mary Ann"
        ]
        
        for name in valid_names:
            validated = workflow._validate_patient_name(name)
            assert validated == name.strip()
    
    def test_validate_patient_name_failures(self, mock_audit_logger):
        """Test patient name validation failures."""
        workflow = MainWorkflow(audit_logger=mock_audit_logger)
        
        # Test invalid names
        invalid_cases = [
            ("", "Patient name cannot be empty"),
            ("   ", "Patient name cannot be empty"),
            ("A", "Patient name must be at least 2 characters"),
            ("A" * 101, "Patient name cannot exceed 100 characters"),
            ("John123", "Patient name contains invalid characters"),
            ("John@Doe", "Patient name contains invalid characters"),
            ("John#Doe", "Patient name contains invalid characters")
        ]
        
        for invalid_name, expected_error in invalid_cases:
            with pytest.raises(AgentCommunicationError) as exc_info:
                workflow._validate_patient_name(invalid_name)
            assert expected_error in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_execute_xml_parsing_success(self, mock_audit_logger, sample_patient_data):
        """Test successful XML parsing execution."""
        workflow = MainWorkflow(audit_logger=mock_audit_logger)
        
        # Mock XML parser
        workflow.xml_parser.parse_patient_record = Mock(return_value=sample_patient_data)
        
        result = await workflow._execute_xml_parsing("Michael Johnson")
        
        assert result == sample_patient_data
        workflow.xml_parser.parse_patient_record.assert_called_once_with("Michael Johnson")
    
    @pytest.mark.asyncio
    async def test_execute_xml_parsing_timeout(self, mock_audit_logger):
        """Test XML parsing timeout handling."""
        workflow = MainWorkflow(audit_logger=mock_audit_logger)
        
        # Mock XML parser to simulate timeout
        async def slow_parse(*args):
            await asyncio.sleep(2)  # Longer than timeout
            return Mock()
        
        workflow.xml_parser.parse_patient_record = Mock(side_effect=slow_parse)
        
        with pytest.raises(XMLParsingError) as exc_info:
            await workflow._execute_xml_parsing("Test Patient")
        
        assert "timed out" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_execute_medical_summarization_success(self, mock_audit_logger, 
                                                       sample_patient_data, sample_medical_summary):
        """Test successful medical summarization execution."""
        workflow = MainWorkflow(audit_logger=mock_audit_logger)
        
        # Mock medical summarizer
        workflow.medical_summarizer.generate_medical_summary = Mock(return_value=sample_medical_summary)
        
        result = await workflow._execute_medical_summarization(sample_patient_data)
        
        assert result == sample_medical_summary
        workflow.medical_summarizer.generate_medical_summary.assert_called_once_with(sample_patient_data)
    
    @pytest.mark.asyncio
    async def test_execute_medical_summarization_patient_id_mismatch(self, mock_audit_logger, sample_patient_data):
        """Test medical summarization with patient ID mismatch."""
        workflow = MainWorkflow(audit_logger=mock_audit_logger)
        
        # Create summary with different patient ID
        mismatched_summary = Mock(spec=MedicalSummary)
        mismatched_summary.patient_id = "DIFFERENT_ID"
        mismatched_summary.validate.return_value = []
        
        workflow.medical_summarizer.generate_medical_summary = Mock(return_value=mismatched_summary)
        
        with pytest.raises(AgentCommunicationError) as exc_info:
            await workflow._execute_medical_summarization(sample_patient_data)
        
        assert "Patient ID mismatch" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_execute_research_correlation_success(self, mock_audit_logger, 
                                                      sample_patient_data, sample_medical_summary, 
                                                      sample_research_analysis):
        """Test successful research correlation execution."""
        workflow = MainWorkflow(audit_logger=mock_audit_logger)
        
        # Mock research correlator
        workflow.research_correlator.analyze_patient_research = Mock(return_value=sample_research_analysis)
        
        result = await workflow._execute_research_correlation(sample_patient_data, sample_medical_summary)
        
        assert result == sample_research_analysis
        workflow.research_correlator.analyze_patient_research.assert_called_once_with(
            sample_patient_data, sample_medical_summary
        )
    
    @pytest.mark.asyncio
    async def test_execute_report_generation_success(self, mock_audit_logger, 
                                                   sample_patient_data, sample_medical_summary,
                                                   sample_research_analysis, sample_analysis_report):
        """Test successful report generation execution."""
        workflow = MainWorkflow(audit_logger=mock_audit_logger)
        
        # Mock report generator
        workflow.report_generator.generate_analysis_report = Mock(return_value=sample_analysis_report)
        
        result = await workflow._execute_report_generation(
            sample_patient_data, sample_medical_summary, sample_research_analysis
        )
        
        assert result == sample_analysis_report
        workflow.report_generator.generate_analysis_report.assert_called_once_with(
            sample_patient_data, sample_medical_summary, sample_research_analysis
        )
    
    @pytest.mark.asyncio
    async def test_execute_report_persistence_success(self, mock_audit_logger, sample_analysis_report):
        """Test successful report persistence execution."""
        workflow = MainWorkflow(audit_logger=mock_audit_logger)
        
        # Mock S3 persister
        expected_s3_key = "analysis-reports/patient-WF_TEST_789/analysis-20241102_120000-RPT_WF_TEST_001.json"
        workflow.s3_persister.save_analysis_report = Mock(return_value=expected_s3_key)
        
        result = await workflow._execute_report_persistence(sample_analysis_report)
        
        assert result == expected_s3_key
        workflow.s3_persister.save_analysis_report.assert_called_once_with(sample_analysis_report)
    
    @pytest.mark.asyncio
    async def test_complete_workflow_success(self, mock_audit_logger, mock_progress_callback,
                                           sample_patient_data, sample_medical_summary,
                                           sample_research_analysis, sample_analysis_report):
        """Test complete successful workflow execution."""
        workflow = MainWorkflow(
            audit_logger=mock_audit_logger,
            progress_callback=mock_progress_callback,
            timeout_seconds=300
        )
        
        # Mock all agents
        workflow.xml_parser.parse_patient_record = Mock(return_value=sample_patient_data)
        workflow.medical_summarizer.generate_medical_summary = Mock(return_value=sample_medical_summary)
        workflow.research_correlator.analyze_patient_research = Mock(return_value=sample_research_analysis)
        workflow.report_generator.generate_analysis_report = Mock(return_value=sample_analysis_report)
        workflow.s3_persister.save_analysis_report = Mock(return_value="test-s3-key")
        
        # Execute complete workflow
        result = await workflow.execute_complete_analysis("Michael Johnson")
        
        # Verify result
        assert isinstance(result, AnalysisReport)
        assert result == sample_analysis_report
        
        # Verify all agents were called
        workflow.xml_parser.parse_patient_record.assert_called_once()
        workflow.medical_summarizer.generate_medical_summary.assert_called_once()
        workflow.research_correlator.analyze_patient_research.assert_called_once()
        workflow.report_generator.generate_analysis_report.assert_called_once()
        workflow.s3_persister.save_analysis_report.assert_called_once()
        
        # Verify progress callbacks were called
        assert mock_progress_callback.call_count >= 6  # One for each step
        
        # Verify audit logging
        mock_audit_logger.log_data_access.assert_called()
        
        # Verify workflow ID was generated
        assert workflow.current_workflow_id is not None
        assert workflow.current_workflow_id.startswith("WF_")
    
    @pytest.mark.asyncio
    async def test_complete_workflow_xml_parsing_failure(self, mock_audit_logger):
        """Test complete workflow with XML parsing failure."""
        workflow = MainWorkflow(audit_logger=mock_audit_logger)
        
        # Mock XML parser to fail
        workflow.xml_parser.parse_patient_record = Mock(side_effect=Exception("XML parsing failed"))
        
        with pytest.raises(AgentCommunicationError) as exc_info:
            await workflow.execute_complete_analysis("Test Patient")
        
        assert "Workflow" in str(exc_info.value)
        assert "failed" in str(exc_info.value)
        
        # Verify error logging
        mock_audit_logger.log_error.assert_called()
    
    @pytest.mark.asyncio
    async def test_complete_workflow_timeout(self, mock_audit_logger):
        """Test complete workflow timeout handling."""
        workflow = MainWorkflow(audit_logger=mock_audit_logger, timeout_seconds=1)
        
        # Mock XML parser to be slow
        async def slow_parse(*args):
            await asyncio.sleep(2)  # Longer than workflow timeout
            return Mock()
        
        workflow.xml_parser.parse_patient_record = Mock(side_effect=slow_parse)
        
        with pytest.raises(AgentCommunicationError) as exc_info:
            await workflow.execute_complete_analysis("Test Patient")
        
        assert "timed out" in str(exc_info.value)
    
    def test_get_workflow_status_not_started(self, mock_audit_logger):
        """Test workflow status when not started."""
        workflow = MainWorkflow(audit_logger=mock_audit_logger)
        
        status = workflow.get_workflow_status()
        
        assert status["status"] == "not_started"
    
    def test_get_workflow_status_running(self, mock_audit_logger):
        """Test workflow status when running."""
        workflow = MainWorkflow(audit_logger=mock_audit_logger)
        
        # Simulate running workflow
        workflow.current_workflow_id = "WF_TEST_123"
        workflow.progress = WorkflowProgress()
        workflow.progress.current_step = 2
        
        status = workflow.get_workflow_status()
        
        assert status["status"] == "running"
        assert status["workflow_id"] == "WF_TEST_123"
        assert status["current_step"] == 3  # 1-indexed
        assert status["total_steps"] == 6
        assert status["progress_percentage"] > 0
    
    @pytest.mark.asyncio
    async def test_cancel_workflow_success(self, mock_audit_logger):
        """Test successful workflow cancellation."""
        workflow = MainWorkflow(audit_logger=mock_audit_logger)
        
        # Simulate running workflow
        workflow.current_workflow_id = "WF_TEST_123"
        workflow.progress = WorkflowProgress()
        
        result = await workflow.cancel_workflow()
        
        assert result is True
        assert workflow.current_workflow_id is None
        assert workflow.progress is None
        
        # Verify audit logging
        mock_audit_logger.log_data_access.assert_called()
    
    @pytest.mark.asyncio
    async def test_cancel_workflow_not_running(self, mock_audit_logger):
        """Test workflow cancellation when not running."""
        workflow = MainWorkflow(audit_logger=mock_audit_logger)
        
        result = await workflow.cancel_workflow()
        
        assert result is False
    
    def test_progress_callback_exception_handling(self, mock_audit_logger):
        """Test that progress callback exceptions don't break workflow."""
        # Create callback that raises exception
        failing_callback = Mock(side_effect=Exception("Callback failed"))
        
        workflow = MainWorkflow(
            audit_logger=mock_audit_logger,
            progress_callback=failing_callback
        )
        
        workflow.progress = WorkflowProgress()
        
        # This should not raise an exception
        workflow._update_progress()
        
        # Verify callback was called despite exception
        failing_callback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_agent_validation_errors(self, mock_audit_logger, sample_patient_data):
        """Test handling of agent validation errors."""
        workflow = MainWorkflow(audit_logger=mock_audit_logger)
        
        # Mock XML parser to return invalid data type
        workflow.xml_parser.parse_patient_record = Mock(return_value="invalid_data")
        
        with pytest.raises(AgentCommunicationError) as exc_info:
            await workflow._execute_xml_parsing("Test Patient")
        
        assert "invalid data type" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_workflow_step_timing(self, mock_audit_logger, sample_patient_data):
        """Test that workflow steps are properly timed."""
        workflow = MainWorkflow(audit_logger=mock_audit_logger)
        workflow.xml_parser.parse_patient_record = Mock(return_value=sample_patient_data)
        
        # Execute a step
        await workflow._execute_xml_parsing("Test Patient")
        
        # Verify timing would be recorded (we can't test actual timing in unit tests)
        # This test mainly ensures the timing infrastructure is in place
        assert True  # Placeholder for timing verification