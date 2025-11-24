"""Research validation and citation verification system."""
import re
import logging
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
from urllib.parse import urlparse

from .hallucination_detector import ValidationIssue, ValidationSeverity, ValidationType
from ..models import ResearchAnalysis
from ..utils.audit_logger import AuditLogger

logger = logging.getLogger(__name__)

@dataclass
class CitationValidationResult:
    """Result of citation validation."""
    is_valid: bool
    confidence_score: float
    issues: List[str]
    suggestions: List[str]
    metadata: Dict[str, Any]

class ResearchValidator:
    """Validates research citations and findings for accuracy and authenticity."""
    
    def __init__(self, audit_logger: Optional[AuditLogger] = None):
        """
        Initialize research validator.
        
        Args:
            audit_logger: Optional audit logger for compliance
        """
        self.audit_logger = audit_logger
        
        # Known reputable medical journals
        self.reputable_journals = {
            # High impact medical journals
            "new england journal of medicine": {"impact_factor": 91.2, "tier": "tier1"},
            "the lancet": {"impact_factor": 79.3, "tier": "tier1"},
            "jama": {"impact_factor": 56.3, "tier": "tier1"},
            "nature medicine": {"impact_factor": 53.4, "tier": "tier1"},
            "cell": {"impact_factor": 41.6, "tier": "tier1"},
            
            # Specialty journals
            "journal of the american college of cardiology": {"impact_factor": 24.0, "tier": "tier2"},
            "diabetes care": {"impact_factor": 19.1, "tier": "tier2"},
            "hypertension": {"impact_factor": 9.8, "tier": "tier2"},
            "american journal of respiratory and critical care medicine": {"impact_factor": 19.3, "tier": "tier2"},
            "journal of clinical oncology": {"impact_factor": 44.5, "tier": "tier2"},
            
            # General medical journals
            "bmj": {"impact_factor": 39.9, "tier": "tier2"},
            "annals of internal medicine": {"impact_factor": 25.3, "tier": "tier2"},
            "plos medicine": {"impact_factor": 13.8, "tier": "tier3"},
            "journal of medical internet research": {"impact_factor": 7.1, "tier": "tier3"},
            "bmc medicine": {"impact_factor": 9.3, "tier": "tier3"}
        }
        
        # Study type hierarchy (higher is better evidence)
        self.study_type_hierarchy = {
            "systematic_review": 10,
            "meta_analysis": 9,
            "randomized_controlled_trial": 8,
            "cohort_study": 6,
            "case_control_study": 5,
            "cross_sectional_study": 4,
            "case_series": 3,
            "case_report": 2,
            "expert_opinion": 1,
            "unknown": 0
        }
        
        # Common predatory journal patterns
        self.predatory_patterns = [
            r"international.*journal.*of.*research",
            r"global.*journal.*of.*science",
            r"world.*journal.*of.*medicine",
            r"american.*research.*journal",
            r"european.*journal.*of.*research"
        ]
        
        # Valid DOI pattern
        self.doi_pattern = r"10\.\d{4,}/[^\s]+"
        
        # Valid PubMed ID pattern
        self.pubmed_pattern = r"^\d{8}$"
        
        logger.info("Research validator initialized")
    
    def validate_research_findings(self, research_findings: List[Dict[str, Any]], 
                                 patient_conditions: List[str]) -> List[ValidationIssue]:
        """
        Validate research findings for authenticity and relevance.
        
        Args:
            research_findings: List of research findings to validate
            patient_conditions: List of patient conditions for relevance checking
            
        Returns:
            List[ValidationIssue]: List of validation issues found
        """
        issues = []
        
        if not research_findings:
            issues.append(ValidationIssue(
                issue_id=f"RES_{datetime.now().strftime('%Y%m%d_%H%M%S')}_001",
                validation_type=ValidationType.COMPLETENESS,
                severity=ValidationSeverity.WARNING,
                description="No research findings provided for validation",
                field_name="research_findings",
                suggestions=["Ensure research search is functioning properly"]
            ))
            return issues
        
        for i, finding in enumerate(research_findings):
            finding_issues = self._validate_single_finding(finding, i, patient_conditions)
            issues.extend(finding_issues)
        
        # Validate overall research quality
        overall_issues = self._validate_research_quality(research_findings)
        issues.extend(overall_issues)
        
        logger.info(f"Research validation completed: {len(issues)} issues found across {len(research_findings)} findings")
        
        return issues
    
    def _validate_single_finding(self, finding: Dict[str, Any], index: int, 
                                patient_conditions: List[str]) -> List[ValidationIssue]:
        """Validate a single research finding."""
        issues = []
        
        # Validate required fields
        required_fields = ["title", "authors", "journal", "publication_year"]
        for field in required_fields:
            if field not in finding or not finding[field]:
                issues.append(ValidationIssue(
                    issue_id=f"RES_{datetime.now().strftime('%Y%m%d_%H%M%S')}_F{index:03d}_001",
                    validation_type=ValidationType.COMPLETENESS,
                    severity=ValidationSeverity.WARNING,
                    description=f"Missing required field: {field}",
                    field_name=f"research_findings[{index}].{field}",
                    suggestions=[f"Ensure {field} is extracted from research source"]
                ))
                continue
        
        # Validate title
        title_issues = self._validate_title(finding.get("title", ""), index)
        issues.extend(title_issues)
        
        # Validate authors
        authors_issues = self._validate_authors(finding.get("authors", []), index)
        issues.extend(authors_issues)
        
        # Validate journal
        journal_issues = self._validate_journal(finding.get("journal", ""), index)
        issues.extend(journal_issues)
        
        # Validate publication year
        year_issues = self._validate_publication_year(finding.get("publication_year"), index)
        issues.extend(year_issues)
        
        # Validate DOI if present
        if "doi" in finding and finding["doi"]:
            doi_issues = self._validate_doi(finding["doi"], index)
            issues.extend(doi_issues)
        
        # Validate PubMed ID if present
        if "pubmed_id" in finding and finding["pubmed_id"]:
            pubmed_issues = self._validate_pubmed_id(finding["pubmed_id"], index)
            issues.extend(pubmed_issues)
        
        # Validate relevance to patient conditions
        relevance_issues = self._validate_relevance(finding, patient_conditions, index)
        issues.extend(relevance_issues)
        
        # Validate study type if present
        if "study_type" in finding and finding["study_type"]:
            study_type_issues = self._validate_study_type(finding["study_type"], index)
            issues.extend(study_type_issues)
        
        return issues
    
    def _validate_title(self, title: str, index: int) -> List[ValidationIssue]:
        """Validate research paper title."""
        issues = []
        
        if not title or len(title.strip()) < 10:
            issues.append(ValidationIssue(
                issue_id=f"RES_{datetime.now().strftime('%Y%m%d_%H%M%S')}_F{index:03d}_TITLE",
                validation_type=ValidationType.COMPLETENESS,
                severity=ValidationSeverity.WARNING,
                description="Research title is missing or too short",
                field_name=f"research_findings[{index}].title",
                actual_value=title,
                suggestions=["Ensure complete title is extracted from research source"]
            ))
        
        # Check for suspicious title patterns
        suspicious_patterns = [
            r"^(a|an|the)\s+study\s+of\s*$",  # Too generic
            r"research\s+paper\s+on",  # Generic research paper
            r"^untitled",  # Untitled papers
            r"^\d+$"  # Just numbers
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, title.lower()):
                issues.append(ValidationIssue(
                    issue_id=f"RES_{datetime.now().strftime('%Y%m%d_%H%M%S')}_F{index:03d}_TITLE_SUSP",
                    validation_type=ValidationType.ACCURACY,
                    severity=ValidationSeverity.INFO,
                    description="Research title appears generic or suspicious",
                    field_name=f"research_findings[{index}].title",
                    actual_value=title,
                    suggestions=["Verify title accuracy from original source"]
                ))
        
        return issues
    
    def _validate_authors(self, authors: List[str], index: int) -> List[ValidationIssue]:
        """Validate research paper authors."""
        issues = []
        
        if not authors or len(authors) == 0:
            issues.append(ValidationIssue(
                issue_id=f"RES_{datetime.now().strftime('%Y%m%d_%H%M%S')}_F{index:03d}_AUTH_EMPTY",
                validation_type=ValidationType.COMPLETENESS,
                severity=ValidationSeverity.WARNING,
                description="No authors listed for research finding",
                field_name=f"research_findings[{index}].authors",
                suggestions=["Ensure author information is extracted from research source"]
            ))
            return issues
        
        # Validate author name format
        valid_author_pattern = r"^[A-Za-z\s\-'\.]+,\s*[A-Za-z\s\-'\.]+$|^[A-Za-z\s\-'\.]+$"
        
        for i, author in enumerate(authors):
            if not author or len(author.strip()) < 2:
                issues.append(ValidationIssue(
                    issue_id=f"RES_{datetime.now().strftime('%Y%m%d_%H%M%S')}_F{index:03d}_AUTH_{i:02d}",
                    validation_type=ValidationType.DATA_CONSISTENCY,
                    severity=ValidationSeverity.INFO,
                    description=f"Author name appears invalid: {author}",
                    field_name=f"research_findings[{index}].authors[{i}]",
                    actual_value=author,
                    suggestions=["Verify author name format"]
                ))
        
        # Check for too many authors (potential data extraction error)
        if len(authors) > 20:
            issues.append(ValidationIssue(
                issue_id=f"RES_{datetime.now().strftime('%Y%m%d_%H%M%S')}_F{index:03d}_AUTH_MANY",
                validation_type=ValidationType.LOGICAL_COHERENCE,
                severity=ValidationSeverity.INFO,
                description=f"Unusually high number of authors: {len(authors)}",
                field_name=f"research_findings[{index}].authors",
                actual_value=str(len(authors)),
                suggestions=["Verify author list extraction accuracy"]
            ))
        
        return issues
    
    def _validate_journal(self, journal: str, index: int) -> List[ValidationIssue]:
        """Validate journal name and reputation."""
        issues = []
        
        if not journal or len(journal.strip()) < 3:
            issues.append(ValidationIssue(
                issue_id=f"RES_{datetime.now().strftime('%Y%m%d_%H%M%S')}_F{index:03d}_JOUR_EMPTY",
                validation_type=ValidationType.COMPLETENESS,
                severity=ValidationSeverity.WARNING,
                description="Journal name is missing or too short",
                field_name=f"research_findings[{index}].journal",
                actual_value=journal,
                suggestions=["Ensure journal name is extracted from research source"]
            ))
            return issues
        
        journal_lower = journal.lower().strip()
        
        # Check against reputable journals
        journal_info = self.reputable_journals.get(journal_lower)
        if journal_info:
            # Known reputable journal - this is good
            pass
        else:
            # Check for predatory journal patterns
            is_predatory = any(re.search(pattern, journal_lower) for pattern in self.predatory_patterns)
            
            if is_predatory:
                issues.append(ValidationIssue(
                    issue_id=f"RES_{datetime.now().strftime('%Y%m%d_%H%M%S')}_F{index:03d}_JOUR_PRED",
                    validation_type=ValidationType.ACCURACY,
                    severity=ValidationSeverity.WARNING,
                    description=f"Journal name matches predatory journal pattern: {journal}",
                    field_name=f"research_findings[{index}].journal",
                    actual_value=journal,
                    suggestions=["Verify journal reputation and authenticity"]
                ))
            else:
                # Unknown journal - not necessarily bad, but worth noting
                issues.append(ValidationIssue(
                    issue_id=f"RES_{datetime.now().strftime('%Y%m%d_%H%M%S')}_F{index:03d}_JOUR_UNK",
                    validation_type=ValidationType.ACCURACY,
                    severity=ValidationSeverity.INFO,
                    description=f"Journal not in known reputable journal database: {journal}",
                    field_name=f"research_findings[{index}].journal",
                    actual_value=journal,
                    suggestions=["Verify journal reputation if needed"]
                ))
        
        return issues
    
    def _validate_publication_year(self, pub_year: Any, index: int) -> List[ValidationIssue]:
        """Validate publication year."""
        issues = []
        
        if pub_year is None:
            issues.append(ValidationIssue(
                issue_id=f"RES_{datetime.now().strftime('%Y%m%d_%H%M%S')}_F{index:03d}_YEAR_MISS",
                validation_type=ValidationType.COMPLETENESS,
                severity=ValidationSeverity.WARNING,
                description="Publication year is missing",
                field_name=f"research_findings[{index}].publication_year",
                suggestions=["Ensure publication year is extracted from research source"]
            ))
            return issues
        
        try:
            year = int(pub_year)
            current_year = datetime.now().year
            
            # Check for reasonable year range
            if year < 1900:
                issues.append(ValidationIssue(
                    issue_id=f"RES_{datetime.now().strftime('%Y%m%d_%H%M%S')}_F{index:03d}_YEAR_OLD",
                    validation_type=ValidationType.LOGICAL_COHERENCE,
                    severity=ValidationSeverity.WARNING,
                    description=f"Publication year seems too old: {year}",
                    field_name=f"research_findings[{index}].publication_year",
                    actual_value=str(year),
                    suggestions=["Verify publication year accuracy"]
                ))
            elif year > current_year:
                issues.append(ValidationIssue(
                    issue_id=f"RES_{datetime.now().strftime('%Y%m%d_%H%M%S')}_F{index:03d}_YEAR_FUT",
                    validation_type=ValidationType.LOGICAL_COHERENCE,
                    severity=ValidationSeverity.ERROR,
                    description=f"Publication year is in the future: {year}",
                    field_name=f"research_findings[{index}].publication_year",
                    actual_value=str(year),
                    suggestions=["Verify publication year accuracy"]
                ))
            elif year < current_year - 20:
                # Very old research - might be less relevant
                issues.append(ValidationIssue(
                    issue_id=f"RES_{datetime.now().strftime('%Y%m%d_%H%M%S')}_F{index:03d}_YEAR_DATED",
                    validation_type=ValidationType.ACCURACY,
                    severity=ValidationSeverity.INFO,
                    description=f"Research is quite old ({year}) - may be less relevant",
                    field_name=f"research_findings[{index}].publication_year",
                    actual_value=str(year),
                    suggestions=["Consider prioritizing more recent research"]
                ))
        
        except (ValueError, TypeError):
            issues.append(ValidationIssue(
                issue_id=f"RES_{datetime.now().strftime('%Y%m%d_%H%M%S')}_F{index:03d}_YEAR_INV",
                validation_type=ValidationType.DATA_CONSISTENCY,
                severity=ValidationSeverity.WARNING,
                description=f"Publication year is not a valid number: {pub_year}",
                field_name=f"research_findings[{index}].publication_year",
                actual_value=str(pub_year),
                suggestions=["Ensure publication year is extracted as a numeric value"]
            ))
        
        return issues
    
    def _validate_doi(self, doi: str, index: int) -> List[ValidationIssue]:
        """Validate DOI format."""
        issues = []
        
        if not re.match(self.doi_pattern, doi):
            issues.append(ValidationIssue(
                issue_id=f"RES_{datetime.now().strftime('%Y%m%d_%H%M%S')}_F{index:03d}_DOI_INV",
                validation_type=ValidationType.DATA_CONSISTENCY,
                severity=ValidationSeverity.WARNING,
                description=f"DOI format appears invalid: {doi}",
                field_name=f"research_findings[{index}].doi",
                actual_value=doi,
                suggestions=["Verify DOI format (should be 10.xxxx/xxxxx)"]
            ))
        
        return issues
    
    def _validate_pubmed_id(self, pubmed_id: str, index: int) -> List[ValidationIssue]:
        """Validate PubMed ID format."""
        issues = []
        
        if not re.match(self.pubmed_pattern, str(pubmed_id)):
            issues.append(ValidationIssue(
                issue_id=f"RES_{datetime.now().strftime('%Y%m%d_%H%M%S')}_F{index:03d}_PMID_INV",
                validation_type=ValidationType.DATA_CONSISTENCY,
                severity=ValidationSeverity.WARNING,
                description=f"PubMed ID format appears invalid: {pubmed_id}",
                field_name=f"research_findings[{index}].pubmed_id",
                actual_value=str(pubmed_id),
                suggestions=["Verify PubMed ID format (should be 8 digits)"]
            ))
        
        return issues
    
    def _validate_relevance(self, finding: Dict[str, Any], 
                          patient_conditions: List[str], index: int) -> List[ValidationIssue]:
        """Validate research relevance to patient conditions."""
        issues = []
        
        if not patient_conditions:
            return issues  # Can't validate relevance without conditions
        
        title = finding.get("title", "").lower()
        abstract = finding.get("abstract", "").lower()
        
        # Check if any patient conditions are mentioned in title or abstract
        condition_mentions = 0
        for condition in patient_conditions:
            condition_lower = condition.lower()
            if condition_lower in title or condition_lower in abstract:
                condition_mentions += 1
        
        relevance_score = condition_mentions / len(patient_conditions) if patient_conditions else 0
        
        # Check explicit relevance score if provided
        explicit_relevance = finding.get("relevance_score", 0)
        
        if explicit_relevance < 0.3 or relevance_score < 0.1:
            issues.append(ValidationIssue(
                issue_id=f"RES_{datetime.now().strftime('%Y%m%d_%H%M%S')}_F{index:03d}_REL_LOW",
                validation_type=ValidationType.LOGICAL_COHERENCE,
                severity=ValidationSeverity.WARNING,
                description=f"Research finding appears to have low relevance to patient conditions",
                field_name=f"research_findings[{index}].relevance",
                actual_value=f"calculated: {relevance_score:.2f}, explicit: {explicit_relevance:.2f}",
                suggestions=["Review research correlation algorithm for accuracy"]
            ))
        
        return issues
    
    def _validate_study_type(self, study_type: str, index: int) -> List[ValidationIssue]:
        """Validate study type."""
        issues = []
        
        study_type_lower = study_type.lower().replace(" ", "_")
        
        if study_type_lower not in self.study_type_hierarchy:
            issues.append(ValidationIssue(
                issue_id=f"RES_{datetime.now().strftime('%Y%m%d_%H%M%S')}_F{index:03d}_TYPE_UNK",
                validation_type=ValidationType.DATA_CONSISTENCY,
                severity=ValidationSeverity.INFO,
                description=f"Unknown study type: {study_type}",
                field_name=f"research_findings[{index}].study_type",
                actual_value=study_type,
                suggestions=["Verify study type classification"]
            ))
        
        return issues
    
    def _validate_research_quality(self, research_findings: List[Dict[str, Any]]) -> List[ValidationIssue]:
        """Validate overall research quality and diversity."""
        issues = []
        
        if len(research_findings) < 3:
            issues.append(ValidationIssue(
                issue_id=f"RES_{datetime.now().strftime('%Y%m%d_%H%M%S')}_QUAL_FEW",
                validation_type=ValidationType.COMPLETENESS,
                severity=ValidationSeverity.INFO,
                description=f"Limited number of research findings: {len(research_findings)}",
                field_name="research_findings_count",
                actual_value=str(len(research_findings)),
                suggestions=["Consider expanding research search to find more relevant studies"]
            ))
        
        # Check for diversity in publication years
        years = []
        for finding in research_findings:
            year = finding.get("publication_year")
            if year:
                try:
                    years.append(int(year))
                except (ValueError, TypeError):
                    pass
        
        if years:
            year_range = max(years) - min(years)
            if year_range < 2:
                issues.append(ValidationIssue(
                    issue_id=f"RES_{datetime.now().strftime('%Y%m%d_%H%M%S')}_QUAL_YEAR_RANGE",
                    validation_type=ValidationType.LOGICAL_COHERENCE,
                    severity=ValidationSeverity.INFO,
                    description=f"Limited year range in research findings: {year_range} years",
                    field_name="research_year_diversity",
                    actual_value=f"{min(years)}-{max(years)}",
                    suggestions=["Consider including research from different time periods"]
                ))
        
        # Check for journal diversity
        journals = set()
        for finding in research_findings:
            journal = finding.get("journal")
            if journal:
                journals.add(journal.lower())
        
        if len(journals) < len(research_findings) / 2:
            issues.append(ValidationIssue(
                issue_id=f"RES_{datetime.now().strftime('%Y%m%d_%H%M%S')}_QUAL_JOUR_DIV",
                validation_type=ValidationType.LOGICAL_COHERENCE,
                severity=ValidationSeverity.INFO,
                description=f"Limited journal diversity: {len(journals)} unique journals for {len(research_findings)} findings",
                field_name="research_journal_diversity",
                actual_value=f"{len(journals)}/{len(research_findings)}",
                suggestions=["Consider including research from diverse journal sources"]
            ))
        
        return issues
    
    def calculate_research_credibility_score(self, research_findings: List[Dict[str, Any]]) -> float:
        """
        Calculate overall credibility score for research findings.
        
        Args:
            research_findings: List of research findings
            
        Returns:
            float: Credibility score between 0 and 1
        """
        if not research_findings:
            return 0.0
        
        total_score = 0.0
        
        for finding in research_findings:
            finding_score = 0.0
            
            # Journal reputation score (0-0.4)
            journal = finding.get("journal", "").lower()
            if journal in self.reputable_journals:
                journal_info = self.reputable_journals[journal]
                if journal_info["tier"] == "tier1":
                    finding_score += 0.4
                elif journal_info["tier"] == "tier2":
                    finding_score += 0.3
                else:
                    finding_score += 0.2
            else:
                finding_score += 0.1  # Unknown journal gets minimal score
            
            # Publication recency score (0-0.2)
            pub_year = finding.get("publication_year")
            if pub_year:
                try:
                    year = int(pub_year)
                    current_year = datetime.now().year
                    years_old = current_year - year
                    
                    if years_old <= 2:
                        finding_score += 0.2
                    elif years_old <= 5:
                        finding_score += 0.15
                    elif years_old <= 10:
                        finding_score += 0.1
                    else:
                        finding_score += 0.05
                except (ValueError, TypeError):
                    finding_score += 0.05
            
            # Study type score (0-0.2)
            study_type = finding.get("study_type", "").lower().replace(" ", "_")
            if study_type in self.study_type_hierarchy:
                type_score = self.study_type_hierarchy[study_type] / 10.0
                finding_score += type_score * 0.2
            else:
                finding_score += 0.05
            
            # Citation/DOI presence score (0-0.1)
            if finding.get("doi") or finding.get("pubmed_id"):
                finding_score += 0.1
            else:
                finding_score += 0.05
            
            # Relevance score (0-0.1)
            relevance = finding.get("relevance_score", 0.5)
            finding_score += relevance * 0.1
            
            total_score += finding_score
        
        # Average score across all findings
        average_score = total_score / len(research_findings)
        
        # Apply penalty for very few findings
        if len(research_findings) < 3:
            average_score *= 0.8
        
        return min(1.0, average_score)
    
    def get_research_quality_metrics(self, research_findings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get comprehensive research quality metrics.
        
        Args:
            research_findings: List of research findings
            
        Returns:
            Dict[str, Any]: Quality metrics
        """
        if not research_findings:
            return {
                "total_findings": 0,
                "credibility_score": 0.0,
                "journal_diversity": 0,
                "year_range": 0,
                "tier1_journals": 0,
                "tier2_journals": 0,
                "tier3_journals": 0,
                "unknown_journals": 0,
                "average_relevance": 0.0,
                "recent_studies": 0,
                "high_evidence_studies": 0
            }
        
        # Basic metrics
        total_findings = len(research_findings)
        credibility_score = self.calculate_research_credibility_score(research_findings)
        
        # Journal analysis
        journals = set()
        tier1_count = tier2_count = tier3_count = unknown_count = 0
        
        for finding in research_findings:
            journal = finding.get("journal", "").lower()
            if journal:
                journals.add(journal)
                
                if journal in self.reputable_journals:
                    tier = self.reputable_journals[journal]["tier"]
                    if tier == "tier1":
                        tier1_count += 1
                    elif tier == "tier2":
                        tier2_count += 1
                    else:
                        tier3_count += 1
                else:
                    unknown_count += 1
        
        # Year analysis
        years = []
        for finding in research_findings:
            year = finding.get("publication_year")
            if year:
                try:
                    years.append(int(year))
                except (ValueError, TypeError):
                    pass
        
        year_range = max(years) - min(years) if years else 0
        current_year = datetime.now().year
        recent_studies = len([y for y in years if current_year - y <= 5])
        
        # Relevance analysis
        relevance_scores = []
        for finding in research_findings:
            relevance = finding.get("relevance_score", 0)
            if relevance:
                relevance_scores.append(relevance)
        
        average_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0
        
        # Evidence level analysis
        high_evidence_studies = 0
        for finding in research_findings:
            study_type = finding.get("study_type", "").lower().replace(" ", "_")
            if study_type in self.study_type_hierarchy:
                if self.study_type_hierarchy[study_type] >= 7:  # RCT or higher
                    high_evidence_studies += 1
        
        return {
            "total_findings": total_findings,
            "credibility_score": credibility_score,
            "journal_diversity": len(journals),
            "year_range": year_range,
            "tier1_journals": tier1_count,
            "tier2_journals": tier2_count,
            "tier3_journals": tier3_count,
            "unknown_journals": unknown_count,
            "average_relevance": average_relevance,
            "recent_studies": recent_studies,
            "high_evidence_studies": high_evidence_studies
        }