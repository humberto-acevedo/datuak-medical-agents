"""
Quality Assurance Engine for Medical Record Analysis System.

This module provides a unified interface for quality assurance, validation,
and hallucination prevention across the entire system.
"""

from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from ..quality.hallucination_detector import (
    HallucinationDetector,
    ValidationIssue,
    ValidationSeverity
)
from ..quality.data_validator import DataValidationService

# Backwards-compatible alias for older tests / callers
DataValidator = DataValidationService
from ..quality.research_validator import ResearchValidator
from ..quality.quality_metrics import QualityMetricsCollector


class QualityLevel(Enum):
    """Overall quality level assessment."""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    CRITICAL = "critical"
    UNACCEPTABLE = "unacceptable"


@dataclass
class QualityAssessment:
    """Complete quality assessment result."""
    quality_level: QualityLevel
    overall_score: float
    validation_issues: List[ValidationIssue]
    data_quality_score: float
    hallucination_risk_score: float
    research_quality_score: float
    recommendations: List[str]
    timestamp: datetime
    
    @property
    def hallucination_risk(self) -> float:
        """Alias for hallucination_risk_score for backward compatibility."""
        return self.hallucination_risk_score
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert quality assessment to dictionary format."""
        return {
            'quality_level': self.quality_level.value,
            'overall_score': self.overall_score,
            'validation_issues': [
                issue.to_dict() if hasattr(issue, 'to_dict') else str(issue)
                for issue in self.validation_issues
            ],
            'data_quality_score': self.data_quality_score,
            'hallucination_risk_score': self.hallucination_risk_score,
            'research_quality_score': self.research_quality_score,
            'recommendations': self.recommendations,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
        }


class QualityAssuranceEngine:
    """
    Unified quality assurance engine that coordinates all quality checks.
    """
    
    def __init__(self):
        """Initialize quality assurance engine."""
    def __init__(self, audit_logger: Optional[Any] = None, error_handler: Optional[Any] = None):
        """Initialize quality assurance engine.

        Accept optional `audit_logger` and `error_handler` for backward compatibility
        with older callers and tests that construct the engine with these params.
        """
        self.hallucination_detector = HallucinationDetector()
        self.data_validator = DataValidationService(audit_logger=audit_logger, error_handler=error_handler)
        self.research_validator = ResearchValidator()
        self.metrics_collector = QualityMetricsCollector()
        self.audit_logger = audit_logger  # Optional audit logger
        self.error_handler = error_handler  # Optional error handler
        
    def assess_analysis_quality(self, 
                                patient_data: Any = None,
                                medical_summary: Any = None,
                                research_analysis: Any = None,
                                analysis_report: Any = None) -> QualityAssessment:
        """
        Perform comprehensive quality assessment of analysis.
        
        Supports multiple calling conventions:
        1. assess_analysis_quality(patient_data, medical_summary, research_analysis, analysis_report)
        2. assess_analysis_quality(analysis_report) - when called with single AnalysisReport
        
        Args:
            patient_data: Parsed patient data (or AnalysisReport if single parameter)
            medical_summary: Generated medical summary (or None if using analysis_report)
            research_analysis: Research correlation results (or None if using analysis_report)
            analysis_report: Final analysis report (can be the only parameter)
            
        Returns:
            QualityAssessment: Complete quality assessment
        """
        try:
            # Handle case where analysis_report is passed as first positional parameter
            # Check if patient_data is actually an AnalysisReport
            if patient_data is not None and hasattr(patient_data, 'patient_data') and hasattr(patient_data, 'medical_summary'):
                # patient_data is actually an AnalysisReport
                analysis_report = patient_data
                patient_data = None
            
            # Handle case where only analysis_report is provided
            if patient_data is None and analysis_report is not None:
                if hasattr(analysis_report, 'patient_data'):
                    patient_data = analysis_report.patient_data
                if hasattr(analysis_report, 'medical_summary'):
                    medical_summary = analysis_report.medical_summary
                if hasattr(analysis_report, 'research_analysis'):
                    research_analysis = analysis_report.research_analysis
            
            validation_issues = []
        except AttributeError as e:
            # Log the specific attribute error for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"AttributeError in assess_analysis_quality: {e}")
            logger.error(f"analysis_report type: {type(analysis_report)}")
            logger.error(f"analysis_report attributes: {dir(analysis_report) if analysis_report else 'None'}")
            raise
        
        try:
            # Validate patient data using the private method (it returns a list of ValidationIssue)
            if patient_data:
                data_validation_issues = self.data_validator._validate_patient_data(patient_data)
                validation_issues.extend(data_validation_issues)
        except AttributeError as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"AttributeError in patient data validation: {e}")
            logger.error(f"patient_data type: {type(patient_data)}")
            raise
        
        try:
            # Check for hallucinations in summary
            if medical_summary and patient_data:
                # Convert medical_summary to dict for validation
                summary_dict = {}
                if hasattr(medical_summary, 'to_dict'):
                    summary_dict = medical_summary.to_dict()
                elif hasattr(medical_summary, '__dict__'):
                    summary_dict = medical_summary.__dict__
                
                patient_id = patient_data.patient_id if hasattr(patient_data, 'patient_id') else "unknown"
                source_xml = patient_data.raw_xml if hasattr(patient_data, 'raw_xml') else ""
                
                hallucination_issues = self.hallucination_detector.validate_against_source(
                    summary_dict,
                    source_xml,
                    patient_id
                )
                validation_issues.extend(hallucination_issues)
        except AttributeError as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"AttributeError in hallucination detection: {e}")
            logger.error(f"medical_summary type: {type(medical_summary)}")
            raise
        
        # Validate research citations
        if research_analysis and hasattr(research_analysis, 'research_findings'):
            for finding in research_analysis.research_findings:
                research_validation = self.research_validator.validate_citation(finding)
                if not research_validation.is_valid:
                    validation_issues.append(
                        ValidationIssue(
                            severity=ValidationSeverity.WARNING,
                            message=f"Research citation issue: {research_validation.issues}",
                            field="research_findings",
                            value=finding.title if hasattr(finding, 'title') else str(finding)
                        )
                    )
        
        # Calculate scores
        data_quality_score = self._calculate_data_quality_score(patient_data, validation_issues)
        hallucination_risk_score = self._calculate_hallucination_risk(validation_issues)
        research_quality_score = self._calculate_research_quality(research_analysis)
        
        # Calculate overall score
        overall_score = (
            data_quality_score * 0.4 +
            (1.0 - hallucination_risk_score) * 0.3 +
            research_quality_score * 0.3
        )
        
        # Determine quality level
        quality_level = self._determine_quality_level(overall_score, validation_issues)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            validation_issues,
            data_quality_score,
            hallucination_risk_score,
            research_quality_score
        )
        
        return QualityAssessment(
            quality_level=quality_level,
            overall_score=overall_score,
            validation_issues=validation_issues,
            data_quality_score=data_quality_score,
            hallucination_risk_score=hallucination_risk_score,
            research_quality_score=research_quality_score,
            recommendations=recommendations,
            timestamp=datetime.now()
        )
    
    def _calculate_data_quality_score(self, patient_data: Any, issues: List[ValidationIssue]) -> float:
        """Calculate data quality score."""
        if hasattr(patient_data, 'data_quality_score'):
            base_score = patient_data.data_quality_score
        else:
            base_score = 0.8
        
        # Reduce score based on critical issues
        critical_issues = [i for i in issues if i.severity == ValidationSeverity.CRITICAL]
        error_issues = [i for i in issues if i.severity == ValidationSeverity.ERROR]
        
        penalty = len(critical_issues) * 0.2 + len(error_issues) * 0.1
        return max(0.0, base_score - penalty)
    
    def _calculate_hallucination_risk(self, issues: List[ValidationIssue]) -> float:
        """Calculate hallucination risk score (0.0 = no risk, 1.0 = high risk)."""
        hallucination_issues = [
            i for i in issues 
            if 'hallucination' in i.message.lower() or 'fabricated' in i.message.lower()
        ]
        
        if not hallucination_issues:
            return 0.0
        
        # Weight by severity
        risk_score = 0.0
        for issue in hallucination_issues:
            if issue.severity == ValidationSeverity.CRITICAL:
                risk_score += 0.3
            elif issue.severity == ValidationSeverity.ERROR:
                risk_score += 0.2
            elif issue.severity == ValidationSeverity.WARNING:
                risk_score += 0.1
        
        return min(1.0, risk_score)
    
    def _calculate_research_quality(self, research_analysis: Any) -> float:
        """Calculate research quality score."""
        if not research_analysis:
            return 0.5
        
        if hasattr(research_analysis, 'analysis_confidence'):
            return research_analysis.analysis_confidence
        
        return 0.7
    
    def _determine_quality_level(self, overall_score: float, issues: List[ValidationIssue]) -> QualityLevel:
        """Determine overall quality level."""
        # Check for critical issues first
        critical_issues = [i for i in issues if i.severity == ValidationSeverity.CRITICAL]
        if critical_issues:
            return QualityLevel.CRITICAL
        
        # Determine by score (matching README thresholds)
        if overall_score >= 0.95:
            return QualityLevel.EXCELLENT
        elif overall_score >= 0.85:
            return QualityLevel.GOOD
        elif overall_score >= 0.70:
            return QualityLevel.ACCEPTABLE
        elif overall_score >= 0.50:
            return QualityLevel.POOR
        else:
            return QualityLevel.UNACCEPTABLE
    
    def _generate_recommendations(self,
                                 issues: List[ValidationIssue],
                                 data_quality: float,
                                 hallucination_risk: float,
                                 research_quality: float) -> List[str]:
        """Generate recommendations based on quality assessment."""
        recommendations = []
        
        # Data quality recommendations
        if data_quality < 0.7:
            recommendations.append(
                "Data quality is below acceptable threshold. Review source XML for completeness."
            )
        
        # Hallucination risk recommendations
        if hallucination_risk > 0.3:
            recommendations.append(
                "High hallucination risk detected. Verify all extracted information against source data."
            )
        
        # Research quality recommendations
        if research_quality < 0.6:
            recommendations.append(
                "Research quality is low. Consider manual review of research correlations."
            )
        
        # Issue-specific recommendations
        critical_issues = [i for i in issues if i.severity == ValidationSeverity.CRITICAL]
        if critical_issues:
            recommendations.append(
                f"Critical issues found: {len(critical_issues)}. Immediate review required."
            )
        
        error_issues = [i for i in issues if i.severity == ValidationSeverity.ERROR]
        if error_issues:
            recommendations.append(
                f"Errors found: {len(error_issues)}. Review and correction recommended."
            )
        
        if not recommendations:
            recommendations.append("Quality assessment passed. No immediate action required.")
        
        return recommendations
    
    def get_quality_statistics(self) -> Dict[str, Any]:
        """Get quality statistics from metrics collector."""
        return self.metrics_collector.get_statistics()


# Global instance
_qa_engine: Optional[QualityAssuranceEngine] = None


def initialize_quality_assurance(audit_logger: Optional[Any] = None,
                                error_handler: Optional[Any] = None) -> QualityAssuranceEngine:
    """
    Initialize and return global quality assurance engine.
    
    Args:
        audit_logger: Optional audit logger for HIPAA compliance
        error_handler: Optional error handler for error management
        
    Returns:
        QualityAssuranceEngine: Initialized quality assurance engine
    """
    global _qa_engine
    if _qa_engine is None:
        _qa_engine = QualityAssuranceEngine()
        # Store references if provided
        if audit_logger:
            _qa_engine.audit_logger = audit_logger
        if error_handler:
            _qa_engine.error_handler = error_handler
    return _qa_engine


def get_quality_assurance_engine() -> QualityAssuranceEngine:
    """Get the global quality assurance engine instance."""
    if _qa_engine is None:
        return initialize_quality_assurance()
    return _qa_engine


# Export all public classes and functions
__all__ = [
    'QualityLevel',
    'QualityAssessment',
    'QualityAssuranceEngine',
    'DataValidator',
    'ValidationSeverity',
    'ValidationIssue',
    'initialize_quality_assurance',
    'get_quality_assurance_engine'
]
