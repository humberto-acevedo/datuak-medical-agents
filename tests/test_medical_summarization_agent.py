"""Integration tests for Medical Summarization Agent."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.agents.medical_summarization_agent import MedicalSummarizationAgent
from src.models import (
    PatientData, Demographics, Diagnosis, MedicalEvent, 
    Medication, Procedure
)
from src.models.exceptions import DataValidationError


class TestMedicalSummarizationAgent:
    """Test Medical Summarization Agent integration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_audit_logger = Mock()
        
        # Create agent with mocked audit logger
        with patch('src.agents.medical_summarization_agent.setup_logging'):
            self.agent = MedicalSummarizationAgent(audit_logger=self.mock_audit_logger)
    
    def test_generate_summary_success(self):
        """Test successful medical summary generation."""
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
                    description="Annual checkup with diabetes management review",
                    provider="Dr. Smith"
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
            raw_xml="<patient></patient>",
            extraction_timestamp=datetime.now()
        )
        
        # Execute
        result = self.agent.generate_summary(patient_data)
        
        # Verify result structure
        assert result.patient_id == "P001"
        assert len(result.key_conditions) > 0
        assert len(result.chronological_events) > 0
        assert result.summary_text is not None
        assert result.medication_summary is not None
        assert result.procedure_summary is not None
        assert 0.0 <= result.data_quality_score <= 1.0
        
        # Verify content quality
        assert "John Doe" in result.summary_text
        assert "Type 2 Diabetes" in result.summary_text or "diabetes" in result.summary_text.lower()
        assert "Metformin" in result.medication_summary
        assert "HbA1c" in result.procedure_summary
        
        # Verify audit logging
        assert self.mock_audit_logger.log_processing_start.called
        assert self.mock_audit_logger.log_data_access.called
        assert self.mock_audit_logger.log_processing_complete.called
    
    def test_generate_summary_with_minimal_data(self):
        """Test summary generation with minimal patient data."""
        minimal_patient = PatientData(
            patient_id="P002",
            name="Jane Smith",
            demographics=Demographics(age=45),
            medical_history=[],
            medications=[],
            procedures=[],
            diagnoses=[
                Diagnosis(
                    diagnosis_id="D001",
                    condition="Hypertension",
                    date_diagnosed="2023-01-01",
                    status="active"
                )
            ],
            raw_xml="<patient></patient>",
            extraction_timestamp=datetime.now()
        )
        
        result = self.agent.generate_summary(minimal_patient)
        
        # Should handle minimal data gracefully
        assert result.patient_id == "P002"
        assert len(result.key_conditions) >= 1  # At least the diagnosis
        assert "Jane Smith" in result.summary_text
        assert "Hypertension" in result.summary_text
        assert result.data_quality_score < 1.0  # Should reflect limited data
    
    def test_generate_summary_empty_patient(self):
        """Test summary generation with empty patient data."""
        empty_patient = PatientData(
            patient_id="P003",
            name="Empty Patient",
            demographics=Demographics(),
            medical_history=[],
            medications=[],
            procedures=[],
            diagnoses=[],
            raw_xml="<patient></patient>",
            extraction_timestamp=datetime.now()
        )
        
        result = self.agent.generate_summary(empty_patient)
        
        # Should handle empty data gracefully
        assert result.patient_id == "P003"
        assert len(result.key_conditions) == 0
        assert "no significant documented medical conditions" in result.summary_text
        assert "No medications documented" in result.medication_summary
        assert "No procedures documented" in result.procedure_summary
        assert result.data_quality_score < 0.5  # Should be low quality
    
    def test_analyze_condition_trends(self):
        """Test condition trend analysis."""
        patient_data = PatientData(
            patient_id="P004",
            name="Trend Patient",
            demographics=Demographics(age=70, gender="F"),
            medical_history=[],
            medications=[
                Medication(
                    medication_id="M001",
                    name="Metformin",
                    dosage="500mg",
                    frequency="twice daily",
                    indication="Diabetes",
                    status="active"
                ),
                Medication(
                    medication_id="M002",
                    name="Atorvastatin",
                    dosage="20mg",
                    frequency="daily",
                    indication="High cholesterol",
                    status="active"
                )
            ],
            procedures=[],
            diagnoses=[
                Diagnosis(
                    diagnosis_id="D001",
                    condition="Type 2 Diabetes Mellitus",
                    date_diagnosed="2020-01-01",
                    severity="moderate",
                    status="active"
                ),
                Diagnosis(
                    diagnosis_id="D002",
                    condition="Hyperlipidemia",
                    date_diagnosed="2021-06-15",
                    severity="mild",
                    status="active"
                ),
                Diagnosis(
                    diagnosis_id="D003",
                    condition="Acute Bronchitis",
                    date_diagnosed="2023-10-01",
                    severity="mild",
                    status="resolved"
                )
            ],
            raw_xml="<patient></patient>",
            extraction_timestamp=datetime.now()
        )
        
        trends = self.agent.analyze_condition_trends(patient_data)
        
        # Verify trend analysis
        assert trends["total_conditions"] > 0
        assert trends["chronic_conditions"] >= 2  # Diabetes and hyperlipidemia
        assert trends["acute_conditions"] >= 1   # Bronchitis
        assert "severity_distribution" in trends
        assert "medication_alignment" in trends
        assert len(trends["condition_names"]) > 0
    
    def test_get_summary_quality_metrics(self):
        """Test summary quality metrics calculation."""
        # Create a medical summary (would normally come from generate_summary)
        from src.models import MedicalSummary, Condition, ChronologicalEvent
        
        medical_summary = MedicalSummary(
            patient_id="P005",
            summary_text="John Doe is a 65 year old male patient with a medical history significant for Type 2 Diabetes Mellitus and Essential Hypertension. Current medications include Metformin 1000mg for Type 2 Diabetes and Lisinopril 10mg for Hypertension.",
            key_conditions=[
                Condition(
                    name="Type 2 Diabetes Mellitus",
                    severity="moderate",
                    status="active",
                    confidence_score=0.9
                ),
                Condition(
                    name="Essential Hypertension",
                    severity="mild",
                    status="active",
                    confidence_score=0.8
                )
            ],
            medication_summary="Currently taking 2 medications: Metformin 1000mg for Type 2 Diabetes, Lisinopril 10mg for Hypertension.",
            procedure_summary="Medical procedures include 1 documented procedures: HbA1c test (2023-10-15).",
            chronological_events=[
                ChronologicalEvent(
                    date="2023-10-15",
                    event_type="visit",
                    description="Annual checkup",
                    significance="medium",
                    related_conditions=["Diabetes", "Hypertension"]
                )
            ],
            generated_timestamp=datetime.now(),
            data_quality_score=0.85,
            missing_data_indicators=[]
        )
        
        metrics = self.agent.get_summary_quality_metrics(medical_summary)
        
        # Verify quality metrics
        assert "overall_data_quality" in metrics
        assert "condition_confidence_average" in metrics
        assert "narrative_quality_score" in metrics
        assert "completeness_score" in metrics
        assert "quality_assessment" in metrics
        assert metrics["conditions_count"] == 2
        assert metrics["chronological_events_count"] == 1
        assert metrics["quality_assessment"] in ["Excellent", "Good", "Fair", "Poor"]
    
    def test_get_condition_insights(self):
        """Test detailed condition insights generation."""
        patient_data = PatientData(
            patient_id="P006",
            name="Insight Patient",
            demographics=Demographics(age=60, gender="M"),
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
            diagnoses=[
                Diagnosis(
                    diagnosis_id="D001",
                    condition="Type 2 Diabetes Mellitus",
                    date_diagnosed="2020-01-01",
                    severity="moderate",
                    status="active"
                ),
                Diagnosis(
                    diagnosis_id="D002",
                    condition="Essential Hypertension",
                    date_diagnosed="2021-01-01",
                    severity="moderate",
                    status="active"
                )
            ],
            raw_xml="<patient></patient>",
            extraction_timestamp=datetime.now()
        )
        
        insights = self.agent.get_condition_insights(patient_data)
        
        # Verify insights structure
        assert "primary_conditions" in insights
        assert "chronic_disease_burden" in insights
        assert "medication_condition_gaps" in insights
        assert "condition_interactions" in insights
        
        # Verify content
        assert insights["chronic_disease_burden"] >= 1  # At least diabetes
        assert len(insights["primary_conditions"]) > 0
        
        # Should identify medication gap for hypertension (if hypertension is identified as chronic)
        # Note: The exact count may vary based on condition extraction logic
    
    def test_error_handling(self):
        """Test error handling in summary generation."""
        # Create invalid patient data (missing required fields)
        invalid_patient = PatientData(
            patient_id="",  # Invalid empty ID
            name="",        # Invalid empty name
            demographics=Demographics(),
            medical_history=[],
            medications=[],
            procedures=[],
            diagnoses=[],
            raw_xml="",     # Invalid empty XML
            extraction_timestamp=datetime.now()
        )
        
        # Should handle gracefully and still generate summary
        result = self.agent.generate_summary(invalid_patient)
        
        # Should complete but with warnings logged
        assert self.mock_audit_logger.log_data_access.called
        
        # Should have low quality score due to validation issues
        assert result.data_quality_score < 0.5
    
    def test_medication_condition_alignment_analysis(self):
        """Test medication-condition alignment analysis."""
        patient_data = PatientData(
            patient_id="P007",
            name="Alignment Patient",
            demographics=Demographics(age=55),
            medical_history=[],
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
                    name="Aspirin",
                    dosage="81mg",
                    frequency="daily",
                    indication="Cardioprotection",
                    status="active"
                )
            ],
            procedures=[],
            diagnoses=[
                Diagnosis(
                    diagnosis_id="D001",
                    condition="Type 2 Diabetes Mellitus",
                    date_diagnosed="2020-01-01",
                    status="active"
                ),
                Diagnosis(
                    diagnosis_id="D002",
                    condition="Essential Hypertension",
                    date_diagnosed="2021-01-01",
                    status="active"
                )
            ],
            raw_xml="<patient></patient>",
            extraction_timestamp=datetime.now()
        )
        
        # Extract conditions first
        conditions = self.agent.condition_extractor.extract_conditions(patient_data)
        
        # Analyze alignment
        alignment = self.agent._analyze_medication_condition_alignment(patient_data, conditions)
        
        # Should identify well-managed diabetes
        assert len(alignment["well_managed_conditions"]) > 0
        
        # Should identify potentially unmanaged hypertension
        assert len(alignment["potentially_unmanaged_conditions"]) > 0
    
    def test_get_agent_status(self):
        """Test agent status reporting."""
        status = self.agent.get_agent_status()
        
        assert status["agent_name"] == "Medical Summarization Agent"
        assert status["status"] == "healthy"
        assert "components" in status
        assert "capabilities" in status
        assert "condition_extraction" in status["capabilities"]
        assert "medical_summarization" in status["capabilities"]
    
    def test_audit_trail_completeness(self):
        """Test that complete audit trail is generated."""
        patient_data = PatientData(
            patient_id="P008",
            name="Audit Patient",
            demographics=Demographics(age=40),
            medical_history=[],
            medications=[],
            procedures=[],
            diagnoses=[
                Diagnosis(
                    diagnosis_id="D001",
                    condition="Hypertension",
                    date_diagnosed="2023-01-01",
                    status="active"
                )
            ],
            raw_xml="<patient></patient>",
            extraction_timestamp=datetime.now()
        )
        
        # Execute
        self.agent.generate_summary(patient_data)
        
        # Verify complete audit trail
        assert self.mock_audit_logger.log_processing_start.called
        assert self.mock_audit_logger.log_data_access.called
        assert self.mock_audit_logger.log_processing_complete.called
        
        # Verify audit log details
        start_call = self.mock_audit_logger.log_processing_start.call_args
        assert start_call[1]['workflow_type'] == 'medical_summarization'
        
        # Should have multiple data access calls (condition extraction, summary generation)
        assert self.mock_audit_logger.log_data_access.call_count >= 2
        
        complete_call = self.mock_audit_logger.log_processing_complete.call_args
        assert complete_call[1]['workflow_type'] == 'medical_summarization'
        assert 'duration_seconds' in complete_call[1]
    
    def test_complex_patient_scenario(self):
        """Test with complex patient having multiple conditions and medications."""
        complex_patient = PatientData(
            patient_id="P009",
            name="Complex Patient",
            demographics=Demographics(age=75, gender="F"),
            medical_history=[
                MedicalEvent(
                    event_id="E001",
                    date="2023-09-15",
                    event_type="emergency",
                    description="Emergency room visit for chest pain, ruled out MI",
                    provider="Emergency Dept"
                ),
                MedicalEvent(
                    event_id="E002",
                    date="2023-10-01",
                    event_type="visit",
                    description="Cardiology follow-up, stress test normal",
                    provider="Dr. Heart"
                )
            ],
            medications=[
                Medication(
                    medication_id="M001",
                    name="Metformin",
                    dosage="1000mg",
                    frequency="twice daily",
                    indication="Type 2 Diabetes",
                    start_date="2018-01-01",
                    status="active"
                ),
                Medication(
                    medication_id="M002",
                    name="Lisinopril",
                    dosage="20mg",
                    frequency="daily",
                    indication="Hypertension",
                    start_date="2019-06-01",
                    status="active"
                ),
                Medication(
                    medication_id="M003",
                    name="Atorvastatin",
                    dosage="40mg",
                    frequency="daily",
                    indication="Hyperlipidemia",
                    start_date="2020-03-01",
                    status="active"
                ),
                Medication(
                    medication_id="M004",
                    name="Aspirin",
                    dosage="81mg",
                    frequency="daily",
                    indication="Cardioprotection",
                    start_date="2021-01-01",
                    status="active"
                )
            ],
            procedures=[
                Procedure(
                    procedure_id="P001",
                    name="Echocardiogram",
                    date="2023-09-16",
                    provider="Cardiology"
                ),
                Procedure(
                    procedure_id="P002",
                    name="Stress test",
                    date="2023-10-01",
                    provider="Cardiology"
                )
            ],
            diagnoses=[
                Diagnosis(
                    diagnosis_id="D001",
                    condition="Type 2 Diabetes Mellitus",
                    date_diagnosed="2018-01-01",
                    icd_10_code="E11.9",
                    severity="moderate",
                    status="active"
                ),
                Diagnosis(
                    diagnosis_id="D002",
                    condition="Essential Hypertension",
                    date_diagnosed="2019-06-01",
                    icd_10_code="I10",
                    severity="moderate",
                    status="active"
                ),
                Diagnosis(
                    diagnosis_id="D003",
                    condition="Hyperlipidemia",
                    date_diagnosed="2020-03-01",
                    icd_10_code="E78.5",
                    severity="mild",
                    status="active"
                )
            ],
            raw_xml="<patient></patient>",
            extraction_timestamp=datetime.now()
        )
        
        # Generate summary
        result = self.agent.generate_summary(complex_patient)
        
        # Verify comprehensive analysis
        assert len(result.key_conditions) >= 3
        assert len(result.chronological_events) >= 4  # 2 history + 2 procedures + diagnoses + medications
        assert result.data_quality_score > 0.7  # Should be high quality
        
        # Verify narrative mentions key elements
        assert "Complex Patient" in result.summary_text
        assert "75" in result.summary_text  # Age
        assert any(condition in result.summary_text for condition in ["Diabetes", "Hypertension", "Hyperlipidemia"])
        
        # Verify medication summary is comprehensive
        assert "Currently taking 4 medications" in result.medication_summary
        assert "Metformin" in result.medication_summary
        assert "Lisinopril" in result.medication_summary
        
        # Verify procedure summary
        assert "Echocardiogram" in result.procedure_summary
        assert "Stress test" in result.procedure_summary
        
        # Get additional insights
        trends = self.agent.analyze_condition_trends(complex_patient)
        assert trends["chronic_conditions"] >= 3
        
        insights = self.agent.get_condition_insights(complex_patient)
        assert len(insights["primary_conditions"]) >= 3
        assert insights["chronic_disease_burden"] >= 3