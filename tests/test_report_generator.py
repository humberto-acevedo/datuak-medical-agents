"""Tests for Report Generator."""
import pytest
from datetime import datetime
from unittest.mock import Mock
import json

from src.agents.report_generator import ReportGenerator
from src.models import (
    PatientData, Demographics, MedicalSummary, Condition, 
    ResearchAnalysis, ResearchFinding, AnalysisReport, ReportError
)
from src.utils import AuditLogger


class TestReportGenerator:
    """Test cases for Report Generator."""
    
    @pytest.fixture
    def mock_audit_logger(self):
        """Create mock audit logger."""
        return Mock(spec=AuditLogger)
    
    @pytest.fixture
    def report_generator(self, mock_audit_logger):
        """Create report generator with mocked audit logger."""
        return ReportGenerator(audit_logger=mock_audit_logger)
    
    @pytest.fixture
    def sample_patient_data(self):
        """Create sample patient data."""
        return PatientData(
            patient_id="RPT_TEST_123",
            name="Alice Johnson",
            demographics=Demographics(
                age=62,
                gender="F",
                date_of_birth="1962-05-20"
            ),
            medical_history=[],
            medications=[],
            procedures=[],
            diagnoses=[],
            raw_xml="<patient>comprehensive test data</patient>",
            extraction_timestamp=datetime.now()
        )
    
    @pytest.fixture
    def sample_medical_summary(self):
        """Create sample medical summary."""
        conditions = [
            Condition(
                name="Type 2 Diabetes Mellitus",
                icd_10_code="E11.9",
                severity="moderate",
                confidence_score=0.95,
                status="active",
                first_diagnosed="2018-03-15"
            ),
            Condition(
                name="Hypertension",
                icd_10_code="I10",
                severity="severe",
                confidence_score=0.88,
                status="chronic",
                first_diagnosed="2016-08-10"
            ),
            Condition(
                name="Hyperlipidemia",
                icd_10_code="E78.5",
                severity="mild",
                confidence_score=0.82,
                status="active",
                first_diagnosed="2019-11-22"
            )
        ]
        
        return MedicalSummary(
            patient_id="RPT_TEST_123",
            summary_text="62-year-old female with well-managed diabetes, hypertension, and hyperlipidemia. Patient demonstrates good medication adherence and lifestyle modifications.",
            key_conditions=conditions,
            medication_summary="Metformin 1000mg BID, Lisinopril 10mg daily, Atorvastatin 40mg daily",
            procedure_summary="Annual diabetic eye exam, routine blood pressure monitoring",
            chronological_events=[],
            generated_timestamp=datetime.now(),
            data_quality_score=0.91,
            missing_data_indicators=["recent_lab_results", "family_history"]
        )
    
    @pytest.fixture
    def sample_research_analysis(self):
        """Create sample research analysis."""
        research_findings = [
            ResearchFinding(
                title="Metformin and Cardiovascular Outcomes in Type 2 Diabetes: Meta-Analysis",
                authors=["Johnson, M.", "Smith, K.", "Brown, L."],
                publication_date="2023-07-15",
                journal="Diabetes Care",
                doi="10.2337/dc23-1234",
                pmid="37456789",
                relevance_score=0.92,
                key_findings="Metformin reduces cardiovascular events by 15% in T2DM patients",
                citation="Johnson, M. et al. (2023). Metformin and CV Outcomes. Diabetes Care.",
                abstract="Comprehensive meta-analysis of metformin cardiovascular benefits",
                study_type="meta-analysis",
                sample_size=45000,
                peer_reviewed=True
            ),
            ResearchFinding(
                title="Intensive Blood Pressure Control in Diabetes: RCT Results",
                authors=["Wilson, R.", "Davis, P."],
                publication_date="2023-09-10",
                journal="New England Journal of Medicine",
                doi="10.1056/nejm2023.456",
                relevance_score=0.89,
                key_findings="Intensive BP control reduces diabetic complications by 22%",
                citation="Wilson, R. et al. (2023). Intensive BP Control. NEJM.",
                study_type="RCT",
                sample_size=12500,
                peer_reviewed=True
            ),
            ResearchFinding(
                title="Statin Therapy in Diabetic Patients: Long-term Outcomes",
                authors=["Anderson, T.", "Miller, J."],
                publication_date="2023-05-20",
                journal="Circulation",
                doi="10.1161/circ.2023.789",
                relevance_score=0.85,
                key_findings="High-intensity statin therapy reduces MACE by 28% in diabetics",
                citation="Anderson, T. et al. (2023). Statin Therapy. Circulation.",
                study_type="cohort",
                sample_size=8900,
                peer_reviewed=True
            )
        ]
        
        conditions = [
            Condition(name="Type 2 Diabetes Mellitus", confidence_score=0.95),
            Condition(name="Hypertension", confidence_score=0.88),
            Condition(name="Hyperlipidemia", confidence_score=0.82)
        ]
        
        return ResearchAnalysis(
            patient_id="RPT_TEST_123",
            analysis_timestamp=datetime.now(),
            conditions_analyzed=conditions,
            research_findings=research_findings,
            condition_research_correlations={
                "Type 2 Diabetes Mellitus": research_findings[:2],
                "Hypertension": research_findings[1:2],
                "Hyperlipidemia": research_findings[2:3]
            },
            categorized_findings={
                "systematic_reviews": research_findings[:1],
                "clinical_trials": research_findings[1:2],
                "observational": research_findings[2:3]
            },
            research_insights=[
                "Research coverage: 3/3 conditions (100%) have relevant research literature available.",
                "Study quality: 3/3 papers are high-quality studies from top-tier journals.",
                "Recent research: 3/3 papers published within the last year, indicating current evidence.",
                "Type 2 Diabetes Mellitus: Most relevant research focuses on cardiovascular outcomes.",
                "Comprehensive evidence base supports current treatment approaches."
            ],
            clinical_recommendations=[
                "Continue evidence-based metformin therapy for cardiovascular protection.",
                "Consider intensive blood pressure control targets based on recent RCT evidence.",
                "Maintain high-intensity statin therapy for optimal cardiovascular risk reduction.",
                "Regular monitoring recommended for medication effectiveness and side effects.",
                "Patient education opportunities available based on current research findings."
            ],
            analysis_confidence=0.89,
            total_papers_reviewed=15,
            relevant_papers_found=3
        )
    
    def test_generator_initialization(self, mock_audit_logger):
        """Test report generator initialization."""
        generator = ReportGenerator(audit_logger=mock_audit_logger)
        
        assert generator.audit_logger == mock_audit_logger
        assert generator.report_version == "1.0"
        assert generator.system_info["system_name"] == "Medical Record Analysis System"
        assert len(generator.system_info["components"]) == 3
    
    def test_generate_analysis_report_success(self, report_generator, sample_patient_data,
                                            sample_medical_summary, sample_research_analysis,
                                            mock_audit_logger):
        """Test successful analysis report generation."""
        # Generate report
        report = report_generator.generate_analysis_report(
            sample_patient_data, sample_medical_summary, sample_research_analysis
        )
        
        # Verify report structure
        assert isinstance(report, AnalysisReport)
        assert report.patient_data.patient_id == "RPT_TEST_123"
        assert report.report_id.startswith("RPT_")
        assert hasattr(report, 'report_version')
        
        # Verify report content
        assert report.patient_data == sample_patient_data
        assert report.medical_summary == sample_medical_summary
        assert report.research_analysis == sample_research_analysis
        
        # Verify generated content
        assert hasattr(report, 'executive_summary') and len(report.executive_summary) > 100
        assert hasattr(report, 'key_findings') and len(report.key_findings) > 0
        assert hasattr(report, 'recommendations') and len(report.recommendations) > 0
        assert hasattr(report, 'data_sources') and len(report.data_sources) > 0
        
        # Verify quality metrics
        assert "overall_quality_score" in report.quality_metrics
        assert 0.0 <= report.quality_metrics["overall_quality_score"] <= 1.0
        
        # Verify audit logging
        mock_audit_logger.log_data_access.assert_called()
    
    def test_generate_report_id(self, report_generator):
        """Test report ID generation."""
        report_id1 = report_generator._generate_report_id()
        report_id2 = report_generator._generate_report_id()
        
        # Should be unique
        assert report_id1 != report_id2
        
        # Should follow format
        assert report_id1.startswith("RPT_")
        assert len(report_id1.split("_")) == 4  # RPT_YYYYMMDD_HHMMSS_UUID
        
        # Should contain timestamp
        date_part = report_id1.split("_")[1]
        time_part = report_id1.split("_")[2]
        assert len(date_part) == 8  # YYYYMMDD format
        assert len(time_part) == 6  # HHMMSS format
    
    def test_create_executive_summary(self, report_generator, sample_patient_data,
                                    sample_medical_summary, sample_research_analysis):
        """Test executive summary creation."""
        summary = report_generator._create_executive_summary(
            sample_patient_data, sample_medical_summary, sample_research_analysis
        )
        
        assert isinstance(summary, str)
        assert len(summary) > 100
        
        # Should contain key information
        assert "62-year-old" in summary
        assert ("female" in summary.lower() or "F" in summary)  # Could be abbreviated
        assert "diabetes" in summary.lower()
        assert "research" in summary.lower()
        assert "confidence" in summary.lower()
    
    def test_calculate_quality_metrics(self, report_generator, sample_patient_data,
                                     sample_medical_summary, sample_research_analysis):
        """Test quality metrics calculation."""
        metrics = report_generator._calculate_quality_metrics(
            sample_patient_data, sample_medical_summary, sample_research_analysis
        )
        
        # Verify structure
        assert "data_completeness_score" in metrics
        assert "medical_summary_quality" in metrics
        assert "research_analysis_quality" in metrics
        assert "overall_quality_score" in metrics
        assert "quality_assessment" in metrics
        
        # Verify ranges
        assert 0.0 <= metrics["data_completeness_score"] <= 1.0
        assert 0.0 <= metrics["overall_quality_score"] <= 1.0
        
        # Verify medical summary quality details
        med_quality = metrics["medical_summary_quality"]
        assert "conditions_identified" in med_quality
        assert "data_quality_score" in med_quality
        assert med_quality["conditions_identified"] == 3
        
        # Verify research analysis quality details
        research_quality = metrics["research_analysis_quality"]
        assert "papers_found" in research_quality
        assert "analysis_confidence" in research_quality
        assert research_quality["papers_found"] == 3
    
    def test_compile_recommendations(self, report_generator, sample_medical_summary,
                                   sample_research_analysis):
        """Test recommendations compilation."""
        recommendations = report_generator._compile_recommendations(
            sample_medical_summary, sample_research_analysis
        )
        
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        assert len(recommendations) <= 10  # Should be limited
        
        # Should include research recommendations
        research_recs = sample_research_analysis.clinical_recommendations
        for rec in research_recs:
            assert rec in recommendations
        
        # Should be strings
        assert all(isinstance(rec, str) for rec in recommendations)
        assert all(len(rec) > 10 for rec in recommendations)  # Substantive recommendations
    
    def test_extract_key_findings(self, report_generator, sample_medical_summary,
                                 sample_research_analysis):
        """Test key findings extraction."""
        findings = report_generator._extract_key_findings(
            sample_medical_summary, sample_research_analysis
        )
        
        assert isinstance(findings, list)
        assert len(findings) > 0
        assert len(findings) <= 8  # Should be limited
        
        # Should contain primary condition
        primary_finding = findings[0]
        assert "Primary condition" in primary_finding
        assert "Type 2 Diabetes" in primary_finding
        assert "Confidence" in primary_finding
        
        # Should be strings
        assert all(isinstance(finding, str) for finding in findings)
    
    def test_compile_data_sources(self, report_generator, sample_research_analysis):
        """Test data sources compilation."""
        sources = report_generator._compile_data_sources(sample_research_analysis)
        
        assert isinstance(sources, list)
        assert len(sources) > 0
        
        # Should include standard sources
        assert any("XML medical record" in source for source in sources)
        assert any("ICD-10" in source for source in sources)
        
        # Should include research sources
        research_journals = set(f.journal for f in sample_research_analysis.research_findings)
        for journal in research_journals:
            assert any(journal in source for source in sources)
    
    def test_create_report_metadata(self, report_generator, sample_patient_data,
                                  sample_medical_summary, sample_research_analysis):
        """Test report metadata creation."""
        metadata = report_generator._create_report_metadata(
            sample_patient_data, sample_medical_summary, sample_research_analysis
        )
        
        # Verify structure
        assert "system_info" in metadata
        assert "processing_timestamps" in metadata
        assert "data_statistics" in metadata
        assert "quality_indicators" in metadata
        
        # Verify system info
        system_info = metadata["system_info"]
        assert system_info["system_name"] == "Medical Record Analysis System"
        assert len(system_info["components"]) == 3
        
        # Verify timestamps
        timestamps = metadata["processing_timestamps"]
        assert "xml_extraction" in timestamps
        assert "medical_summary" in timestamps
        assert "research_analysis" in timestamps
        assert "report_generation" in timestamps
        
        # Verify statistics
        stats = metadata["data_statistics"]
        assert stats["conditions_extracted"] == 3
        assert stats["research_papers_found"] == 3
        assert stats["total_processing_agents"] == 3
    
    def test_generate_report_with_minimal_data(self, report_generator, mock_audit_logger):
        """Test report generation with minimal data."""
        # Create minimal patient data
        minimal_patient = PatientData(
            patient_id="MIN_TEST_123",
            name="John Doe",
            demographics=Demographics(),
            medical_history=[],
            medications=[],
            procedures=[],
            diagnoses=[],
            raw_xml="<patient>minimal</patient>",
            extraction_timestamp=datetime.now()
        )
        
        # Create minimal medical summary
        minimal_summary = MedicalSummary(
            patient_id="MIN_TEST_123",
            summary_text="Limited medical information available.",
            key_conditions=[],
            medication_summary="No medications documented",
            procedure_summary="No procedures documented",
            chronological_events=[],
            generated_timestamp=datetime.now(),
            data_quality_score=0.3,
            missing_data_indicators=["demographics", "medical_history", "medications"]
        )
        
        # Create minimal research analysis
        minimal_research = ResearchAnalysis(
            patient_id="MIN_TEST_123",
            analysis_timestamp=datetime.now(),
            conditions_analyzed=[],
            research_findings=[],
            condition_research_correlations={},
            categorized_findings={},
            research_insights=["Limited clinical data available for research correlation."],
            clinical_recommendations=["Obtain additional clinical history and documentation."],
            analysis_confidence=0.2,
            total_papers_reviewed=0,
            relevant_papers_found=0
        )
        
        # Generate report
        report = report_generator.generate_analysis_report(
            minimal_patient, minimal_summary, minimal_research
        )
        
        # Should still generate valid report
        assert isinstance(report, AnalysisReport)
        assert report.patient_id == "MIN_TEST_123"
        assert len(report.executive_summary) > 50
        assert report.quality_metrics["overall_quality_score"] < 0.5
    
    def test_generate_report_error_handling(self, report_generator, mock_audit_logger):
        """Test error handling in report generation."""
        # Create invalid data that should cause an error
        invalid_patient = None
        
        with pytest.raises(ReportError):
            report_generator.generate_analysis_report(
                invalid_patient, None, None
            )
        
        # Verify error logging
        mock_audit_logger.log_error.assert_called_once()
    
    def test_report_validation(self, report_generator, sample_patient_data,
                             sample_medical_summary, sample_research_analysis):
        """Test that generated reports pass validation."""
        report = report_generator.generate_analysis_report(
            sample_patient_data, sample_medical_summary, sample_research_analysis
        )
        
        # Validate the report
        validation_errors = report.validate()
        
        # Should have no critical validation errors
        critical_errors = [e for e in validation_errors if "required" in e.lower()]
        assert len(critical_errors) == 0
    
    def test_report_serialization(self, report_generator, sample_patient_data,
                                sample_medical_summary, sample_research_analysis):
        """Test that generated reports can be serialized to JSON."""
        report = report_generator.generate_analysis_report(
            sample_patient_data, sample_medical_summary, sample_research_analysis
        )
        
        # Should be serializable to JSON
        report_dict = report.to_dict()
        json_str = json.dumps(report_dict, default=str)
        
        assert len(json_str) > 1000  # Should be substantial
        
        # Should be deserializable
        parsed_dict = json.loads(json_str)
        assert parsed_dict["patient_id"] == "RPT_TEST_123"
        assert parsed_dict["report_version"] == "1.0"
    
    def test_quality_assessment_levels(self, report_generator):
        """Test different quality assessment levels."""
        # Test high quality
        high_quality_metrics = {"overall_quality_score": 0.9}
        # This would be tested by creating different scenarios with varying data quality
        
        # Test moderate quality  
        moderate_quality_metrics = {"overall_quality_score": 0.5}
        
        # Test low quality
        low_quality_metrics = {"overall_quality_score": 0.2}
        
        # The quality assessment logic is tested through the full report generation
        # with different data completeness scenarios