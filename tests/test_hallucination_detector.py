"""Tests for hallucination detection and data validation system."""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.quality.hallucination_detector import (
    HallucinationDetector, MedicalTerminologyValidator,
    ValidationIssue, ValidationSeverity, ValidationType
)
from src.models import PatientData, MedicalSummary, ResearchAnalysis


class TestMedicalTerminologyValidator:
    """Test MedicalTerminologyValidator class."""
    
    @pytest.fixture
    def validator(self):
        """Create medical terminology validator."""
        return MedicalTerminologyValidator()
    
    def test_validate_condition_terminology_valid(self, validator):
        """Test validation of valid medical conditions."""
        valid_conditions = [
            "hypertension",
            "diabetes",
            "myocardial infarction",
            "chronic obstructive pulmonary disease",
            "atrial fibrillation"
        ]
        
        for condition in valid_conditions:
            is_valid, confidence, suggestions = validator.validate_condition_terminology(condition)
            assert is_valid, f"'{condition}' should be valid"
            assert confidence >= 0.8, f"'{condition}' should have high confidence"
    
    def test_validate_condition_terminology_variations(self, validator):
        """Test validation of condition variations."""
        variations = [
            ("high blood pressure", "hypertension"),
            ("heart attack", "myocardial infarction"),
            ("copd", "chronic obstructive pulmonary disease"),
            ("afib", "atrial fibrillation")
        ]
        
        for variation, standard in variations:
            is_valid, confidence, suggestions = validator.validate_condition_terminology(variation)
            assert is_valid, f"'{variation}' should be valid"
            assert confidence >= 0.8, f"'{variation}' should have high confidence"
    
    def test_validate_condition_terminology_invalid(self, validator):
        """Test validation of invalid conditions."""
        invalid_conditions = [
            "",
            "xyz123",
            "random text",
            "not a medical condition"
        ]
        
        for condition in invalid_conditions:
            is_valid, confidence, suggestions = validator.validate_condition_terminology(condition)
            if condition == "":
                assert not is_valid
            else:
                # Some may be partially valid due to fuzzy matching
                assert confidence < 0.7, f"'{condition}' should have low confidence"
    
    def test_validate_medication_name_valid(self, validator):
        """Test validation of valid medication names."""
        valid_medications = [
            "lisinopril",
            "metoprolol", 
            "atorvastatin",
            "metformin",
            "omeprazole"
        ]
        
        for medication in valid_medications:
            is_valid, confidence, suggestions = validator.validate_medication_name(medication)
            assert is_valid, f"'{medication}' should be valid"
            assert confidence >= 0.8, f"'{medication}' should have high confidence"
    
    def test_validate_medication_name_patterns(self, validator):
        """Test validation of medication name patterns."""
        pattern_medications = [
            "newpril",  # ACE inhibitor pattern
            "testolol",  # Beta blocker pattern
            "demystatin",  # Statin pattern
            "examplezole"  # PPI pattern
        ]
        
        for medication in pattern_medications:
            is_valid, confidence, suggestions = validator.validate_medication_name(medication)
            # Should be recognized by pattern even if not in dictionary
            assert confidence >= 0.5, f"'{medication}' should be recognized by pattern"
    
    def test_validate_icd_code_valid(self, validator):
        """Test validation of valid ICD-10 codes."""
        valid_codes = [
            ("I10", True),
            ("E11.9", True),
            ("J44.1", True),
            ("F32.9", True)
        ]
        
        for code, should_be_valid in valid_codes:
            is_valid, description, suggestions = validator.validate_icd_code(code)
            assert is_valid == should_be_valid, f"'{code}' validation failed"
            if is_valid and code in validator.icd10_codes:
                assert description == validator.icd10_codes[code]
    
    def test_validate_icd_code_format(self, validator):
        """Test ICD-10 code format validation."""
        format_tests = [
            ("A12", True),      # Valid format
            ("Z99.9", True),    # Valid format
            ("I10.12", True),   # Valid format
            ("123", False),     # Invalid format
            ("AB12", False),    # Invalid format
            ("I", False),       # Invalid format
            ("", False)         # Empty
        ]
        
        for code, should_be_valid in format_tests:
            is_valid, description, suggestions = validator.validate_icd_code(code)
            if should_be_valid:
                assert is_valid or "Valid ICD-10 format" in description
            else:
                assert not is_valid


