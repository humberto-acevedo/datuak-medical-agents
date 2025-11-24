"""Unit tests for data models."""

import pytest
from datetime import datetime
from src.models import (
    PatientData, Demographics, MedicalEvent, Medication, 
    Procedure, Diagnosis, MedicalSummary, Condition,
    ChronologicalEvent, ResearchAnalysis, ResearchFinding,
    AnalysisReport
)


class TestPatientData:
    """Test PatientData model and validation."""
    
    def test_patient_data_creation(self):
        """Test creating a valid PatientData instance."""
        demographics = Demographics(age=45, gender="F")
        patient = PatientData(
            patient_id="P001",
            name="Jane Smith",
            demographics=demographics,
            medical_history=[],
            medications=[],
            procedures=[],
            diagnoses=[],
            raw_xml="<patient></patient>",
            extraction_timestamp=datetime.now()
        )
        
        assert patient.patient_id == "P001"
        assert patient.name == "Jane Smith"
        assert patient.demographics.age == 45
        
    def test_patient_data_validation_success(self):
        """Test successful validation of patient data."""
        demographics = Demographics(age=45, gender="F")
        patient = PatientData(
            patient_id="P001",
            name="Jane Smith",
            demographics=demographics,
            medical_history=[],
            medications=[],
            procedures=[],
            diagnoses=[],
            raw_xml="<patient></patient>",
            extraction_timestamp=datetime.now()
        )
        
        errors = patient.validate()
        assert len(errors) == 0
        
    def test_patient_data_validation_errors(self):
        """Test validation errors for invalid patient data."""
        demographics = Demographics(age=-5)  # Invalid age
        patient = PatientData(
            patient_id="",  # Missing patient ID
            name="",  # Missing name
            demographics=demographics,
            medical_history=[],
            medications=[],
            procedures=[],
            diagnoses=[],
            raw_xml="",  # Missing raw XML
            extraction_timestamp=datetime.now()
        )
        
        errors = patient.validate()
        assert len(errors) >= 4  # Should have multiple validation errors
        assert any("Patient ID is required" in error for error in errors)
        assert any("Patient name is required" in error for error in errors)
        assert any("Raw XML source is required" in error for error in errors)
        assert any("Invalid age value" in error for error in errors)
        
    def test_get_active_conditions(self):
        """Test getting active conditions from patient data."""
        diagnosis1 = Diagnosis(
            diagnosis_id="D001",
            condition="Hypertension",
            date_diagnosed="2023-01-01",
            status="active"
        )
        diagnosis2 = Diagnosis(
            diagnosis_id="D002",
            condition="Diabetes",
            date_diagnosed="2022-01-01",
            status="chronic"
        )
        
        patient = PatientData(
            patient_id="P001",
            name="Jane Smith",
            demographics=Demographics(),
            medical_history=[],
            medications=[],
            procedures=[],
            diagnoses=[diagnosis1, diagnosis2],
            raw_xml="<patient></patient>",
            extraction_timestamp=datetime.now()
        )
        
        active_conditions = patient.get_active_conditions()
        assert "Hypertension" in active_conditions
        assert "Diabetes" not in active_conditions  # chronic, not active
        
    def test_serialization(self):
        """Test JSON serialization and deserialization."""
        demographics = Demographics(age=45, gender="F")
        patient = PatientData(
            patient_id="P001",
            name="Jane Smith",
            demographics=demographics,
            medical_history=[],
            medications=[],
            procedures=[],
            diagnoses=[],
            raw_xml="<patient></patient>",
            extraction_timestamp=datetime.now()
        )
        
        # Test serialization
        json_data = patient.to_json()
        assert isinstance(json_data, str)
        
        # Test deserialization
        restored_patient = PatientData.from_json(json_data)
        assert restored_patient.patient_id == patient.patient_id
        assert restored_patient.name == patient.name


class TestMedicalSummary:
    """Test MedicalSummary model and validation."""
    
    def test_medical_summary_creation(self):
        """Test creating a valid MedicalSummary instance."""
        condition = Condition(
            name="Hypertension",
            severity="moderate",
            confidence_score=0.9
        )
        
        summary = MedicalSummary(
            patient_id="P001",
            summary_text="Patient has well-controlled hypertension.",
            key_conditions=[condition],
            medication_summary="Taking ACE inhibitor daily.",
            procedure_summary="No recent procedures.",
            chronological_events=[],
            generated_timestamp=datetime.now(),
            data_quality_score=0.85,
            missing_data_indicators=[]
        )
        
        assert summary.patient_id == "P001"
        assert len(summary.key_conditions) == 1
        assert summary.data_quality_score == 0.85
        
    def test_medical_summary_validation(self):
        """Test medical summary validation."""
        condition = Condition(
            name="",  # Invalid empty name
            confidence_score=1.5  # Invalid score > 1
        )
        
        summary = MedicalSummary(
            patient_id="",  # Missing patient ID
            summary_text="",  # Empty summary
            key_conditions=[condition],
            medication_summary="",
            procedure_summary="",
            chronological_events=[],
            generated_timestamp=datetime.now(),
            data_quality_score=1.5,  # Invalid score > 1
            missing_data_indicators=[]
        )
        
        errors = summary.validate()
        assert len(errors) >= 4
        
    def test_get_high_priority_conditions(self):
        """Test filtering high priority conditions."""
        condition1 = Condition(name="Hypertension", severity="high")
        condition2 = Condition(name="Diabetes", status="chronic")
        condition3 = Condition(name="Cold", severity="low")
        
        summary = MedicalSummary(
            patient_id="P001",
            summary_text="Test summary",
            key_conditions=[condition1, condition2, condition3],
            medication_summary="",
            procedure_summary="",
            chronological_events=[],
            generated_timestamp=datetime.now(),
            data_quality_score=0.8,
            missing_data_indicators=[]
        )
        
        high_priority = summary.get_high_priority_conditions()
        assert len(high_priority) == 2
        assert condition1 in high_priority
        assert condition2 in high_priority
        assert condition3 not in high_priority


