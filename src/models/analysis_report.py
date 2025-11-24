"""Complete analysis report model combining all agent outputs."""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from dataclasses_json import dataclass_json

from .patient_data import PatientData
from .medical_summary import MedicalSummary
from .research_analysis import ResearchAnalysis


@dataclass_json
@dataclass
class AnalysisReport:
    """Complete medical record analysis report."""
    patient_data: PatientData
    medical_summary: MedicalSummary
    research_analysis: ResearchAnalysis
    generated_timestamp: datetime
    report_id: str
    processing_time_seconds: float
    agent_versions: dict  # Track which agent versions generated this report
    quality_metrics: dict  # Overall quality and confidence metrics
    
    def validate(self) -> List[str]:
        """Validate complete analysis report."""
        errors = []
        
        # Basic validation
        if not self.report_id:
            errors.append("Report ID is required")
        if not self.patient_data:
            errors.append("Patient data is required")
        if not self.medical_summary:
            errors.append("Medical summary is required")
        if not self.research_analysis:
            errors.append("Research analysis is required")
            
        # Cross-validation between components
        if self.patient_data.patient_id != self.medical_summary.patient_id:
            errors.append("Patient ID mismatch between data and summary")
            
        # Validate individual components
        errors.extend([f"Patient data: {error}" for error in self.patient_data.validate()])
        errors.extend([f"Medical summary: {error}" for error in self.medical_summary.validate()])
        errors.extend([f"Research analysis: {error}" for error in self.research_analysis.validate()])
        
        return errors
    
    def get_overall_confidence_score(self) -> float:
        """Calculate overall confidence score for the analysis."""
        data_quality = self.medical_summary.data_quality_score
        research_quality = len(self.research_analysis.get_high_quality_findings()) / max(1, len(self.research_analysis.research_findings))
        
        # Weighted average: 60% data quality, 40% research quality
        return (data_quality * 0.6) + (research_quality * 0.4)
    
    def get_key_insights(self) -> List[str]:
        """Extract key insights from the complete analysis."""
        insights = []
        
        # High priority conditions
        high_priority = self.medical_summary.get_high_priority_conditions()
        if high_priority:
            insights.append(f"High priority conditions identified: {', '.join([c.name for c in high_priority])}")
        
        # Research-backed findings
        high_quality_research = self.research_analysis.get_high_quality_findings()
        if high_quality_research:
            insights.append(f"Found {len(high_quality_research)} high-quality research papers supporting the analysis")
        
        # Data quality concerns
        if self.medical_summary.missing_data_indicators:
            insights.append(f"Data limitations: {', '.join(self.medical_summary.missing_data_indicators)}")
            
        return insights
    
    def to_summary_dict(self) -> dict:
        """Create a summary dictionary for quick overview."""
        return {
            "report_id": self.report_id,
            "patient_id": self.patient_data.patient_id,
            "patient_name": self.patient_data.name,
            "generated_at": self.generated_timestamp.isoformat(),
            "processing_time": f"{self.processing_time_seconds:.2f}s",
            "confidence_score": f"{self.get_overall_confidence_score():.2f}",
            "conditions_count": len(self.medical_summary.key_conditions),
            "research_papers": len(self.research_analysis.research_findings),
            "high_quality_research": len(self.research_analysis.get_high_quality_findings()),
            "key_insights": self.get_key_insights()
        }