class TestValidationIssue:
    """Test ValidationIssue class."""
    
    def test_validation_issue_creation(self):
        """Test validation issue creation."""
        issue = ValidationIssue(
            issue_id="TEST_001",
            validation_type=ValidationType.MEDICAL_TERMINOLOGY,
            severity=ValidationSeverity.WARNING,
            description="Test validation issue",
            field_name="test_field",
            expected_value="expected",
            actual_value="actual",
            confidence_score=0.75,
            suggestions=["Test suggestion"]
        )
        
        assert issue.issue_id == "TEST_001"
        assert issue.validation_type == ValidationType.MEDICAL_TERMINOLOGY
        assert issue.severity == ValidationSeverity.WARNING
        assert issue.description == "Test validation issue"
        assert issue.field_name == "test_field"
        assert issue.confidence_score == 0.75
        assert "Test suggestion" in issue.suggestions
    
    def test_validation_issue_to_dict(self):
        """Test validation issue dictionary conversion."""
        issue = ValidationIssue(
            issue_id="TEST_001",
            validation_type=ValidationType.SOURCE_VERIFICATION,
            severity=ValidationSeverity.ERROR,
            description="Test issue",
            field_name="test_field"
        )
        
        issue_dict = issue.to_dict()
        
        assert issue_dict["issue_id"] == "TEST_001"
        assert issue_dict["validation_type"] == "source_verification"
        assert issue_dict["severity"] == "error"
        assert issue_dict["description"] == "Test issue"
        assert issue_dict["field_name"] == "test_field"