class TestResearchAnalysis:
    """Test ResearchAnalysis model and validation."""
    
    def test_research_finding_creation(self):
        """Test creating a valid ResearchFinding instance."""
        finding = ResearchFinding(
            title="Hypertension Treatment Study",
            authors=["Dr. Smith", "Dr. Jones"],
            publication_date="2023-01-01",
            journal="Medical Journal",
            relevance_score=0.85,
            citation="Smith et al. (2023). Medical Journal."
        )
        
        assert finding.title == "Hypertension Treatment Study"
        assert len(finding.authors) == 2
        assert finding.relevance_score == 0.85
        
    def test_research_finding_validation(self):
        """Test research finding validation."""
        finding = ResearchFinding(
            title="",  # Missing title
            authors=[],  # No authors
            publication_date="2023-01-01",
            journal="",  # Missing journal
            relevance_score=1.5,  # Invalid score
            citation=""  # Missing citation
        )
        
        errors = finding.validate()
        assert len(errors) >= 5
        
    def test_research_finding_quality_checks(self):
        """Test research quality assessment methods."""
        high_quality_finding = ResearchFinding(
            title="RCT Study",
            authors=["Dr. Smith"],
            publication_date="2023-01-01",
            journal="Top Journal",
            relevance_score=0.9,
            citation="Smith (2023)",
            study_type="RCT",
            peer_reviewed=True
        )
        
        low_quality_finding = ResearchFinding(
            title="Blog Post",
            authors=["Blogger"],
            publication_date="2020-01-01",
            journal="Blog",
            relevance_score=0.3,
            citation="Blogger (2020)",
            study_type="opinion",
            peer_reviewed=False
        )
        
        assert high_quality_finding.is_high_quality()
        assert not low_quality_finding.is_high_quality()
        assert high_quality_finding.is_recent(years=2)
        assert not low_quality_finding.is_recent(years=2)


class TestAnalysisReport:
    """Test complete AnalysisReport model."""
    
    def test_analysis_report_creation(self):
        """Test creating a complete analysis report."""
        # Create minimal valid components
        demographics = Demographics(age=45)
        patient_data = PatientData(
            patient_id="P001",
            name="Jane Smith",
            demographics=demographics,
            medical_history=[],
            medications=[],
            procedures=[],
            diagnoses=[],
            raw_xml="<patient></patient>",
            extraction_timestamp=datetime.now()
        )
        
        medical_summary = MedicalSummary(
            patient_id="P001",
            summary_text="Test summary",
            key_conditions=[],
            medication_summary="",
            procedure_summary="",
            chronological_events=[],
            generated_timestamp=datetime.now(),
            data_quality_score=0.8,
            missing_data_indicators=[]
        )
        
        research_analysis = ResearchAnalysis(
            conditions_researched=["Hypertension"],
            research_findings=[],
            total_papers_found=0,
            high_quality_papers=0,
            generated_timestamp=datetime.now(),
            search_strategy="keyword search",
            limitations=[]
        )
        
        report = AnalysisReport(
            patient_data=patient_data,
            medical_summary=medical_summary,
            research_analysis=research_analysis,
            generated_timestamp=datetime.now(),
            report_id="R001",
            processing_time_seconds=45.2,
            agent_versions={"xml_parser": "1.0", "summarizer": "1.0", "research": "1.0"},
            quality_metrics={"overall_confidence": 0.8}
        )
        
        assert report.report_id == "R001"
        assert report.patient_data.patient_id == "P001"
        
    def test_analysis_report_validation(self):
        """Test analysis report cross-validation."""
        # Test patient ID mismatch
        patient_data = PatientData(
            patient_id="P001",
            name="Jane Smith",
            demographics=Demographics(),
            medical_history=[],
            medications=[],
            procedures=[],
            diagnoses=[],
            raw_xml="<patient></patient>",
            extraction_timestamp=datetime.now()
        )
        
        medical_summary = MedicalSummary(
            patient_id="P002",  # Different patient ID
            summary_text="Test summary",
            key_conditions=[],
            medication_summary="",
            procedure_summary="",
            chronological_events=[],
            generated_timestamp=datetime.now(),
            data_quality_score=0.8,
            missing_data_indicators=[]
        )
        
        research_analysis = ResearchAnalysis(
            conditions_researched=[],
            research_findings=[],
            total_papers_found=0,
            high_quality_papers=0,
            generated_timestamp=datetime.now(),
            search_strategy="",
            limitations=[]
        )
        
        report = AnalysisReport(
            patient_data=patient_data,
            medical_summary=medical_summary,
            research_analysis=research_analysis,
            generated_timestamp=datetime.now(),
            report_id="R001",
            processing_time_seconds=45.2,
            agent_versions={},
            quality_metrics={}
        )
        
        errors = report.validate()
        assert any("Patient ID mismatch" in error for error in errors)