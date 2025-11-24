"""Tests for hallucination prevention system."""
import pytest
from unittest.mock import Mock, patch

from src.utils.hallucination_prevention import (
    HallucinationPreventionSystem, MedicalKnowledgeValidator,
    HallucinationRiskLevel, HallucinationCheck,
    initialize_hallucination_prevention, get_hallucination_prevention_system
)
from src.models.exceptions import HallucinationDetectedError
from src.utils.audit_logger import AuditLogger
from src.utils.error_handler import ErrorHandler

class TestMedicalKnowledgeValidator:
    """Test cases for MedicalKnowledgeValidator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = MedicalKnowledgeValidator()
    
    def test_load_medical_terms(self):
        """Test loading of medical terms."""
        terms = self.validator._load_medical_terms()
        
        assert isinstance(terms, set)
        assert len(terms) > 0
        assert 'hypertension' in terms
        assert 'diabetes' in terms
        assert 'cardiology' in terms
    
    def test_load_drug_names(self):
        """Test loading of drug names."""
        drugs = self.validator._load_drug_names()
        
        assert isinstance(drugs, set)
        assert len(drugs) > 0
        assert 'aspirin' in drugs
        assert 'metformin' in drugs
        assert 'lisinopril' in drugs
    
    def test_validate_clean_medical_content(self):
        """Test validation of clean medical content."""
        content = "Patient diagnosed with hypertension and prescribed lisinopril 10mg daily."
        
        result = self.validator.validate_medical_content(content, "general")
        
        assert result.risk_level == HallucinationRiskLevel.MINIMAL
        assert result.confidence > 0.8
        assert len(result.detected_patterns) == 0
        assert not result.requires_human_review
    
    def test_validate_suspicious_content(self):
        """Test validation of content with suspicious patterns."""
        content = "Patient has fictional disease from Star Wars universe with magical healing."
        
        result = self.validator.validate_medical_content(content, "general")
        
        assert result.risk_level != HallucinationRiskLevel.MINIMAL
        assert result.confidence < 0.8
        assert len(result.detected_patterns) > 0
        assert any("Suspicious pattern" in pattern for pattern in result.detected_patterns)
    
    def test_validate_medication_known_drugs(self):
        """Test validation of content with known medications."""
        content = "Patient prescribed aspirin 81mg daily and metformin 500mg twice daily."
        
        result = self.validator.validate_medical_content(content, "medication")
        
        assert result.risk_level in [HallucinationRiskLevel.MINIMAL, HallucinationRiskLevel.LOW]
        assert result.confidence > 0.7
    
    def test_validate_medication_unknown_drugs(self):
        """Test validation of content with unknown medications."""
        content = "Patient prescribed fictionaldrugxyz 100mg and imaginarymedicine 50mg daily."
        
        result = self.validator.validate_medical_content(content, "medication")
        
        assert result.risk_level != HallucinationRiskLevel.MINIMAL
        assert any("Unknown medications" in pattern for pattern in result.detected_patterns)
        assert len(result.suggested_corrections) > 0
    
    def test_validate_medication_high_dosage(self):
        """Test validation of medications with unusually high dosages."""
        content = "Patient prescribed aspirin 15000mg daily."  # Extremely high dose
        
        result = self.validator.validate_medical_content(content, "medication")
        
        assert result.risk_level != HallucinationRiskLevel.MINIMAL
        assert any("high dosage" in pattern.lower() for pattern in result.detected_patterns)
    
    def test_validate_condition_known_conditions(self):
        """Test validation of content with known medical conditions."""
        content = "Patient has type 2 diabetes mellitus and essential hypertension."
        
        result = self.validator.validate_medical_content(content, "condition")
        
        assert result.risk_level == HallucinationRiskLevel.MINIMAL
        assert result.confidence > 0.8
    
    def test_validate_condition_no_recognized_conditions(self):
        """Test validation of condition content with no recognized conditions."""
        content = "Patient has some unknown mysterious ailment that affects their wellbeing."
        
        result = self.validator.validate_medical_content(content, "condition")
        
        assert result.risk_level != HallucinationRiskLevel.MINIMAL
        assert any("No recognized medical conditions" in pattern for pattern in result.detected_patterns)
    
    def test_validate_condition_contradictory(self):
        """Test validation of contradictory condition statements."""
        content = "Patient is completely asymptomatic but has severe chronic symptoms."
        
        result = self.validator.validate_medical_content(content, "condition")
        
        assert result.risk_level != HallucinationRiskLevel.MINIMAL
        assert any("Contradiction detected" in pattern for pattern in result.detected_patterns)
    
    def test_validate_procedure_known_procedures(self):
        """Test validation of content with known procedures."""
        content = "Patient underwent coronary angioplasty and echocardiogram."
        
        result = self.validator.validate_medical_content(content, "procedure")
        
        assert result.risk_level == HallucinationRiskLevel.MINIMAL
        assert result.confidence > 0.7
    
    def test_validate_procedure_impossible_combinations(self):
        """Test validation of impossible procedure combinations."""
        content = "Patient had outpatient major surgery with minimally invasive open surgery."
        
        result = self.validator.validate_medical_content(content, "procedure")
        
        assert result.risk_level != HallucinationRiskLevel.MINIMAL
        assert any("Impossible combination" in pattern for pattern in result.detected_patterns)
    
    def test_validate_general_low_medical_density(self):
        """Test validation of general content with low medical term density."""
        content = "The patient went to the store and bought some things for their house and family."
        
        result = self.validator.validate_medical_content(content, "general")
        
        assert result.risk_level != HallucinationRiskLevel.MINIMAL
        assert any("Low medical terminology density" in pattern for pattern in result.detected_patterns)
    
    def test_validate_medical_codes_valid_icd(self):
        """Test validation of valid ICD codes."""
        content = "Patient diagnosed with E11.9 (Type 2 diabetes without complications)."
        
        result = self.validator.validate_medical_content(content, "general")
        
        # Should not flag valid ICD codes
        code_issues = [p for p in result.detected_patterns if "Invalid ICD code" in p]
        assert len(code_issues) == 0
    
    def test_validate_medical_codes_invalid_icd(self):
        """Test validation of invalid ICD codes."""
        content = "Patient diagnosed with XYZ123 (invalid code format)."
        
        result = self.validator.validate_medical_content(content, "general")
        
        assert any("Invalid ICD code format" in pattern for pattern in result.detected_patterns)
    
    def test_validate_logical_consistency_temporal(self):
        """Test validation of temporal logical consistency."""
        content = "Patient had pediatric condition but is also geriatric patient."
        
        result = self.validator.validate_medical_content(content, "general")
        
        assert result.risk_level != HallucinationRiskLevel.MINIMAL
        assert any("Temporal inconsistency" in pattern for pattern in result.detected_patterns)
    
    def test_validate_empty_content(self):
        """Test validation of empty content."""
        content = ""
        
        result = self.validator.validate_medical_content(content, "general")
        
        assert result.risk_level == HallucinationRiskLevel.MINIMAL
        assert result.confidence == 1.0
        assert len(result.detected_patterns) == 0

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
    
    def test_initialization(self):
        """Test system initialization."""
        assert self.system.audit_logger is self.audit_logger
        assert self.system.error_handler is self.error_handler
        assert self.system.strict_mode is True
        assert self.system.medical_validator is not None
        assert self.system.prevention_stats["total_checks"] == 0
    
    def test_check_content_safe(self):
        """Test checking safe medical content."""
        content = "Patient has well-controlled diabetes and hypertension."
        
        result = self.system.check_content(content, "general", "P12345")
        
        assert result.risk_level == HallucinationRiskLevel.MINIMAL
        assert not result.requires_human_review
        assert self.system.prevention_stats["total_checks"] == 1
        assert self.system.prevention_stats["by_risk_level"]["minimal"] == 1
    
    def test_check_content_medium_risk(self):
        """Test checking medium-risk content."""
        content = "Patient has some unknown condition with placeholder symptoms."
        
        result = self.system.check_content(content, "general", "P12345")
        
        assert result.risk_level in [HallucinationRiskLevel.LOW, HallucinationRiskLevel.MEDIUM]
        assert len(result.detected_patterns) > 0
        assert self.system.prevention_stats["total_checks"] == 1
    
    def test_check_content_high_risk_strict_mode(self):
        """Test checking high-risk content in strict mode."""
        content = "Patient has fictional magical disease from Harry Potter with supernatural healing powers."
        
        # Should not raise exception for HIGH risk, only CRITICAL
        result = self.system.check_content(content, "general", "P12345")
        
        assert result.risk_level in [HallucinationRiskLevel.HIGH, HallucinationRiskLevel.MEDIUM]
        assert result.requires_human_review or result.risk_level == HallucinationRiskLevel.MEDIUM
        
        # Should log the detection
        if result.risk_level == HallucinationRiskLevel.HIGH:
            assert self.audit_logger.log_system_event.called
    
    def test_check_content_critical_risk_strict_mode(self):
        """Test checking critical-risk content in strict mode."""
        # Create content that will definitely trigger critical risk
        content = ("Patient has fictional imaginary made-up disease from Star Wars "
                  "with magical supernatural healing powers and invented symptoms "
                  "treated with placeholder dummy medications.")
        
        with pytest.raises(HallucinationDetectedError) as exc_info:
            self.system.check_content(content, "general", "P12345")
        
        assert "Critical hallucination risk detected" in str(exc_info.value)
        assert self.system.prevention_stats["high_risk_blocked"] == 1
        assert self.audit_logger.log_system_event.called
    
    def test_check_content_non_strict_mode(self):
        """Test checking critical content in non-strict mode."""
        system = HallucinationPreventionSystem(strict_mode=False)
        content = ("Patient has fictional imaginary disease from Star Wars "
                  "with magical supernatural healing powers.")
        
        # Should not raise exception in non-strict mode
        result = system.check_content(content, "general", "P12345")
        
        assert result.risk_level in [HallucinationRiskLevel.HIGH, HallucinationRiskLevel.CRITICAL]
        assert len(result.detected_patterns) > 0
    
    def test_check_content_with_patient_context(self):
        """Test checking content with patient context."""
        content = "Patient diagnosed with hypertension."
        patient_id = "P12345"
        
        result = self.system.check_content(content, "condition", patient_id, "diagnosis_validation")
        
        assert result.risk_level == HallucinationRiskLevel.MINIMAL
        # Verify the operation was logged with correct context
        # (This would be verified through the log_operation context manager)
    
    def test_prevention_statistics_tracking(self):
        """Test prevention statistics tracking."""
        # Check various types of content
        self.system.check_content("Normal medical content", "general")
        self.system.check_content("Patient has some unknown symptoms", "general")
        
        try:
            self.system.check_content("Fictional magical disease", "general")
        except HallucinationDetectedError:
            pass  # Expected in strict mode
        
        stats = self.system.get_prevention_statistics()
        
        assert stats["total_checks"] >= 2
        assert "hallucination_rate" in stats
        assert "human_review_rate" in stats
        assert "block_rate" in stats
        assert "by_risk_level" in stats
        
        # Verify rate calculations
        if stats["total_checks"] > 0:
            assert 0.0 <= stats["hallucination_rate"] <= 1.0
            assert 0.0 <= stats["human_review_rate"] <= 1.0
            assert 0.0 <= stats["block_rate"] <= 1.0
    
    def test_prevention_statistics_empty(self):
        """Test prevention statistics when no checks performed."""
        stats = self.system.get_prevention_statistics()
        
        assert stats["total_checks"] == 0
        assert stats["hallucination_rate"] == 0.0
        assert stats["human_review_rate"] == 0.0
        assert stats["block_rate"] == 0.0
    
    def test_error_handling_integration(self):
        """Test integration with error handler."""
        content = ("Patient has fictional imaginary made-up disease from Star Wars "
                  "with magical supernatural healing powers.")
        
        with pytest.raises(HallucinationDetectedError):
            self.system.check_content(content, "general", "P12345")
        
        # Verify error handler was called
        assert self.error_handler.handle_error.called
        
        # Verify error context
        call_args = self.error_handler.handle_error.call_args
        error, context = call_args[0]
        
        assert isinstance(error, HallucinationDetectedError)
        assert context.operation == "content_validation"
        assert context.component == "hallucination_prevention"
        assert context.patient_id == "P12345"

class TestHallucinationPreventionIntegration:
    """Integration tests for hallucination prevention system."""
    
    def test_initialize_hallucination_prevention(self):
        """Test hallucination prevention system initialization."""
        audit_logger = Mock(spec=AuditLogger)
        error_handler = Mock(spec=ErrorHandler)
        
        system = initialize_hallucination_prevention(
            audit_logger=audit_logger,
            error_handler=error_handler,
            strict_mode=False
        )
        
        assert system is not None
        assert system.audit_logger is audit_logger
        assert system.error_handler is error_handler
        assert not system.strict_mode
        assert get_hallucination_prevention_system() is system
    
    def test_initialize_with_defaults(self):
        """Test initialization with default parameters."""
        system = initialize_hallucination_prevention()
        
        assert system is not None
        assert system.audit_logger is None
        assert system.error_handler is None
        assert system.strict_mode is True
    
    def test_multiple_content_types(self):
        """Test checking multiple content types."""
        system = initialize_hallucination_prevention(strict_mode=False)
        
        test_contents = {
            "medication": "Patient prescribed aspirin 81mg and metformin 500mg daily.",
            "condition": "Patient diagnosed with type 2 diabetes and hypertension.",
            "procedure": "Patient underwent echocardiogram and stress test.",
            "general": "Patient has well-controlled chronic conditions."
        }
        
        results = {}
        for content_type, content in test_contents.items():
            results[content_type] = system.check_content(content, content_type, "P12345")
        
        # All should be low risk for valid medical content
        for content_type, result in results.items():
            assert result.risk_level in [HallucinationRiskLevel.MINIMAL, HallucinationRiskLevel.LOW]
            assert result.confidence > 0.6
    
    def test_progressive_risk_detection(self):
        """Test progressive risk detection with increasingly suspicious content."""
        system = initialize_hallucination_prevention(strict_mode=False)
        
        test_cases = [
            ("Clean medical content", "Patient has diabetes and hypertension."),
            ("Slightly suspicious", "Patient has some unknown condition."),
            ("More suspicious", "Patient has placeholder symptoms and test medications."),
            ("Very suspicious", "Patient has fictional disease from movies."),
            ("Extremely suspicious", "Patient has magical supernatural healing powers from fantasy.")
        ]
        
        previous_risk = HallucinationRiskLevel.MINIMAL
        
        for description, content in test_cases:
            result = system.check_content(content, "general", "P12345")
            
            # Risk should generally increase (though not strictly monotonic due to different patterns)
            assert result.risk_level is not None
            
            # Very suspicious content should definitely be high risk
            if "magical supernatural" in content:
                assert result.risk_level in [HallucinationRiskLevel.HIGH, HallucinationRiskLevel.CRITICAL]
    
    def test_content_type_specific_validation(self):
        """Test that content type affects validation appropriately."""
        system = initialize_hallucination_prevention(strict_mode=False)
        
        # Same suspicious content, different types
        content = "Patient has unknown fictionalname condition."
        
        general_result = system.check_content(content, "general", "P12345")
        condition_result = system.check_content(content, "condition", "P12345")
        medication_result = system.check_content(content, "medication", "P12345")
        
        # Condition-specific validation might be more strict about unknown conditions
        # Medication-specific validation might flag unknown drug names differently
        assert all(r.risk_level != HallucinationRiskLevel.MINIMAL 
                  for r in [general_result, condition_result, medication_result])
    
    def test_statistics_aggregation(self):
        """Test statistics aggregation across multiple checks."""
        system = initialize_hallucination_prevention(strict_mode=False)
        
        # Perform various checks
        test_contents = [
            "Normal medical content",
            "Patient has unknown symptoms",
            "Patient prescribed fictional medication",
            "Patient has magical healing powers"
        ]
        
        for content in test_contents:
            try:
                system.check_content(content, "general", "P12345")
            except HallucinationDetectedError:
                pass  # Some might be blocked in strict mode
        
        stats = system.get_prevention_statistics()
        
        assert stats["total_checks"] == len(test_contents)
        assert sum(stats["by_risk_level"].values()) == stats["total_checks"]
        
        # Verify statistics consistency
        if stats["total_checks"] > 0:
            calculated_rate = stats["hallucinations_detected"] / stats["total_checks"]
            assert abs(stats["hallucination_rate"] - calculated_rate) < 0.001

if __name__ == "__main__":
    pytest.main([__file__])