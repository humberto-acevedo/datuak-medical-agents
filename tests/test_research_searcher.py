"""Unit tests for ResearchSearcher."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import asyncio
import httpx

from src.agents.research_searcher import ResearchSearcher
from src.models.exceptions import ResearchError


class TestResearchSearcher:
    """Test ResearchSearcher functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.searcher = ResearchSearcher(max_results_per_condition=5, timeout_seconds=10)
    
    def test_initialization(self):
        """Test research searcher initialization."""
        searcher = ResearchSearcher(
            pubmed_api_key="test_key",
            max_results_per_condition=10,
            timeout_seconds=30
        )
        
        assert searcher.pubmed_api_key == "test_key"
        assert searcher.max_results_per_condition == 10
        assert searcher.timeout_seconds == 30
        assert searcher.search_params['api_key'] == "test_key"
    
    def test_build_search_query(self):
        """Test search query building."""
        # Test basic condition
        query = self.searcher._build_search_query("Hypertension")
        assert '"Hypertension"[Title/Abstract]' in query
        assert 'hypertension OR "blood pressure"' in query
        
        # Test diabetes condition
        query = self.searcher._build_search_query("Type 2 Diabetes")
        assert '"Type 2 Diabetes"[Title/Abstract]' in query
        assert 'diabetes OR diabetic' in query
        
        # Test cardiac condition
        query = self.searcher._build_search_query("Heart Disease")
        assert '"Heart Disease"[Title/Abstract]' in query
        assert 'cardiac OR cardiovascular' in query
        
        # Test date filter
        assert 'Date - Publication' in query
    
    def test_extract_authors(self):
        """Test author extraction from PubMed data."""
        # Test with dict format
        authors_data = [
            {'name': 'Smith J'},
            {'name': 'Jones M'},
            {'name': 'Brown K'}
        ]
        
        authors = self.searcher._extract_authors(authors_data)
        assert authors == ['Smith J', 'Jones M', 'Brown K']
        
        # Test with string format
        authors_data = ['Smith J', 'Jones M']
        authors = self.searcher._extract_authors(authors_data)
        assert authors == ['Smith J', 'Jones M']
        
        # Test empty data
        authors = self.searcher._extract_authors([])
        assert authors == ['Unknown Author']
    
    def test_extract_publication_date(self):
        """Test publication date extraction."""
        # Test with pubdate
        paper_info = {'pubdate': '2023 Jan 15'}
        date = self.searcher._extract_publication_date(paper_info)
        assert date == '2023 Jan 15'
        
        # Test with epubdate
        paper_info = {'epubdate': '2023/01/15'}
        date = self.searcher._extract_publication_date(paper_info)
        assert date == '2023/01/15'
        
        # Test with no date
        paper_info = {}
        date = self.searcher._extract_publication_date(paper_info)
        assert date == 'Unknown Date'
    
    def test_extract_doi(self):
        """Test DOI extraction."""
        # Test with doi field
        paper_info = {'doi': '10.1234/example.doi'}
        doi = self.searcher._extract_doi(paper_info)
        assert doi == '10.1234/example.doi'
        
        # Test with doi: prefix
        paper_info = {'elocationid': 'doi:10.1234/example.doi'}
        doi = self.searcher._extract_doi(paper_info)
        assert doi == '10.1234/example.doi'
        
        # Test with no DOI
        paper_info = {}
        doi = self.searcher._extract_doi(paper_info)
        assert doi is None
    
    def test_calculate_relevance_score(self):
        """Test relevance score calculation."""
        condition = "Type 2 Diabetes"
        
        # High relevance paper
        paper_info = {
            'title': 'Type 2 Diabetes Management: A Meta-Analysis',
            'pubdate': '2023 Jan',
            'fulljournalname': 'New England Journal of Medicine'
        }
        
        score = self.searcher._calculate_relevance_score(paper_info, condition)
        assert score > 0.7  # Should be high relevance
        
        # Low relevance paper
        paper_info = {
            'title': 'Unrelated Medical Topic',
            'pubdate': '2010 Jan',
            'fulljournalname': 'Unknown Journal'
        }
        
        score = self.searcher._calculate_relevance_score(paper_info, condition)
        assert score < 0.3  # Should be low relevance
    
    def test_determine_study_type(self):
        """Test study type determination."""
        test_cases = [
            ('Meta-analysis of diabetes treatments', 'meta-analysis'),
            ('Systematic review of hypertension management', 'systematic_review'),
            ('Randomized controlled trial of new drug', 'RCT'),
            ('Clinical trial results', 'clinical_trial'),
            ('Cohort study of heart disease', 'observational'),
            ('General medical research', 'other')
        ]
        
        for title, expected_type in test_cases:
            paper_info = {'title': title}
            study_type = self.searcher._determine_study_type(paper_info)
            assert study_type == expected_type, f"Failed for title: {title}"
    
    def test_format_citation(self):
        """Test citation formatting."""
        # Single author
        citation = self.searcher._format_citation(
            ['Smith J'], 
            'Test Study', 
            'Test Journal', 
            '2023 Jan'
        )
        assert 'Smith J. Test Study. Test Journal. 2023.' == citation
        
        # Multiple authors
        citation = self.searcher._format_citation(
            ['Smith J', 'Jones M', 'Brown K'], 
            'Test Study', 
            'Test Journal', 
            '2023 Jan'
        )
        assert 'Smith J, Jones M, and Brown K. Test Study. Test Journal. 2023.' == citation
        
        # Many authors (et al.)
        citation = self.searcher._format_citation(
            ['Smith J', 'Jones M', 'Brown K', 'Davis L', 'Wilson R'], 
            'Test Study', 
            'Test Journal', 
            '2023 Jan'
        )
        assert 'Smith J et al. Test Study. Test Journal. 2023.' == citation
    
    def test_extract_key_findings(self):
        """Test key findings extraction."""
        # Paper with outcome terms
        paper_info = {
            'title': 'New treatment reduces blood pressure effectively in patients'
        }
        
        findings = self.searcher._extract_key_findings(paper_info, 'Hypertension')
        assert 'reduces' in findings or 'effectively' in findings
        
        # Paper without outcome terms
        paper_info = {
            'title': 'Study of patient demographics'
        }
        
        findings = self.searcher._extract_key_findings(paper_info, 'Hypertension')
        assert 'Research study on Hypertension' == findings
    
    def test_create_research_finding(self):
        """Test research finding creation."""
        paper_info = {
            'uid': '12345',
            'title': 'Diabetes Management Study',
            'authors': [{'name': 'Smith J'}, {'name': 'Jones M'}],
            'pubdate': '2023 Jan 15',
            'fulljournalname': 'Diabetes Care',
            'doi': '10.1234/example.doi'
        }
        
        finding = self.searcher._create_research_finding(paper_info, 'Diabetes')
        
        assert finding is not None
        assert finding.title == 'Diabetes Management Study'
        assert finding.authors == ['Smith J', 'Jones M']
        assert finding.publication_date == '2023 Jan 15'
        assert finding.journal == 'Diabetes Care'
        assert finding.doi == '10.1234/example.doi'
        assert finding.pmid == '12345'
        assert finding.peer_reviewed is True
        assert 0.0 <= finding.relevance_score <= 1.0
    
    def test_deduplicate_findings(self):
        """Test deduplication of research findings."""
        from src.models import ResearchFinding
        
        findings = [
            ResearchFinding(
                title="Duplicate Study",
                authors=["Smith J"],
                publication_date="2023-01-01",
                journal="Test Journal",
                relevance_score=0.8,
                key_findings="Test findings",
                citation="Smith J. Duplicate Study. Test Journal. 2023.",
                study_type="RCT",
                peer_reviewed=True
            ),
            ResearchFinding(
                title="Duplicate Study",  # Same title
                authors=["Jones M"],
                publication_date="2023-01-01",
                journal="Test Journal",
                relevance_score=0.7,
                key_findings="Test findings",
                citation="Jones M. Duplicate Study. Test Journal. 2023.",
                study_type="RCT",
                peer_reviewed=True
            ),
            ResearchFinding(
                title="Unique Study",
                authors=["Brown K"],
                publication_date="2023-01-01",
                journal="Test Journal",
                relevance_score=0.9,
                key_findings="Test findings",
                citation="Brown K. Unique Study. Test Journal. 2023.",
                study_type="RCT",
                peer_reviewed=True
            )
        ]
        
        unique_findings = self.searcher._deduplicate_findings(findings)
        
        # Should have 2 unique findings (duplicates removed)
        assert len(unique_findings) == 2
        titles = [f.title for f in unique_findings]
        assert "Duplicate Study" in titles
        assert "Unique Study" in titles
    
    def test_get_fallback_research(self):
        """Test fallback research generation."""
        conditions = ["Diabetes", "Hypertension", "Heart Disease", "Extra Condition"]
        
        fallback_findings = self.searcher.get_fallback_research(conditions)
        
        # Should return findings for first 3 conditions only
        assert len(fallback_findings) == 3
        
        for finding in fallback_findings:
            assert finding.title.startswith("Clinical Management of")
            assert finding.authors == ["Medical Research Team"]
            assert finding.relevance_score == 0.5
            assert finding.peer_reviewed is True
    
    @pytest.mark.asyncio
    async def test_search_conditions_with_mock_response(self):
        """Test search conditions with mocked HTTP responses."""
        conditions = ["Diabetes"]
        
        # Mock search response
        search_response_data = {
            'esearchresult': {
                'idlist': ['12345', '67890']
            }
        }
        
        # Mock summary response
        summary_response_data = {
            'result': {
                '12345': {
                    'uid': '12345',
                    'title': 'Diabetes Treatment Study',
                    'authors': [{'name': 'Smith J'}],
                    'pubdate': '2023 Jan',
                    'fulljournalname': 'Diabetes Care'
                },
                '67890': {
                    'uid': '67890',
                    'title': 'Diabetes Prevention Research',
                    'authors': [{'name': 'Jones M'}],
                    'pubdate': '2023 Feb',
                    'fulljournalname': 'Journal of Diabetes'
                }
            }
        }
        
        # Mock HTTP client
        with patch('httpx.AsyncClient') as mock_client:
            mock_client_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            # Mock search request
            search_response = Mock()
            search_response.json.return_value = search_response_data
            search_response.raise_for_status.return_value = None
            
            # Mock summary request
            summary_response = Mock()
            summary_response.json.return_value = summary_response_data
            summary_response.raise_for_status.return_value = None
            
            # Configure mock to return different responses for different URLs
            def mock_get(url, **kwargs):
                if 'esearch' in url:
                    return search_response
                elif 'esummary' in url:
                    return summary_response
                else:
                    raise ValueError(f"Unexpected URL: {url}")
            
            mock_client_instance.get = AsyncMock(side_effect=mock_get)
            
            # Execute search
            findings = await self.searcher.search_conditions(conditions)
            
            # Verify results
            assert len(findings) == 2
            assert findings[0].title in ['Diabetes Treatment Study', 'Diabetes Prevention Research']
            assert findings[1].title in ['Diabetes Treatment Study', 'Diabetes Prevention Research']
            
            # Verify HTTP calls were made
            assert mock_client_instance.get.call_count == 2  # Search + Summary
    
    @pytest.mark.asyncio
    async def test_search_conditions_with_http_error(self):
        """Test search conditions with HTTP error."""
        conditions = ["Diabetes"]
        
        # Mock HTTP client to raise an exception
        with patch('httpx.AsyncClient') as mock_client:
            mock_client_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            mock_client_instance.get.side_effect = httpx.RequestError("Network error")
            
            # Should raise ResearchError when all searches fail
            with pytest.raises(ResearchError, match="All condition searches failed"):
                await self.searcher.search_conditions(conditions)
    
    @pytest.mark.asyncio
    async def test_search_conditions_empty_results(self):
        """Test search conditions with empty results."""
        conditions = ["NonexistentCondition"]
        
        # Mock empty search response
        search_response_data = {
            'esearchresult': {
                'idlist': []
            }
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            search_response = Mock()
            search_response.json.return_value = search_response_data
            search_response.raise_for_status.return_value = None
            
            mock_client_instance.get.return_value = search_response
            
            # Execute search
            findings = await self.searcher.search_conditions(conditions)
            
            # Should return empty list
            assert len(findings) == 0
    
    def test_search_params_with_api_key(self):
        """Test that API key is properly included in search parameters."""
        searcher_with_key = ResearchSearcher(pubmed_api_key="test_api_key")
        
        assert 'api_key' in searcher_with_key.search_params
        assert searcher_with_key.search_params['api_key'] == "test_api_key"
    
    def test_search_params_without_api_key(self):
        """Test search parameters without API key."""
        searcher_no_key = ResearchSearcher()
        
        assert 'api_key' not in searcher_no_key.search_params