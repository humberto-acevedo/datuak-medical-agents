"""Integration tests for Research Correlation Agent."""
import pytest
from datetime import datetime
from unittest.mock import Mock

from src.agents.research_correlation_agent import ResearchCorrelationAgent
from src.models import (
    PatientData, Demographics, MedicalSummary, Condition, 
    ResearchAnalysis, ResearchFinding
)


class TestResearchIntegration:
    """Integration tests for the complete research correlation workflow."""
    
    @pytest.fixture
    def sample_patient_data(self):
        """Create sample patient data."""
        return PatientData(
            patient_id="INTEGRATION_TEST_123",
            name="Jane Smith",
            demographics=Demographics(
                age=55,
                gender="F",
                date_of_birth="1969-03-15"
            ),
            medical_history=[],
            medications=[],
            procedures=[],
            diagnoses=[],
            raw_xml="<patient>integration test</patient>",
            extraction_timestamp=datetime.now()
        )
    
    @pytest.fixture
    def sample_medical_summary(self):
        """Create sample medical summary with realistic conditions."""
        conditions = [
            Condition(
                name="Type 2 Diabetes Mellitus",
                icd_10_code="E11.9",
                severity="moderate",
                confidence_score=0.92,
                status="active",
                first_diagnosed="2020-01-15"
            ),
            Condition(
                name="Essential Hypertension",
                icd_10_code="I10",
                severity="mild",
                confidence_score=0.88,
                status="active",
                first_diagnosed="2019-06-20"
            ),
            Condition(
                name="Mixed Hyperlipidemia",
                icd_10_code="E78.2",
                severity="moderate",
                confidence_score=0.85,
                status="active",
                first_diagnosed="2021-03-10"
            )
        ]
        
        return MedicalSummary(
            patient_id="INTEGRATION_TEST_123",
            summary_text="55-year-old female with well-controlled diabetes, hypertension, and hyperlipidemia. Patient shows good medication adherence and lifestyle modifications.",
            key_conditions=conditions,
            medication_summary="Metformin 1000mg BID, Lisinopril 10mg daily, Atorvastatin 20mg daily",
            procedure_summary="No recent procedures",
            chronological_events=[],
            generated_timestamp=datetime.now(),
            data_quality_score=0.89,
            missing_data_indicators=[]
        )
    
    def test_complete_research_workflow(self, sample_patient_data, sample_medical_summary):
        """Test the complete research correlation workflow."""
        # Initialize agent
        audit_logger = Mock()
        agent = ResearchCorrelationAgent(audit_logger=audit_logger)
        
        # Execute research analysis
        research_analysis = agent.analyze_patient_research(
            sample_patient_data, sample_medical_summary
        )
        
        # Verify research analysis structure
        assert isinstance(research_analysis, ResearchAnalysis)
        assert research_analysis.patient_id == "INTEGRATION_TEST_123"
        assert research_analysis.analysis_timestamp is not None
        
        # Verify conditions were analyzed
        assert len(research_analysis.conditions_analyzed) > 0
        condition_names = [c.name for c in research_analysis.conditions_analyzed]
        assert any("diabetes" in name.lower() for name in condition_names)
        
        # Verify research findings were generated
        assert len(research_analysis.research_findings) > 0
        assert all(isinstance(f, ResearchFinding) for f in research_analysis.research_findings)
        
        # Verify relevance scores are reasonable
        for finding in research_analysis.research_findings:
            assert 0.0 <= finding.relevance_score <= 1.0
            assert finding.title is not None
            assert finding.authors is not None
            assert finding.journal is not None
        
        # Verify correlations were generated
        assert isinstance(research_analysis.condition_research_correlations, dict)
        assert len(research_analysis.condition_research_correlations) > 0
        
        # Verify insights and recommendations
        assert len(research_analysis.research_insights) > 0
        assert len(research_analysis.clinical_recommendations) > 0
        
        # Verify analysis confidence
        assert 0.0 <= research_analysis.analysis_confidence <= 1.0
        
        # Verify categorized findings
        assert isinstance(research_analysis.categorized_findings, dict)
        
        # Verify audit logging was called
        audit_logger.log_data_access.assert_called()
        
        print(f"✅ Research Analysis Complete:")
        print(f"   - Patient: {research_analysis.patient_id}")
        print(f"   - Conditions analyzed: {len(research_analysis.conditions_analyzed)}")
        print(f"   - Research papers found: {len(research_analysis.research_findings)}")
        print(f"   - Analysis confidence: {research_analysis.analysis_confidence:.2f}")
        print(f"   - Research insights: {len(research_analysis.research_insights)}")
        print(f"   - Clinical recommendations: {len(research_analysis.clinical_recommendations)}")
    
    def test_research_analysis_validation(self, sample_patient_data, sample_medical_summary):
        """Test that research analysis passes validation."""
        agent = ResearchCorrelationAgent()
        research_analysis = agent.analyze_patient_research(
            sample_patient_data, sample_medical_summary
        )
        
        # Validate the analysis
        validation_errors = research_analysis.validate()
        assert len(validation_errors) == 0, f"Validation errors: {validation_errors}"
    
    def test_research_analysis_helper_methods(self, sample_patient_data, sample_medical_summary):
        """Test research analysis helper methods work correctly."""
        agent = ResearchCorrelationAgent()
        research_analysis = agent.analyze_patient_research(
            sample_patient_data, sample_medical_summary
        )
        
        # Test top findings
        top_findings = research_analysis.get_top_findings(limit=3)
        assert len(top_findings) <= 3
        if len(top_findings) > 1:
            assert top_findings[0].relevance_score >= top_findings[1].relevance_score
        
        # Test recent findings
        recent_findings = research_analysis.get_recent_findings(years=5)
        assert isinstance(recent_findings, list)
        
        # Test high quality findings
        high_quality = research_analysis.get_high_quality_findings()
        assert isinstance(high_quality, list)
        
        # Test condition research lookup
        if research_analysis.condition_research_correlations:
            condition_name = list(research_analysis.condition_research_correlations.keys())[0]
            condition_research = research_analysis.get_condition_research(condition_name)
            assert isinstance(condition_research, list)
        
        # Test research summary
        summary = research_analysis.get_research_summary()
        assert isinstance(summary, dict)
        assert "total_conditions" in summary
        assert "analysis_confidence" in summary
        assert "total_papers_reviewed" in summary
    
    def test_research_findings_quality(self, sample_patient_data, sample_medical_summary):
        """Test that research findings meet quality standards."""
        agent = ResearchCorrelationAgent()
        research_analysis = agent.analyze_patient_research(
            sample_patient_data, sample_medical_summary
        )
        
        # Check that findings are relevant to patient conditions
        patient_condition_terms = [
            "diabetes", "hypertension", "hyperlipidemia", 
            "metabolic", "cardiovascular"
        ]
        
        relevant_findings = 0
        for finding in research_analysis.research_findings:
            finding_text = f"{finding.title} {finding.key_findings}".lower()
            if any(term in finding_text for term in patient_condition_terms):
                relevant_findings += 1
        
        # At least 50% of findings should be relevant
        relevance_ratio = relevant_findings / len(research_analysis.research_findings)
        assert relevance_ratio >= 0.5, f"Only {relevance_ratio:.1%} of findings are relevant"
        
        # Check that findings have required metadata
        for finding in research_analysis.research_findings:
            assert finding.title, "Finding missing title"
            assert finding.authors, "Finding missing authors"
            assert finding.journal, "Finding missing journal"
            assert finding.citation, "Finding missing citation"
            assert finding.key_findings, "Finding missing key findings"
            assert finding.peer_reviewed is not None, "Finding missing peer review status"
    
    def test_research_insights_quality(self, sample_patient_data, sample_medical_summary):
        """Test that research insights are meaningful and informative."""
        agent = ResearchCorrelationAgent()
        research_analysis = agent.analyze_patient_research(
            sample_patient_data, sample_medical_summary
        )
        
        insights = research_analysis.research_insights
        assert len(insights) >= 3, "Should generate at least 3 insights"
        
        # Check for expected insight types
        insight_text = " ".join(insights).lower()
        expected_topics = ["coverage", "quality", "recent", "research"]
        
        topics_found = sum(1 for topic in expected_topics if topic in insight_text)
        assert topics_found >= 2, f"Insights should cover multiple topics, found: {topics_found}"
        
        # Check that insights are substantive (not just empty strings)
        for insight in insights:
            assert len(insight.strip()) > 20, f"Insight too short: {insight}"
    
    def test_clinical_recommendations_quality(self, sample_patient_data, sample_medical_summary):
        """Test that clinical recommendations are actionable and relevant."""
        agent = ResearchCorrelationAgent()
        research_analysis = agent.analyze_patient_research(
            sample_patient_data, sample_medical_summary
        )
        
        recommendations = research_analysis.clinical_recommendations
        assert len(recommendations) >= 2, "Should generate at least 2 recommendations"
        
        # Check for clinical relevance
        rec_text = " ".join(recommendations).lower()
        clinical_terms = [
            "treatment", "therapy", "monitoring", "care", "management", 
            "guideline", "consultation", "education", "approach"
        ]
        
        clinical_relevance = sum(1 for term in clinical_terms if term in rec_text)
        assert clinical_relevance >= 2, "Recommendations should be clinically relevant"
        
        # Check that recommendations are substantive
        for rec in recommendations:
            assert len(rec.strip()) > 30, f"Recommendation too short: {rec}"