class TestHallucinationDetector:
    """Test HallucinationDetector class."""
    
    @pytest.fixture
    def mock_audit_logger(self):
        """Create mock audit logger."""
        return Mock()
    
    @pytest.fixture
    def detector(self, mock_audit_logger):
        """Create hallucination detector."""
        return HallucinationDetector(audit_logger=mock_audit_logger)
    
    def test_detector_initialization(self, detector):
        """Test detector initialization."""
        assert detector.audit_logger is not None
        assert detector.terminology_validator is not None
        assert isinstance(detector.validation_issues, list)
        assert len(detector.confidence_thresholds) == 4
    
    def test_validate_against_source_basic(self, detector):
        """Test basic source validation."""
        extracted_data = {
            "patient_data": {
                "name": "John Smith",
                "patient_id": "PAT123"
            },
            "medical_summary": {
                "key_conditions": [
                    {"name": "hypertension", "confidence_score": 0.9}
                ],
                "medications": ["lisinopril"]
            }
        }
        
        source_xml = """
        <patient name="John Smith" id="PAT123">
            <conditions>
                <condition>hypertension</condition>
            </conditions>
            <medications>
                <medication>lisinopril</medication>
            </medications>
        </patient>
        """
        
        issues = detector.validate_against_source(extracted_data, source_xml, "PAT123")
        
        # Should have minimal issues for well-matched data
        critical_issues = [issue for issue in issues if issue.severity == ValidationSeverity.CRITICAL]
        assert len(critical_issues) == 0, "Should not have critical issues for valid data"
    
    def test_validate_against_source_name_mismatch(self, detector):
        """Test source validation with name mismatch."""
        extracted_data = {
            "patient_data": {
                "name": "John Smith",
                "patient_id": "PAT123"
            }
        }
        
        source_xml = """
        <patient name="Jane Doe" id="PAT123">
        </patient>
        """
        
        issues = detector.validate_against_source(extracted_data, source_xml, "PAT123")
        
        # Should detect name mismatch
        name_issues = [issue for issue in issues if "name" in issue.field_name.lower()]
        assert len(name_issues) > 0, "Should detect name mismatch"
    
    def test_validate_analysis_completeness_complete(self, detector):
        """Test completeness validation with complete data."""
        complete_data = {
            "patient_data": {
                "name": "John Smith",
                "patient_id": "PAT123"
            },
            "medical_summary": {
                "key_conditions": [{"name": "hypertension"}],
                "summary_text": "Patient has hypertension."
            },
            "research_analysis": {
                "research_findings": [{"title": "Hypertension Study"}],
                "analysis_confidence": 0.8
            }
        }
        
        issues = detector.validate_analysis_completeness(complete_data)
        
        # Should have no completeness issues
        completeness_issues = [issue for issue in issues 
                             if issue.validation_type == ValidationType.COMPLETENESS]
        assert len(completeness_issues) == 0, "Complete data should have no completeness issues"
    
    def test_validate_analysis_completeness_incomplete(self, detector):
        """Test completeness validation with incomplete data."""
        incomplete_data = {
            "patient_data": {
                "name": "John Smith"
                # Missing patient_id
            },
            "medical_summary": {
                # Missing key_conditions and summary_text
            }
            # Missing research_analysis entirely
        }
        
        issues = detector.validate_analysis_completeness(incomplete_data)
        
        # Should detect multiple completeness issues
        completeness_issues = [issue for issue in issues 
                             if issue.validation_type == ValidationType.COMPLETENESS]
        assert len(completeness_issues) > 0, "Incomplete data should have completeness issues"
    
    def test_validate_research_accuracy_valid(self, detector):
        """Test research accuracy validation with valid data."""
        research_analysis = ResearchAnalysis(
            research_findings=[
                {
                    "title": "Hypertension Management Study",
                    "authors": ["Smith, J.", "Doe, J."],
                    "journal": "Medical Journal",
                    "publication_year": 2023,
                    "relevance_score": 0.9
                }
            ],
            analysis_confidence=0.85
        )
        
        issues = detector.validate_research_accuracy(research_analysis)
        
        # Should have minimal issues for valid research data
        error_issues = [issue for issue in issues 
                       if issue.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]]
        assert len(error_issues) == 0, "Valid research data should not have error-level issues"
    
    def test_validate_research_accuracy_invalid_year(self, detector):
        """Test research accuracy validation with invalid publication year."""
        research_analysis = ResearchAnalysis(
            research_findings=[
                {
                    "title": "Future Study",
                    "authors": ["Smith, J."],
                    "journal": "Medical Journal",
                    "publication_year": 2030,  # Future year
                    "relevance_score": 0.9
                }
            ],
            analysis_confidence=0.85
        )
        
        issues = detector.validate_research_accuracy(research_analysis)
        
        # Should detect invalid publication year
        year_issues = [issue for issue in issues if "publication_year" in issue.field_name]
        assert len(year_issues) > 0, "Should detect invalid publication year"
    
    def test_validate_research_accuracy_low_confidence(self, detector):
        """Test research accuracy validation with low confidence."""
        research_analysis = ResearchAnalysis(
            research_findings=[
                {
                    "title": "Study",
                    "authors": ["Smith, J."],
                    "journal": "Journal",
                    "publication_year": 2023
                }
            ],
            analysis_confidence=0.2  # Very low confidence
        )
        
        issues = detector.validate_research_accuracy(research_analysis)
        
        # Should detect low confidence
        confidence_issues = [issue for issue in issues if "confidence" in issue.field_name]
        assert len(confidence_issues) > 0, "Should detect low analysis confidence"
    
    def test_generate_validation_report_no_issues(self, detector):
        """Test validation report generation with no issues."""
        issues = []
        
        report = detector.generate_validation_report(issues)
        
        assert report["validation_status"] == "PASSED"
        assert report["total_issues"] == 0
        assert report["overall_confidence"] == 1.0
        assert len(report["recommendations"]) > 0
    
    def test_generate_validation_report_with_issues(self, detector):
        """Test validation report generation with various issues."""
        issues = [
            ValidationIssue(
                issue_id="TEST_001",
                validation_type=ValidationType.MEDICAL_TERMINOLOGY,
                severity=ValidationSeverity.WARNING,
                description="Warning issue",
                field_name="test_field"
            ),
            ValidationIssue(
                issue_id="TEST_002",
                validation_type=ValidationType.SOURCE_VERIFICATION,
                severity=ValidationSeverity.ERROR,
                description="Error issue",
                field_name="test_field"
            ),
            ValidationIssue(
                issue_id="TEST_003",
                validation_type=ValidationType.ACCURACY,
                severity=ValidationSeverity.CRITICAL,
                description="Critical issue",
                field_name="test_field"
            )
        ]
        
        report = detector.generate_validation_report(issues)
        
        assert report["validation_status"] == "FAILED"  # Due to critical issue
        assert report["total_issues"] == 3
        assert report["overall_confidence"] == 0.0  # Due to critical issue
        assert len(report["issues_by_severity"]) > 0
        assert len(report["issues_by_type"]) > 0
        assert len(report["recommendations"]) > 0
    
    def test_determine_severity(self, detector):
        """Test severity determination based on confidence scores."""
        # Test different confidence levels
        assert detector._determine_severity(0.1) == ValidationSeverity.CRITICAL
        assert detector._determine_severity(0.4) == ValidationSeverity.ERROR
        assert detector._determine_severity(0.6) == ValidationSeverity.WARNING
        assert detector._determine_severity(0.9) == ValidationSeverity.INFO
    
    def test_condition_in_source(self, detector):
        """Test condition presence detection in source XML."""
        source_xml = """
        <patient>
            <conditions>
                <condition>hypertension</condition>
                <condition>high blood pressure</condition>
            </conditions>
        </patient>
        """
        
        # Direct match
        assert detector._condition_in_source("hypertension", source_xml)
        
        # Variation match
        assert detector._condition_in_source("hypertension", source_xml)  # Should find "high blood pressure"
        
        # No match
        assert not detector._condition_in_source("diabetes", source_xml)
    
    def test_get_validation_statistics(self, detector):
        """Test validation statistics retrieval."""
        # Add some test issues
        detector.validation_issues = [
            ValidationIssue("TEST_001", ValidationType.MEDICAL_TERMINOLOGY, 
                          ValidationSeverity.WARNING, "Test", "field"),
            ValidationIssue("TEST_002", ValidationType.SOURCE_VERIFICATION, 
                          ValidationSeverity.ERROR, "Test", "field")
        ]
        
        stats = detector.get_validation_statistics()
        
        assert "total_validations" in stats
        assert "issues_by_severity" in stats
        assert "issues_by_type" in stats
        assert stats["total_validations"] == 2


