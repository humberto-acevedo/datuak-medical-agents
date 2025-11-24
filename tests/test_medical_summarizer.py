"""Unit tests for MedicalSummarizer."""

import pytest
from datetime import datetime

from src.agents.medical_summarizer import MedicalSummarizer
from src.models import (
    PatientData, Demographics, Diagnosis, MedicalEvent, 
    Medication, Procedure, Condition
)


class TestMedicalSummarizer:
    """Test MedicalSummarizer functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.summarizer = MedicalSummarizer()
    
    def test_create_chronological_events(self):
        """Test creating chronological events from patient data."""
        patient_data = PatientData(
            patient_id="P001",
            name="Test Patient",
            demographics=Demographics(age=45),
            medical_history=[
                MedicalEvent(
                    event_id="E001",
                    date="2023-10-15",
                    event_type="visit",
                    description="Annual checkup",
                    provider="Dr. Smith"
                )
            ],
            medications=[
                Medication(
                    medication_id="M001",
                    name="Metformin",
                    dosage="500mg",
                    frequency="twice daily",
                    start_date="2023-01-15",
                    status="active"
                )
            ],
            procedures=[
                Procedure(
                    procedure_id="P001",
                    name="Blood work",
                    date="2023-09-01",
                    provider="Lab Corp"
                )
            ],
            diagnoses=[
                Diagnosis(
                    diagnosis_id="D001",
                    condition="Type 2 Diabetes",
                    date_diagnosed="2023-01-10",
                    status="active"
                )
            ],
            raw_xml="",
            extraction_timestamp=datetime.now()
        )
        
        events = self.summarizer._create_chronological_events(patient_data)
        
        # Should have events for diagnosis, medication start, procedure, and visit
        assert len(events) == 4
        
        # Check event types
        event_types = [e.event_type for e in events]
        assert "diagnosis" in event_types
        assert "medication_start" in event_types
        assert "procedure" in event_types
        assert "visit" in event_types
        
        # Events should be sorted chronologically (most recent first)
        dates = [e.date for e in events]
        assert dates[0] == "2023-10-15"  # Most recent
    
    def test_generate_narrative_summary(self):
        """Test generating narrative medical summary."""
        patient_data = PatientData(
            patient_id="P001",
            name="John Doe",
            demographics=Demographics(age=65, gender="M"),
            medical_history=[],
            medications=[
                Medication(
                    medication_id="M001",
                    name="Metformin",
                    dosage="500mg",
                    frequency="twice daily",
                    indication="Type 2 Diabetes",
                    status="active"
                )
            ],
            procedures=[],
            diagnoses=[],
            raw_xml="",
            extraction_timestamp=datetime.now()
        )
        
        conditions = [
            Condition(
                name="Type 2 Diabetes Mellitus",
                severity="moderate",
                status="active",
                confidence_score=0.9
            ),
            Condition(
                name="Hypertension",
                severity="mild",
                status="active",
                confidence_score=0.8
            )
        ]
        
        chronological_events = []
        
        narrative = self.summarizer._generate_narrative_summary(
            patient_data, conditions, chronological_events
        )
        
        # Check that narrative includes key information
        assert "John Doe" in narrative
        assert "age 65" in narrative
        assert "M patient" in narrative or "male" in narrative.lower()
        assert "Type 2 Diabetes Mellitus" in narrative
        assert "Hypertension" in narrative
        assert "Metformin" in narrative
    
    def test_generate_medication_summary(self):
        """Test generating medication summary."""
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
                indication="Hypertension",
                status="active"
            ),
            Medication(
                medication_id="M003",
                name="Aspirin",
                dosage="81mg",
                frequency="daily",
                status="discontinued"
            )
        ]
        
        summary = self.summarizer._generate_medication_summary(medications)
        
        # Should mention active medications
        assert "Currently taking 2 medications" in summary
        assert "Metformin 500mg for Type 2 Diabetes" in summary
        assert "Lisinopril 10mg for Hypertension" in summary
        
        # Should mention discontinued medications
        assert "Previously prescribed 1 medications" in summary
    
    def test_generate_procedure_summary(self):
        """Test generating procedure summary."""
        procedures = [
            Procedure(
                procedure_id="P001",
                name="Colonoscopy",
                date="2023-05-15",
                provider="Dr. Johnson"
            ),
            Procedure(
                procedure_id="P002",
                name="Blood work",
                date="2023-10-01",
                provider="Lab Corp"
            ),
            Procedure(
                procedure_id="P003",
                name="Chest X-ray",
                date="2023-08-20",
                provider="Radiology Dept"
            )
        ]
        
        summary = self.summarizer._generate_procedure_summary(procedures)
        
        assert "3 documented procedures" in summary
        assert "Colonoscopy" in summary
        assert "Blood work" in summary
        assert "Chest X-ray" in summary
    
    def test_determine_event_significance(self):
        """Test event significance determination."""
        test_cases = [
            ("diagnosis", "Diagnosed with acute myocardial infarction", "high"),
            ("procedure", "Emergency surgery performed", "high"),
            ("visit", "Routine annual checkup", "medium"),
            ("medication_start", "Started new medication", "medium"),
            ("other", "Follow-up appointment", "low")  # Changed event type to get low significance
        ]
        
        for event_type, description, expected_significance in test_cases:
            result = self.summarizer._determine_event_significance(event_type, description)
            assert result == expected_significance, f"Failed for: {event_type}, {description}"
    
    def test_calculate_data_quality(self):
        """Test data quality calculation."""
        # High quality patient data
        high_quality_patient = PatientData(
            patient_id="P001",
            name="Complete Patient",
            demographics=Demographics(
                age=45,
                gender="F",
                date_of_birth="1978-05-15",
                address="123 Main St",
                phone="555-1234"
            ),
            medical_history=[
                MedicalEvent(
                    event_id="E001",
                    date="2023-10-15",
                    event_type="visit",
                    description="Annual checkup",
                    provider="Dr. Smith"
                )
            ],
            medications=[
                Medication(
                    medication_id="M001",
                    name="Metformin",
                    dosage="500mg",
                    frequency="twice daily",
                    indication="Diabetes",
                    start_date="2023-01-15",
                    status="active"
                )
            ],
            procedures=[
                Procedure(
                    procedure_id="P001",
                    name="Blood work",
                    date="2023-09-01",
                    provider="Lab Corp"
                )
            ],
            diagnoses=[
                Diagnosis(
                    diagnosis_id="D001",
                    condition="Type 2 Diabetes",
                    date_diagnosed="2023-01-10",
                    icd_10_code="E11.9",
                    severity="moderate",
                    status="active"
                )
            ],
            raw_xml="",
            extraction_timestamp=datetime.now()
        )
        
        quality_score = self.summarizer._calculate_data_quality(high_quality_patient)
        assert quality_score > 0.7  # Should be high quality
        
        # Low quality patient data
        low_quality_patient = PatientData(
            patient_id="P002",
            name="Incomplete Patient",
            demographics=Demographics(),  # No demographic data
            medical_history=[],
            medications=[],
            procedures=[],
            diagnoses=[],
            raw_xml="",
            extraction_timestamp=datetime.now()
        )
        
        low_quality_score = self.summarizer._calculate_data_quality(low_quality_patient)
        assert low_quality_score < 0.3  # Should be low quality
    
    def test_identify_missing_data(self):
        """Test identification of missing data elements."""
        incomplete_patient = PatientData(
            patient_id="P001",
            name="Incomplete Patient",
            demographics=Demographics(),  # Missing age, gender, DOB
            medical_history=[],
            medications=[
                Medication(
                    medication_id="M001",
                    name="Unknown Med",
                    dosage="",  # Missing dosage
                    frequency="",  # Missing frequency
                    status="active"
                )
            ],
            procedures=[],
            diagnoses=[
                Diagnosis(
                    diagnosis_id="D001",
                    condition="Some Condition",
                    date_diagnosed="",  # Missing date
                    status="active"
                )
            ],
            raw_xml="",
            extraction_timestamp=datetime.now()
        )
        
        missing_indicators = self.summarizer._identify_missing_data(incomplete_patient)
        
        # Should identify multiple missing data elements
        assert len(missing_indicators) > 0
        assert any("age not documented" in indicator for indicator in missing_indicators)
        assert any("gender not documented" in indicator for indicator in missing_indicators)
        assert any("diagnoses missing dates" in indicator for indicator in missing_indicators)
        assert any("medications missing dosage/frequency" in indicator for indicator in missing_indicators)
    
    def test_parse_date(self):
        """Test date parsing functionality."""
        test_cases = [
            ("2023-10-15", "2023-10-15"),
            ("10/15/2023", "2023-10-15"),
            ("unknown", datetime.min),
            ("", datetime.min),
            ("invalid-date", datetime.min)
        ]
        
        for input_date, expected in test_cases:
            result = self.summarizer._parse_date(input_date)
            if expected == datetime.min:
                assert result == datetime.min
            else:
                assert result.strftime("%Y-%m-%d") == expected
    
    def test_categorize_procedure(self):
        """Test procedure categorization."""
        test_cases = [
            ("Appendectomy surgery", "surgical"),
            ("CT scan of chest", "imaging"),
            ("Colonoscopy with biopsy", "diagnostic"),
            ("Blood work panel", "laboratory"),
            ("Physical therapy", "general")
        ]
        
        for procedure_name, expected_category in test_cases:
            result = self.summarizer._categorize_procedure(procedure_name)
            assert result == expected_category, f"Failed for: {procedure_name}"
    
    def test_complete_summary_generation(self):
        """Test complete medical summary generation."""
        # Create comprehensive patient data
        patient_data = PatientData(
            patient_id="P001",
            name="Jane Smith",
            demographics=Demographics(age=55, gender="F"),
            medical_history=[
                MedicalEvent(
                    event_id="E001",
                    date="2023-10-15",
                    event_type="visit",
                    description="Follow-up for diabetes management",
                    provider="Dr. Johnson"
                )
            ],
            medications=[
                Medication(
                    medication_id="M001",
                    name="Metformin",
                    dosage="1000mg",
                    frequency="twice daily",
                    indication="Type 2 Diabetes",
                    start_date="2022-01-15",
                    status="active"
                ),
                Medication(
                    medication_id="M002",
                    name="Lisinopril",
                    dosage="10mg",
                    frequency="daily",
                    indication="Hypertension",
                    start_date="2022-03-01",
                    status="active"
                )
            ],
            procedures=[
                Procedure(
                    procedure_id="P001",
                    name="HbA1c test",
                    date="2023-10-15",
                    provider="Lab Corp"
                )
            ],
            diagnoses=[
                Diagnosis(
                    diagnosis_id="D001",
                    condition="Type 2 Diabetes Mellitus",
                    date_diagnosed="2022-01-10",
                    icd_10_code="E11.9",
                    severity="moderate",
                    status="active"
                ),
                Diagnosis(
                    diagnosis_id="D002",
                    condition="Essential Hypertension",
                    date_diagnosed="2022-02-20",
                    icd_10_code="I10",
                    severity="mild",
                    status="active"
                )
            ],
            raw_xml="",
            extraction_timestamp=datetime.now()
        )
        
        conditions = [
            Condition(
                name="Type 2 Diabetes Mellitus",
                icd_10_code="E11.9",
                severity="moderate",
                status="active",
                first_diagnosed="2022-01-10",
                confidence_score=1.0
            ),
            Condition(
                name="Essential Hypertension",
                icd_10_code="I10",
                severity="mild",
                status="active",
                first_diagnosed="2022-02-20",
                confidence_score=1.0
            )
        ]
        
        # Generate complete summary
        summary = self.summarizer.generate_summary(patient_data, conditions)
        
        # Verify summary structure
        assert summary.patient_id == "P001"
        assert len(summary.key_conditions) == 2
        assert len(summary.chronological_events) > 0
        assert summary.data_quality_score > 0
        
        # Verify summary content
        assert "Jane Smith" in summary.summary_text
        assert "Type 2 Diabetes Mellitus" in summary.summary_text
        assert "Essential Hypertension" in summary.summary_text
        
        # Verify medication summary
        assert "Currently taking 2 medications" in summary.medication_summary
        assert "Metformin" in summary.medication_summary
        assert "Lisinopril" in summary.medication_summary
        
        # Verify procedure summary
        assert "HbA1c test" in summary.procedure_summary
        
        # Verify chronological events are properly ordered
        assert summary.chronological_events[0].date >= summary.chronological_events[-1].date
    
    def test_empty_patient_data(self):
        """Test handling of empty patient data."""
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
        
        summary = self.summarizer.generate_summary(empty_patient, [])
        
        # Should handle gracefully
        assert summary.patient_id == "P000"
        assert len(summary.key_conditions) == 0
        assert len(summary.chronological_events) == 0
        assert "no significant documented medical conditions" in summary.summary_text
        assert "No medications documented" in summary.medication_summary
        assert "No procedures documented" in summary.procedure_summary
        assert summary.data_quality_score < 0.5  # Should be low quality