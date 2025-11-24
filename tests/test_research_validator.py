"""Tests for research validation and citation verification system."""
import pytest
from unittest.mock import Mock
from datetime import datetime

from src.quality.research_validator import ResearchValidator, CitationValidationResult
from src.quality.hallucination_detector import ValidationSeverity, ValidationType


class TestResearchValidator:
    """Test ResearchValidator class."""
    
    @pytest.fixture
    def validator(self):
        """Create research validator."""
        return ResearchValidator()
    
    @pytest.fixture
    def sample_research_findings(self):
        """Create sample research findings for testing."""
        return [
            {
                "title": "Hypertension Management in Primary Care: A Systematic Review",
                "authors": ["Smith, J.A.", "Johnson, M.B.", "Brown, K.C."],
                "journal": "New England Journal of Medicine",
                "publication_year": 2023,
                "doi": "10.1056/NEJMra2301234",
                "pubmed_id": "12345678",
                "study_type": "systematic_review",
                "relevance_score": 0.92,
                "abstract": "This systematic review examines current approaches to hypertension management in primary care settings."
            },
            {
                "title": "Diabetes Treatment Guidelines Update",
                "authors": ["Wilson, A.D.", "Davis, L.M."],
                "journal": "Diabetes Care",
                "publication_year": 2022,
                "doi": "10.2337/dc22-1234",
                "study_type": "expert_opinion",
                "relevance_score": 0.85
            },
            {
                "title": "Cardiovascular Risk Assessment in Elderly Patients",
                "authors": ["Taylor, R.S."],
                "journal": "Journal of the American College of Cardiology",
                "publication_year": 2021,
                "study_type": "cohort_study",
                "relevance_score": 0.78
            }
        ]
    
    def test_validator_initialization(self, validator):
        """Test validator initialization."""
        assert validator.audit_logger is None  # No audit logger provided
        assert len(validator.reputable_journals) > 10
        assert len(validator.study_type_hierarchy) > 5
        assert len(validator.predatory_patterns) > 0
    
    def test_validate_research_findings_valid(self, validator, sample_research_findings):
        """Test validation of valid research findings."""
        patient_conditions = ["hypertension", "diabetes"]
        
        issues = validator.validate_research_findings(sample_research_findings, patient_conditions)
        
        # Should have minimal issues for valid research
        critical_issues = [issue for issue in issues if issue.severity == ValidationSeverity.CRITICAL]
        error_issues = [issue for issue in issues if issue.severity == ValidationSeverity.ERROR]
        
        assert len(critical_issues) == 0, "Valid research should not have critical issues"
        assert len(error_issues) == 0, "Valid research should not have error-level issues"
    
    def test_validate_research_findings_empty(self, validator):
        """Test validation with empty research findings."""
        issues = validator.validate_research_findings([], ["hypertension"])
        
        # Should detect missing research
        assert len(issues) > 0
        completeness_issues = [issue for issue in issues 
                             if issue.validation_type == ValidationType.COMPLETENESS]
        assert len(completeness_issues) > 0
    
    def test_validate_title_valid(self, validator):
        """Test title validation with valid titles."""
        valid_titles = [
            "Hypertension Management in Primary Care: A Systematic Review",
            "Effects of ACE Inhibitors on Cardiovascular Outcomes",
            "Diabetes Prevention Through Lifestyle Interventions"
        ]
        
        for title in valid_titles:
            issues = validator._validate_title(title, 0)
            # Should have no issues for valid titles
            assert len(issues) == 0, f"Valid title should not have issues: {title}"
    
    def test_validate_title_invalid(self, validator):
        """Test title validation with invalid titles."""
        invalid_titles = [
            "",  # Empty
            "A study",  # Too short
            "Research paper on",  # Generic
            "Untitled study",  # Untitled
            "123"  # Just numbers
        ]
        
        for title in invalid_titles:
            issues = validator._validate_title(title, 0)
            assert len(issues) > 0, f"Invalid title should have issues: {title}"
    
    def test_validate_authors_valid(self, validator):
        """Test author validation with valid authors."""
        valid_authors = [
            ["Smith, J.A.", "Johnson, M.B."],
            ["Wilson, A.", "Davis, L.", "Brown, K."],
            ["Taylor, Robert S."]
        ]
        
        for authors in valid_authors:
            issues = validator._validate_authors(authors, 0)
            # Should have minimal issues for valid authors
            error_issues = [issue for issue in issues 
                          if issue.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]]
            assert len(error_issues) == 0, f"Valid authors should not have error-level issues: {authors}"
    
    def test_validate_authors_invalid(self, validator):
        """Test author validation with invalid authors."""
        invalid_authors = [
            [],  # Empty
            [""],  # Empty author name
            ["A"],  # Too short
            ["Author " + str(i) for i in range(25)]  # Too many authors
        ]
        
        for authors in invalid_authors:
            issues = validator._validate_authors(authors, 0)
            assert len(issues) > 0, f"Invalid authors should have issues: {authors}"
    
    def test_validate_journal_reputable(self, validator):
        """Test journal validation with reputable journals."""
        reputable_journals = [
            "New England Journal of Medicine",
            "The Lancet",
            "JAMA",
            "Nature Medicine",
            "BMJ"
        ]
        
        for journal in reputable_journals:
            issues = validator._validate_journal(journal, 0)
            # Reputable journals should have no issues
            warning_issues = [issue for issue in issues 
                            if issue.severity in [ValidationSeverity.WARNING, ValidationSeverity.ERROR]]
            assert len(warning_issues) == 0, f"Reputable journal should not have warning-level issues: {journal}"
    
    def test_validate_journal_predatory(self, validator):
        """Test journal validation with predatory journal patterns."""
        predatory_journals = [
            "International Journal of Research in Medicine",
            "Global Journal of Science and Technology",
            "World Journal of Medical Research",
            "American Research Journal of Medicine"
        ]
        
        for journal in predatory_journals:
            issues = validator._validate_journal(journal, 0)
            # Should detect predatory patterns
            predatory_issues = [issue for issue in issues if "predatory" in issue.description.lower()]
            assert len(predatory_issues) > 0, f"Should detect predatory pattern: {journal}"
    
    def test_validate_journal_unknown(self, validator):
        """Test journal validation with unknown journals."""
        unknown_journals = [
            "Some Unknown Medical Journal",
            "Local Hospital Newsletter",
            "Regional Medical Review"
        ]
        
        for journal in unknown_journals:
            issues = validator._validate_journal(journal, 0)
            # Should note unknown journal
            unknown_issues = [issue for issue in issues if "unknown" in issue.description.lower()]
            assert len(unknown_issues) > 0, f"Should note unknown journal: {journal}"
    
    def test_validate_publication_year_valid(self, validator):
        """Test publication year validation with valid years."""
        current_year = datetime.now().year
        valid_years = [current_year, current_year - 1, current_year - 5, 2000, 1990]
        
        for year in valid_years:
            issues = validator._validate_publication_year(year, 0)
            # Should have minimal issues for reasonable years
            error_issues = [issue for issue in issues 
                          if issue.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]]
            assert len(error_issues) == 0, f"Valid year should not have error-level issues: {year}"
    
    def test_validate_publication_year_invalid(self, validator):
        """Test publication year validation with invalid years."""
        current_year = datetime.now().year
        invalid_years = [
            None,  # Missing
            current_year + 1,  # Future
            1800,  # Too old
            "not_a_year",  # Invalid format
            ""  # Empty
        ]
        
        for year in invalid_years:
            issues = validator._validate_publication_year(year, 0)
            assert len(issues) > 0, f"Invalid year should have issues: {year}"
    
    def test_validate_doi_valid(self, validator):
        """Test DOI validation with valid DOIs."""
        valid_dois = [
            "10.1056/NEJMra2301234",
            "10.2337/dc22-1234",
            "10.1001/jama.2023.12345",
            "10.1016/j.cell.2023.01.001"
        ]
        
        for doi in valid_dois:
            issues = validator._validate_doi(doi, 0)
            assert len(issues) == 0, f"Valid DOI should not have issues: {doi}"
    
    def test_validate_doi_invalid(self, validator):
        """Test DOI validation with invalid DOIs."""
        invalid_dois = [
            "not_a_doi",
            "10.invalid",
            "doi:10.1234/invalid",
            "10.1234",  # Missing suffix
            ""  # Empty
        ]
        
        for doi in invalid_dois:
            issues = validator._validate_doi(doi, 0)
            assert len(issues) > 0, f"Invalid DOI should have issues: {doi}"
    
    def test_validate_pubmed_id_valid(self, validator):
        """Test PubMed ID validation with valid IDs."""
        valid_ids = ["12345678", "87654321", "11111111"]
        
        for pmid in valid_ids:
            issues = validator._validate_pubmed_id(pmid, 0)
            assert len(issues) == 0, f"Valid PubMed ID should not have issues: {pmid}"
    
    def test_validate_pubmed_id_invalid(self, validator):
        """Test PubMed ID validation with invalid IDs."""
        invalid_ids = [
            "1234567",  # Too short
            "123456789",  # Too long
            "abcd1234",  # Contains letters
            "",  # Empty
            "12-34-56"  # Contains hyphens
        ]
        
        for pmid in invalid_ids:
            issues = validator._validate_pubmed_id(pmid, 0)
            assert len(issues) > 0, f"Invalid PubMed ID should have issues: {pmid}"
    
    def test_validate_relevance_high(self, validator):
        """Test relevance validation with high relevance."""
        finding = {
            "title": "Hypertension Management in Primary Care",
            "abstract": "This study examines hypertension treatment approaches and diabetes management.",
            "relevance_score": 0.9
        }
        
        patient_conditions = ["hypertension", "diabetes"]
        
        issues = validator._validate_relevance(finding, patient_conditions, 0)
        
        # Should have no relevance issues
        relevance_issues = [issue for issue in issues if "relevance" in issue.description.lower()]
        assert len(relevance_issues) == 0, "High relevance should not have issues"
    
    def test_validate_relevance_low(self, validator):
        """Test relevance validation with low relevance."""
        finding = {
            "title": "Cancer Treatment Protocols",
            "abstract": "This study examines cancer treatment approaches.",
            "relevance_score": 0.1
        }
        
        patient_conditions = ["hypertension", "diabetes"]
        
        issues = validator._validate_relevance(finding, patient_conditions, 0)
        
        # Should detect low relevance
        relevance_issues = [issue for issue in issues if "relevance" in issue.description.lower()]
        assert len(relevance_issues) > 0, "Low relevance should be detected"
    
    def test_validate_study_type_valid(self, validator):
        """Test study type validation with valid types."""
        valid_types = [
            "systematic_review",
            "meta_analysis", 
            "randomized_controlled_trial",
            "cohort_study",
            "case_control_study"
        ]
        
        for study_type in valid_types:
            issues = validator._validate_study_type(study_type, 0)
            assert len(issues) == 0, f"Valid study type should not have issues: {study_type}"
    
    def test_validate_study_type_unknown(self, validator):
        """Test study type validation with unknown types."""
        unknown_types = [
            "unknown_study_type",
            "invalid_type",
            "made_up_study"
        ]
        
        for study_type in unknown_types:
            issues = validator._validate_study_type(study_type, 0)
            assert len(issues) > 0, f"Unknown study type should have issues: {study_type}"
    
    def test_validate_research_quality_sufficient(self, validator, sample_research_findings):
        """Test research quality validation with sufficient findings."""
        issues = validator._validate_research_quality(sample_research_findings)
        
        # Should have minimal quality issues for good research set
        quality_issues = [issue for issue in issues 
                         if issue.severity in [ValidationSeverity.WARNING, ValidationSeverity.ERROR]]
        assert len(quality_issues) == 0, "Sufficient research should not have quality warnings"
    
    def test_validate_research_quality_insufficient(self, validator):
        """Test research quality validation with insufficient findings."""
        limited_findings = [
            {
                "title": "Single Study",
                "authors": ["Author, A."],
                "journal": "Same Journal",
                "publication_year": 2023
            },
            {
                "title": "Another Study",
                "authors": ["Author, B."],
                "journal": "Same Journal",
                "publication_year": 2023
            }
        ]
        
        issues = validator._validate_research_quality(limited_findings)
        
        # Should detect quality issues
        assert len(issues) > 0, "Limited research should have quality issues"
    
    def test_calculate_research_credibility_score_high(self, validator, sample_research_findings):
        """Test credibility score calculation with high-quality research."""
        score = validator.calculate_research_credibility_score(sample_research_findings)
        
        # Should have high credibility score for quality research
        assert score > 0.7, f"High-quality research should have high credibility score: {score}"
    
    def test_calculate_research_credibility_score_low(self, validator):
        """Test credibility score calculation with low-quality research."""
        low_quality_findings = [
            {
                "title": "Questionable Study",
                "authors": ["Unknown, A."],
                "journal": "Predatory Journal of Research",
                "publication_year": 1990,
                "study_type": "case_report",
                "relevance_score": 0.2
            }
        ]
        
        score = validator.calculate_research_credibility_score(low_quality_findings)
        
        # Should have low credibility score
        assert score < 0.5, f"Low-quality research should have low credibility score: {score}"
    
    def test_calculate_research_credibility_score_empty(self, validator):
        """Test credibility score calculation with empty findings."""
        score = validator.calculate_research_credibility_score([])
        assert score == 0.0, "Empty research should have zero credibility score"
    
    def test_get_research_quality_metrics_comprehensive(self, validator, sample_research_findings):
        """Test comprehensive research quality metrics."""
        metrics = validator.get_research_quality_metrics(sample_research_findings)
        
        # Check all expected metrics are present
        expected_metrics = [
            "total_findings", "credibility_score", "journal_diversity",
            "year_range", "tier1_journals", "tier2_journals", "tier3_journals",
            "unknown_journals", "average_relevance", "recent_studies", "high_evidence_studies"
        ]
        
        for metric in expected_metrics:
            assert metric in metrics, f"Missing metric: {metric}"
        
        # Check metric values make sense
        assert metrics["total_findings"] == len(sample_research_findings)
        assert 0 <= metrics["credibility_score"] <= 1
        assert metrics["journal_diversity"] > 0
        assert metrics["tier1_journals"] > 0  # Sample has NEJM
        assert metrics["average_relevance"] > 0
    
    def test_get_research_quality_metrics_empty(self, validator):
        """Test research quality metrics with empty findings."""
        metrics = validator.get_research_quality_metrics([])
        
        # All metrics should be zero for empty research
        assert metrics["total_findings"] == 0
        assert metrics["credibility_score"] == 0.0
        assert metrics["journal_diversity"] == 0
        assert metrics["average_relevance"] == 0.0


