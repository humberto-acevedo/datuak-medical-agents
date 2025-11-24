"""Research analysis models for medical literature correlation."""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict
from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class ResearchFinding:
    """Individual research paper or study finding."""
    title: str
    authors: List[str]
    publication_date: str
    journal: str
    doi: Optional[str] = None
    pmid: Optional[str] = None  # PubMed ID
    relevance_score: float = 0.0  # 0.0 to 1.0
    key_findings: str = ""
    citation: str = ""
    abstract: Optional[str] = None
    study_type: Optional[str] = None  # RCT, observational, meta-analysis, etc.
    sample_size: Optional[int] = None
    peer_reviewed: bool = True
    
    def validate(self) -> List[str]:
        """Validate research finding data."""
        errors = []
        
        if not self.title:
            errors.append("Research title is required")
        if not self.authors:
            errors.append("At least one author is required")
        if not self.journal:
            errors.append("Journal name is required")
        if self.relevance_score < 0 or self.relevance_score > 1:
            errors.append("Relevance score must be between 0 and 1")
        if not self.citation:
            errors.append("Citation format is required")
            
        return errors
    
    def is_recent(self, years: int = 5) -> bool:
        """Check if research is from the last N years."""
        try:
            pub_year = int(self.publication_date.split('-')[0])
            current_year = datetime.now().year
            return (current_year - pub_year) <= years
        except (ValueError, IndexError):
            return False
    
    def is_high_quality(self) -> bool:
        """Determine if research meets high quality criteria."""
        return (
            self.peer_reviewed and 
            self.relevance_score >= 0.7 and
            self.study_type in ["RCT", "meta-analysis", "systematic_review"]
        )


@dataclass_json
@dataclass
class ResearchAnalysis:
    """Complete research analysis for patient conditions."""
    patient_id: str
    analysis_timestamp: datetime
    conditions_analyzed: List['Condition']  # Forward reference
    research_findings: List[ResearchFinding]
    condition_research_correlations: Dict[str, List[ResearchFinding]]
    categorized_findings: Dict[str, List[ResearchFinding]]
    research_insights: List[str]
    clinical_recommendations: List[str]
    analysis_confidence: float
    total_papers_reviewed: int
    relevant_papers_found: int
    
    def validate(self) -> List[str]:
        """Validate research analysis data."""
        errors = []
        
        if not self.patient_id:
            errors.append("Patient ID is required")
        if not self.conditions_analyzed:
            errors.append("At least one condition must be analyzed")
        if self.analysis_confidence < 0 or self.analysis_confidence > 1:
            errors.append("Analysis confidence must be between 0 and 1")
        if self.relevant_papers_found > self.total_papers_reviewed:
            errors.append("Relevant papers cannot exceed total papers reviewed")
            
        # Validate individual findings
        for finding in self.research_findings:
            finding_errors = finding.validate()
            errors.extend([f"Research finding '{finding.title}': {error}" for error in finding_errors])
            
        return errors
    
    def get_top_findings(self, limit: int = 5) -> List[ResearchFinding]:
        """Get top research findings by relevance score."""
        return sorted(
            self.research_findings, 
            key=lambda x: x.relevance_score, 
            reverse=True
        )[:limit]
    
    def get_recent_findings(self, years: int = 5) -> List[ResearchFinding]:
        """Get research findings from the last N years."""
        return [finding for finding in self.research_findings if finding.is_recent(years)]
    
    def get_high_quality_findings(self) -> List[ResearchFinding]:
        """Get high quality research findings."""
        return [finding for finding in self.research_findings if finding.is_high_quality()]
    
    def get_condition_research(self, condition_name: str) -> List[ResearchFinding]:
        """Get research findings for a specific condition."""
        return self.condition_research_correlations.get(condition_name, [])
    
    def get_research_summary(self) -> Dict[str, any]:
        """Get summary statistics of the research analysis."""
        return {
            "total_conditions": len(self.conditions_analyzed),
            "total_papers_reviewed": self.total_papers_reviewed,
            "relevant_papers_found": self.relevant_papers_found,
            "analysis_confidence": self.analysis_confidence,
            "high_quality_papers": len(self.get_high_quality_findings()),
            "recent_papers": len(self.get_recent_findings()),
            "conditions_with_research": len([c for c in self.condition_research_correlations.values() if c]),
            "research_categories": list(self.categorized_findings.keys())
        }