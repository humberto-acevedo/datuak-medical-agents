"""Medical history summarization with chronological organization and narrative generation."""

import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict

from ..models import (
    PatientData, MedicalSummary, ChronologicalEvent, Condition,
    MedicalEvent, Medication, Procedure, Diagnosis
)


logger = logging.getLogger(__name__)


class MedicalSummarizer:
    """Creates comprehensive medical summaries with chronological organization and narrative generation."""
    
    def __init__(self):
        """Initialize medical summarizer."""
        self.significance_weights = self._load_significance_weights()
    
    def generate_summary(self, patient_data: PatientData, conditions: List[Condition]) -> MedicalSummary:
        """
        Generate comprehensive medical summary from patient data and identified conditions.
        
        Args:
            patient_data: Structured patient medical data
            conditions: Identified medical conditions
            
        Returns:
            MedicalSummary: Comprehensive medical summary with narrative and structured data
        """
        logger.info(f"Generating medical summary for patient {patient_data.patient_id}")
        
        # Generate chronological events
        chronological_events = self._create_chronological_events(patient_data)
        
        # Generate narrative summaries
        summary_text = self._generate_narrative_summary(patient_data, conditions, chronological_events)
        medication_summary = self._generate_medication_summary(patient_data.medications)
        procedure_summary = self._generate_procedure_summary(patient_data.procedures)
        
        # Calculate data quality metrics
        data_quality_score = self._calculate_data_quality(patient_data)
        missing_data_indicators = self._identify_missing_data(patient_data)
        
        summary = MedicalSummary(
            patient_id=patient_data.patient_id,
            summary_text=summary_text,
            key_conditions=conditions,
            medication_summary=medication_summary,
            procedure_summary=procedure_summary,
            chronological_events=chronological_events,
            generated_timestamp=datetime.now(),
            data_quality_score=data_quality_score,
            missing_data_indicators=missing_data_indicators
        )
        
        logger.info(f"Generated medical summary with {len(conditions)} conditions and "
                   f"{len(chronological_events)} chronological events")
        
        return summary
    
    def _create_chronological_events(self, patient_data: PatientData) -> List[ChronologicalEvent]:
        """Create chronologically ordered events from all patient data."""
        events = []
        
        # Add diagnosis events
        for diagnosis in patient_data.diagnoses:
            event = ChronologicalEvent(
                date=diagnosis.date_diagnosed,
                event_type="diagnosis",
                description=f"Diagnosed with {diagnosis.condition}",
                significance=self._determine_event_significance("diagnosis", diagnosis.condition),
                related_conditions=[diagnosis.condition]
            )
            events.append(event)
        
        # Add procedure events
        for procedure in patient_data.procedures:
            event = ChronologicalEvent(
                date=procedure.date,
                event_type="procedure",
                description=f"{procedure.name} performed by {procedure.provider}",
                significance=self._determine_event_significance("procedure", procedure.name),
                related_conditions=self._infer_related_conditions_from_procedure(procedure)
            )
            events.append(event)
        
        # Add medication start events
        for medication in patient_data.medications:
            if medication.start_date and medication.start_date != "unknown":
                event = ChronologicalEvent(
                    date=medication.start_date,
                    event_type="medication_start",
                    description=f"Started {medication.name} {medication.dosage} {medication.frequency}",
                    significance=self._determine_event_significance("medication", medication.name),
                    related_conditions=self._infer_related_conditions_from_medication(medication)
                )
                events.append(event)
        
        # Add medical history events
        for med_event in patient_data.medical_history:
            event = ChronologicalEvent(
                date=med_event.date,
                event_type=med_event.event_type,
                description=med_event.description,
                significance=self._determine_event_significance(med_event.event_type, med_event.description),
                related_conditions=self._extract_conditions_from_description(med_event.description)
            )
            events.append(event)
        
        # Sort chronologically (most recent first)
        events.sort(key=lambda e: self._parse_date(e.date), reverse=True)
        
        return events
    
    def _generate_narrative_summary(self, patient_data: PatientData, 
                                  conditions: List[Condition], 
                                  chronological_events: List[ChronologicalEvent]) -> str:
        """Generate narrative medical summary."""
        summary_parts = []
        
        # Patient overview
        age_text = f", age {patient_data.demographics.age}" if patient_data.demographics.age else ""
        gender_text = f" {patient_data.demographics.gender}" if patient_data.demographics.gender else ""
        
        summary_parts.append(
            f"{patient_data.name} is a{age_text}{gender_text} patient with a medical history significant for "
        )
        
        # Primary conditions
        if conditions:
            primary_conditions = conditions[:3]  # Top 3 conditions
            condition_names = [c.name for c in primary_conditions]
            
            if len(condition_names) == 1:
                summary_parts.append(f"{condition_names[0]}.")
            elif len(condition_names) == 2:
                summary_parts.append(f"{condition_names[0]} and {condition_names[1]}.")
            else:
                summary_parts.append(f"{', '.join(condition_names[:-1])}, and {condition_names[-1]}.")
        else:
            summary_parts.append("no significant documented medical conditions.")
        
        # Current medications
        active_medications = [med for med in patient_data.medications if med.status == "active"]
        if active_medications:
            summary_parts.append(f"\n\nCurrent medications include ")
            med_descriptions = []
            for med in active_medications[:5]:  # Limit to top 5
                med_desc = f"{med.name} {med.dosage}"
                if med.indication:
                    med_desc += f" for {med.indication}"
                med_descriptions.append(med_desc)
            
            if len(med_descriptions) == 1:
                summary_parts.append(f"{med_descriptions[0]}.")
            else:
                summary_parts.append(f"{', '.join(med_descriptions[:-1])}, and {med_descriptions[-1]}.")
        
        # Recent significant events
        recent_events = [e for e in chronological_events if e.significance == "high"][:3]
        if recent_events:
            summary_parts.append(f"\n\nRecent significant medical events include ")
            event_descriptions = [self._format_event_for_narrative(event) for event in recent_events]
            
            if len(event_descriptions) == 1:
                summary_parts.append(f"{event_descriptions[0]}.")
            else:
                summary_parts.append(f"{', '.join(event_descriptions[:-1])}, and {event_descriptions[-1]}.")
        
        # Chronic condition management
        chronic_conditions = [c for c in conditions if self._is_chronic_condition(c.name)]
        if chronic_conditions:
            summary_parts.append(f"\n\nChronic condition management focuses on ")
            chronic_names = [c.name for c in chronic_conditions[:3]]
            
            if len(chronic_names) == 1:
                summary_parts.append(f"{chronic_names[0]} management.")
            else:
                summary_parts.append(f"{', '.join(chronic_names[:-1])}, and {chronic_names[-1]} management.")
        
        return ''.join(summary_parts)
    
    def _generate_medication_summary(self, medications: List[Medication]) -> str:
        """Generate medication summary."""
        if not medications:
            return "No medications documented."
        
        active_meds = [med for med in medications if med.status == "active"]
        inactive_meds = [med for med in medications if med.status != "active"]
        
        summary_parts = []
        
        if active_meds:
            summary_parts.append(f"Currently taking {len(active_meds)} medications: ")
            
            # Group by indication/condition
            med_by_indication = defaultdict(list)
            for med in active_meds:
                indication = med.indication or "General"
                med_by_indication[indication].append(med)
            
            indication_summaries = []
            for indication, meds in med_by_indication.items():
                med_names = [f"{med.name} {med.dosage}" for med in meds]
                if indication != "General":
                    indication_summaries.append(f"{', '.join(med_names)} for {indication}")
                else:
                    indication_summaries.append(', '.join(med_names))
            
            summary_parts.append('; '.join(indication_summaries) + ".")
        
        if inactive_meds:
            summary_parts.append(f" Previously prescribed {len(inactive_meds)} medications that are no longer active.")
        
        return ''.join(summary_parts)
    
    def _generate_procedure_summary(self, procedures: List[Procedure]) -> str:
        """Generate procedure summary."""
        if not procedures:
            return "No procedures documented."
        
        # Group procedures by type/category
        procedure_categories = defaultdict(list)
        for procedure in procedures:
            category = self._categorize_procedure(procedure.name)
            procedure_categories[category].append(procedure)
        
        summary_parts = []
        summary_parts.append(f"Medical procedures include {len(procedures)} documented procedures: ")
        
        category_summaries = []
        for category, procs in procedure_categories.items():
            if len(procs) == 1:
                proc = procs[0]
                category_summaries.append(f"{proc.name} ({proc.date})")
            else:
                recent_proc = max(procs, key=lambda p: self._parse_date(p.date))
                category_summaries.append(f"{len(procs)} {category} procedures, most recent: {recent_proc.name} ({recent_proc.date})")
        
        summary_parts.append('; '.join(category_summaries) + ".")
        
        return ''.join(summary_parts)
    
    def _determine_event_significance(self, event_type: str, description: str) -> str:
        """Determine the significance level of a medical event."""
        description_lower = description.lower()
        
        # High significance indicators
        high_significance_terms = [
            'acute', 'emergency', 'critical', 'severe', 'hospitalization', 'admission',
            'surgery', 'operation', 'myocardial infarction', 'stroke', 'cancer',
            'diagnosis', 'new diagnosis'
        ]
        
        # Medium significance indicators
        medium_significance_terms = [
            'procedure', 'test', 'imaging', 'biopsy', 'endoscopy', 'catheterization',
            'medication change', 'dose adjustment'
        ]
        
        # Check for high significance
        for term in high_significance_terms:
            if term in description_lower:
                return "high"
        
        # Check for medium significance
        for term in medium_significance_terms:
            if term in description_lower:
                return "medium"
        
        # Event type based significance
        if event_type in ['diagnosis', 'procedure', 'surgery']:
            return "high"
        elif event_type in ['medication_start', 'visit']:
            return "medium"
        
        return "low"
    
    def _calculate_data_quality(self, patient_data: PatientData) -> float:
        """Calculate overall data quality score."""
        quality_factors = []
        
        # Demographics completeness
        demo_score = 0
        if patient_data.demographics.age:
            demo_score += 0.3
        if patient_data.demographics.gender:
            demo_score += 0.2
        if patient_data.demographics.date_of_birth:
            demo_score += 0.3
        if patient_data.demographics.address or patient_data.demographics.phone:
            demo_score += 0.2
        quality_factors.append(demo_score)
        
        # Medical data completeness
        has_diagnoses = len(patient_data.diagnoses) > 0
        has_medications = len(patient_data.medications) > 0
        has_procedures = len(patient_data.procedures) > 0
        has_history = len(patient_data.medical_history) > 0
        
        medical_score = sum([has_diagnoses, has_medications, has_procedures, has_history]) / 4
        quality_factors.append(medical_score)
        
        # Data detail quality
        detail_score = 0
        total_items = 0
        
        # Check diagnosis detail
        for diagnosis in patient_data.diagnoses:
            total_items += 1
            if diagnosis.icd_10_code:
                detail_score += 0.5
            if diagnosis.severity:
                detail_score += 0.3
            if diagnosis.date_diagnosed and diagnosis.date_diagnosed != "unknown":
                detail_score += 0.2
        
        # Check medication detail
        for medication in patient_data.medications:
            total_items += 1
            if medication.dosage and medication.frequency:
                detail_score += 0.4
            if medication.indication:
                detail_score += 0.3
            if medication.start_date:
                detail_score += 0.3
        
        if total_items > 0:
            detail_quality = detail_score / total_items
            quality_factors.append(detail_quality)
        
        # Overall quality score
        return sum(quality_factors) / len(quality_factors) if quality_factors else 0.0
    
    def _identify_missing_data(self, patient_data: PatientData) -> List[str]:
        """Identify missing or incomplete data elements."""
        missing_indicators = []
        
        # Check demographics
        if not patient_data.demographics.age:
            missing_indicators.append("Patient age not documented")
        if not patient_data.demographics.gender:
            missing_indicators.append("Patient gender not documented")
        if not patient_data.demographics.date_of_birth:
            missing_indicators.append("Date of birth not documented")
        
        # Check medical data
        if not patient_data.diagnoses:
            missing_indicators.append("No diagnoses documented")
        if not patient_data.medications:
            missing_indicators.append("No medications documented")
        
        # Check data quality issues
        diagnoses_without_dates = [d for d in patient_data.diagnoses 
                                 if not d.date_diagnosed or d.date_diagnosed == "unknown"]
        if diagnoses_without_dates:
            missing_indicators.append(f"{len(diagnoses_without_dates)} diagnoses missing dates")
        
        medications_without_details = [m for m in patient_data.medications 
                                     if not m.dosage or not m.frequency]
        if medications_without_details:
            missing_indicators.append(f"{len(medications_without_details)} medications missing dosage/frequency")
        
        return missing_indicators
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string to datetime object for sorting."""
        if not date_str or date_str == "unknown":
            return datetime.min
        
        try:
            # Try common date formats
            for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%Y-%m-%d %H:%M:%S"]:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            
            # If no format matches, return minimum date
            return datetime.min
            
        except Exception:
            return datetime.min
    
    def _format_event_for_narrative(self, event: ChronologicalEvent) -> str:
        """Format chronological event for narrative inclusion."""
        if event.event_type == "diagnosis":
            return f"diagnosis of {event.description.replace('Diagnosed with ', '')}"
        elif event.event_type == "procedure":
            return f"{event.description.lower()}"
        elif event.event_type == "medication_start":
            return f"initiation of {event.description.replace('Started ', '')}"
        else:
            return event.description.lower()
    
    def _is_chronic_condition(self, condition_name: str) -> bool:
        """Check if condition is chronic."""
        chronic_conditions = {
            'diabetes mellitus', 'diabetes', 'hypertension', 'hyperlipidemia',
            'coronary artery disease', 'chronic kidney disease', 'copd', 'asthma',
            'arthritis', 'depression', 'anxiety', 'hypothyroidism'
        }
        return condition_name.lower() in chronic_conditions
    
    def _categorize_procedure(self, procedure_name: str) -> str:
        """Categorize procedure by type."""
        procedure_lower = procedure_name.lower()
        
        if any(term in procedure_lower for term in ['surgery', 'operation', 'surgical']):
            return "surgical"
        elif any(term in procedure_lower for term in ['imaging', 'scan', 'x-ray', 'ct', 'mri', 'ultrasound']):
            return "imaging"
        elif any(term in procedure_lower for term in ['biopsy', 'endoscopy', 'colonoscopy', 'catheter']):
            return "diagnostic"
        elif any(term in procedure_lower for term in ['lab', 'blood', 'test']):
            return "laboratory"
        else:
            return "general"
    
    def _infer_related_conditions_from_procedure(self, procedure: Procedure) -> List[str]:
        """Infer related conditions from procedure."""
        conditions = []
        
        if procedure.indication:
            conditions.append(procedure.indication)
        
        # Infer from procedure name
        proc_lower = procedure.name.lower()
        if 'cardiac' in proc_lower or 'heart' in proc_lower:
            conditions.append("Heart Disease")
        elif 'colonoscopy' in proc_lower:
            conditions.append("Colorectal Screening")
        elif 'mammogram' in proc_lower:
            conditions.append("Breast Cancer Screening")
        
        return conditions
    
    def _infer_related_conditions_from_medication(self, medication: Medication) -> List[str]:
        """Infer related conditions from medication."""
        conditions = []
        
        if medication.indication:
            conditions.append(medication.indication)
        
        # Common medication-condition mappings
        med_lower = medication.name.lower()
        if 'metformin' in med_lower or 'insulin' in med_lower:
            conditions.append("Diabetes Mellitus")
        elif 'lisinopril' in med_lower or 'amlodipine' in med_lower:
            conditions.append("Hypertension")
        elif 'atorvastatin' in med_lower or 'simvastatin' in med_lower:
            conditions.append("Hyperlipidemia")
        
        return conditions
    
    def _extract_conditions_from_description(self, description: str) -> List[str]:
        """Extract condition mentions from text description."""
        conditions = []
        desc_lower = description.lower()
        
        # Common condition patterns
        if 'diabetes' in desc_lower:
            conditions.append("Diabetes Mellitus")
        if 'hypertension' in desc_lower or 'blood pressure' in desc_lower:
            conditions.append("Hypertension")
        if 'cholesterol' in desc_lower:
            conditions.append("Hyperlipidemia")
        
        return conditions
    
    def _load_significance_weights(self) -> Dict[str, float]:
        """Load significance weights for different event types."""
        return {
            'diagnosis': 1.0,
            'procedure': 0.8,
            'surgery': 1.0,
            'medication_start': 0.6,
            'visit': 0.4,
            'emergency': 1.0
        }