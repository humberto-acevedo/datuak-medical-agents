"""Integration tests for complete workflow orchestration."""
import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, patch
import json

from src.workflow.main_workflow import MainWorkflow, WorkflowProgress
from src.models import (
    PatientData, Demographics, MedicalSummary, Condition,
    ResearchAnalysis, ResearchFinding, AnalysisReport
)
from src.utils import AuditLogger


class TestWorkflowIntegration:
    """Integration tests for the complete workflow orchestration."""
    
    @pytest.fixture
    def mock_audit_logger(self):
        """Create mock audit logger."""
        return Mock(spec=AuditLogger)
    
    @pytest.fixture
    def progress_tracker(self):
        """Create progress tracker for testing."""
        progress_updates = []
        
        def track_progress(progress: WorkflowProgress):
            progress_updates.append({
                "step": progress.current_step,
                "percentage": progress.get_progress_percentage(),
                "step_name": progress.step_names[progress.current_step] if progress.current_step < len(progress.step_names) else "Completed"
            })
        
        track_progress.updates = progress_updates
        return track_progress
    
    @pytest.mark.asyncio
    async def test_complete_workflow_integration(self, mock_audit_logger, progress_tracker):
        """Test complete workflow integration with all agents working together."""
        
        # Create comprehensive test data
        patient_data = PatientData(
            patient_id="INTEGRATION_WF_001",
            name="Elizabeth Thompson",
            demographics=Demographics(
                age=72,
                gender="F",
                date_of_birth="1952-04-18"
            ),
            medical_history=[],
            medications=[],
            procedures=[],
            diagnoses=[],
            raw_xml="<patient>comprehensive workflow integration test</patient>",
            extraction_timestamp=datetime.now()
        )
        
        conditions = [
            Condition(
                name="Atrial Fibrillation",
                icd_10_code="I48.9",
                severity="moderate",
                confidence_score=0.92,
                status="chronic"
            ),
            Condition(
                name="Heart Failure with Preserved Ejection Fraction",
                icd_10_code="I50.30",
                severity="severe",
                confidence_score=0.89,
                status="active"
            ),
            Condition(
                name="Chronic Kidney Disease Stage 3",
                icd_10_code="N18.3",
                severity="moderate",
                confidence_score=0.85,
                status="chronic"
            )
        ]
        
        medical_summary = MedicalSummary(
            patient_id="INTEGRATION_WF_001",
            summary_text="72-year-old female with complex cardiovascular and renal comorbidities requiring comprehensive management and monitoring.",
            key_conditions=conditions,
            medication_summary="Warfarin 5mg daily, Metoprolol 50mg BID, Furosemide 40mg daily, Lisinopril 10mg daily",
            procedure_summary="Recent echocardiogram, routine INR monitoring",
            chronological_events=[],
            generated_timestamp=datetime.now(),
            data_quality_score=0.88,
            missing_data_indicators=["recent_lab_values"]
        )
        
        research_findings = [
            ResearchFinding(
                title="Anticoagulation in Elderly Patients with Atrial Fibrillation: Meta-Analysis",
                authors=["Johnson, K.", "Smith, R.", "Brown, L."],
                publication_date="2023-08-15",
                journal="Journal of the American College of Cardiology",
                doi="10.1016/j.jacc.2023.456",
                relevance_score=0.94,
                key_findings="DOACs show superior safety profile compared to warfarin in elderly AF patients",
                citation="Johnson, K. et al. (2023). Anticoagulation in Elderly AF. JACC.",
                study_type="meta-analysis",
                sample_size=25000,
                peer_reviewed=True
            ),
            ResearchFinding(
                title="Heart Failure with Preserved Ejection Fraction: Treatment Guidelines Update",
                authors=["Williams, M.", "Davis, P."],
                publication_date="2023-09-20",
                journal="European Heart Journal",
                doi="10.1093/eurheartj/2023.789",
                relevance_score=0.91,
                key_findings="SGLT2 inhibitors reduce hospitalizations in HFpEF patients by 32%",
                citation="Williams, M. et al. (2023). HFpEF Guidelines. Eur Heart J.",
                study_type="guideline",
                peer_reviewed=True
            )
        ]
        
        research_analysis = ResearchAnalysis(
            patient_id="INTEGRATION_WF_001",
            analysis_timestamp=datetime.now(),
            conditions_analyzed=conditions,
            research_findings=research_findings,
            condition_research_correlations={
                "Atrial Fibrillation": research_findings[:1],
                "Heart Failure with Preserved Ejection Fraction": research_findings[1:2]
            },
            categorized_findings={
                "systematic_reviews": research_findings[:1],
                "guidelines": research_findings[1:2]
            },
            research_insights=[
                "Strong evidence base for anticoagulation management in elderly AF patients",
                "Recent guidelines support SGLT2 inhibitor use in HFpEF",
                "Comprehensive cardiovascular risk management approach recommended"
            ],
            clinical_recommendations=[
                "Consider DOAC therapy instead of warfarin for improved safety profile",
                "Evaluate for SGLT2 inhibitor therapy in HFpEF management",
                "Regular monitoring of renal function given CKD comorbidity",
                "Multidisciplinary cardiology and nephrology care coordination"
            ],
            analysis_confidence=0.90,
            total_papers_reviewed=18,
            relevant_papers_found=2
        )
        
        analysis_report = AnalysisReport(
            report_id="RPT_INTEGRATION_WF_001",
            patient_data=patient_data,
            medical_summary=medical_summary,
            research_analysis=research_analysis,
            generated_timestamp=datetime.now(),
            processing_time_seconds=2.5,
            agent_versions={
                "xml_parser": "1.0",
                "medical_summarizer": "1.0",
                "research_correlator": "1.0",
                "report_generator": "1.0"
            },
            quality_metrics={
                "overall_quality_score": 0.89,
                "data_completeness_score": 0.85,
                "research_analysis_quality": {
                    "papers_found": 2,
                    "analysis_confidence": 0.90
                }
            }
        )
        
        # Add additional report attributes
        analysis_report.executive_summary = "Comprehensive analysis of 72-year-old female with complex cardiovascular conditions requiring evidence-based management optimization."
        analysis_report.key_findings = [
            "Multiple cardiovascular comorbidities requiring coordinated care",
            "Strong evidence for anticoagulation optimization",
            "Opportunity for HFpEF treatment enhancement"
        ]
        analysis_report.recommendations = research_analysis.clinical_recommendations
        
        # Initialize workflow with progress tracking
        workflow = MainWorkflow(
            audit_logger=mock_audit_logger,
            progress_callback=progress_tracker,
            timeout_seconds=300
        )
        
        # Mock all agents to return our test data
        workflow.xml_parser.parse_patient_record = Mock(return_value=patient_data)
        workflow.medical_summarizer.generate_medical_summary = Mock(return_value=medical_summary)
        workflow.research_correlator.analyze_patient_research = Mock(return_value=research_analysis)
        workflow.report_generator.generate_analysis_report = Mock(return_value=analysis_report)
        workflow.s3_persister.save_analysis_report = Mock(return_value="analysis-reports/patient-INTEGRATION_WF_001/analysis-20241102_140000-RPT_INTEGRATION_WF_001.json")
        
        # Execute complete workflow
        start_time = datetime.now()
        result = await workflow.execute_complete_analysis("Elizabeth Thompson")
        end_time = datetime.now()
        
        # Verify workflow execution
        assert isinstance(result, AnalysisReport)
        assert result.report_id == "RPT_INTEGRATION_WF_001"
        assert result.patient_data.patient_id == "INTEGRATION_WF_001"
        
        # Verify all agents were called in correct order
        workflow.xml_parser.parse_patient_record.assert_called_once_with("Elizabeth Thompson")
        workflow.medical_summarizer.generate_medical_summary.assert_called_once_with(patient_data)
        workflow.research_correlator.analyze_patient_research.assert_called_once_with(patient_data, medical_summary)
        workflow.report_generator.generate_analysis_report.assert_called_once_with(patient_data, medical_summary, research_analysis)
        workflow.s3_persister.save_analysis_report.assert_called_once_with(analysis_report)
        
        # Verify progress tracking
        assert len(progress_tracker.updates) == 6  # One update per step
        assert progress_tracker.updates[0]["percentage"] == 0.0
        assert progress_tracker.updates[-1]["percentage"] == 100.0
        
        # Verify workflow timing
        execution_time = (end_time - start_time).total_seconds()
        assert execution_time < 5.0  # Should complete quickly in test
        
        # Verify audit logging
        mock_audit_logger.log_data_access.assert_called()
        
        # Verify workflow status
        status = workflow.get_workflow_status()
        assert status["status"] == "completed"
        assert status["workflow_id"] is not None
        assert status["progress_percentage"] == 100.0
        
        print(f"✅ Complete Workflow Integration Test Passed:")
        print(f"   - Patient: {result.patient_data.name} (ID: {result.patient_data.patient_id})")
        print(f"   - Conditions: {len(medical_summary.key_conditions)}")
        print(f"   - Research Papers: {len(research_analysis.research_findings)}")
        print(f"   - Execution Time: {execution_time:.2f}s")
        print(f"   - Progress Updates: {len(progress_tracker.updates)}")
        print(f"   - Quality Score: {analysis_report.quality_metrics['overall_quality_score']:.2f}")
    
    @pytest.mark.asyncio
    async def test_workflow_error_recovery(self, mock_audit_logger, progress_tracker):
        """Test workflow error handling and recovery mechanisms."""
        workflow = MainWorkflow(
            audit_logger=mock_audit_logger,
            progress_callback=progress_tracker,
            timeout_seconds=300
        )
        
        # Test XML parsing failure
        workflow.xml_parser.parse_patient_record = Mock(side_effect=Exception("S3 connection failed"))
        
        with pytest.raises(Exception):
            await workflow.execute_complete_analysis("Test Patient")
        
        # Verify error was logged
        mock_audit_logger.log_error.assert_called()
        
        # Verify workflow can be cancelled after error
        cancel_result = await workflow.cancel_workflow()
        assert cancel_result is False  # No workflow running after error
    
    @pytest.mark.asyncio
    async def test_workflow_timeout_handling(self, mock_audit_logger):
        """Test workflow timeout handling."""
        workflow = MainWorkflow(
            audit_logger=mock_audit_logger,
            timeout_seconds=1  # Very short timeout
        )
        
        # Mock XML parser to be slow
        async def slow_operation(*args):
            await asyncio.sleep(2)  # Longer than timeout
            return Mock()
        
        workflow.xml_parser.parse_patient_record = Mock(side_effect=slow_operation)
        
        with pytest.raises(Exception) as exc_info:
            await workflow.execute_complete_analysis("Test Patient")
        
        # Should timeout and raise appropriate error
        assert "timed out" in str(exc_info.value) or "failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_workflow_data_validation(self, mock_audit_logger):
        """Test workflow data validation between agents."""
        workflow = MainWorkflow(audit_logger=mock_audit_logger)
        
        # Create patient data
        patient_data = PatientData(
            patient_id="VALIDATION_TEST_001",
            name="Test Patient",
            demographics=Demographics(age=50, gender="M"),
            medical_history=[],
            medications=[],
            procedures=[],
            diagnoses=[],
            raw_xml="<patient>test</patient>",
            extraction_timestamp=datetime.now()
        )
        
        # Create medical summary with DIFFERENT patient ID (should cause validation error)
        medical_summary = MedicalSummary(
            patient_id="DIFFERENT_ID",  # This should cause validation failure
            summary_text="Test summary",
            key_conditions=[],
            medication_summary="None",
            procedure_summary="None",
            chronological_events=[],
            generated_timestamp=datetime.now(),
            data_quality_score=0.8,
            missing_data_indicators=[]
        )
        
        # Mock agents
        workflow.xml_parser.parse_patient_record = Mock(return_value=patient_data)
        workflow.medical_summarizer.generate_medical_summary = Mock(return_value=medical_summary)
        
        # Execute workflow - should fail at validation
        with pytest.raises(Exception) as exc_info:
            await workflow.execute_complete_analysis("Test Patient")
        
        assert "Patient ID mismatch" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_workflow_progress_reporting(self, mock_audit_logger):
        """Test detailed workflow progress reporting."""
        progress_history = []
        
        def detailed_progress_tracker(progress: WorkflowProgress):
            progress_history.append({
                "timestamp": datetime.now(),
                "current_step": progress.current_step,
                "step_name": progress.step_names[progress.current_step] if progress.current_step < len(progress.step_names) else "Completed",
                "percentage": progress.get_progress_percentage(),
                "total_duration": progress.get_total_duration()
            })
        
        workflow = MainWorkflow(
            audit_logger=mock_audit_logger,
            progress_callback=detailed_progress_tracker
        )
        
        # Mock all agents with minimal data
        patient_data = PatientData(
            patient_id="PROGRESS_TEST_001",
            name="Progress Test",
            demographics=Demographics(),
            medical_history=[],
            medications=[],
            procedures=[],
            diagnoses=[],
            raw_xml="<patient>test</patient>",
            extraction_timestamp=datetime.now()
        )
        
        medical_summary = MedicalSummary(
            patient_id="PROGRESS_TEST_001",
            summary_text="Test",
            key_conditions=[],
            medication_summary="None",
            procedure_summary="None",
            chronological_events=[],
            generated_timestamp=datetime.now(),
            data_quality_score=0.8,
            missing_data_indicators=[]
        )
        
        research_analysis = ResearchAnalysis(
            patient_id="PROGRESS_TEST_001",
            analysis_timestamp=datetime.now(),
            conditions_analyzed=[],
            research_findings=[],
            condition_research_correlations={},
            categorized_findings={},
            research_insights=[],
            clinical_recommendations=[],
            analysis_confidence=0.5,
            total_papers_reviewed=0,
            relevant_papers_found=0
        )
        
        analysis_report = AnalysisReport(
            report_id="RPT_PROGRESS_TEST",
            patient_data=patient_data,
            medical_summary=medical_summary,
            research_analysis=research_analysis,
            generated_timestamp=datetime.now(),
            processing_time_seconds=1.0,
            agent_versions={"test": "1.0"},
            quality_metrics={"overall_quality_score": 0.5}
        )
        
        workflow.xml_parser.parse_patient_record = Mock(return_value=patient_data)
        workflow.medical_summarizer.generate_medical_summary = Mock(return_value=medical_summary)
        workflow.research_correlator.analyze_patient_research = Mock(return_value=research_analysis)
        workflow.report_generator.generate_analysis_report = Mock(return_value=analysis_report)
        workflow.s3_persister.save_analysis_report = Mock(return_value="test-s3-key")
        
        # Execute workflow
        await workflow.execute_complete_analysis("Progress Test")
        
        # Verify progress reporting
        assert len(progress_history) == 6  # One for each step
        
        # Verify progress increases
        for i in range(1, len(progress_history)):
            assert progress_history[i]["percentage"] >= progress_history[i-1]["percentage"]
        
        # Verify step names are correct
        expected_steps = [
            "Patient Name Input",
            "XML Parsing & Data Extraction",
            "Medical Summarization", 
            "Research Correlation",
            "Report Generation",
            "Report Persistence"
        ]
        
        for i, step_name in enumerate(expected_steps):
            assert progress_history[i]["step_name"] == step_name
        
        print(f"✅ Progress Reporting Test Passed:")
        print(f"   - Total Progress Updates: {len(progress_history)}")
        print(f"   - Final Progress: {progress_history[-1]['percentage']:.1f}%")
        print(f"   - All Steps Tracked: {len(expected_steps)} steps")
    
    @pytest.mark.asyncio
    async def test_workflow_performance_metrics(self, mock_audit_logger):
        """Test workflow performance metrics and timing."""
        workflow = MainWorkflow(audit_logger=mock_audit_logger)
        
        # Create test data
        patient_data = PatientData(
            patient_id="PERF_TEST_001",
            name="Performance Test",
            demographics=Demographics(age=45, gender="F"),
            medical_history=[],
            medications=[],
            procedures=[],
            diagnoses=[],
            raw_xml="<patient>performance test</patient>",
            extraction_timestamp=datetime.now()
        )
        
        # Mock agents with small delays to test timing
        async def mock_with_delay(return_value, delay=0.01):
            await asyncio.sleep(delay)
            return return_value
        
        workflow.xml_parser.parse_patient_record = Mock(
            side_effect=lambda x: mock_with_delay(patient_data, 0.01)
        )
        
        # Execute workflow
        start_time = datetime.now()
        
        # For this test, we'll just test the timing infrastructure
        # by checking that workflow status includes timing information
        workflow.current_workflow_id = "PERF_TEST"
        workflow.progress = WorkflowProgress()
        workflow.progress.start_step(0)
        await asyncio.sleep(0.01)
        workflow.progress.complete_step(0)
        
        status = workflow.get_workflow_status()
        
        # Verify timing information is captured
        assert "total_duration_seconds" in status
        assert "step_durations" in status
        assert status["total_duration_seconds"] > 0
        
        print(f"✅ Performance Metrics Test Passed:")
        print(f"   - Timing Infrastructure: Working")
        print(f"   - Status Reporting: Complete")
        print(f"   - Duration Tracking: {status['total_duration_seconds']:.3f}s")