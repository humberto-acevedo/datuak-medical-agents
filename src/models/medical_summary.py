"""Medical summary models for analysis results."""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class Condition:
    """Medical condition with metadata."""
    name: str
    icd_10_code: Optional[str] = None
    severity: Optional[str] = None
    status: str = "active"  # active, resolved, chronic
    first_diagnosed: Optional[str] = None
    last_updated: Optional[str] = None
    confidence_score: float = 1.0  # 0.0 to 1.0


@dataclass_json
@dataclass
class ChronologicalEvent:
    """Medical event organized chronologically."""
    date: str
    event_type: str
    description: str
    significance: str  # high, medium, low
    related_conditions: List[str]


@dataclass_json
@dataclass
class MedicalSummary:
    """Comprehensive medical summary with analysis."""
    patient_id: str
    summary_text: str
    key_conditions: List[Condition]
    medication_summary: str
    procedure_summary: str
    chronological_events: List[ChronologicalEvent]
    generated_timestamp: datetime
    data_quality_score: float  # 0.0 to 1.0
    missing_data_indicators: List[str]
    
    def validate(self) -> List[str]:
        """Validate medical summary data."""
        errors = []
        
        if not self.patient_id:
            errors.append("Patient ID is required")
        if not self.summary_text:
            errors.append("Summary text cannot be empty")
        if self.data_quality_score < 0 or self.data_quality_score > 1:
            errors.append("Data quality score must be between 0 and 1")
            
        # Validate conditions
        for condition in self.key_conditions:
            if not condition.name:
                errors.append("Condition name cannot be empty")
            if condition.confidence_score < 0 or condition.confidence_score > 1:
                errors.append(f"Invalid confidence score for condition {condition.name}")
                
        return errors
    
    def get_high_priority_conditions(self) -> List[Condition]:
        """Get conditions marked as high severity or chronic."""
        return [
            condition for condition in self.key_conditions 
            if condition.severity == "high" or condition.status == "chronic"
        ]
    
    def get_recent_events(self, days: int = 30) -> List[ChronologicalEvent]:
        """Get events from the last N days."""
        # For now, return high significance events
        # TODO: Implement actual date filtering
        return [
            event for event in self.chronological_events 
            if event.significance == "high"
        ]