"""Unit tests for ConditionExtractor."""

import pytest
from datetime import datetime

from src.agents.condition_extractor import ConditionExtractor
from src.models import (
    PatientData, Demographics, Diagnosis, MedicalEvent, 
    Medication, Procedure
)


class TestConditionExtractor:
    """Test ConditionExtractor functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = ConditionExtractor()
    
    def test_extract_from_diagnoses(self):
        """Test extracting conditions from explicit diagnoses."""
        diagnoses = [
            Diagnosis(
                diagnosis_id="D001",
                condition="Type 2 Diabetes Mellitus",
                date_diagnosed="2023-01-15",
                icd_10_code="E11.9",
                severity="moderate",
                status="active"
            ),
            Diagnosis(
                diagnosis_id="D002",
                condition="Essential Hypertension",
                date_diagnosed="2022-06-20",
                icd_10_code="I10",
                status="active"
            )
        ]
        
        conditions = self.extractor._extract_from_diagnoses(diagnoses)
        
        assert len(conditions) == 2
        
        # Check diabetes condition
        diabetes = next(c for c in conditions if "Diabetes" in c.name)
        assert diabetes.icd_10_code == "E11.9"
        assert diabetes.severity == "moderate"
        assert diabetes.status == "active"
        assert diabetes.confidence_score == 1.0
        
        # Check hypertension condition
        hypertension = next(c for c in conditions if "Hypertension" in c.name)
        assert hypertension.icd_10_code == "I10"
        assert hypertension.status == "active"
    
    def test_extract_from_medical_history(self):
        """Test extracting conditions from medical history events."""
        medical_history = [
            MedicalEvent(
                event_id="E001",
                date="2023-10-15",
                event_type="visit",
                description="Patient presents with diabetes management and blood pressure check",
                provider="Dr. Smith"
            ),
            MedicalEvent(
                event_id="E002",
                date="2023-08-20",
                event_type="visit",
                description="Follow-up for hypertension, patient reports good control",
                provider="Dr. Jones"
            )
        ]
        
        conditions = self.extractor._extract_from_medical_history(medical_history)
        
        # Should find diabetes and hypertension mentions
        condition_names = [c.name for c in conditions]
        assert "Diabetes Mellitus" in condition_names
        assert "Hypertension" in condition_names
        
        # Check confidence scores
        for condition in conditions:
            assert condition.confidence_score == 0.7
            assert condition.status == "active"
    
    def test_infer_from_medications(self):
        """Test inferring conditions from medications."""
        medications = [
            Medication(
                medication_id="M001",
                name="Metformin",
                dosage="500mg",
                frequency="twice daily",
                indication="Type 2 Diabetes",
                status="active"
            ),
            Medication(
                medication_id="M002",
                name="Lisinopril",
                dosage="10mg",
                frequency="daily",
                status="active"
            ),
            Medication(
                medication_id="M003",
                name="Atorvastatin",
                dosage="20mg",
                frequency="daily",
                indication="High cholesterol",
                status="active"
            )
        ]
        
        conditions = self.extractor._infer_from_medications(medications)
        
        # Should find conditions from both indications and medication inference
        condition_names = [c.name for c in conditions]
        assert "Type 2 Diabetes" in condition_names
        assert "High Cholesterol" in condition_names
        assert "Diabetes Mellitus" in condition_names  # Inferred from Metformin
        assert "Hypertension" in condition_names  # Inferred from Lisinopril
        assert "Hyperlipidemia" in condition_names  # Inferred from Atorvastatin
    
    def test_merge_similar_conditions(self):
        """Test merging similar conditions."""
        from src.models import Condition
        
        conditions = [
            Condition(
                name="Diabetes Mellitus",
                severity="moderate",
                status="active",
                first_diagnosed="2023-01-15",
                confidence_score=1.0
            ),
            Condition(
                name="Diabetes",  # Similar to above
                severity="mild",
                status="active", 
                first_diagnosed="2022-12-01",
                confidence_score=0.8
            ),
            Condition(
                name="Hypertension",
                severity="moderate",
                status="active",
                first_diagnosed="2023-02-01",
                confidence_score=0.9
            )
        ]
        
        merged = self.extractor._merge_similar_conditions(conditions)
        
        assert len(merged) == 2  # Diabetes conditions should be merged
        
        # Find merged diabetes condition
        diabetes = next(c for c in merged if "diabetes" in c.name.lower())
        assert diabetes.first_diagnosed == "2022-12-01"  # Earliest date
        assert diabetes.severity == "moderate"  # Most severe
        assert diabetes.confidence_score == 0.9  # Average of 1.0 and 0.8
    
    def test_rank_conditions(self):
        """Test ranking conditions by severity and importance."""
        from src.models import Condition
        
        conditions = [
            Condition(
                name="Common Cold",
                severity="mild",
                status="active",
                confidence_score=0.8
            ),
            Condition(
                name="Diabetes Mellitus",  # Chronic condition
                severity="moderate",
                status="active",
                confidence_score=0.9
            ),
            Condition(
                name="Acute Myocardial Infarction",
                severity="high",
                status="active",
                confidence_score=1.0
            )
        ]
        
        patient_data = PatientData(
            patient_id="P001",
            name="Test Patient",
            demographics=Demographics(),
            medical_history=[],
            medications=[],
            procedures=[],
            diagnoses=[],
            raw_xml="",
            extraction_timestamp=datetime.now()
        )
        
        ranked = self.extractor._rank_conditions(conditions, patient_data)
        
        # Should be ranked: MI (high severity) > Diabetes (chronic, moderate) > Cold (mild)
        assert "Myocardial Infarction" in ranked[0].name
        assert "Diabetes" in ranked[1].name
        assert "Cold" in ranked[2].name
    
    def test_normalize_condition_name(self):
        """Test condition name normalization."""
        test_cases = [
            ("diabetes mellitus", "Diabetes Mellitus"),
            ("  hypertension  ", "Hypertension"),
            ("DM", "Diabetes Mellitus"),
            ("HTN", "Hypertension"),
            ("CAD", "Coronary Artery Disease"),
            ("COPD", "COPD")
        ]
        
        for input_name, expected in test_cases:
            result = self.extractor._normalize_condition_name(input_name)
            assert result == expected, f"Failed for input: {input_name}"
    
    def test_determine_severity(self):
        """Test severity determination logic."""
        test_cases = [
            ("Acute Myocardial Infarction", None, "high"),
            ("Severe Depression", None, "high"),
            ("Chronic Kidney Disease", None, "moderate"),
            ("Mild Hypertension", None, "mild"),
            ("Controlled Diabetes", None, "mild"),
            ("Diabetes Mellitus", "moderate", "moderate"),  # Explicit severity
            ("Unknown Condition", None, None)
        ]
        
        for condition_name, explicit_severity, expected in test_cases:
            result = self.extractor._determine_severity(condition_name, explicit_severity)
            assert result == expected, f"Failed for: {condition_name}"
    
    def test_find_condition_mentions(self):
        """Test finding condition mentions in text."""
        test_cases = [
            ("Patient has diabetes and high blood pressure", ["Diabetes Mellitus", "Hypertension"]),
            ("Follow-up for hypertension management", ["Hypertension"]),
            ("No significant medical history", []),
            ("Patient reports diabetes mellitus well controlled", ["Diabetes Mellitus"]),
            ("High cholesterol noted on labs", ["Hyperlipidemia"])
        ]
        
        for text, expected_conditions in test_cases:
            result = self.extractor._find_condition_mentions(text)
            for expected in expected_conditions:
                assert expected in result, f"Expected {expected} in {result} for text: {text}"
    
    def test_infer_conditions_from_medication(self):
        """Test inferring conditions from medication names."""
        test_cases = [
            ("Metformin", ["Diabetes Mellitus"]),
            ("Lisinopril", ["Hypertension"]),
            ("Atorvastatin", ["Hyperlipidemia"]),
            ("Albuterol", ["Asthma"]),
            ("Unknown Medication", [])
        ]
        
        for medication, expected_conditions in test_cases:
            result = self.extractor._infer_conditions_from_medication(medication)
            assert result == expected_conditions, f"Failed for medication: {medication}"
    
    def test_is_chronic_condition(self):
        """Test chronic condition identification."""
        chronic_conditions = [
            "Diabetes Mellitus",
            "Hypertension", 
            "COPD",
            "Chronic Kidney Disease"
        ]
        
        acute_conditions = [
            "Common Cold",
            "Acute Bronchitis",
            "Urinary Tract Infection"
        ]
        
        for condition in chronic_conditions:
            assert self.extractor._is_chronic_condition(condition), f"{condition} should be chronic"
        
        for condition in acute_conditions:
            assert not self.extractor._is_chronic_condition(condition), f"{condition} should not be chronic"
    
    def test_complete_extraction_workflow(self):
        """Test complete condition extraction workflow."""
        # Create comprehensive patient data
        patient_data = PatientData(
            patient_id="P001",
            name="John Doe",
            demographics=Demographics(age=65, gender="M"),
            medical_history=[
                MedicalEvent(
                    event_id="E001",
                    date="2023-10-15",
                    event_type="visit",
                    description="Annual checkup, diabetes and hypertension stable",
                    provider="Dr. Smith"
                )
            ],
            medications=[
                Medication(
                    medication_id="M001",
                    name="Metformin",
                    dosage="500mg",
                    frequency="twice daily",
                    indication="Type 2 Diabetes",
                    status="active"
                ),
                Medication(
                    medication_id="M002",
                    name="Lisinopril",
                    dosage="10mg",
                    frequency="daily",
                    status="active"
                )
            ],
            procedures=[],
            diagnoses=[
                Diagnosis(
                    diagnosis_id="D001",
                    condition="Type 2 Diabetes Mellitus",
                    date_diagnosed="2020-01-15",
                    icd_10_code="E11.9",
                    severity="moderate",
                    status="active"
                )
            ],
            raw_xml="<patient></patient>",
            extraction_timestamp=datetime.now()
        )
        
        # Extract conditions
        conditions = self.extractor.extract_conditions(patient_data)
        
        # Verify results
        assert len(conditions) > 0
        
        # Should have diabetes (from diagnosis and medication)
        diabetes_conditions = [c for c in conditions if "diabetes" in c.name.lower()]
        assert len(diabetes_conditions) >= 1
        
        # Should have hypertension (from history and medication)
        hypertension_conditions = [c for c in conditions if "hypertension" in c.name.lower()]
        assert len(hypertension_conditions) >= 1
        
        # Verify ranking (chronic conditions should be prioritized)
        chronic_conditions = [c for c in conditions if self.extractor._is_chronic_condition(c.name)]
        assert len(chronic_conditions) > 0
        
        # Verify confidence scores are reasonable
        for condition in conditions:
            assert 0.0 <= condition.confidence_score <= 1.0
    
    def test_edge_cases(self):
        """Test edge cases and error handling."""
        # Empty patient data
        empty_patient = PatientData(
            patient_id="P000",
            name="Empty Patient",
            demographics=Demographics(),
            medical_history=[],
            medications=[],
            procedures=[],
            diagnoses=[],
            raw_xml="",
            extraction_timestamp=datetime.now()
        )
        
        conditions = self.extractor.extract_conditions(empty_patient)
        assert conditions == []
        
        # Patient with only unknown/generic conditions
        generic_patient = PatientData(
            patient_id="P002",
            name="Generic Patient",
            demographics=Demographics(),
            medical_history=[
                MedicalEvent(
                    event_id="E001",
                    date="2023-01-01",
                    event_type="visit",
                    description="Routine checkup, no issues",
                    provider="Dr. Test"
                )
            ],
            medications=[],
            procedures=[],
            diagnoses=[],
            raw_xml="",
            extraction_timestamp=datetime.now()
        )
        
        conditions = self.extractor.extract_conditions(generic_patient)
        # Should handle gracefully, may return empty list or very low confidence conditions
        for condition in conditions:
            assert condition.confidence_score >= 0.0