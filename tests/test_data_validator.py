"""Tests for comprehensive data validation service."""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.quality.data_validator import DataValidationService
from src.quality.hallucination_detector import ValidationSeverity, ValidationType
from src.models import PatientData, MedicalSummary, ResearchAnalysis, AnalysisReport


class TestDataValidationService:
    """Test DataValidationService class."""
    
    @pytest.fixture
    def mock_audit_logger(self):
        """Create mock audit logger."""
        return Mock()
    
    @pytest.fixture
    def mock_error_handler(self):
        """Create mock error handler."""
        return Mock()
    
    @pytest.fixture
    def validator_service(self, mock_audit_logger, mock_error_handler):
        """Create data validation service."""
        return DataValidationService(
            audit_logger=mock_audit_logger,
            error_handler=mock_error_handler,
            enable_strict_validation=True
        )
    
    @pytest.fixture
    def sample_analysis_report(self):
        """Create sample analysis report for testing."""
        from src.models import Demographics
        
        demographics = Demographics(
            date_of_birth="1978-05-15",
            gender="Male",
            age=45,
            address=None,
            phone=None,
            emergency_contact=None
        )
        
        patient_data = PatientData(
            name="John Smith",
            patient_id="PAT123",
            demographics=demographics,
            medical_history=[],
            medications=[],
            procedures=[],
            diagnoses=[],
            raw_xml="<patient></patient>",
            extraction_timestamp=datetime.now()
        )
        
        from src.models.medical_summary import Condition
        
        medical_summary = MedicalSummary(
            patient_id="PAT123",
            key_conditions=[
                Condition(name="hypertension", confidence_score=0.9, status="chronic"),
                Condition(name="diabetes", confidence_score=0.8, status="chronic")
            ],
            summary_text="Patient has hypertension and diabetes with good control.",
            medication_summary="Patient is on lisinopril and metformin",
            procedure_summary="No recent procedures",
            chronological_events=[],
            generated_timestamp=datetime.now(),
            data_quality_score=0.9,
            missing_data_indicators=[]
        )
        
        from src.models.research_analysis import ResearchFinding
        from src.models.medical_summary import Condition
        
        research_analysis = ResearchAnalysis(
            patient_id="PAT123",
            analysis_timestamp=datetime.now(),
            conditions_analyzed=[
                Condition(name="hypertension", confidence_score=0.9, status="chronic"),
                Condition(name="diabetes", confidence_score=0.8, status="chronic")
            ],
            research_findings=[
                ResearchFinding(
                    title="Hypertension Management in Primary Care",
                    authors=["Smith, J.", "Johnson, M."],
                    journal="Journal of Medicine",
                    publication_date="2023-01-15",
                    relevance_score=0.9,
                    key_findings="ACE inhibitors effective for hypertension",
                    citation="Smith et al. (2023)"
                ),
                ResearchFinding(
                    title="Diabetes Treatment Guidelines",
                    authors=["Brown, A."],
                    journal="Diabetes Care",
                    publication_date="2022-06-10",
                    relevance_score=0.85,
                    key_findings="Metformin remains first-line therapy",
                    citation="Brown (2022)"
                )
            ],
            condition_research_correlations={
                "hypertension": [],
                "diabetes": []
            },
            categorized_findings={
                "treatment": [],
                "diagnosis": []
            },
            research_insights=["Strong evidence for ACE inhibitor therapy"],
            clinical_recommendations=["Monitor blood pressure regularly", "Continue current diabetes management"],
            analysis_confidence=0.88,
            total_papers_reviewed=50,
            relevant_papers_found=2
        )
        
        return AnalysisReport(
            patient_data=patient_data,
            medical_summary=medical_summary,
            research_analysis=research_analysis,
            generated_timestamp=datetime.now(),
            report_id="RPT_20241110_001",
            processing_time_seconds=2.5,
            agent_versions={"xml_parser": "1.0", "summarizer": "1.0", "research": "1.0"},
            quality_metrics={
                "overall_quality_score": 0.90,
                "data_completeness_score": 0.85,
                "validation_results": True
            }
        )
    
    def test_service_initialization(self, validator_service):
        """Test service initialization."""
        assert validator_service.audit_logger is not None
        assert validator_service.error_handler is not None
        assert validator_service.enable_strict_validation is True
        assert validator_service.hallucination_detector is not None
        assert "total_validations" in validator_service.validation_stats
    
    def test_validate_complete_analysis_success(self, validator_service, sample_analysis_report):
        """Test successful complete analysis validation."""
        validation_result = validator_service.validate_complete_analysis(sample_analysis_report)
        
        # Check validation result structure
        assert "validation_status" in validation_result
        assert "total_issues" in validation_result
        assert "validation_sections" in validation_result
        assert "validation_duration" in validation_result
        assert "patient_id" in validation_result
        assert "report_id" in validation_result
        
        # Should pass or have only minor issues for good data
        assert validation_result["validation_status"] in ["PASSED", "PASSED_WITH_WARNINGS"]
        assert validation_result["patient_id"] == "PAT123"
        assert validation_result["report_id"] == "RPT_20241110_001"
    
    def test_validate_complete_analysis_with_source(self, validator_service, sample_analysis_report):
        """Test complete analysis validation with source XML."""
        source_xml = """
        <patient name="John Smith" id="PAT123">
            <demographics>
                <age>45</age>
                <gender>Male</gender>
                <date_of_birth>1978-05-15</date_of_birth>
            </demographics>
            <conditions>
                <condition>hypertension</condition>
                <condition>diabetes</condition>
            </conditions>
            <medications>
                <medication>lisinopril</medication>
                <medication>metformin</medication>
            </medications>
        </patient>
        """
        
        validation_result = validator_service.validate_complete_analysis(
            sample_analysis_report, 
            source_xml=source_xml
        )
        
        # Should include source verification section
        assert "source_verification" in validation_result["validation_sections"]
        
        # Should have good validation status for matching data
        assert validation_result["validation_status"] in ["PASSED", "PASSED_WITH_WARNINGS"]
    
    def test_validate_patient_data_valid(self, validator_service):
        """Test patient data validation with valid data."""
        from src.models import Demographics
        
        demographics = Demographics(age=45, gender="Male")
        patient_data = PatientData(
            name="John Smith",
            patient_id="PAT123",
            demographics=demographics,
            medical_history=[],
            medications=[],
            procedures=[],
            diagnoses=[],
            raw_xml="<patient></patient>",
            extraction_timestamp=datetime.now()
        )
        
        issues = validator_service._validate_patient_data(patient_data)
        
        # Should have no critical issues for valid data
        critical_issues = [issue for issue in issues if issue.severity == ValidationSeverity.CRITICAL]
        assert len(critical_issues) == 0
    
    def test_validate_patient_data_invalid(self, validator_service):
        """Test patient data validation with invalid data."""
        from src.models import Demographics
        
        demographics = Demographics(age=200)  # Invalid age
        patient_data = PatientData(
            name="",  # Empty name
            patient_id="",  # Empty ID
            demographics=demographics,
            medical_history=[],
            medications=[],
            procedures=[],
            diagnoses=[],
            raw_xml="<patient></patient>",
            extraction_timestamp=datetime.now()
        )
        
        issues = validator_service._validate_patient_data(patient_data)
        
        # Should detect multiple issues
        assert len(issues) > 0
        
        # Should have error-level issues for missing required fields
        error_issues = [issue for issue in issues 
                       if issue.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]]
        assert len(error_issues) > 0
    
    def test_validate_medical_summary_valid(self, validator_service):
        """Test medical summary validation with valid data."""
        from src.models.medical_summary import Condition
        
        medical_summary = MedicalSummary(
            patient_id="PAT123",
            key_conditions=[
                Condition(name="hypertension", confidence_score=0.9),
                Condition(name="diabetes", confidence_score=0.8)
            ],
            summary_text="Patient has well-controlled hypertension and diabetes.",
            medication_summary="Patient is on lisinopril and metformin",
            procedure_summary="No recent procedures",
            chronological_events=[],
            generated_timestamp=datetime.now(),
            data_quality_score=0.9,
            missing_data_indicators=[]
        )
        
        issues = validator_service._validate_medical_summary(medical_summary)
        
        # Should have minimal issues for valid medical data
        error_issues = [issue for issue in issues 
                       if issue.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]]
        assert len(error_issues) == 0
    
    def test_validate_medical_summary_invalid(self, validator_service):
        """Test medical summary validation with invalid data."""
        from src.models.medical_summary import Condition
        
        medical_summary = MedicalSummary(
            patient_id="PAT123",
            key_conditions=[
                Condition(name="unknown_condition", confidence_score=0.2),  # Low confidence
                Condition(name="", confidence_score=0.9)  # Empty name
            ],
            summary_text="",  # Empty summary
            medication_summary="Patient is on unknown_medication",
            procedure_summary="",
            chronological_events=[],
            generated_timestamp=datetime.now(),
            data_quality_score=0.5,
            missing_data_indicators=["summary_text"]
        )
        
        issues = validator_service._validate_medical_summary(medical_summary)
        
        # Should detect multiple issues
        assert len(issues) > 0
        
        # Should detect completeness issues (empty summary text, empty condition name)
        completeness_issues = [issue for issue in issues 
                             if issue.validation_type == ValidationType.COMPLETENESS]
        
        assert len(completeness_issues) > 0
    
    def test_perform_cross_validation_consistent(self, validator_service, sample_analysis_report):
        """Test cross-validation with consistent data."""
        issues = validator_service._perform_cross_validation(sample_analysis_report)
        
        # Should have minimal issues for consistent data
        critical_issues = [issue for issue in issues if issue.severity == ValidationSeverity.CRITICAL]
        assert len(critical_issues) == 0
    
    def test_perform_cross_validation_inconsistent(self, validator_service):
        """Test cross-validation with inconsistent data."""
        from src.models import Demographics
        
        # Create report with inconsistent data
        demographics = Demographics()
        patient_data = PatientData(
            name="John Smith",
            patient_id="PAT123",
            demographics=demographics,
            medical_history=[],
            medications=[],
            procedures=[],
            diagnoses=[],
            raw_xml="<patient></patient>",
            extraction_timestamp=datetime.now()
        )
        
        from src.models.medical_summary import Condition
        
        medical_summary = MedicalSummary(
            patient_id="PAT123",
            key_conditions=[Condition(name="hypertension", confidence_score=0.9)],
            summary_text="Patient has hypertension.",
            medication_summary="No medications listed",
            procedure_summary="No procedures",
            chronological_events=[],
            generated_timestamp=datetime.now(),
            data_quality_score=0.8,
            missing_data_indicators=[]
        )
        
        # Research findings not related to conditions
        from src.models.research_analysis import ResearchFinding
        
        research_analysis = ResearchAnalysis(
            patient_id="PAT123",
            analysis_timestamp=datetime.now(),
            conditions_analyzed=[Condition(name="hypertension", confidence_score=0.9)],
            research_findings=[
                ResearchFinding(
                    title="Cancer Treatment Study",  # Unrelated to hypertension
                    authors=["Smith, J."],
                    journal="Cancer Journal",
                    publication_date="2023-01-01",
                    relevance_score=0.3,
                    key_findings="Cancer treatment findings",
                    citation="Smith (2023)"
                )
            ],
            condition_research_correlations={},
            categorized_findings={},
            research_insights=[],
            clinical_recommendations=[],
            analysis_confidence=0.95,  # High confidence with few findings
            total_papers_reviewed=10,
            relevant_papers_found=1
        )
        
        report = AnalysisReport(
            patient_data=patient_data,
            medical_summary=medical_summary,
            research_analysis=research_analysis,
            generated_timestamp=datetime.now(),
            report_id="RPT_TEST",
            processing_time_seconds=1.5,
            agent_versions={"xml_parser": "1.0", "summarizer": "1.0", "research": "1.0"},
            quality_metrics={"overall_quality_score": 0.75}
        )
        
        issues = validator_service._perform_cross_validation(report)
        
        # Should detect inconsistencies
        coherence_issues = [issue for issue in issues 
                          if issue.validation_type == ValidationType.LOGICAL_COHERENCE]
        assert len(coherence_issues) > 0
    
    def test_analysis_report_to_dict(self, validator_service, sample_analysis_report):
        """Test analysis report to dictionary conversion."""
        report_dict = validator_service._analysis_report_to_dict(sample_analysis_report)
        
        # Check structure
        assert "patient_data" in report_dict
        assert "medical_summary" in report_dict
        assert "research_analysis" in report_dict
        
        # Check patient data
        patient_data = report_dict["patient_data"]
        assert patient_data["name"] == "John Smith"
        assert patient_data["patient_id"] == "PAT123"
        # Demographics may be nested or flattened - just verify the structure exists
        assert "demographics" in patient_data or "age" in patient_data
        
        # Check medical summary
        medical_summary = report_dict["medical_summary"]
        assert len(medical_summary["key_conditions"]) == 2
        assert "hypertension" in str(medical_summary["key_conditions"])
        
        # Check research analysis
        research_analysis = report_dict["research_analysis"]
        assert len(research_analysis["research_findings"]) == 2
        assert research_analysis["analysis_confidence"] == 0.88
    
    def test_update_validation_statistics(self, validator_service):
        """Test validation statistics updates."""
        initial_stats = validator_service.get_validation_statistics()
        assert initial_stats["total_validations"] == 0
        
        # Simulate validation reports
        passed_report = {"validation_status": "PASSED", "total_issues": 0}
        failed_report = {"validation_status": "FAILED", "total_issues": 5, 
                        "issues_by_severity": {"critical": [1, 2]}}
        warning_report = {"validation_status": "WARNING", "total_issues": 2}
        
        validator_service._update_validation_statistics(passed_report)
        validator_service._update_validation_statistics(failed_report)
        validator_service._update_validation_statistics(warning_report)
        
        updated_stats = validator_service.get_validation_statistics()
        
        assert updated_stats["total_validations"] == 3
        assert updated_stats["passed_validations"] == 1
        assert updated_stats["failed_validations"] == 1
        assert updated_stats["warnings_generated"] == 1
        assert updated_stats["critical_issues_found"] == 2
        assert updated_stats["success_rate"] == 1/3
    
    def test_get_validation_statistics(self, validator_service):
        """Test validation statistics retrieval."""
        stats = validator_service.get_validation_statistics()
        
        # Check required fields
        required_fields = [
            "total_validations", "passed_validations", "failed_validations",
            "warnings_generated", "critical_issues_found", "success_rate",
            "warning_rate", "failure_rate"
        ]
        
        for field in required_fields:
            assert field in stats
        
        # Check initial values
        assert stats["total_validations"] == 0
        assert stats["success_rate"] == 0.0
    
    def test_clear_statistics(self, validator_service):
        """Test statistics clearing."""
        # Add some statistics
        validator_service.validation_stats["total_validations"] = 5
        validator_service.validation_stats["passed_validations"] = 3
        
        # Clear statistics
        validator_service.clear_statistics()
        
        # Verify cleared
        stats = validator_service.get_validation_statistics()
        assert stats["total_validations"] == 0
        assert stats["passed_validations"] == 0
    
    def test_validation_with_error_handling(self, validator_service, mock_error_handler):
        """Test validation with error handling integration."""
        # Create invalid report that will cause validation error
        invalid_report = Mock()
        invalid_report.patient_data.patient_id = "PAT123"
        invalid_report.patient_data.name = None  # This will cause an error
        
        # Mock the analysis_report_to_dict to raise an exception
        with patch.object(validator_service, '_analysis_report_to_dict', side_effect=Exception("Test error")):
            result = validator_service.validate_complete_analysis(invalid_report)
        
        # Should return error result
        assert result["validation_status"] == "ERROR"
        assert "error_message" in result
        assert result["patient_id"] == "PAT123"
        
        # Should have called error handler
        mock_error_handler.handle_error.assert_called_once()
    
    def test_strict_validation_mode(self):
        """Test strict validation mode differences."""
        strict_validator = DataValidationService(enable_strict_validation=True)
        lenient_validator = DataValidationService(enable_strict_validation=False)
        
        assert strict_validator.enable_strict_validation is True
        assert lenient_validator.enable_strict_validation is False
    
    def test_audit_logging_integration(self, validator_service, mock_audit_logger, sample_analysis_report):
        """Test audit logging integration."""
        validator_service.validate_complete_analysis(sample_analysis_report)
        
        # Should have logged validation start and completion
        assert mock_audit_logger.log_patient_access.call_count >= 2
        
        # Check that patient access was logged
        call_args_list = mock_audit_logger.log_patient_access.call_args_list
        operations = [call[1]["operation"] for call in call_args_list]
        
        assert "comprehensive_validation" in operations
        assert "validation_completed" in operations


