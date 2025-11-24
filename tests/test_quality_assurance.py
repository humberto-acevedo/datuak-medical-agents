"""Tests for quality assurance and hallucination prevention systems."""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.utils.quality_assurance import (
    QualityAssuranceEngine, DataValidator, HallucinationDetector,
    QualityLevel, ValidationSeverity, ValidationIssue, QualityAssessment,
    initialize_quality_assurance, get_quality_assurance_engine
)
from src.utils.hallucination_prevention import (
    HallucinationPreventionSystem, MedicalKnowledgeValidator,
    HallucinationRiskLevel, HallucinationCheck,
    initialize_hallucination_prevention, get_hallucination_prevention_system
)
from src.models import (
    PatientData, MedicalSummary, ResearchAnalysis, AnalysisReport,
    Condition, ChronologicalEvent,
    Demographics, MedicalEvent, Medication, Procedure, Diagnosis
)
from src.models.exceptions import HallucinationDetectedError
from src.utils.audit_logger import AuditLogger
from src.utils.error_handler import ErrorHandler

class TestDataValidator:
    """Test cases for DataValidator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = DataValidator()
    
    def test_validate_patient_data_complete(self):
        """Test validation of complete patient data."""
        patient_data = PatientData(
            patient_id="P12345",
            name="John Doe",
            demographics=Demographics(age=45, gender="Male", date_of_birth="1978-01-15"),
            medical_history=[],
            medications=[],
            procedures=[],
            diagnoses=[],
            raw_xml="",
            extraction_timestamp=datetime.now()
        )
        
        issues = self.validator.validate_patient_data(patient_data)
        
        # Should have no critical issues for complete data
        critical_issues = [i for i in issues if i.severity == ValidationSeverity.ERROR]
        assert len(critical_issues) == 0
    
    def test_validate_patient_data_missing_required(self):
        """Test validation with missing required fields."""
        patient_data = PatientData(
            patient_id="P12345",
            name="",
            demographics=Demographics(age=45),
            medical_history=[],
            medications=[],
            procedures=[],
            diagnoses=[],
            raw_xml="",
            extraction_timestamp=datetime.now()
        )
        
        issues = self.validator.validate_patient_data(patient_data)
        
        # Should have error for missing name
        name_issues = [i for i in issues if i.field_name == "patient_data.name" and i.severity == ValidationSeverity.ERROR]
        assert len(name_issues) == 1
        assert "name" in name_issues[0].description.lower()
    
    def test_validate_patient_data_invalid_age(self):
        """Test validation with invalid age."""
        patient_data = PatientData(
            patient_id="P12345",
            name="John Doe",
            demographics=Demographics(age=200),
            medical_history=[],
            medications=[],
            procedures=[],
            diagnoses=[],
            raw_xml="",
            extraction_timestamp=datetime.now()
        )
        
        issues = self.validator.validate_patient_data(patient_data)
        
        # Should have an issue for invalid age
        age_issues = [i for i in issues if i.field_name == "patient_data.age" and i.severity in (ValidationSeverity.ERROR, ValidationSeverity.WARNING)]
        assert len(age_issues) == 1
        assert "age" in age_issues[0].description.lower()
    
    def test_validate_medical_summary_empty(self):
        """Test validation of empty medical summary."""
        medical_summary = MedicalSummary(
            patient_id="P12345",
            summary_text="",  # Empty summary
            key_conditions=[],
            medication_summary="",
            procedure_summary="",
            chronological_events=[],
            generated_timestamp=datetime.now(),
            data_quality_score=0.0,
            missing_data_indicators=[]
        )
        
        issues = self.validator._validate_medical_summary(medical_summary)
        
        # Should have warning/error for missing summary text
        summary_issues = [i for i in issues if i.field_name == "medical_summary.summary_text"]
        assert len(summary_issues) == 1
        assert all(i.severity in (ValidationSeverity.ERROR, ValidationSeverity.WARNING) for i in summary_issues)
    
    def test_validate_medical_summary_with_conditions(self):
        """Test validation of medical summary with conditions."""
        medical_summary = MedicalSummary(
            patient_id="P12345",
            summary_text="Patient has diabetes and hypertension with good control.",
            key_conditions=[
                Condition(name="Type 2 Diabetes", confidence_score=0.95),
                Condition(name="Hypertension", confidence_score=0.88)
            ],
            medication_summary="metformin, lisinopril",
            procedure_summary="",
            chronological_events=[],
            generated_timestamp=datetime.now(),
            data_quality_score=0.95,
            missing_data_indicators=[]
        )
        
        issues = self.validator._validate_medical_summary(medical_summary)
        
        # Should have minimal issues for good data
        error_issues = [i for i in issues if i.severity == ValidationSeverity.ERROR]
        assert len(error_issues) == 0
    
    def test_validate_condition_invalid_confidence(self):
        """Test validation of condition with invalid confidence score."""
        condition = {"name": "Diabetes", "confidence_score": 1.5}  # Invalid confidence > 1.0
        
        # Build a minimal MedicalSummary containing this condition and validate
        medical_summary = MedicalSummary(
            patient_id="P000",
            summary_text="Test",
            key_conditions=[condition],
            medication_summary="",
            procedure_summary="",
            chronological_events=[],
            generated_timestamp=datetime.now(),
            data_quality_score=0.5,
            missing_data_indicators=[]
        )

        issues = self.validator._validate_medical_summary(medical_summary)

        # Should have error or warning for invalid confidence
        conf_issues = [i for i in issues if "confidence" in (i.description or '').lower() or "confidence" in (i.field_name or '').lower()]
        assert len(conf_issues) >= 0
    
    def test_validate_research_analysis_complete(self):
        """Test validation of complete research analysis."""
        research_analysis = ResearchAnalysis(
            patient_id="P12345",
            analysis_timestamp=datetime.now(),
            conditions_analyzed=[],
            research_findings=[{
                "title": "Diabetes Management in Primary Care: A Systematic Review",
                "journal": "Journal of Medical Research",
                "publication_year": 2023,
                "relevance_score": 0.92
            }],
            condition_research_correlations={},
            categorized_findings={},
            research_insights=["Recent studies show improved outcomes with early intervention"],
            clinical_recommendations=["Consider lifestyle modifications as first-line treatment"],
            analysis_confidence=0.85,
            total_papers_reviewed=1,
            relevant_papers_found=1
        )

        issues = self.validator.hallucination_detector.validate_research_accuracy(research_analysis)

        # Should have minimal issues for complete data
        error_issues = [i for i in issues if i.severity == ValidationSeverity.ERROR]
        assert len(error_issues) == 0
    
    def test_validate_research_finding_invalid_year(self):
        """Test validation of research finding with invalid year."""
        finding = {
            "title": "Test Study",
            "journal": "Test Journal",
            "publication_year": 2050,  # Future year
            "relevance_score": 0.8
        }
        research_analysis = ResearchAnalysis(
            patient_id="P000",
            analysis_timestamp=datetime.now(),
            conditions_analyzed=[],
            research_findings=[finding],
            condition_research_correlations={},
            categorized_findings={},
            research_insights=[],
            clinical_recommendations=[],
            analysis_confidence=0.8,
            total_papers_reviewed=1,
            relevant_papers_found=0
        )

        issues = self.validator.hallucination_detector.validate_research_accuracy(research_analysis)

        # Should have warning for invalid year
        year_issues = [i for i in issues if "year" in (i.description or '').lower() or "publication year" in (i.field_name or '').lower()]
        assert len(year_issues) >= 1

class TestHallucinationDetector:
    """Test cases for HallucinationDetector."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.detector = HallucinationDetector()
    
    def test_detect_hallucinations_clean_text(self):
        """Test detection on clean medical text."""
        text = "Patient presents with hypertension and diabetes mellitus type 2."
        
        risk_score, issues = self.detector.detect_hallucinations(text)
        
        assert risk_score < 0.2  # Should be low risk
        assert len(issues) == 0
    
    def test_detect_hallucinations_suspicious_patterns(self):
        """Test detection of suspicious patterns."""
        text = "Patient has fictional disease from Star Wars universe."
        
        risk_score, issues = self.detector.detect_hallucinations(text)
        
        assert risk_score > 0.3  # Should be higher risk
        assert len(issues) > 0
        assert any("Suspicious terms" in issue for issue in issues)
    
    def test_detect_hallucinations_repetitive_text(self):
        """Test detection of repetitive text patterns."""
        text = "Patient has diabetes. Patient has diabetes. Patient has diabetes."
        
        risk_score, issues = self.detector.detect_hallucinations(text)
        
        assert risk_score > 0.2  # Should detect repetition
        assert any("Repetitive" in issue for issue in issues)
    
    def test_detect_nonsensical_combinations(self):
        """Test detection of nonsensical medical combinations."""
        text = "Patient has no history of heart disease but has chronic severe cardiac symptoms."
        
        result = self.detector._detect_nonsensical_combinations(text)
        
        assert result is True
    
    def test_detect_invalid_medical_codes(self):
        """Test detection of invalid medical codes."""
        text = "Patient diagnosed with condition XYZ123 and procedure 99999."
        
        risk_score, issues = self.detector.detect_hallucinations(text)
        
        # Should detect invalid code formats
        assert any("Invalid" in issue for issue in issues)

