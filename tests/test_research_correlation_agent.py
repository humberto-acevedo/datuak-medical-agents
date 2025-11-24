"""Tests for Research Correlation Agent."""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from src.agents.research_correlation_agent import ResearchCorrelationAgent
from src.models import (
    PatientData, MedicalSummary, ResearchAnalysis, ResearchFinding, 
    Condition, ResearchError
)
from src.utils import AuditLogger


class TestResearchCorrelationAgent:
    """Test cases for Research Correlation Agent."""
    
    @pytest.fixture
    def mock_audit_logger(self):
        """Create mock audit logger."""
        return Mock(spec=AuditLogger)
    
    @pytest.fixture
    def research_agent(self, mock_audit_logger):
        """Create research correlation agent with mocked dependencies."""
        return ResearchCorrelationAgent(audit_logger=mock_audit_logger)
    
    @pytest.fixture
    def sample_patient_data(self):
        """Create sample patient data."""
        from src.models import Demographics
        return PatientData(
            patient_id="TEST123",
            name="John Doe",
            demographics=Demographics(
                age=44,
                gender="M",
                date_of_birth="1980-01-01"
            ),
            medical_history=[],
            medications=[],
            procedures=[],
            diagnoses=[],
            raw_xml="<patient>test</patient>",
            extraction_timestamp=datetime.now()
        )
    
    @pytest.fixture
    def sample_conditions(self):
        """Create sample medical conditions."""
        return [
            Condition(
                name="Type 2 Diabetes",
                icd_10_code="E11.9",
                severity="moderate",
                confidence_score=0.9,
                status="active"
            ),
            Condition(
                name="Hypertension",
                icd_10_code="I10",
                severity="mild",
                confidence_score=0.8,
                status="active"
            ),
            Condition(
                name="Hyperlipidemia",
                icd_10_code="E78.5",
                severity="moderate",
                confidence_score=0.7,
                status="active"
            )
        ]
    
    @pytest.fixture
    def sample_medical_summary(self, sample_conditions):
        """Create sample medical summary."""
        return MedicalSummary(
            patient_id="TEST123",
            summary_text="Patient presents with diabetes, hypertension, and hyperlipidemia.",
            key_conditions=sample_conditions,
            medication_summary="Metformin, Lisinopril, Atorvastatin",
            chronological_events=[],
            risk_factors=["Metabolic syndrome", "Cardiovascular risk factors"],
            recommendations=["Lifestyle modifications", "Regular monitoring"],
            confidence_score=0.85,
            generated_timestamp=datetime.now()
        )
    
    @pytest.fixture
    def sample_research_findings(self):
        """Create sample research findings."""
        return [
            ResearchFinding(
                title="Metformin in Type 2 Diabetes: A Systematic Review",
                authors=["Smith, J.", "Johnson, A."],
                publication_date="2023-06-15",
                journal="Diabetes Care",
                doi="10.2337/dc23-0123",
                pmid="37234567",
                relevance_score=0.9,
                key_findings="Metformin reduces HbA1c by 1.5% and cardiovascular events by 25%",
                citation="Smith, J. et al. (2023). Metformin in Type 2 Diabetes. Diabetes Care.",
                abstract="Systematic review of metformin efficacy in type 2 diabetes management.",
                study_type="systematic_review",
                sample_size=12847,
                peer_reviewed=True
            ),
            ResearchFinding(
                title="ACE Inhibitors vs ARBs in Hypertension Management",
                authors=["Wilson, M.", "Davis, R."],
                publication_date="2023-08-22",
                journal="Hypertension",
                doi="10.1161/hyp.2023.456",
                relevance_score=0.8,
                key_findings="Similar cardiovascular protection with slight advantage for ACE inhibitors",
                citation="Wilson, M. et al. (2023). ACE Inhibitors vs ARBs. Hypertension.",
                study_type="RCT",
                sample_size=8934,
                peer_reviewed=True
            ),
            ResearchFinding(
                title="Statin Therapy in Hyperlipidemia: Current Evidence",
                authors=["Anderson, P.", "Miller, L."],
                publication_date="2023-04-10",
                journal="Journal of Lipid Research",
                doi="10.1194/jlr.2023.789",
                relevance_score=0.7,
                key_findings="High-intensity statin therapy reduces cardiovascular events by 30%",
                citation="Anderson, P. et al. (2023). Statin Therapy. J Lipid Res.",
                study_type="meta-analysis",
                sample_size=25000,
                peer_reviewed=True
            )
        ]
    
    def test_agent_initialization(self, mock_audit_logger):
        """Test agent initialization."""
        agent = ResearchCorrelationAgent(audit_logger=mock_audit_logger)
        
        assert agent.audit_logger == mock_audit_logger
        assert agent.research_searcher is not None
        assert agent.relevance_ranker is not None
        assert agent.max_research_papers == 20
        assert agent.min_relevance_threshold == 0.3
    
    @patch('src.agents.research_correlation_agent.ResearchSearcher')
    @patch('src.agents.research_correlation_agent.RelevanceRanker')
    def test_analyze_patient_research_success(self, mock_ranker_class, mock_searcher_class,
                                            sample_patient_data, sample_medical_summary,
                                            sample_research_findings, mock_audit_logger):
        """Test successful patient research analysis."""
        # Setup mocks
        mock_searcher = Mock()
        mock_ranker = Mock()
        mock_searcher_class.return_value = mock_searcher
        mock_ranker_class.return_value = mock_ranker
        
        mock_searcher.search_research.return_value = sample_research_findings
        mock_ranker.rank_research_findings.return_value = sample_research_findings
        mock_ranker.prioritize_by_condition_severity.return_value = sample_research_findings
        mock_ranker.get_top_findings_by_category.return_value = {
            "systematic_reviews": sample_research_findings[:1],
            "clinical_trials": sample_research_findings[1:2]
        }
        
        agent = ResearchCorrelationAgent(audit_logger=mock_audit_logger)
        agent.research_searcher = mock_searcher
        agent.relevance_ranker = mock_ranker
        
        # Execute analysis
        result = agent.analyze_patient_research(sample_patient_data, sample_medical_summary)
        
        # Verify result
        assert isinstance(result, ResearchAnalysis)
        assert result.patient_id == "TEST123"
        assert len(result.research_findings) == 3
        assert result.analysis_confidence > 0
        assert len(result.research_insights) > 0
        assert len(result.clinical_recommendations) > 0
        
        # Verify method calls
        mock_searcher.search_research.assert_called_once()
        mock_ranker.rank_research_findings.assert_called_once()
        mock_ranker.prioritize_by_condition_severity.assert_called_once()
        
        # Verify audit logging
        mock_audit_logger.log_data_access.assert_called()
    
    @patch('src.agents.research_correlation_agent.ResearchSearcher')
    def test_analyze_patient_research_search_failure(self, mock_searcher_class,
                                                   sample_patient_data, sample_medical_summary,
                                                   mock_audit_logger):
        """Test research analysis with search failure."""
        # Setup mock to raise exception
        mock_searcher = Mock()
        mock_searcher_class.return_value = mock_searcher
        mock_searcher.search_research.side_effect = Exception("Search API failed")
        
        agent = ResearchCorrelationAgent(audit_logger=mock_audit_logger)
        agent.research_searcher = mock_searcher
        
        # Execute and verify exception
        with pytest.raises(ResearchError) as exc_info:
            agent.analyze_patient_research(sample_patient_data, sample_medical_summary)
        
        assert "Research analysis failed" in str(exc_info.value)
        mock_audit_logger.log_error.assert_called_once()
    
    def test_prepare_conditions_for_research(self, research_agent, sample_conditions):
        """Test condition preparation for research."""
        # Test with high confidence conditions
        prepared = research_agent._prepare_conditions_for_research(sample_conditions)
        
        assert len(prepared) <= 10
        assert all(c.confidence_score >= 0.3 for c in prepared)
        
        # Verify sorting by severity and confidence
        assert prepared[0].confidence_score >= prepared[-1].confidence_score
    
    def test_prepare_conditions_low_confidence(self, research_agent):
        """Test condition preparation with low confidence conditions."""
        low_confidence_conditions = [
            Condition(
                name="Condition 1",
                severity="mild",
                confidence_score=0.2,
                icd_10_code="A00"
            ),
            Condition(
                name="Condition 2",
                severity="moderate",
                confidence_score=0.4,
                icd_10_code="A01"
            )
        ]
        
        prepared = research_agent._prepare_conditions_for_research(low_confidence_conditions)
        
        # Should include medium confidence when high confidence is insufficient
        assert len(prepared) >= 1
        assert any(c.confidence_score >= 0.3 for c in prepared)
    
    def test_generate_research_correlations(self, research_agent, sample_conditions, 
                                          sample_research_findings):
        """Test research correlation generation."""
        correlations = research_agent._generate_research_correlations(
            sample_conditions, sample_research_findings
        )
        
        assert isinstance(correlations, dict)
        assert len(correlations) == len(sample_conditions)
        
        # Check that diabetes condition has relevant research
        diabetes_research = correlations.get("Type 2 Diabetes", [])
        assert len(diabetes_research) > 0
        
        # Verify findings are sorted by relevance
        for condition_findings in correlations.values():
            if len(condition_findings) > 1:
                for i in range(len(condition_findings) - 1):
                    assert condition_findings[i].relevance_score >= condition_findings[i + 1].relevance_score
    
    def test_generate_research_insights(self, research_agent, sample_conditions, 
                                      sample_research_findings):
        """Test research insights generation."""
        correlations = {
            "Type 2 Diabetes": sample_research_findings[:1],
            "Hypertension": sample_research_findings[1:2],
            "Hyperlipidemia": sample_research_findings[2:3]
        }
        
        insights = research_agent._generate_research_insights(
            sample_conditions, sample_research_findings, correlations
        )
        
        assert isinstance(insights, list)
        assert len(insights) > 0
        
        # Check for expected insight types
        insight_text = " ".join(insights)
        assert "Research coverage" in insight_text
        assert "Study quality" in insight_text
        assert "Recent research" in insight_text
    
    def test_generate_clinical_recommendations(self, research_agent, sample_conditions,
                                             sample_research_findings):
        """Test clinical recommendations generation."""
        correlations = {
            "Type 2 Diabetes": sample_research_findings[:1],
            "Hypertension": sample_research_findings[1:2],
            "Hyperlipidemia": sample_research_findings[2:3]
        }
        
        recommendations = research_agent._generate_clinical_recommendations(
            sample_conditions, sample_research_findings, correlations
        )
        
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        
        # Check for expected recommendation types
        rec_text = " ".join(recommendations)
        assert any(keyword in rec_text.lower() for keyword in 
                  ["treatment", "monitoring", "care", "guideline", "education"])
    
    def test_calculate_analysis_confidence(self, research_agent, sample_research_findings):
        """Test analysis confidence calculation."""
        correlations = {
            "Type 2 Diabetes": sample_research_findings[:2],
            "Hypertension": sample_research_findings[1:3]
        }
        
        confidence = research_agent._calculate_analysis_confidence(
            sample_research_findings, correlations
        )
        
        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.5  # Should be reasonably high for good sample data
    
    def test_calculate_analysis_confidence_no_findings(self, research_agent):
        """Test confidence calculation with no findings."""
        confidence = research_agent._calculate_analysis_confidence([], {})
        assert confidence == 0.0
    
    def test_is_finding_relevant_to_condition(self, research_agent, sample_conditions,
                                            sample_research_findings):
        """Test finding relevance to condition."""
        diabetes_condition = sample_conditions[0]  # Type 2 Diabetes
        diabetes_finding = sample_research_findings[0]  # Metformin study
        
        # Should be relevant
        assert research_agent._is_finding_relevant_to_condition(
            diabetes_finding, diabetes_condition
        )
        
        # Test with unrelated condition
        unrelated_condition = Condition(
            name="Pneumonia",
            severity="moderate",
            confidence_score=0.8,
            icd_10_code="J18.9"
        )
        
        # Should not be relevant
        assert not research_agent._is_finding_relevant_to_condition(
            diabetes_finding, unrelated_condition
        )
    
    def test_get_severity_weight(self, research_agent):
        """Test severity weight calculation."""
        assert research_agent._get_severity_weight("critical") == 1.0
        assert research_agent._get_severity_weight("severe") == 0.8
        assert research_agent._get_severity_weight("moderate") == 0.6
        assert research_agent._get_severity_weight("mild") == 0.4
        assert research_agent._get_severity_weight("low") == 0.2
        assert research_agent._get_severity_weight("unknown") == 0.5
    
    def test_is_recent_study(self, research_agent):
        """Test recent study identification."""
        current_year = datetime.now().year
        
        # Recent study
        recent_date = f"{current_year - 2}-06-15"
        assert research_agent._is_recent_study(recent_date)
        
        # Old study
        old_date = f"{current_year - 10}-06-15"
        assert not research_agent._is_recent_study(old_date)
        
        # Invalid date
        assert not research_agent._is_recent_study("invalid-date")
    
    def test_extract_key_research_theme(self, research_agent, sample_research_findings):
        """Test key research theme extraction."""
        theme = research_agent._extract_key_research_theme(sample_research_findings)
        
        assert isinstance(theme, str)
        assert len(theme) > 0
        # Should extract meaningful words from titles
        assert theme != "treatment and management"  # Should find specific theme
    
    def test_research_analysis_validation(self, sample_patient_data, sample_conditions,
                                        sample_research_findings):
        """Test research analysis validation."""
        analysis = ResearchAnalysis(
            patient_id=sample_patient_data.patient_id,
            analysis_timestamp=datetime.now(),
            conditions_analyzed=sample_conditions,
            research_findings=sample_research_findings,
            condition_research_correlations={
                "Type 2 Diabetes": sample_research_findings[:1]
            },
            categorized_findings={
                "systematic_reviews": sample_research_findings[:1]
            },
            research_insights=["Test insight"],
            clinical_recommendations=["Test recommendation"],
            analysis_confidence=0.8,
            total_papers_reviewed=10,
            relevant_papers_found=3
        )
        
        errors = analysis.validate()
        assert len(errors) == 0
    
    def test_research_analysis_invalid_data(self):
        """Test research analysis with invalid data."""
        analysis = ResearchAnalysis(
            patient_id="",  # Invalid: empty
            analysis_timestamp=datetime.now(),
            conditions_analyzed=[],  # Invalid: empty
            research_findings=[],
            condition_research_correlations={},
            categorized_findings={},
            research_insights=[],
            clinical_recommendations=[],
            analysis_confidence=1.5,  # Invalid: > 1.0
            total_papers_reviewed=5,
            relevant_papers_found=10  # Invalid: > total_papers_reviewed
        )
        
        errors = analysis.validate()
        assert len(errors) >= 4  # Should have multiple validation errors
    
    def test_research_analysis_helper_methods(self, sample_patient_data, sample_conditions,
                                            sample_research_findings):
        """Test research analysis helper methods."""
        analysis = ResearchAnalysis(
            patient_id=sample_patient_data.patient_id,
            analysis_timestamp=datetime.now(),
            conditions_analyzed=sample_conditions,
            research_findings=sample_research_findings,
            condition_research_correlations={
                "Type 2 Diabetes": sample_research_findings[:1],
                "Hypertension": sample_research_findings[1:2]
            },
            categorized_findings={
                "systematic_reviews": sample_research_findings[:1],
                "clinical_trials": sample_research_findings[1:2]
            },
            research_insights=["Test insight"],
            clinical_recommendations=["Test recommendation"],
            analysis_confidence=0.8,
            total_papers_reviewed=10,
            relevant_papers_found=3
        )
        
        # Test helper methods
        top_findings = analysis.get_top_findings(limit=2)
        assert len(top_findings) == 2
        assert top_findings[0].relevance_score >= top_findings[1].relevance_score
        
        condition_research = analysis.get_condition_research("Type 2 Diabetes")
        assert len(condition_research) == 1
        
        summary = analysis.get_research_summary()
        assert isinstance(summary, dict)
        assert "total_conditions" in summary
        assert "analysis_confidence" in summary