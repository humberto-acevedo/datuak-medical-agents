"""Patient data models for medical record analysis."""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class Demographics:
    """Patient demographic information."""
    age: Optional[int] = None
    gender: Optional[str] = None
    date_of_birth: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    emergency_contact: Optional[str] = None


@dataclass_json
@dataclass
class MedicalEvent:
    """A medical event in patient history."""
    event_id: str
    date: str
    event_type: str  # diagnosis, procedure, visit, etc.
    description: str
    provider: Optional[str] = None
    location: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None  # active, resolved, chronic, etc.


@dataclass_json
@dataclass
class Medication:
    """Patient medication information."""
    medication_id: str
    name: str
    dosage: str
    frequency: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    prescribing_physician: Optional[str] = None
    indication: Optional[str] = None
    status: str = "active"  # active, discontinued, completed


@dataclass_json
@dataclass
class Procedure:
    """Medical procedure information."""
    procedure_id: str
    name: str
    date: str
    provider: str
    location: Optional[str] = None
    indication: Optional[str] = None
    outcome: Optional[str] = None
    complications: Optional[str] = None
    cpt_code: Optional[str] = None


@dataclass_json
@dataclass
class Diagnosis:
    """Medical diagnosis information."""
    diagnosis_id: str
    condition: str
    date_diagnosed: str
    icd_10_code: Optional[str] = None
    severity: Optional[str] = None
    status: str = "active"  # active, resolved, chronic
    diagnosing_physician: Optional[str] = None
    notes: Optional[str] = None


@dataclass_json
@dataclass
class PatientData:
    """Complete patient medical data structure."""
    patient_id: str
    name: str
    demographics: Demographics
    medical_history: List[MedicalEvent]
    medications: List[Medication]
    procedures: List[Procedure]
    diagnoses: List[Diagnosis]
    raw_xml: str
    extraction_timestamp: datetime
    
    def validate(self) -> List[str]:
        """Validate patient data integrity and return any validation errors."""
        errors = []
        
        # Required field validation
        if not self.patient_id:
            errors.append("Patient ID is required")
        if not self.name:
            errors.append("Patient name is required")
        if not self.raw_xml:
            errors.append("Raw XML source is required for audit trail")
            
        # Data consistency validation
        if self.demographics.age and (self.demographics.age < 0 or self.demographics.age > 150):
            errors.append("Invalid age value")
            
        # Medication validation
        for med in self.medications:
            if not med.name or not med.dosage:
                errors.append(f"Incomplete medication data for {med.medication_id}")
                
        # Diagnosis validation
        for diag in self.diagnoses:
            if not diag.condition:
                errors.append(f"Missing condition for diagnosis {diag.diagnosis_id}")
                
        return errors
    
    def get_active_conditions(self) -> List[str]:
        """Get list of active medical conditions."""
        return [diag.condition for diag in self.diagnoses if diag.status == "active"]
    
    def get_chronic_conditions(self) -> List[str]:
        """Get list of chronic medical conditions."""
        return [diag.condition for diag in self.diagnoses if diag.status == "chronic"]