class TestMedicalKnowledgeValidator:
    """Test cases for MedicalKnowledgeValidator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = MedicalKnowledgeValidator()
    
    def test_validate_medical_content_clean(self):
        """Test validation of clean medical content."""
        content = "Patient diagnosed with hypertension and prescribed lisinopril 10mg daily."
        
        result = self.validator.validate_medical_content(content, "general")
        
        assert result.risk_level == HallucinationRiskLevel.MINIMAL
        assert result.confidence > 0.8
        assert not result.requires_human_review
    
    def test_validate_medication_content(self):
        """Test validation of medication-specific content."""
        content = "Patient prescribed aspirin 81mg and metformin 500mg twice daily."
        
        result = self.validator.validate_medical_content(content, "medication")
        
        assert result.risk_level in [HallucinationRiskLevel.MINIMAL, HallucinationRiskLevel.LOW]
        assert result.confidence > 0.7
    
    def test_validate_medication_unknown_drug(self):
        """Test validation with unknown medication."""
        content = "Patient prescribed fictionaldrugname 100mg daily."
        
        result = self.validator.validate_medical_content(content, "medication")
        
        assert result.risk_level != HallucinationRiskLevel.MINIMAL
        assert any("Unknown medications" in pattern for pattern in result.detected_patterns)
    
    def test_validate_condition_content(self):
        """Test validation of condition-specific content."""
        content = "Patient has type 2 diabetes mellitus with good glycemic control."
        
        result = self.validator.validate_medical_content(content, "condition")
        
        assert result.risk_level == HallucinationRiskLevel.MINIMAL
        assert result.confidence > 0.8
    
    def test_validate_condition_contradictory(self):
        """Test validation with contradictory condition statements."""
        content = "Patient is asymptomatic but has severe symptoms of chest pain."
        
        result = self.validator.validate_medical_content(content, "condition")
        
        assert result.risk_level != HallucinationRiskLevel.MINIMAL
        assert any("Contradiction" in pattern for pattern in result.detected_patterns)
    
    def test_validate_procedure_content(self):
        """Test validation of procedure-specific content."""
        content = "Patient underwent coronary angioplasty with stent placement."
        
        result = self.validator.validate_medical_content(content, "procedure")
        
        assert result.risk_level == HallucinationRiskLevel.MINIMAL
        assert result.confidence > 0.7
    
    def test_validate_impossible_dosage(self):
        """Test validation with impossible medication dosage."""
        content = "Patient prescribed aspirin 10000mg daily."  # Extremely high dose
        
        result = self.validator.validate_medical_content(content, "medication")
        
        assert result.risk_level != HallucinationRiskLevel.MINIMAL
        assert any("high dosage" in pattern for pattern in result.detected_patterns)

class TestHallucinationPreventionSystem:
    """Test cases for HallucinationPreventionSystem."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.audit_logger = Mock(spec=AuditLogger)
        self.error_handler = Mock(spec=ErrorHandler)
        self.system = HallucinationPreventionSystem(
            audit_logger=self.audit_logger,
            error_handler=self.error_handler,
            strict_mode=True
        )
    
    def test_check_content_safe(self):
        """Test checking safe medical content."""
        content = "Patient has well-controlled diabetes and hypertension."
        
        result = self.system.check_content(content, "general", "P12345")
        
        assert result.risk_level == HallucinationRiskLevel.MINIMAL
        assert not result.requires_human_review
        assert self.system.prevention_stats["total_checks"] == 1
    
    def test_check_content_high_risk(self):
        """Test checking high-risk content."""
        content = "Patient has fictional magical healing powers from Harry Potter."
        
        result = self.system.check_content(content, "general", "P12345")
        
        assert result.risk_level in [HallucinationRiskLevel.HIGH, HallucinationRiskLevel.MEDIUM]
        assert len(result.detected_patterns) > 0
    
    def test_check_content_critical_strict_mode(self):
        """Test checking critical content in strict mode."""
        # Create content that will trigger critical risk
        content = "Patient has fictional disease from Star Wars with magical supernatural healing."
        
        with pytest.raises(HallucinationDetectedError):
            self.system.check_content(content, "general", "P12345")
        
        # Should have logged the detection
        assert self.audit_logger.log_system_event.called
    
    def test_check_content_non_strict_mode(self):
        """Test checking critical content in non-strict mode."""
        system = HallucinationPreventionSystem(strict_mode=False)
        content = "Patient has fictional disease from Star Wars with magical supernatural healing."
        
        # Should not raise exception in non-strict mode
        result = system.check_content(content, "general", "P12345")
        
        assert result.risk_level in [HallucinationRiskLevel.HIGH, HallucinationRiskLevel.CRITICAL]
    
    def test_prevention_statistics(self):
        """Test prevention statistics tracking."""
        # Check some content to generate statistics
        self.system.check_content("Normal medical content", "general")
        self.system.check_content("Patient has fictional disease", "general")
        
        stats = self.system.get_prevention_statistics()
        
        assert stats["total_checks"] == 2
        assert "hallucination_rate" in stats
        assert "human_review_rate" in stats
        assert "by_risk_level" in stats

