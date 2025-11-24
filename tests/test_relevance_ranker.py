"""Tests for Relevance Ranker functionality."""
import pytest
from datetime import datetime
from unittest.mock import Mock

from src.agents.relevance_ranker import RelevanceRanker
from src.models import ResearchFinding, Condition


class TestRelevanceRanker:
    """Test cases for Relevance Ranker."""
    
    @pytest.fixture
    def relevance_ranker(self):
        """Create relevance ranker instance."""
        return RelevanceRanker()
    
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
                severity="severe",
                confidence_score=0.8,
                status="active"
            ),
            Condition(
                name="Hyperlipidemia",
                icd_10_code="E78.5",
                severity="mild",
                confidence_score=0.7,
                status="active"
            )
        ]
    
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
                relevance_score=0.7,
                key_findings="Metformin reduces HbA1c by 1.5%",
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
                relevance_score=0.6,
                key_findings="Similar cardiovascular protection",
                citation="Wilson, M. et al. (2023). ACE Inhibitors vs ARBs. Hypertension.",
                study_type="RCT",
                sample_size=8934,
                peer_reviewed=True
            ),
            ResearchFinding(
                title="Statin Therapy in Hyperlipidemia: Current Evidence",
                authors=["Anderson, P.", "Miller, L."],
                publication_date="2020-04-10",
                journal="Journal of Lipid Research",
                doi="10.1194/jlr.2020.789",
                relevance_score=0.5,
                key_findings="High-intensity statin therapy reduces cardiovascular events",
                citation="Anderson, P. et al. (2020). Statin Therapy. J Lipid Res.",
                study_type="meta-analysis",
                sample_size=25000,
                peer_reviewed=True
            ),
            ResearchFinding(
                title="Unrelated Cancer Research Study",
                authors=["Brown, K."],
                publication_date="2023-01-01",
                journal="Cancer Research",
                relevance_score=0.2,
                key_findings="Cancer treatment outcomes",
                citation="Brown, K. (2023). Cancer Research. Cancer Res.",
                study_type="observational",
                sample_size=500,
                peer_reviewed=True
            )
        ]
    
    def test_ranker_initialization(self, relevance_ranker):
        """Test relevance ranker initialization."""
        assert relevance_ranker.condition_weights is not None
        assert relevance_ranker.study_type_weights is not None
        assert relevance_ranker.journal_impact_scores is not None
        assert relevance_ranker.medical_terminology is not None
        
        # Check some expected weights
        assert "diabetes" in relevance_ranker.condition_weights
        assert "meta-analysis" in relevance_ranker.study_type_weights
        assert "new england journal of medicine" in relevance_ranker.journal_impact_scores
    
    def test_rank_research_findings(self, relevance_ranker, sample_conditions, 
                                  sample_research_findings):
        """Test research findings ranking."""
        ranked_findings = relevance_ranker.rank_research_findings(
            sample_research_findings, sample_conditions
        )
        
        assert len(ranked_findings) == len(sample_research_findings)
        
        # Check that findings are sorted by relevance score (descending)
        for i in range(len(ranked_findings) - 1):
            assert ranked_findings[i].relevance_score >= ranked_findings[i + 1].relevance_score
        
        # Check that relevance scores have been enhanced
        diabetes_finding = next(f for f in ranked_findings if "diabetes" in f.title.lower())
        assert diabetes_finding.relevance_score > 0.7  # Should be enhanced
    
    def test_prioritize_by_condition_severity(self, relevance_ranker, sample_conditions,
                                            sample_research_findings):
        """Test prioritization by condition severity."""
        prioritized_findings = relevance_ranker.prioritize_by_condition_severity(
            sample_research_findings.copy(), sample_conditions
        )
        
        assert len(prioritized_findings) == len(sample_research_findings)
        
        # Hypertension finding should get severity bonus (severe condition)
        hypertension_finding = next(f for f in prioritized_findings if "hypertension" in f.title.lower())
        original_hypertension = next(f for f in sample_research_findings if "hypertension" in f.title.lower())
        
        # Should have enhanced score due to severe condition
        assert hypertension_finding.relevance_score >= original_hypertension.relevance_score
    
    def test_get_top_findings_by_category(self, relevance_ranker, sample_research_findings):
        """Test categorization of findings by study type."""
        categorized = relevance_ranker.get_top_findings_by_category(
            sample_research_findings, limit_per_category=2
        )
        
        assert isinstance(categorized, dict)
        assert len(categorized) > 0
        
        # Check expected categories
        expected_categories = ["systematic_reviews", "clinical_trials", "observational"]
        for category in expected_categories:
            if category in categorized:
                assert len(categorized[category]) <= 2
                # Check that findings in category are sorted by relevance
                category_findings = categorized[category]
                for i in range(len(category_findings) - 1):
                    assert category_findings[i].relevance_score >= category_findings[i + 1].relevance_score
    
    def test_calculate_enhanced_relevance_score(self, relevance_ranker, sample_conditions):
        """Test enhanced relevance score calculation."""
        # High relevance finding
        high_relevance_finding = ResearchFinding(
            title="Type 2 Diabetes Management: Meta-Analysis",
            authors=["Smith, J."],
            publication_date="2023-06-15",
            journal="New England Journal of Medicine",
            relevance_score=0.8,
            key_findings="Diabetes management strategies",
            citation="Smith, J. (2023). Diabetes Management. NEJM.",
            study_type="meta-analysis",
            sample_size=50000,
            peer_reviewed=True
        )
        
        enhanced_score = relevance_ranker._calculate_enhanced_relevance_score(
            high_relevance_finding, sample_conditions
        )
        
        assert 0.0 <= enhanced_score <= 1.0
        assert enhanced_score > high_relevance_finding.relevance_score
    
    def test_calculate_condition_matching_score(self, relevance_ranker, sample_conditions):
        """Test condition matching score calculation."""
        # Perfect match finding
        perfect_match = ResearchFinding(
            title="Type 2 Diabetes Treatment Guidelines",
            authors=["Smith, J."],
            publication_date="2023-01-01",
            journal="Test Journal",
            key_findings="Type 2 diabetes management recommendations",
            citation="Test citation",
            abstract="Comprehensive review of type 2 diabetes treatment approaches"
        )
        
        score = relevance_ranker._calculate_condition_matching_score(
            perfect_match, sample_conditions
        )
        
        assert score > 0.5  # Should be high for perfect match
        
        # No match finding
        no_match = ResearchFinding(
            title="Unrelated Medical Research",
            authors=["Smith, J."],
            publication_date="2023-01-01",
            journal="Test Journal",
            key_findings="Unrelated medical findings",
            citation="Test citation"
        )
        
        score = relevance_ranker._calculate_condition_matching_score(
            no_match, sample_conditions
        )
        
        assert score < 0.2  # Should be low for no match
    
    def test_calculate_study_quality_score(self, relevance_ranker):
        """Test study quality score calculation."""
        # High quality study
        high_quality = ResearchFinding(
            title="Test Study",
            authors=["Smith, J."],
            publication_date="2023-01-01",
            journal="Test Journal",
            key_findings="Test findings",
            citation="Test citation",
            study_type="meta-analysis",
            peer_reviewed=True,
            doi="10.1234/test"
        )
        
        score = relevance_ranker._calculate_study_quality_score(high_quality)
        assert score > 0.8  # Should be high for meta-analysis + peer reviewed + DOI
        
        # Low quality study
        low_quality = ResearchFinding(
            title="Test Study",
            authors=["Smith, J."],
            publication_date="2023-01-01",
            journal="Test Journal",
            key_findings="Test findings",
            citation="Test citation",
            study_type="case_study",
            peer_reviewed=False
        )
        
        score = relevance_ranker._calculate_study_quality_score(low_quality)
        assert score < 0.6  # Should be lower for case study + not peer reviewed
    
    def test_calculate_recency_score(self, relevance_ranker):
        """Test recency score calculation."""
        current_year = datetime.now().year
        
        # Very recent study
        recent_score = relevance_ranker._calculate_recency_score(f"{current_year}-01-01")
        assert recent_score == 1.0
        
        # Moderately recent study
        moderate_score = relevance_ranker._calculate_recency_score(f"{current_year - 3}-01-01")
        assert 0.6 <= moderate_score <= 1.0
        
        # Old study
        old_score = relevance_ranker._calculate_recency_score(f"{current_year - 15}-01-01")
        assert old_score == 0.4
        
        # Invalid date
        invalid_score = relevance_ranker._calculate_recency_score("invalid-date")
        assert invalid_score == 0.5
    
    def test_calculate_journal_impact_score(self, relevance_ranker):
        """Test journal impact score calculation."""
        # High impact journal
        high_impact_score = relevance_ranker._calculate_journal_impact_score(
            "New England Journal of Medicine"
        )
        assert high_impact_score == 1.0
        
        # Medium impact journal
        medium_impact_score = relevance_ranker._calculate_journal_impact_score(
            "Journal of Clinical Medicine"
        )
        assert medium_impact_score >= 0.5
        
        # Unknown journal
        unknown_score = relevance_ranker._calculate_journal_impact_score(
            "Unknown Medical Journal"
        )
        assert unknown_score == 0.5
    
    def test_calculate_sample_size_score(self, relevance_ranker):
        """Test sample size score calculation."""
        # Large sample size
        large_score = relevance_ranker._calculate_sample_size_score(15000)
        assert large_score == 1.0
        
        # Medium sample size
        medium_score = relevance_ranker._calculate_sample_size_score(2000)
        assert 0.7 <= medium_score <= 0.9
        
        # Small sample size
        small_score = relevance_ranker._calculate_sample_size_score(50)
        assert small_score == 0.4
        
        # No sample size
        no_size_score = relevance_ranker._calculate_sample_size_score(None)
        assert no_size_score == 0.3
    
    def test_apply_diversity_filtering(self, relevance_ranker, sample_conditions):
        """Test diversity filtering application."""
        # Create many similar findings
        many_findings = []
        for i in range(15):
            finding = ResearchFinding(
                title=f"Diabetes Study {i}",
                authors=["Smith, J."],
                publication_date="2023-01-01",
                journal="Test Journal",
                relevance_score=0.8 - (i * 0.01),  # Decreasing scores
                key_findings="Diabetes research",
                citation="Test citation",
                study_type="RCT" if i < 8 else "observational"
            )
            many_findings.append(finding)
        
        diverse_findings = relevance_ranker._apply_diversity_filtering(
            many_findings, sample_conditions
        )
        
        # Should limit results and ensure diversity
        assert len(diverse_findings) <= 20
        
        # Check study type diversity (no more than 3 per type)
        study_type_counts = {}
        for finding in diverse_findings:
            study_type = relevance_ranker._categorize_study_type(finding.study_type)
            study_type_counts[study_type] = study_type_counts.get(study_type, 0) + 1
        
        for count in study_type_counts.values():
            assert count <= 3
    
    def test_get_severity_score(self, relevance_ranker):
        """Test severity score conversion."""
        assert relevance_ranker._get_severity_score("critical") == 1.0
        assert relevance_ranker._get_severity_score("severe") == 0.8
        assert relevance_ranker._get_severity_score("moderate") == 0.6
        assert relevance_ranker._get_severity_score("mild") == 0.4
        assert relevance_ranker._get_severity_score("low") == 0.2
        assert relevance_ranker._get_severity_score("unknown") == 0.5
    
    def test_finding_relates_to_condition(self, relevance_ranker):
        """Test finding-condition relationship detection."""
        diabetes_finding = ResearchFinding(
            title="Type 2 Diabetes Management Study",
            authors=["Smith, J."],
            publication_date="2023-01-01",
            journal="Test Journal",
            key_findings="Diabetes treatment outcomes",
            citation="Test citation",
            abstract="Study of diabetes management approaches"
        )
        
        # Should relate to diabetes
        assert relevance_ranker._finding_relates_to_condition(
            diabetes_finding, "type 2 diabetes"
        )
        
        # Should not relate to unrelated condition
        assert not relevance_ranker._finding_relates_to_condition(
            diabetes_finding, "pneumonia"
        )
    
    def test_categorize_study_type(self, relevance_ranker):
        """Test study type categorization."""
        test_cases = [
            ("meta-analysis", "systematic_reviews"),
            ("systematic review", "systematic_reviews"),
            ("randomized controlled trial", "clinical_trials"),
            ("RCT", "clinical_trials"),
            ("cohort study", "observational"),
            ("longitudinal study", "observational"),
            ("case study", "case_studies"),
            ("case report", "case_studies"),
            ("unknown type", "other"),
            (None, "other")
        ]
        
        for study_type, expected_category in test_cases:
            category = relevance_ranker._categorize_study_type(study_type)
            assert category == expected_category
    
    def test_extract_conditions_from_finding(self, relevance_ranker, sample_conditions):
        """Test condition extraction from findings."""
        multi_condition_finding = ResearchFinding(
            title="Diabetes and Hypertension Comorbidity Study",
            authors=["Smith, J."],
            publication_date="2023-01-01",
            journal="Test Journal",
            key_findings="Study of diabetes and hypertension interactions",
            citation="Test citation"
        )
        
        related_conditions = relevance_ranker._extract_conditions_from_finding(
            multi_condition_finding, sample_conditions
        )
        
        assert "type 2 diabetes" in related_conditions
        assert "hypertension" in related_conditions
        assert len(related_conditions) >= 2
    
    def test_load_configuration_data(self, relevance_ranker):
        """Test that configuration data is properly loaded."""
        # Test condition weights
        condition_weights = relevance_ranker._load_condition_weights()
        assert isinstance(condition_weights, dict)
        assert "diabetes" in condition_weights
        assert condition_weights["cancer"] == 1.0  # Highest weight
        
        # Test study type weights
        study_weights = relevance_ranker._load_study_type_weights()
        assert isinstance(study_weights, dict)
        assert study_weights["meta-analysis"] == 1.0  # Highest quality
        assert study_weights["case_study"] < study_weights["rct"]
        
        # Test journal impact scores
        journal_scores = relevance_ranker._load_journal_impact_scores()
        assert isinstance(journal_scores, dict)
        assert journal_scores["new england journal of medicine"] == 1.0
        
        # Test medical terminology
        terminology = relevance_ranker._load_medical_terminology()
        assert isinstance(terminology, dict)
        assert "diabetes" in terminology
        assert isinstance(terminology["diabetes"], list)