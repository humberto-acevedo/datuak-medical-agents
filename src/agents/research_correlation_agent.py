"""Research Correlation Agent for finding and correlating medical research with patient conditions."""
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import asyncio

from ..models import (
    PatientData, MedicalSummary, ResearchAnalysis, ResearchFinding, 
    Condition, AnalysisReport, ResearchError
)
from ..utils import AuditLogger
from .research_searcher import ResearchSearcher
from .relevance_ranker import RelevanceRanker

logger = logging.getLogger(__name__)

class ResearchCorrelationAgent:
    """
    Agent responsible for finding and correlating medical research with patient conditions.
    
    This agent:
    1. Takes patient conditions from medical summaries
    2. Searches medical databases for relevant research
    3. Ranks and prioritizes research findings
    4. Correlates findings with patient conditions
    5. Generates research analysis reports
    """
    
    def __init__(self, audit_logger: Optional[AuditLogger] = None):
        """
        Initialize Research Correlation Agent.
        
        Args:
            audit_logger: Optional audit logger for HIPAA compliance
        """
        self.audit_logger = audit_logger
        self.research_searcher = ResearchSearcher(audit_logger)
        self.relevance_ranker = RelevanceRanker()
        
        # Configuration
        self.max_research_papers = 20
        self.min_relevance_threshold = 0.3
        self.correlation_confidence_threshold = 0.5
        
        logger.info("Research Correlation Agent initialized")
    
    def analyze_patient_research(self, patient_data: PatientData, 
                               medical_summary: MedicalSummary) -> ResearchAnalysis:
        """
        Analyze patient conditions and correlate with medical research.
        
        Args:
            patient_data: Patient demographic and clinical data
            medical_summary: Medical summary with extracted conditions
            
        Returns:
            ResearchAnalysis: Comprehensive research analysis with correlations
            
        Raises:
            ResearchError: If research analysis fails
        """
        logger.info(f"Starting research analysis for patient {patient_data.patient_id}")
        
        try:
            # Log research analysis start
            if self.audit_logger:
                self.audit_logger.log_data_access(
                    patient_id=patient_data.patient_id,
                    operation="research_analysis_start",
                    details={
                        "conditions_count": len(medical_summary.key_conditions),
                        "analysis_timestamp": datetime.now().isoformat()
                    }
                )
            
            # Step 1: Extract conditions for research
            research_conditions = self._prepare_conditions_for_research(medical_summary.key_conditions)
            logger.info(f"Prepared {len(research_conditions)} conditions for research")
            
            # Step 2: Search for relevant research
            research_findings = self.research_searcher.search_research(
                conditions=[c.name for c in research_conditions],
                patient_id=patient_data.patient_id
            )
            logger.info(f"Found {len(research_findings)} research papers")
            
            # Step 3: Rank and prioritize findings
            ranked_findings = self.relevance_ranker.rank_research_findings(
                research_findings, research_conditions
            )
            
            # Step 4: Apply severity-based prioritization
            prioritized_findings = self.relevance_ranker.prioritize_by_condition_severity(
                ranked_findings, research_conditions
            )
            
            # Step 5: Filter by relevance threshold
            relevant_findings = [
                f for f in prioritized_findings 
                if f.relevance_score >= self.min_relevance_threshold
            ][:self.max_research_papers]
            
            logger.info(f"Selected {len(relevant_findings)} relevant research papers")
            
            # Step 6: Generate condition-research correlations
            correlations = self._generate_research_correlations(
                research_conditions, relevant_findings
            )
            
            # Step 7: Categorize findings by study type
            categorized_findings = self.relevance_ranker.get_top_findings_by_category(
                relevant_findings, limit_per_category=5
            )
            
            # Step 8: Generate research insights and recommendations
            insights = self._generate_research_insights(
                research_conditions, relevant_findings, correlations
            )
            
            recommendations = self._generate_clinical_recommendations(
                research_conditions, relevant_findings, correlations
            )
            
            # Step 9: Calculate overall analysis confidence
            analysis_confidence = self._calculate_analysis_confidence(
                relevant_findings, correlations
            )
            
            # Create research analysis
            research_analysis = ResearchAnalysis(
                patient_id=patient_data.patient_id,
                analysis_timestamp=datetime.now(),
                conditions_analyzed=research_conditions,
                research_findings=relevant_findings,
                condition_research_correlations=correlations,
                categorized_findings=categorized_findings,
                research_insights=insights,
                clinical_recommendations=recommendations,
                analysis_confidence=analysis_confidence,
                total_papers_reviewed=len(research_findings),
                relevant_papers_found=len(relevant_findings)
            )
            
            # Log successful completion
            if self.audit_logger:
                self.audit_logger.log_data_access(
                    patient_id=patient_data.patient_id,
                    operation="research_analysis_complete",
                    details={
                        "papers_found": len(relevant_findings),
                        "correlations_generated": len(correlations),
                        "analysis_confidence": analysis_confidence,
                        "processing_time_seconds": (datetime.now() - research_analysis.analysis_timestamp).total_seconds()
                    }
                )
            
            logger.info(f"Research analysis completed successfully for patient {patient_data.patient_id}")
            return research_analysis
            
        except Exception as e:
            error_msg = f"Research analysis failed for patient {patient_data.patient_id}: {str(e)}"
            logger.error(error_msg)
            
            if self.audit_logger:
                self.audit_logger.log_error(
                    patient_id=patient_data.patient_id,
                    operation="research_analysis",
                    error=e
                )
            
            raise ResearchError(error_msg)
    
    def _prepare_conditions_for_research(self, conditions: List[Condition]) -> List[Condition]:
        """
        Prepare and filter conditions for research search.
        
        Args:
            conditions: Raw conditions from medical summary
            
        Returns:
            List[Condition]: Filtered and prepared conditions for research
        """
        # Filter out conditions with None or empty names
        valid_conditions = [c for c in conditions if c.name and c.name.strip()]
        
        if not valid_conditions:
            logger.warning("No valid conditions found for research")
            return []
        
        # Filter conditions by confidence score
        high_confidence_conditions = [
            c for c in valid_conditions 
            if c.confidence_score >= self.correlation_confidence_threshold
        ]
        
        # If we have too few high-confidence conditions, include medium confidence
        if len(high_confidence_conditions) < 3:
            medium_confidence_conditions = [
                c for c in conditions 
                if 0.3 <= c.confidence_score < self.correlation_confidence_threshold
            ]
            high_confidence_conditions.extend(medium_confidence_conditions[:5])
        
        # Sort by severity and confidence
        prepared_conditions = sorted(
            high_confidence_conditions,
            key=lambda x: (self._get_severity_weight(x.severity), x.confidence_score),
            reverse=True
        )
        
        # Limit to top conditions to avoid overwhelming search
        return prepared_conditions[:10]
    
    def _generate_research_correlations(self, conditions: List[Condition], 
                                      findings: List[ResearchFinding]) -> Dict[str, List[ResearchFinding]]:
        """
        Generate correlations between conditions and research findings.
        
        Args:
            conditions: Patient conditions
            findings: Research findings
            
        Returns:
            Dict[str, List[ResearchFinding]]: Condition name to relevant research mapping
        """
        correlations = {}
        
        for condition in conditions:
            condition_name = condition.name
            relevant_findings = []
            
            for finding in findings:
                # Check if finding is relevant to this condition
                if self._is_finding_relevant_to_condition(finding, condition):
                    relevant_findings.append(finding)
            
            # Sort by relevance score
            relevant_findings.sort(key=lambda x: x.relevance_score, reverse=True)
            correlations[condition_name] = relevant_findings[:8]  # Limit per condition
        
        return correlations
    
    def _generate_research_insights(self, conditions: List[Condition], 
                                  findings: List[ResearchFinding],
                                  correlations: Dict[str, List[ResearchFinding]]) -> List[str]:
        """
        Generate research insights based on findings and correlations.
        
        Args:
            conditions: Patient conditions
            findings: Research findings
            correlations: Condition-research correlations
            
        Returns:
            List[str]: Research insights and observations
        """
        insights = []
        
        # Insight 1: Coverage analysis
        conditions_with_research = len([c for c in correlations.values() if c])
        total_conditions = len(conditions)
        coverage_percentage = (conditions_with_research / total_conditions) * 100 if total_conditions > 0 else 0
        
        insights.append(
            f"Research coverage: {conditions_with_research}/{total_conditions} conditions "
            f"({coverage_percentage:.1f}%) have relevant research literature available."
        )
        
        # Insight 2: Study quality analysis
        high_quality_studies = len([f for f in findings if f.relevance_score >= 0.7])
        insights.append(
            f"Study quality: {high_quality_studies}/{len(findings)} papers are high-quality "
            f"studies (systematic reviews, RCTs, or meta-analyses)."
        )
        
        # Insight 3: Recent research availability
        recent_studies = len([
            f for f in findings 
            if self._is_recent_study(f.publication_date)
        ])
        insights.append(
            f"Recent research: {recent_studies}/{len(findings)} papers published "
            f"within the last 5 years, indicating current evidence availability."
        )
        
        # Insight 4: Condition-specific insights
        for condition_name, condition_findings in correlations.items():
            if condition_findings:
                top_finding = condition_findings[0]
                insights.append(
                    f"{condition_name}: Most relevant research focuses on "
                    f"{self._extract_key_research_theme(condition_findings)}. "
                    f"Top study: {top_finding.title[:100]}..."
                )
        
        # Insight 5: Research gaps
        conditions_without_research = [
            c.name for c in conditions 
            if c.name not in correlations or not correlations[c.name]
        ]
        if conditions_without_research:
            insights.append(
                f"Research gaps identified for: {', '.join(conditions_without_research[:3])}. "
                f"Consider consulting specialist literature or clinical guidelines."
            )
        
        return insights
    
    def _generate_clinical_recommendations(self, conditions: List[Condition],
                                         findings: List[ResearchFinding],
                                         correlations: Dict[str, List[ResearchFinding]]) -> List[str]:
        """
        Generate clinical recommendations based on research findings.
        
        Args:
            conditions: Patient conditions
            findings: Research findings
            correlations: Condition-research correlations
            
        Returns:
            List[str]: Clinical recommendations
        """
        recommendations = []
        
        # Recommendation 1: Evidence-based treatment approaches
        for condition_name, condition_findings in correlations.items():
            if condition_findings:
                # Find treatment-focused studies
                treatment_studies = [
                    f for f in condition_findings 
                    if any(keyword in f.title.lower() or keyword in f.key_findings.lower()
                          for keyword in ["treatment", "therapy", "intervention", "management"])
                ]
                
                if treatment_studies:
                    top_treatment_study = treatment_studies[0]
                    recommendations.append(
                        f"{condition_name}: Consider evidence-based approaches from "
                        f"{top_treatment_study.journal} research. "
                        f"Key finding: {top_treatment_study.key_findings[:150]}..."
                    )
        
        # Recommendation 2: Monitoring and follow-up
        high_severity_conditions = [c for c in conditions if c.severity in ["severe", "critical"]]
        if high_severity_conditions:
            recommendations.append(
                f"Enhanced monitoring recommended for high-severity conditions: "
                f"{', '.join([c.name for c in high_severity_conditions[:3]])}. "
                f"Recent research emphasizes importance of regular assessment."
            )
        
        # Recommendation 3: Multidisciplinary care
        complex_conditions = [c for c in conditions if len(correlations.get(c.name, [])) >= 3]
        if len(complex_conditions) >= 2:
            recommendations.append(
                "Consider multidisciplinary care approach given complexity of conditions "
                "and extensive research literature available for comprehensive management."
            )
        
        # Recommendation 4: Clinical guideline consultation
        conditions_with_limited_research = [
            c.name for c in conditions 
            if len(correlations.get(c.name, [])) < 2
        ]
        if conditions_with_limited_research:
            recommendations.append(
                f"Consult current clinical guidelines for conditions with limited "
                f"research literature: {', '.join(conditions_with_limited_research[:2])}."
            )
        
        # Recommendation 5: Patient education opportunities
        if findings:
            recommendations.append(
                "Patient education opportunities available based on current research "
                "findings. Consider sharing relevant, accessible information about "
                "condition management and treatment options."
            )
        
        return recommendations
    
    def _calculate_analysis_confidence(self, findings: List[ResearchFinding],
                                     correlations: Dict[str, List[ResearchFinding]]) -> float:
        """
        Calculate overall confidence in the research analysis.
        
        Args:
            findings: Research findings
            correlations: Condition-research correlations
            
        Returns:
            float: Analysis confidence score (0.0 to 1.0)
        """
        if not findings:
            return 0.0
        
        # Factor 1: Average relevance score of findings
        avg_relevance = sum(f.relevance_score for f in findings) / len(findings)
        
        # Factor 2: Coverage of conditions with research
        total_correlations = sum(len(corr) for corr in correlations.values())
        coverage_score = min(total_correlations / (len(correlations) * 3), 1.0) if correlations else 0.0
        
        # Factor 3: Quality of studies (peer-reviewed, recent, high-impact)
        quality_score = sum(
            1 for f in findings 
            if f.peer_reviewed and self._is_recent_study(f.publication_date)
        ) / len(findings)
        
        # Factor 4: Diversity of study types
        study_types = set(f.study_type for f in findings if f.study_type)
        diversity_score = min(len(study_types) / 4, 1.0)  # Normalize to max 4 types
        
        # Weighted combination
        confidence = (
            avg_relevance * 0.4 +
            coverage_score * 0.3 +
            quality_score * 0.2 +
            diversity_score * 0.1
        )
        
        return min(confidence, 1.0)
    
    def _is_finding_relevant_to_condition(self, finding: ResearchFinding, 
                                        condition: Condition) -> bool:
        """Check if a research finding is relevant to a specific condition."""
        # Defensive check for None or empty condition name
        if not condition.name:
            return False
        
        condition_lower = condition.name.lower()
        search_text = f"{finding.title} {finding.key_findings} {finding.abstract or ''}".lower()
        
        # Direct condition name match
        if condition_lower in search_text:
            return True
        
        # Word-based matching for multi-word conditions
        condition_words = [word for word in condition_lower.split() if len(word) > 3]
        matches = sum(1 for word in condition_words if word in search_text)
        
        # Require at least 50% word match for multi-word conditions
        return matches >= len(condition_words) * 0.5 if condition_words else False
    
    def _get_severity_weight(self, severity: str) -> float:
        """Get numeric weight for condition severity."""
        # Defensive check for None or empty severity
        if not severity:
            return 0.5  # Default weight
        
        severity_weights = {
            "critical": 1.0,
            "severe": 0.8,
            "moderate": 0.6,
            "mild": 0.4,
            "low": 0.2
        }
        return severity_weights.get(severity.lower(), 0.5)
    
    def _is_recent_study(self, publication_date: str) -> bool:
        """Check if study is recent (within last 5 years)."""
        try:
            pub_year = int(publication_date.split("-")[0])
            current_year = datetime.now().year
            return (current_year - pub_year) <= 5
        except (ValueError, IndexError):
            return False
    
    def _extract_key_research_theme(self, findings: List[ResearchFinding]) -> str:
        """Extract key research theme from findings."""
        # Simple keyword extraction from titles
        common_words = {}
        for finding in findings[:3]:  # Look at top 3 findings
            words = finding.title.lower().split()
            for word in words:
                if len(word) > 4 and word not in ["study", "analysis", "research", "clinical"]:
                    common_words[word] = common_words.get(word, 0) + 1
        
        if common_words:
            most_common = max(common_words.items(), key=lambda x: x[1])
            return most_common[0]
        
        return "treatment and management"