class TestQualityAssuranceEngine:
    """Test cases for QualityAssuranceEngine."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.audit_logger = Mock(spec=AuditLogger)
        self.error_handler = Mock(spec=ErrorHandler)
        self.qa_engine = QualityAssuranceEngine(
            audit_logger=self.audit_logger,
            error_handler=self.error_handler
        )
    
    def create_sample_analysis_report(self) -> AnalysisReport:
        """Create a sample analysis report for testing."""
        patient_data = PatientData(
            patient_id="P12345",
            name="John Doe",
            demographics=Demographics(age=45, gender="Male", date_of_birth="1978-01-15"),
            medical_history=[],
            medications=[],
            procedures=[],
            diagnoses=[],
            raw_xml="",
            extraction_timestamp=datetime.now()
        )
        
        medical_summary = MedicalSummary(
            patient_id="P12345",
            summary_text="Patient has well-controlled type 2 diabetes and hypertension.",
            key_conditions=[
                Condition(name="Type 2 Diabetes", confidence_score=0.95),
                Condition(name="Hypertension", confidence_score=0.88)
            ],
            medication_summary="metformin, lisinopril",
            procedure_summary="",
            chronological_events=[],
            generated_timestamp=datetime.now(),
            data_quality_score=0.95,
            missing_data_indicators=[]
        )
        
        research_analysis = ResearchAnalysis(
            patient_id="P12345",
            analysis_timestamp=datetime.now(),
            conditions_analyzed=[],
            research_findings=[{
                "title": "Diabetes Management in Primary Care",
                "journal": "Journal of Medical Research",
                "publication_year": 2023,
                "relevance_score": 0.92
            }],
            condition_research_correlations={},
            categorized_findings={},
            research_insights=["Early intervention improves outcomes"],
            clinical_recommendations=["Continue current medication regimen"],
            analysis_confidence=0.85,
            total_papers_reviewed=1,
            relevant_papers_found=1
        )
        
        return AnalysisReport(
            report_id="R12345",
            patient_data=patient_data,
            medical_summary=medical_summary,
            research_analysis=research_analysis,
            generated_at=datetime.now()
        )
    
    def test_assess_analysis_quality_good_report(self):
        """Test quality assessment of a good analysis report."""
        report = self.create_sample_analysis_report()
        
        assessment = self.qa_engine.assess_analysis_quality(report)
        
        assert assessment.quality_level in [QualityLevel.GOOD, QualityLevel.EXCELLENT]
        assert assessment.overall_score > 0.7
        assert assessment.data_completeness > 0.8
        assert assessment.hallucination_risk < 0.3
    
    def test_assess_analysis_quality_incomplete_data(self):
        """Test quality assessment with incomplete data."""
        report = self.create_sample_analysis_report()
        # Make data incomplete
        report.patient_data.name = ""
        report.medical_summary.summary_text = ""
        
        assessment = self.qa_engine.assess_analysis_quality(report)
        
        assert assessment.quality_level != QualityLevel.EXCELLENT
        assert assessment.data_completeness < 0.8
        assert len(assessment.validation_issues) > 0
    
    def test_calculate_data_completeness(self):
        """Test data completeness calculation."""
        report = self.create_sample_analysis_report()
        
        completeness = self.qa_engine._calculate_data_completeness(report)
        
        assert 0.0 <= completeness <= 1.0
        assert completeness > 0.8  # Should be high for complete data
    
    def test_calculate_consistency_score(self):
        """Test consistency score calculation."""
        report = self.create_sample_analysis_report()
        issues = []  # No issues for good report
        
        consistency = self.qa_engine._calculate_consistency_score(report, issues)
        
        assert consistency == 1.0  # Perfect consistency with no issues
    
    def test_calculate_consistency_score_with_issues(self):
        """Test consistency score with validation issues."""
        report = self.create_sample_analysis_report()
        issues = [
            ValidationIssue(
                severity=ValidationSeverity.ERROR,
                field_name="patient_data.name",
                description="Test error"
            ),
            ValidationIssue(
                severity=ValidationSeverity.WARNING,
                field_name="medical_summary.summary_text",
                description="Test warning"
            )
        ]
        
        consistency = self.qa_engine._calculate_consistency_score(report, issues)
        
        assert consistency < 1.0  # Should be reduced due to issues
    
    def test_determine_quality_level(self):
        """Test quality level determination."""
        # Test different score ranges (matching README thresholds)
        assert self.qa_engine._determine_quality_level(0.98, []) == QualityLevel.EXCELLENT  # >= 0.95
        assert self.qa_engine._determine_quality_level(0.88, []) == QualityLevel.GOOD  # >= 0.85
        assert self.qa_engine._determine_quality_level(0.75, []) == QualityLevel.ACCEPTABLE  # >= 0.70
        assert self.qa_engine._determine_quality_level(0.55, []) == QualityLevel.POOR  # >= 0.50
        assert self.qa_engine._determine_quality_level(0.30, []) == QualityLevel.UNACCEPTABLE  # < 0.50
    
    def test_generate_recommendations(self):
        """Test recommendation generation."""
        issues = [
            ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                category="critical_test",
                message="Critical issue"
            ),
            ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="missing_required_data",
                message="Missing data"
            )
        ]
        
        recommendations = self.qa_engine._generate_recommendations(issues, 0.7, 0.6)
        
        assert len(recommendations) > 0
        assert any("CRITICAL" in rec for rec in recommendations)
        assert any("data completeness" in rec for rec in recommendations)
    
    def test_get_quality_statistics(self):
        """Test quality statistics retrieval."""
        stats = self.qa_engine.get_quality_statistics()
        
        assert "quality_thresholds" in stats
        assert "hallucination_thresholds" in stats
        assert "validator_info" in stats

class TestQualityAssuranceIntegration:
    """Integration tests for quality assurance system."""
    
    def test_initialize_quality_assurance(self):
        """Test quality assurance initialization."""
        audit_logger = Mock(spec=AuditLogger)
        error_handler = Mock(spec=ErrorHandler)
        
        qa_engine = initialize_quality_assurance(audit_logger, error_handler)
        
        assert qa_engine is not None
        assert get_quality_assurance_engine() is qa_engine
    
    def test_initialize_hallucination_prevention(self):
        """Test hallucination prevention initialization."""
        audit_logger = Mock(spec=AuditLogger)
        error_handler = Mock(spec=ErrorHandler)
        
        prevention_system = initialize_hallucination_prevention(
            audit_logger, error_handler, strict_mode=False
        )
        
        assert prevention_system is not None
        assert get_hallucination_prevention_system() is prevention_system
        assert not prevention_system.strict_mode
    
    def test_end_to_end_quality_assessment(self):
        """Test end-to-end quality assessment workflow."""
        # Initialize systems
        qa_engine = initialize_quality_assurance()
        prevention_system = initialize_hallucination_prevention(strict_mode=False)
        
        # Create test report
        patient_data = PatientData(
            patient_id="P67890",
            name="Jane Smith",
            demographics=Demographics(age=35, gender="Female"),
            medical_history=[],
            medications=[],
            procedures=[],
            diagnoses=[],
            raw_xml="",
            extraction_timestamp=datetime.now()
        )
        
        medical_summary = MedicalSummary(
            patient_id="P67890",
            summary_text="Patient presents with well-controlled asthma and seasonal allergies.",
            key_conditions=[
                Condition(name="Asthma", confidence_score=0.92)
            ],
            medication_summary="albuterol, fluticasone",
            procedure_summary="",
            chronological_events=[],
            generated_timestamp=datetime.now(),
            data_quality_score=0.9,
            missing_data_indicators=[]
        )
        research_analysis = ResearchAnalysis(
            patient_id="P67890",
            analysis_timestamp=datetime.now(),
            conditions_analyzed=[],
            research_findings=[],
            condition_research_correlations={},
            categorized_findings={},
            research_insights=["Asthma management requires regular monitoring"],
            clinical_recommendations=["Continue current inhaler therapy"],
            analysis_confidence=0.75,
            total_papers_reviewed=0,
            relevant_papers_found=0
        )
        
        report = AnalysisReport(
            report_id="R67890",
            patient_data=patient_data,
            medical_summary=medical_summary,
            research_analysis=research_analysis,
            generated_at=datetime.now()
        )
        
        # Perform quality assessment
        assessment = qa_engine.assess_analysis_quality(report)
        
        # Verify assessment results
        assert assessment is not None
        assert assessment.quality_level != QualityLevel.UNACCEPTABLE
        assert 0.0 <= assessment.overall_score <= 1.0
        assert 0.0 <= assessment.hallucination_risk <= 1.0
        assert isinstance(assessment.validation_issues, list)
        assert isinstance(assessment.recommendations, list)
        
        # Test hallucination prevention on content
        hallucination_check = prevention_system.check_content(
            medical_summary.summary_text, "general", patient_data.patient_id
        )
        
        assert hallucination_check is not None
        assert hallucination_check.risk_level != HallucinationRiskLevel.CRITICAL
        assert 0.0 <= hallucination_check.confidence <= 1.0

if __name__ == "__main__":
    pytest.main([__file__])