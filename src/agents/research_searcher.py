"""Research search functionality for finding relevant medical literature."""
import logging
import asyncio
from typing import List, Dict, Optional, Set
from datetime import datetime, timedelta
import re
import json
from ..models import ResearchFinding, ResearchError
from ..utils import AuditLogger

logger = logging.getLogger(__name__)

class ResearchSearcher:
    """Searches medical databases and APIs for relevant research literature."""
    
    def __init__(self, audit_logger: Optional[AuditLogger] = None):
        """
        Initialize research searcher.
        Args:
            audit_logger: Optional audit logger for HIPAA compliance
        """
        self.audit_logger = audit_logger
        self.search_apis = self._initialize_search_apis()
        self.search_cache = {}  # Simple in-memory cache
        self.max_results_per_condition = 10
        self.search_timeout = 30  # seconds
    
    def search_research(self, conditions: List[str], patient_id: str) -> List[ResearchFinding]:
        """
        Search for research papers relevant to patient conditions.
        Args:
            conditions: List of medical conditions to search for
            patient_id: Patient ID for audit logging
        Returns:
            List[ResearchFinding]: Relevant research papers with metadata
        Raises:
            ResearchError: If search operations fail
        """
        logger.info(f"Starting research search for {len(conditions)} conditions")
        
        if not conditions:
            return []
        
        try:
            # Log research search start
            if self.audit_logger:
                self.audit_logger.log_data_access(
                    patient_id=patient_id,
                    operation="research_search_start",
                    details={
                        "conditions_searched": conditions,
                        "search_apis": list(self.search_apis.keys())
                    }
                )
            
            all_findings = []
            # Search for each condition
            for condition in conditions:
                logger.info(f"Searching research for condition: {condition}")
                # Check cache first
                cache_key = self._generate_cache_key(condition)
                if cache_key in self.search_cache:
                    cached_results = self.search_cache[cache_key]
                    logger.info(f"Using cached results for {condition}")
                    all_findings.extend(cached_results)
                    continue
                
                # Search multiple sources
                condition_findings = []
                # Search PubMed (simulated)
                pubmed_results = self._search_pubmed(condition)
                condition_findings.extend(pubmed_results)
                
                # Search medical databases (simulated)
                database_results = self._search_medical_databases(condition)
                condition_findings.extend(database_results)
                
                # Search clinical trials (simulated)
                trial_results = self._search_clinical_trials(condition)
                condition_findings.extend(trial_results)
                
                # Cache results
                self.search_cache[cache_key] = condition_findings
                all_findings.extend(condition_findings)
            
            # Remove duplicates and limit results
            unique_findings = self._deduplicate_findings(all_findings)
            limited_findings = unique_findings[:50]  # Limit total results
            
            # Log search completion
            if self.audit_logger:
                self.audit_logger.log_data_access(
                    patient_id=patient_id,
                    operation="research_search_complete",
                    details={
                        "total_papers_found": len(limited_findings),
                        "conditions_with_results": len([c for c in conditions if any(c.lower() in f.title.lower() for f in limited_findings)]),
                        "search_sources": ["pubmed", "medical_databases", "clinical_trials"]
                    }
                )
            
            logger.info(f"Research search completed: {len(limited_findings)} papers found")
            return limited_findings
            
        except Exception as e:
            error_msg = f"Research search failed: {str(e)}"
            logger.error(error_msg)
            if self.audit_logger:
                self.audit_logger.log_error(
                    patient_id=patient_id,
                    operation="research_search",
                    error=e
                )
            raise ResearchError(error_msg)
    
    def _search_pubmed(self, condition: str) -> List[ResearchFinding]:
        """
        Search PubMed for research papers (simulated implementation).
        In a real implementation, this would use the PubMed API.
        """
        logger.debug(f"Searching PubMed for: {condition}")
        
        # Handle None or empty condition
        if not condition or not condition.strip():
            return []
        
        # Simulated PubMed results based on common conditions
        pubmed_database = self._get_simulated_pubmed_database()
        findings = []
        condition_lower = condition.lower()
        
        for paper in pubmed_database:
            # Simple keyword matching (in real implementation, use proper API)
            if any(keyword in condition_lower for keyword in paper.get("keywords", [])):
                finding = ResearchFinding(
                    title=paper["title"],
                    authors=paper["authors"],
                    publication_date=paper["publication_date"],
                    journal=paper["journal"],
                    doi=paper.get("doi"),
                    pmid=paper.get("pmid"),
                    relevance_score=self._calculate_relevance_score(condition, paper),
                    key_findings=paper["abstract"][:200] + "..." if len(paper["abstract"]) > 200 else paper["abstract"],
                    citation=self._format_citation(paper),
                    abstract=paper["abstract"],
                    study_type=paper.get("study_type", "observational"),
                    sample_size=paper.get("sample_size"),
                    peer_reviewed=True
                )
                findings.append(finding)
        
        # Sort by relevance and limit results
        findings.sort(key=lambda x: x.relevance_score, reverse=True)
        return findings[:self.max_results_per_condition]
    
    def _search_medical_databases(self, condition: str) -> List[ResearchFinding]:
        """
        Search medical databases for research papers (simulated implementation).
        In a real implementation, this would search databases like Cochrane, MEDLINE, etc.
        """
        logger.debug(f"Searching medical databases for: {condition}")
        
        # Handle None or empty condition
        if not condition or not condition.strip():
            return []
        
        # Simulated medical database results
        database_papers = self._get_simulated_database_papers()
        findings = []
        condition_lower = condition.lower()
        
        for paper in database_papers:
            if any(keyword in condition_lower for keyword in paper.get("keywords", [])):
                finding = ResearchFinding(
                    title=paper["title"],
                    authors=paper["authors"],
                    publication_date=paper["publication_date"],
                    journal=paper["journal"],
                    doi=paper.get("doi"),
                    relevance_score=self._calculate_relevance_score(condition, paper),
                    key_findings=paper["key_findings"],
                    citation=self._format_citation(paper),
                    study_type=paper.get("study_type", "systematic_review"),
                    sample_size=paper.get("sample_size"),
                    peer_reviewed=True
                )
                findings.append(finding)
        
        findings.sort(key=lambda x: x.relevance_score, reverse=True)
        return findings[:self.max_results_per_condition]
    
    def _search_clinical_trials(self, condition: str) -> List[ResearchFinding]:
        """
        Search clinical trials databases (simulated implementation).
        In a real implementation, this would use ClinicalTrials.gov API.
        """
        logger.debug(f"Searching clinical trials for: {condition}")
        
        # Handle None or empty condition
        if not condition or not condition.strip():
            return []
        
        # Simulated clinical trial results
        trial_papers = self._get_simulated_clinical_trials()
        findings = []
        condition_lower = condition.lower()
        
        for trial in trial_papers:
            if any(keyword in condition_lower for keyword in trial.get("keywords", [])):
                finding = ResearchFinding(
                    title=trial["title"],
                    authors=trial["authors"],
                    publication_date=trial["publication_date"],
                    journal=trial["journal"],
                    relevance_score=self._calculate_relevance_score(condition, trial),
                    key_findings=trial["key_findings"],
                    citation=self._format_citation(trial),
                    study_type="RCT",
                    sample_size=trial.get("sample_size"),
                    peer_reviewed=True
                )
                findings.append(finding)
        
        findings.sort(key=lambda x: x.relevance_score, reverse=True)
        return findings[:self.max_results_per_condition]
    
    def _calculate_relevance_score(self, condition: str, paper: Dict) -> float:
        """Calculate relevance score between condition and paper."""
        # Handle None or empty condition
        if not condition or not condition.strip():
            return 0.0
        
        score = 0.0
        condition_lower = condition.lower()
        
        # Title relevance (highest weight)
        title_lower = paper["title"].lower()
        if condition_lower in title_lower:
            score += 0.4
        elif any(word in title_lower for word in condition_lower.split()):
            score += 0.2
        
        # Abstract relevance
        abstract_lower = paper.get("abstract", "").lower()
        condition_words = condition_lower.split()
        word_matches = sum(1 for word in condition_words if word in abstract_lower)
        score += (word_matches / len(condition_words)) * 0.3
        
        # Study type bonus
        study_type = paper.get("study_type", "").lower()
        if study_type in ["rct", "meta-analysis", "systematic_review"]:
            score += 0.2
        elif study_type in ["cohort", "case-control"]:
            score += 0.1
        
        # Recent publication bonus
        try:
            pub_year = int(paper["publication_date"].split("-")[0])
            current_year = datetime.now().year
            if current_year - pub_year <= 5:
                score += 0.1
        except (ValueError, IndexError):
            pass
        
        return min(score, 1.0)
    
    def _format_citation(self, paper: Dict) -> str:
        """Format paper citation in standard format."""
        authors = paper["authors"]
        if len(authors) > 3:
            author_str = f"{authors[0]} et al."
        else:
            author_str = ", ".join(authors)
        
        year = paper["publication_date"].split("-")[0]
        title = paper["title"]
        journal = paper["journal"]
        return f"{author_str} ({year}). {title}. {journal}."
    
    def _deduplicate_findings(self, findings: List[ResearchFinding]) -> List[ResearchFinding]:
        """Remove duplicate research findings."""
        seen_titles = set()
        unique_findings = []
        
        for finding in findings:
            # Use title as deduplication key (could be improved with DOI/PMID)
            title_key = finding.title.lower().strip()
            if title_key not in seen_titles:
                seen_titles.add(title_key)
                unique_findings.append(finding)
        
        return unique_findings
    
    def _generate_cache_key(self, condition: str) -> str:
        """Generate cache key for condition search."""
        # Handle None or empty condition
        if not condition or not condition.strip():
            return "search_unknown"
        return f"search_{condition.lower().replace(' ', '_')}"
    
    def _initialize_search_apis(self) -> Dict[str, Dict]:
        """Initialize search API configurations."""
        return {
            "pubmed": {
                "base_url": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/",
                "api_key": None,  # Would be configured from environment
                "rate_limit": 3  # requests per second
            },
            "cochrane": {
                "base_url": "https://www.cochranelibrary.com/api/",
                "api_key": None,
                "rate_limit": 1
            },
            "clinicaltrials": {
                "base_url": "https://clinicaltrials.gov/api/",
                "api_key": None,
                "rate_limit": 2
            }
        }
    
    def _get_simulated_pubmed_database(self) -> List[Dict]:
        """Get simulated PubMed database for testing/demo purposes."""
        return [
            {
                "title": "Metformin in Type 2 Diabetes: A Systematic Review and Meta-Analysis",
                "authors": ["Smith, J.", "Johnson, A.", "Brown, K."],
                "publication_date": "2023-06-15",
                "journal": "Diabetes Care",
                "doi": "10.2337/dc23-0123",
                "pmid": "37234567",
                "abstract": "This systematic review and meta-analysis evaluates the efficacy and safety of metformin in type 2 diabetes management. Analysis of 45 randomized controlled trials involving 12,847 patients demonstrates significant improvements in glycemic control and cardiovascular outcomes.",
                "keywords": ["diabetes", "metformin", "glycemic control"],
                "study_type": "meta-analysis",
                "sample_size": 12847
            },
            {
                "title": "ACE Inhibitors vs ARBs in Hypertension Management: Long-term Outcomes",
                "authors": ["Wilson, M.", "Davis, R.", "Taylor, S."],
                "publication_date": "2023-08-22",
                "journal": "Hypertension",
                "doi": "10.1161/hyp.2023.456",
                "pmid": "37345678",
                "abstract": "Comparative effectiveness study of ACE inhibitors versus ARBs in hypertension management over 10 years. Results show similar cardiovascular protection with slight advantage for ACE inhibitors in heart failure prevention.",
                "keywords": ["hypertension", "ace inhibitors", "arbs", "cardiovascular"],
                "study_type": "RCT",
                "sample_size": 8934
            },
            {
                "title": "Statin Therapy in Hyperlipidemia: Current Evidence and Guidelines",
                "authors": ["Anderson, P.", "Miller, L.", "Garcia, C."],
                "publication_date": "2023-04-10",
                "journal": "Journal of Lipid Research",
                "doi": "10.1194/jlr.2023.789",
                "pmid": "37456789",
                "abstract": "Comprehensive review of statin therapy effectiveness in hyperlipidemia management. Evidence supports significant reduction in cardiovascular events and mortality with high-intensity statin therapy.",
                "keywords": ["hyperlipidemia", "statins", "cholesterol", "cardiovascular"],
                "study_type": "systematic_review",
                "sample_size": 25000
            }
        ]
    
    def _get_simulated_database_papers(self) -> List[Dict]:
        """Get simulated medical database papers."""
        return [
            {
                "title": "Diabetes Prevention: Lifestyle Interventions vs Pharmacological Approaches",
                "authors": ["Rodriguez, A.", "Kim, S.", "Patel, N."],
                "publication_date": "2023-05-18",
                "journal": "Cochrane Database of Systematic Reviews",
                "doi": "10.1002/14651858.CD012345",
                "key_findings": "Lifestyle interventions show 58% reduction in diabetes incidence compared to 31% with metformin alone.",
                "keywords": ["diabetes", "prevention", "lifestyle", "metformin"],
                "study_type": "systematic_review",
                "sample_size": 15000
            },
            {
                "title": "Hypertension in Elderly: Treatment Targets and Outcomes",
                "authors": ["Chen, L.", "Williams, D.", "Jackson, M."],
                "publication_date": "2023-09-12",
                "journal": "BMJ",
                "doi": "10.1136/bmj.2023.567",
                "key_findings": "Intensive blood pressure control (<130/80) in elderly patients reduces cardiovascular events by 25% but increases hypotension risk.",
                "keywords": ["hypertension", "elderly", "blood pressure", "cardiovascular"],
                "study_type": "cohort",
                "sample_size": 5678
            }
        ]
    
    def _get_simulated_clinical_trials(self) -> List[Dict]:
        """Get simulated clinical trial data."""
        return [
            {
                "title": "Novel GLP-1 Agonist in Type 2 Diabetes: Phase III Trial Results",
                "authors": ["Martinez, R.", "Singh, P.", "O'Connor, T."],
                "publication_date": "2023-10-30",
                "journal": "New England Journal of Medicine",
                "key_findings": "New GLP-1 agonist demonstrates superior glycemic control and weight loss compared to existing therapies with similar safety profile.",
                "keywords": ["diabetes", "glp-1", "clinical trial", "glycemic control"],
                "study_type": "RCT",
                "sample_size": 2340
            },
            {
                "title": "Combination Therapy for Resistant Hypertension: Multi-center Trial",
                "authors": ["Foster, K.", "Liu, X.", "Brown, A."],
                "publication_date": "2023-11-15",
                "journal": "Circulation",
                "key_findings": "Triple combination therapy achieves target blood pressure in 78% of resistant hypertension patients with acceptable side effect profile.",
                "keywords": ["hypertension", "resistant", "combination therapy", "blood pressure"],
                "study_type": "RCT",
                "sample_size": 890
            }
        ]