class TestResearchValidatorIntegration:
    """Test research validator integration scenarios."""
    
    def test_comprehensive_research_validation(self):
        """Test complete research validation workflow."""
        validator = ResearchValidator()
        
        # Create comprehensive test data with various quality levels
        research_findings = [
            # High quality
            {
                "title": "Hypertension Management: A Comprehensive Systematic Review and Meta-Analysis",
                "authors": ["Smith, J.A.", "Johnson, M.B.", "Brown, K.C.", "Wilson, D.E."],
                "journal": "New England Journal of Medicine",
                "publication_year": 2023,
                "doi": "10.1056/NEJMra2301234",
                "pubmed_id": "12345678",
                "study_type": "systematic_review",
                "relevance_score": 0.95,
                "abstract": "Comprehensive review of hypertension management strategies in primary care."
            },
            # Medium quality
            {
                "title": "Diabetes Treatment Outcomes in Community Settings",
                "authors": ["Davis, L.M.", "Taylor, R.S."],
                "journal": "Diabetes Care",
                "publication_year": 2022,
                "study_type": "cohort_study",
                "relevance_score": 0.82
            },
            # Lower quality
            {
                "title": "Case Report: Unusual Presentation of Hypertension",
                "authors": ["Unknown, A."],
                "journal": "Local Medical Journal",
                "publication_year": 2020,
                "study_type": "case_report",
                "relevance_score": 0.65
            },
            # Problematic
            {
                "title": "Research on Medicine",
                "authors": [],
                "journal": "International Journal of Research in Global Medicine",
                "publication_year": 2025,  # Future year
                "study_type": "unknown_type",
                "relevance_score": 0.1
            }
        ]
        
        patient_conditions = ["hypertension", "diabetes"]
        
        # Run comprehensive validation
        issues = validator.validate_research_findings(research_findings, patient_conditions)
        
        # Should detect various types of issues
        assert len(issues) > 5, "Should detect multiple validation issues"
        
        # Check for different types of issues
        issue_types = set(issue.validation_type for issue in issues)
        assert len(issue_types) > 2, "Should have multiple types of validation issues"
        
        # Check for different severity levels
        severities = set(issue.severity for issue in issues)
        assert len(severities) > 1, "Should have multiple severity levels"
        
        # Calculate quality metrics
        metrics = validator.get_research_quality_metrics(research_findings)
        credibility_score = validator.calculate_research_credibility_score(research_findings)
        
        # Verify metrics
        assert metrics["total_findings"] == 4
        assert metrics["tier1_journals"] == 1  # NEJM
        assert metrics["tier2_journals"] == 1  # Diabetes Care
        assert metrics["unknown_journals"] == 2  # Local and predatory journals
        assert 0 < credibility_score < 1  # Mixed quality should give moderate score
        
        # Should detect future publication year
        future_year_issues = [issue for issue in issues if "future" in issue.description.lower()]
        assert len(future_year_issues) > 0, "Should detect future publication year"
        
        # Should detect predatory journal pattern
        predatory_issues = [issue for issue in issues if "predatory" in issue.description.lower()]
        assert len(predatory_issues) > 0, "Should detect predatory journal pattern"
        
        # Should detect missing authors
        author_issues = [issue for issue in issues if "author" in issue.field_name.lower()]
        assert len(author_issues) > 0, "Should detect missing authors"
    
    def test_research_validation_with_audit_logging(self):
        """Test research validation with audit logging."""
        mock_audit_logger = Mock()
        validator = ResearchValidator(audit_logger=mock_audit_logger)
        
        research_findings = [
            {
                "title": "Test Study",
                "authors": ["Test, A."],
                "journal": "Test Journal",
                "publication_year": 2023
            }
        ]
        
        validator.validate_research_findings(research_findings, ["test_condition"])
        
        # Audit logger should be available but not necessarily called
        # (depends on implementation details)
        assert validator.audit_logger is mock_audit_logger