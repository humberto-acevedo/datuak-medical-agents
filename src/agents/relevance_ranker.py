"""Relevance ranking and prioritization of research findings."""
import logging
from typing import List, Dict, Tuple, Set, Optional
from datetime import datetime
import re
from collections import defaultdict
from ..models import ResearchFinding, Condition

logger = logging.getLogger(__name__)

class RelevanceRanker:
    """Ranks and prioritizes research findings by relevance to patient conditions."""
    
    def __init__(self):
        """Initialize relevance ranker with scoring algorithms."""
        self.condition_weights = self._load_condition_weights()
        self.study_type_weights = self._load_study_type_weights()
        self.journal_impact_scores = self._load_journal_impact_scores()
        self.medical_terminology = self._load_medical_terminology()
    
    def rank_research_findings(self, findings: List[ResearchFinding], 
                             conditions: List[Condition]) -> List[ResearchFinding]:
        """
        Rank research findings by relevance to patient conditions.
        
        Args:
            findings: List of research findings to rank
            conditions: Patient conditions with severity and confidence
            
        Returns:
            List[ResearchFinding]: Ranked research findings (highest relevance first)
        """
        logger.info(f"Ranking {len(findings)} research findings for {len(conditions)} conditions")
        
        # Calculate enhanced relevance scores
        scored_findings = []
        for finding in findings:
            enhanced_score = self._calculate_enhanced_relevance_score(finding, conditions)
            # Update the finding with enhanced score
            finding.relevance_score = enhanced_score
            scored_findings.append(finding)
        
        # Sort by relevance score (descending)
        ranked_findings = sorted(scored_findings, key=lambda x: x.relevance_score, reverse=True)
        
        # Apply diversity filtering to ensure variety in results
        diverse_findings = self._apply_diversity_filtering(ranked_findings, conditions)
        
        logger.info(f"Ranking complete: top score = {diverse_findings[0].relevance_score:.3f}" if diverse_findings else "No findings to rank")
        return diverse_findings
    
    def prioritize_by_condition_severity(self, findings: List[ResearchFinding], 
                                       conditions: List[Condition]) -> List[ResearchFinding]:
        """
        Prioritize research findings based on condition severity and clinical importance.
        
        Args:
            findings: Research findings to prioritize
            conditions: Patient conditions with severity information
            
        Returns:
            List[ResearchFinding]: Prioritized research findings
        """
        logger.info("Prioritizing research by condition severity")
        
        # Create condition severity mapping
        condition_severity_map = {}
        for condition in conditions:
            # Skip conditions with None or empty names
            if not condition.name or not condition.name.strip():
                continue
            severity_score = self._get_severity_score(condition.severity)
            condition_severity_map[condition.name.lower()] = severity_score
        
        # Score findings based on condition severity
        prioritized_findings = []
        for finding in findings:
            severity_bonus = 0.0
            
            # Check if finding relates to high-severity conditions
            for condition_name, severity_score in condition_severity_map.items():
                if self._finding_relates_to_condition(finding, condition_name):
                    severity_bonus = max(severity_bonus, severity_score * 0.3)
            
            # Apply severity bonus to relevance score
            enhanced_score = finding.relevance_score + severity_bonus
            finding.relevance_score = min(enhanced_score, 1.0)
            prioritized_findings.append(finding)
        
        # Sort by enhanced scores
        prioritized_findings.sort(key=lambda x: x.relevance_score, reverse=True)
        return prioritized_findings
    
    def get_top_findings_by_category(self, findings: List[ResearchFinding], 
                                   limit_per_category: int = 3) -> Dict[str, List[ResearchFinding]]:
        """
        Get top research findings organized by category/study type.
        
        Args:
            findings: Research findings to categorize
            limit_per_category: Maximum findings per category
            
        Returns:
            Dict[str, List[ResearchFinding]]: Findings organized by category
        """
        logger.info("Organizing findings by category")
        
        # Group findings by study type
        categorized_findings = defaultdict(list)
        for finding in findings:
            category = self._categorize_study_type(finding.study_type)
            categorized_findings[category].append(finding)
        
        # Sort each category by relevance and limit results
        top_by_category = {}
        for category, category_findings in categorized_findings.items():
            sorted_findings = sorted(category_findings, key=lambda x: x.relevance_score, reverse=True)
            top_by_category[category] = sorted_findings[:limit_per_category]
        
        return top_by_category
    
    def _calculate_enhanced_relevance_score(self, finding: ResearchFinding, 
                                         conditions: List[Condition]) -> float:
        """Calculate enhanced relevance score using multiple factors."""
        base_score = finding.relevance_score or 0.0
        
        # Factor 1: Condition matching and confidence
        condition_score = self._calculate_condition_matching_score(finding, conditions)
        
        # Factor 2: Study quality and type
        study_quality_score = self._calculate_study_quality_score(finding)
        
        # Factor 3: Publication recency
        recency_score = self._calculate_recency_score(finding.publication_date)
        
        # Factor 4: Journal impact
        journal_score = self._calculate_journal_impact_score(finding.journal)
        
        # Factor 5: Sample size reliability
        sample_size_score = self._calculate_sample_size_score(finding.sample_size)
        
        # Weighted combination of factors
        enhanced_score = (
            base_score * 0.3 +
            condition_score * 0.25 +
            study_quality_score * 0.2 +
            recency_score * 0.1 +
            journal_score * 0.1 +
            sample_size_score * 0.05
        )
        
        return min(enhanced_score, 1.0)
    
    def _calculate_condition_matching_score(self, finding: ResearchFinding, 
                                         conditions: List[Condition]) -> float:
        """Calculate how well the finding matches patient conditions."""
        max_match_score = 0.0
        
        for condition in conditions:
            # Skip conditions with None or empty names
            if not condition.name or not condition.name.strip():
                continue
            
            match_score = 0.0
            condition_lower = condition.name.lower()
            
            # Title matching (highest weight)
            if condition_lower in finding.title.lower():
                match_score += 0.5
            elif any(word in finding.title.lower() for word in condition_lower.split()):
                match_score += 0.3
            
            # Abstract matching
            if finding.abstract and condition_lower in finding.abstract.lower():
                match_score += 0.3
            elif finding.abstract and any(word in finding.abstract.lower() for word in condition_lower.split()):
                match_score += 0.2
            
            # Key findings matching
            if condition_lower in finding.key_findings.lower():
                match_score += 0.2
            
            # Apply condition confidence weight
            weighted_score = match_score * condition.confidence_score
            max_match_score = max(max_match_score, weighted_score)
        
        return max_match_score
    
    def _calculate_study_quality_score(self, finding: ResearchFinding) -> float:
        """Calculate study quality score based on study type and peer review."""
        base_score = 0.0
        
        # Study type scoring
        study_type = finding.study_type.lower() if finding.study_type else ""
        base_score = self.study_type_weights.get(study_type, 0.3)
        
        # Peer review bonus
        if finding.peer_reviewed:
            base_score += 0.2
        
        # DOI/PMID availability (indicates proper publication)
        if finding.doi or finding.pmid:
            base_score += 0.1
        
        return min(base_score, 1.0)
    
    def _calculate_recency_score(self, publication_date: str) -> float:
        """Calculate recency score based on publication date."""
        try:
            pub_year = int(publication_date.split("-")[0])
            current_year = datetime.now().year
            years_old = current_year - pub_year
            
            # Recent papers get higher scores
            if years_old <= 2:
                return 1.0
            elif years_old <= 5:
                return 0.8
            elif years_old <= 10:
                return 0.6
            else:
                return 0.4
        except (ValueError, IndexError):
            return 0.5  # Default for unparseable dates
    
    def _calculate_journal_impact_score(self, journal: str) -> float:
        """Calculate journal impact score."""
        journal_lower = journal.lower()
        
        # Check against known high-impact journals
        for journal_pattern, score in self.journal_impact_scores.items():
            if journal_pattern in journal_lower:
                return score
        
        return 0.5  # Default score for unknown journals
    
    def _calculate_sample_size_score(self, sample_size: Optional[int]) -> float:
        """Calculate score based on study sample size."""
        if not sample_size:
            return 0.3
        
        # Larger sample sizes generally indicate more reliable results
        if sample_size >= 10000:
            return 1.0
        elif sample_size >= 5000:
            return 0.9
        elif sample_size >= 1000:
            return 0.8
        elif sample_size >= 500:
            return 0.7
        elif sample_size >= 100:
            return 0.6
        else:
            return 0.4
    
    def _apply_diversity_filtering(self, findings: List[ResearchFinding], 
                                 conditions: List[Condition]) -> List[ResearchFinding]:
        """Apply diversity filtering to ensure variety in research types and topics."""
        if len(findings) <= 10:
            return findings
        
        diverse_findings = []
        study_type_counts = defaultdict(int)
        condition_coverage = set()
        
        for finding in findings:
            study_type = self._categorize_study_type(finding.study_type)
            
            # Ensure diversity in study types
            if study_type_counts[study_type] >= 3:
                continue
            
            # Ensure coverage of different conditions
            finding_conditions = self._extract_conditions_from_finding(finding, conditions)
            if not finding_conditions.intersection(condition_coverage) or len(diverse_findings) < 5:
                diverse_findings.append(finding)
                study_type_counts[study_type] += 1
                condition_coverage.update(finding_conditions)
            
            if len(diverse_findings) >= 20:  # Limit total results
                break
        
        return diverse_findings
    
    def _get_severity_score(self, severity: str) -> float:
        """Convert severity string to numeric score."""
        # Handle None or empty severity
        if not severity:
            return 0.5  # Default score
        
        severity_scores = {
            "critical": 1.0,
            "severe": 0.8,
            "moderate": 0.6,
            "mild": 0.4,
            "low": 0.2
        }
        return severity_scores.get(severity.lower(), 0.5)
    
    def _finding_relates_to_condition(self, finding: ResearchFinding, condition_name: str) -> bool:
        """Check if finding relates to specific condition."""
        # Handle None or empty condition name
        if not condition_name or not condition_name.strip():
            return False
        
        condition_lower = condition_name.lower()
        text_to_search = f"{finding.title} {finding.key_findings} {finding.abstract or ''}".lower()
        
        # Direct match
        if condition_lower in text_to_search:
            return True
        
        # Word-based matching
        condition_words = condition_lower.split()
        return any(word in text_to_search for word in condition_words if len(word) > 3)
    
    def _categorize_study_type(self, study_type: Optional[str]) -> str:
        """Categorize study type into broader categories."""
        if not study_type:
            return "other"
        
        study_type_lower = study_type.lower()
        
        if "meta-analysis" in study_type_lower or "systematic" in study_type_lower:
            return "systematic_reviews"
        elif "rct" in study_type_lower or "randomized" in study_type_lower:
            return "clinical_trials"
        elif "cohort" in study_type_lower or "longitudinal" in study_type_lower:
            return "observational"
        elif "case" in study_type_lower:
            return "case_studies"
        else:
            return "other"
    
    def _extract_conditions_from_finding(self, finding: ResearchFinding, 
                                       conditions: List[Condition]) -> Set[str]:
        """Extract which conditions this finding relates to."""
        related_conditions = set()
        text_to_search = f"{finding.title} {finding.key_findings}".lower()
        
        for condition in conditions:
            # Skip conditions with None or empty names
            if not condition.name or not condition.name.strip():
                continue
            if self._finding_relates_to_condition(finding, condition.name):
                related_conditions.add(condition.name.lower())
        
        return related_conditions
    
    def _load_condition_weights(self) -> Dict[str, float]:
        """Load condition importance weights."""
        return {
            "diabetes": 0.9,
            "hypertension": 0.8,
            "heart disease": 0.9,
            "copd": 0.8,
            "cancer": 1.0,
            "stroke": 0.9,
            "kidney disease": 0.8,
            "depression": 0.7,
            "anxiety": 0.6,
            "arthritis": 0.5
        }
    
    def _load_study_type_weights(self) -> Dict[str, float]:
        """Load study type quality weights."""
        return {
            "meta-analysis": 1.0,
            "systematic_review": 0.9,
            "rct": 0.8,
            "randomized_controlled_trial": 0.8,
            "cohort": 0.7,
            "case-control": 0.6,
            "cross-sectional": 0.5,
            "case_study": 0.4,
            "observational": 0.5
        }
    
    def _load_journal_impact_scores(self) -> Dict[str, float]:
        """Load journal impact factor scores."""
        return {
            "new england journal of medicine": 1.0,
            "lancet": 1.0,
            "jama": 0.95,
            "nature": 1.0,
            "science": 1.0,
            "bmj": 0.9,
            "circulation": 0.85,
            "diabetes care": 0.8,
            "hypertension": 0.75,
            "cochrane": 0.9,
            "plos": 0.7,
            "journal of": 0.6  # Generic pattern for specialty journals
        }
    
    def _load_medical_terminology(self) -> Dict[str, List[str]]:
        """Load medical terminology mappings for better matching."""
        return {
            "diabetes": ["diabetes mellitus", "diabetic", "hyperglycemia", "insulin resistance"],
            "hypertension": ["high blood pressure", "hypertensive", "bp", "blood pressure"],
            "heart disease": ["cardiovascular", "cardiac", "coronary", "myocardial", "heart failure"],
            "copd": ["chronic obstructive pulmonary", "emphysema", "chronic bronchitis"],
            "depression": ["major depressive disorder", "mdd", "depressive symptoms"],
            "anxiety": ["anxiety disorder", "anxious", "panic disorder"]
        }