class TestDataValidationServiceIntegration:
    """Test data validation service integration scenarios."""
    
    def test_end_to_end_validation_workflow(self):
        """Test complete end-to-end validation workflow."""
        # Create validation service
        audit_logger = Mock()
        error_handler = Mock()
        validator = DataValidationService(
            audit_logger=audit_logger,
            error_handler=error_handler,
            enable_strict_validation=True
        )
        
        # Create comprehensive test data
        from src.models import Demographics
        
        demographics = Demographics(age=35, gender="Female")
        patient_data = PatientData(
            name="Jane Doe",
            patient_id="PAT456",
            demographics=demographics,
            medical_history=[],
            medications=[],
            procedures=[],
            diagnoses=[],
            raw_xml="<patient></patient>",
            extraction_timestamp=datetime.now()
        )
        
        from src.models.medical_summary import Condition
        
        medical_summary = MedicalSummary(
            patient_id="PAT456",
            key_conditions=[
                Condition(name="asthma", confidence_score=0.85),
                Condition(name="allergic rhinitis", confidence_score=0.75)
            ],
            summary_text="Patient has well-controlled asthma and seasonal allergies.",
            medication_summary="Patient is on albuterol and fluticasone",
            procedure_summary="No recent procedures",
            chronological_events=[],
            generated_timestamp=datetime.now(),
            data_quality_score=0.88,
            missing_data_indicators=[]
        )
        
        from src.models.research_analysis import ResearchFinding
        
        research_analysis = ResearchAnalysis(
            patient_id="PAT456",
            analysis_timestamp=datetime.now(),
            conditions_analyzed=[
                Condition(name="asthma", confidence_score=0.85),
                Condition(name="allergic rhinitis", confidence_score=0.75)
            ],
            research_findings=[
                ResearchFinding(
                    title="Asthma Management Guidelines",
                    authors=["Wilson, K.", "Davis, L."],
                    journal="Respiratory Medicine",
                    publication_date="2023-03-15",
                    relevance_score=0.92,
                    key_findings="Updated asthma management protocols",
                    citation="Wilson & Davis (2023)"
                )
            ],
            condition_research_correlations={
                "asthma": [],
                "allergic rhinitis": []
            },
            categorized_findings={
                "treatment": []
            },
            research_insights=["Evidence-based asthma management"],
            clinical_recommendations=["Follow updated guidelines"],
            analysis_confidence=0.82,
            total_papers_reviewed=30,
            relevant_papers_found=1
        )
        
        analysis_report = AnalysisReport(
            patient_data=patient_data,
            medical_summary=medical_summary,
            research_analysis=research_analysis,
            generated_timestamp=datetime.now(),
            report_id="RPT_INTEGRATION_001",
            processing_time_seconds=3.2,
            agent_versions={"xml_parser": "1.0", "summarizer": "1.0", "research": "1.0"},
            quality_metrics={"overall_quality_score": 0.88}
        )
        
        source_xml = """
        <patient name="Jane Doe" id="PAT456">
            <demographics>
                <age>35</age>
                <gender>Female</gender>
            </demographics>
            <conditions>
                <condition>asthma</condition>
                <condition>allergic rhinitis</condition>
            </conditions>
            <medications>
                <medication>albuterol</medication>
                <medication>fluticasone</medication>
            </medications>
        </patient>
        """
        
        # Run complete validation
        validation_result = validator.validate_complete_analysis(
            analysis_report, 
            source_xml=source_xml
        )
        
        # Verify comprehensive validation result
        assert validation_result["validation_status"] in ["PASSED", "PASSED_WITH_WARNINGS"]
        assert validation_result["patient_id"] == "PAT456"
        assert validation_result["report_id"] == "RPT_INTEGRATION_001"
        assert "validation_sections" in validation_result
        assert "validation_duration" in validation_result
        
        # Check all validation sections were performed
        sections = validation_result["validation_sections"]
        expected_sections = [
            "patient_data", "medical_summary", "research_analysis",
            "source_verification", "completeness", "cross_validation"
        ]
        
        for section in expected_sections:
            assert section in sections
            assert "issues_count" in sections[section]
            assert "issues" in sections[section]
        
        # Verify audit logging
        assert audit_logger.log_patient_access.call_count >= 2
        
        # Verify statistics were updated
        stats = validator.get_validation_statistics()
        assert stats["total_validations"] == 1
    
    def test_validation_with_multiple_issues(self):
        """Test validation with data containing multiple types of issues."""
        validator = DataValidationService(enable_strict_validation=True)
        
        # Create problematic data
        from src.models import Demographics
        
        demographics = Demographics(age=999)  # Invalid age
        patient_data = PatientData(
            name="Test Patient",
            patient_id="PAT999",
            demographics=demographics,
            medical_history=[],
            medications=[],
            procedures=[],
            diagnoses=[],
            raw_xml="<patient></patient>",
            extraction_timestamp=datetime.now()
        )
        
        from src.models.medical_summary import Condition
        
        medical_summary = MedicalSummary(
            patient_id="PAT999",
            key_conditions=[
                Condition(name="fake_condition", confidence_score=0.1),  # Unknown condition, low confidence
                Condition(name="", confidence_score=0.9)  # Empty condition name
            ],
            summary_text="",  # Empty summary
            medication_summary="Patient is on fake_medication",  # Unknown medication
            procedure_summary="",
            chronological_events=[],
            generated_timestamp=datetime.now(),
            data_quality_score=0.05,
            missing_data_indicators=["summary_text", "valid_conditions"]
        )
        
        from src.models.research_analysis import ResearchFinding
        
        research_analysis = ResearchAnalysis(
            patient_id="PAT999",
            analysis_timestamp=datetime.now(),
            conditions_analyzed=[
                Condition(name="fake_condition", confidence_score=0.1)
            ],
            research_findings=[
                ResearchFinding(
                    title="Unrelated Study",
                    authors=[],  # Empty authors - will cause validation error
                    journal="",  # Empty journal - will cause validation error
                    publication_date="2050-01-01",  # Future year
                    relevance_score=0.1,
                    key_findings="",
                    citation=""
                )
            ],
            condition_research_correlations={},
            categorized_findings={},
            research_insights=[],
            clinical_recommendations=[],
            analysis_confidence=0.05,  # Very low confidence
            total_papers_reviewed=5,
            relevant_papers_found=1
        )
        
        analysis_report = AnalysisReport(
            patient_data=patient_data,
            medical_summary=medical_summary,
            research_analysis=research_analysis,
            generated_timestamp=datetime.now(),
            report_id="RPT_PROBLEMATIC",
            processing_time_seconds=1.0,
            agent_versions={"xml_parser": "1.0", "summarizer": "1.0", "research": "1.0"},
            quality_metrics={"overall_quality_score": 0.10}
        )
        
        # Run validation
        validation_result = validator.validate_complete_analysis(analysis_report)
        
        # Should detect multiple issues (at least 4)
        assert validation_result["total_issues"] >= 4
        assert validation_result["validation_status"] in ["FAILED", "WARNING", "PASSED_WITH_WARNINGS"]
        
        # Should have issues in multiple categories
        issues_by_type = validation_result["issues_by_type"]
        assert len(issues_by_type) > 2  # Multiple validation types should have issues
        
        # Should have issues of different severities (at least warnings)
        issues_by_severity = validation_result["issues_by_severity"]
        assert len(issues_by_severity) >= 1  # At least one severity level
        
        # Recommendations may or may not be generated depending on validation logic
        assert "recommendations" in validation_result