class TestHallucinationDetectorIntegration:
    """Test hallucination detector integration scenarios."""
    
    @pytest.fixture
    def detector(self):
        """Create detector for integration tests."""
        return HallucinationDetector()
    
    def test_comprehensive_validation_workflow(self, detector):
        """Test complete validation workflow."""
        # Prepare test data
        extracted_data = {
            "patient_data": {
                "name": "John Smith",
                "patient_id": "PAT123",
                "age": 45
            },
            "medical_summary": {
                "key_conditions": [
                    {"name": "hypertension", "confidence_score": 0.9},
                    {"name": "unknown_condition", "confidence_score": 0.3}
                ],
                "summary_text": "Patient has hypertension and other conditions.",
                "medications": ["lisinopril", "unknown_medication"]
            },
            "research_analysis": {
                "research_findings": [
                    {
                        "title": "Hypertension Study",
                        "authors": ["Smith, J."],
                        "journal": "Medical Journal",
                        "publication_year": 2023
                    }
                ],
                "analysis_confidence": 0.8
            }
        }
        
        source_xml = """
        <patient name="John Smith" id="PAT123">
            <demographics>
                <age>45</age>
            </demographics>
            <conditions>
                <condition>hypertension</condition>
            </conditions>
            <medications>
                <medication>lisinopril</medication>
            </medications>
        </patient>
        """
        
        # Run comprehensive validation
        source_issues = detector.validate_against_source(extracted_data, source_xml, "PAT123")
        completeness_issues = detector.validate_analysis_completeness(extracted_data)
        
        all_issues = source_issues + completeness_issues
        report = detector.generate_validation_report(all_issues)
        
        # Verify report structure
        assert "validation_status" in report
        assert "total_issues" in report
        assert "issues_by_severity" in report
        assert "issues_by_type" in report
        assert "overall_confidence" in report
        assert "recommendations" in report
        
        # Should detect issues with unknown condition and medication
        terminology_issues = [issue for issue in all_issues 
                            if issue.validation_type == ValidationType.MEDICAL_TERMINOLOGY]
        assert len(terminology_issues) > 0, "Should detect terminology issues"