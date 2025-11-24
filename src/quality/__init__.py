"""Quality assurance and hallucination prevention package."""

from .hallucination_detector import (
    HallucinationDetector,
    MedicalTerminologyValidator,
    ValidationIssue,
    ValidationSeverity,
    ValidationType
)
from .data_validator import DataValidationService
from .research_validator import ResearchValidator, CitationValidationResult
from .quality_metrics import (
    QualityMetricsCollector,
    QualityMetric,
    QualityTrend,
    MetricType
)

__all__ = [
    'HallucinationDetector',
    'MedicalTerminologyValidator', 
    'ValidationIssue',
    'ValidationSeverity',
    'ValidationType',
    'DataValidationService',
    'ResearchValidator',
    'CitationValidationResult',
    'QualityMetricsCollector',
    'QualityMetric',
    'QualityTrend',
    'MetricType'
]