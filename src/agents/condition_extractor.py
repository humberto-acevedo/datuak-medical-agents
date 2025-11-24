"""Medical condition identification and extraction from patient data."""

import logging
import re
from typing import List, Dict, Set, Optional, Tuple
from datetime import datetime

from ..models import PatientData, Condition, Diagnosis, MedicalEvent, Medication


logger = logging.getLogger(__name__)


class ConditionExtractor:
    """Extracts and identifies medical conditions from patient data with severity and prevalence ranking."""
    
    def __init__(self):
        """Initialize condition extractor with medical knowledge bases."""
        self.chronic_conditions = self._load_chronic_conditions()
        self.severity_indicators = self._load_severity_indicators()
        self.condition_synonyms = self._load_condition_synonyms()
        self.medication_conditions = self._load_medication_condition_mapping()
    
    def extract_conditions(self, patient_data: PatientData) -> List[Condition]:
        """
        Extract and identify medical conditions from patient data.
        
        Args:
            patient_data: Structured patient medical data
            
        Returns:
            List[Condition]: Identified medical conditions with metadata
        """
        logger.info(f"Extracting conditions for patient {patient_data.patient_id}")
        
        conditions = []
        
        # Extract from explicit diagnoses
        diagnosis_conditions = self._extract_from_diagnoses(patient_data.diagnoses)
        conditions.extend(diagnosis_conditions)
        
        # Extract from medical history events
        history_conditions = self._extract_from_medical_history(patient_data.medical_history)
        conditions.extend(history_conditions)
        
        # Infer from medications
        medication_conditions = self._infer_from_medications(patient_data.medications)
        conditions.extend(medication_conditions)
        
        # Deduplicate and merge similar conditions
        merged_conditions = self._merge_similar_conditions(conditions)
        
        # Rank by severity and prevalence
        ranked_conditions = self._rank_conditions(merged_conditions, patient_data)
        
        logger.info(f"Extracted {len(ranked_conditions)} conditions for patient {patient_data.patient_id}")
        
        return ranked_conditions
    
    def _extract_from_diagnoses(self, diagnoses: List[Diagnosis]) -> List[Condition]:
        """Extract conditions from explicit diagnoses."""
        conditions = []
        
        for diagnosis in diagnoses:
            # Skip diagnoses with no condition name
            if not diagnosis.condition or not diagnosis.condition.strip():
                continue
            
            normalized_name = self._normalize_condition_name(diagnosis.condition)
            
            # Skip "Unknown Condition" entries
            if normalized_name == "Unknown Condition":
                continue
            
            condition = Condition(
                name=normalized_name,
                icd_10_code=diagnosis.icd_10_code,
                severity=self._determine_severity(diagnosis.condition, diagnosis.severity),
                status=diagnosis.status or "active",
                first_diagnosed=diagnosis.date_diagnosed,
                last_updated=diagnosis.date_diagnosed,
                confidence_score=1.0  # High confidence from explicit diagnosis
            )
            conditions.append(condition)
            
        return conditions
    
    def _extract_from_medical_history(self, medical_history: List[MedicalEvent]) -> List[Condition]:
        """Extract conditions mentioned in medical history events."""
        conditions = []
        
        for event in medical_history:
            # Look for condition mentions in event descriptions
            mentioned_conditions = self._find_condition_mentions(event.description)
            
            for condition_name in mentioned_conditions:
                condition = Condition(
                    name=condition_name,
                    severity=self._determine_severity(condition_name),
                    status="active",  # Assume active if mentioned in recent history
                    first_diagnosed=event.date,
                    last_updated=event.date,
                    confidence_score=0.7  # Medium confidence from history mention
                )
                conditions.append(condition)
        
        return conditions
    
    def _infer_from_medications(self, medications: List[Medication]) -> List[Condition]:
        """Infer conditions from prescribed medications."""
        conditions = []
        
        for medication in medications:
            # Check if medication has explicit indication
            if medication.indication:
                condition_name = self._normalize_condition_name(medication.indication)
                condition = Condition(
                    name=condition_name,
                    severity=self._determine_severity(condition_name),
                    status="active" if medication.status == "active" else "managed",
                    first_diagnosed=medication.start_date,
                    last_updated=medication.start_date or "unknown",
                    confidence_score=0.8  # High confidence from medication indication
                )
                conditions.append(condition)
            
            # Infer from medication name using knowledge base
            inferred_conditions = self._infer_conditions_from_medication(medication.name)
            for condition_name in inferred_conditions:
                condition = Condition(
                    name=condition_name,
                    severity=self._determine_severity(condition_name),
                    status="active" if medication.status == "active" else "managed",
                    first_diagnosed=medication.start_date,
                    last_updated=medication.start_date or "unknown",
                    confidence_score=0.6  # Lower confidence from inference
                )
                conditions.append(condition)
        
        return conditions
    
    def _merge_similar_conditions(self, conditions: List[Condition]) -> List[Condition]:
        """Merge similar or duplicate conditions."""
        if not conditions:
            return []
        
        # Group conditions by normalized name
        condition_groups = {}
        
        for condition in conditions:
            normalized_name = self._get_canonical_name(condition.name)
            
            if normalized_name not in condition_groups:
                condition_groups[normalized_name] = []
            condition_groups[normalized_name].append(condition)
        
        # Merge each group
        merged_conditions = []
        for group in condition_groups.values():
            merged_condition = self._merge_condition_group(group)
            merged_conditions.append(merged_condition)
        
        return merged_conditions
    
    def _merge_condition_group(self, conditions: List[Condition]) -> Condition:
        """Merge a group of similar conditions into one."""
        if len(conditions) == 1:
            return conditions[0]
        
        # Use the condition with highest confidence as base
        base_condition = max(conditions, key=lambda c: c.confidence_score)
        
        # Merge information from all conditions
        all_dates = [c.first_diagnosed for c in conditions if c.first_diagnosed and c.first_diagnosed != "unknown"]
        earliest_date = min(all_dates) if all_dates else base_condition.first_diagnosed
        
        all_update_dates = [c.last_updated for c in conditions if c.last_updated and c.last_updated != "unknown"]
        latest_date = max(all_update_dates) if all_update_dates else base_condition.last_updated
        
        # Use most severe severity
        severities = [c.severity for c in conditions if c.severity]
        severity_order = {"high": 3, "moderate": 2, "mild": 1, "low": 0}
        max_severity = max(severities, key=lambda s: severity_order.get(s, 0)) if severities else base_condition.severity
        
        # Use highest confidence ICD code
        icd_codes = [c.icd_10_code for c in conditions if c.icd_10_code]
        best_icd = icd_codes[0] if icd_codes else base_condition.icd_10_code
        
        # Average confidence scores
        avg_confidence = sum(c.confidence_score for c in conditions) / len(conditions)
        
        return Condition(
            name=base_condition.name,
            icd_10_code=best_icd,
            severity=max_severity,
            status=base_condition.status,
            first_diagnosed=earliest_date,
            last_updated=latest_date,
            confidence_score=min(avg_confidence, 1.0)
        )
    
    def _rank_conditions(self, conditions: List[Condition], patient_data: PatientData) -> List[Condition]:
        """Rank conditions by severity and clinical importance."""
        def condition_priority(condition: Condition) -> Tuple[int, int, float]:
            # Priority factors: (severity_score, chronicity_score, confidence_score)
            
            # Severity scoring
            severity_scores = {"high": 4, "moderate": 3, "mild": 2, "low": 1}
            severity_score = severity_scores.get(condition.severity, 0)
            
            # Chronicity scoring (chronic conditions get higher priority)
            chronicity_score = 2 if self._is_chronic_condition(condition.name) else 1
            
            return (severity_score, chronicity_score, condition.confidence_score)
        
        # Sort by priority (descending)
        ranked_conditions = sorted(conditions, key=condition_priority, reverse=True)
        
        return ranked_conditions
    
    def _normalize_condition_name(self, condition_name: str) -> str:
        """Normalize condition name for consistency."""
        if not condition_name:
            return "Unknown Condition"
        
        # Basic normalization
        normalized = condition_name.strip().title()
        
        # Handle common abbreviations and variations
        normalized = re.sub(r'\bDm\b', 'Diabetes Mellitus', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\bHtn\b', 'Hypertension', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\bCad\b', 'Coronary Artery Disease', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\bCopd\b', 'COPD', normalized, flags=re.IGNORECASE)
        
        return normalized
    
    def _determine_severity(self, condition_name: str, explicit_severity: Optional[str] = None) -> Optional[str]:
        """Determine condition severity based on name and indicators."""
        if explicit_severity:
            return explicit_severity.lower()
        
        condition_lower = condition_name.lower()
        
        # High severity indicators
        high_severity_terms = [
            'acute', 'severe', 'critical', 'emergency', 'crisis', 'failure',
            'myocardial infarction', 'stroke', 'cancer', 'malignant'
        ]
        
        # Moderate severity indicators
        moderate_severity_terms = [
            'chronic', 'moderate', 'uncontrolled', 'complicated'
        ]
        
        # Mild severity indicators
        mild_severity_terms = [
            'mild', 'controlled', 'stable', 'managed'
        ]
        
        for term in high_severity_terms:
            if term in condition_lower:
                return "high"
        
        for term in moderate_severity_terms:
            if term in condition_lower:
                return "moderate"
        
        for term in mild_severity_terms:
            if term in condition_lower:
                return "mild"
        
        # Default based on condition type
        if self._is_chronic_condition(condition_name):
            return "moderate"
        
        return None
    
    def _find_condition_mentions(self, text: str) -> List[str]:
        """Find condition mentions in free text."""
        if not text:
            return []
        
        conditions_found = []
        text_lower = text.lower()
        
        # Common condition patterns
        condition_patterns = [
            r'diabetes\s*(mellitus)?',
            r'hypertension|high\s*blood\s*pressure',
            r'hyperlipidemia|high\s*cholesterol',
            r'depression|anxiety',
            r'asthma|copd',
            r'arthritis',
            r'heart\s*disease|coronary\s*artery\s*disease',
            r'kidney\s*disease|renal\s*disease'
        ]
        
        for pattern in condition_patterns:
            matches = re.findall(pattern, text_lower)
            if matches:
                # Convert pattern back to readable condition name
                if 'diabetes' in pattern:
                    conditions_found.append('Diabetes Mellitus')
                elif 'hypertension' in pattern or 'blood pressure' in pattern:
                    conditions_found.append('Hypertension')
                elif 'cholesterol' in pattern or 'hyperlipidemia' in pattern:
                    conditions_found.append('Hyperlipidemia')
                # Add more mappings as needed
        
        return list(set(conditions_found))  # Remove duplicates
    
    def _infer_conditions_from_medication(self, medication_name: str) -> List[str]:
        """Infer conditions from medication name using knowledge base."""
        if not medication_name:
            return []
        
        med_lower = medication_name.lower()
        conditions = []
        
        # Common medication-condition mappings
        med_mappings = self.medication_conditions
        
        for med_pattern, condition in med_mappings.items():
            if med_pattern.lower() in med_lower:
                conditions.append(condition)
        
        return conditions
    
    def _get_canonical_name(self, condition_name: str) -> str:
        """Get canonical name for condition grouping."""
        canonical = condition_name.lower().strip()
        
        # Apply synonym mappings
        for synonyms, canonical_name in self.condition_synonyms.items():
            if canonical in synonyms:
                return canonical_name
        
        return canonical
    
    def _is_chronic_condition(self, condition_name: str) -> bool:
        """Check if condition is typically chronic."""
        return condition_name.lower() in self.chronic_conditions
    
    def _load_chronic_conditions(self) -> Set[str]:
        """Load set of chronic conditions."""
        return {
            'diabetes mellitus', 'diabetes', 'type 2 diabetes', 'type 1 diabetes',
            'hypertension', 'high blood pressure',
            'hyperlipidemia', 'high cholesterol',
            'coronary artery disease', 'heart disease',
            'chronic kidney disease', 'kidney disease',
            'copd', 'chronic obstructive pulmonary disease',
            'asthma',
            'arthritis', 'rheumatoid arthritis', 'osteoarthritis',
            'depression', 'anxiety',
            'hypothyroidism', 'hyperthyroidism'
        }
    
    def _load_severity_indicators(self) -> Dict[str, str]:
        """Load severity indicator mappings."""
        return {
            'acute': 'high',
            'severe': 'high',
            'critical': 'high',
            'moderate': 'moderate',
            'mild': 'mild',
            'controlled': 'mild',
            'stable': 'mild'
        }
    
    def _load_condition_synonyms(self) -> Dict[tuple, str]:
        """Load condition synonym mappings."""
        return {
            ('diabetes', 'dm', 'diabetes mellitus'): 'diabetes mellitus',
            ('hypertension', 'htn', 'high blood pressure'): 'hypertension',
            ('hyperlipidemia', 'high cholesterol', 'dyslipidemia'): 'hyperlipidemia',
            ('coronary artery disease', 'cad', 'heart disease'): 'coronary artery disease',
            ('copd', 'chronic obstructive pulmonary disease'): 'copd'
        }
    
    def _load_medication_condition_mapping(self) -> Dict[str, str]:
        """Load medication to condition mappings."""
        return {
            'metformin': 'Diabetes Mellitus',
            'insulin': 'Diabetes Mellitus',
            'glipizide': 'Diabetes Mellitus',
            'lisinopril': 'Hypertension',
            'amlodipine': 'Hypertension',
            'losartan': 'Hypertension',
            'atenolol': 'Hypertension',
            'atorvastatin': 'Hyperlipidemia',
            'simvastatin': 'Hyperlipidemia',
            'rosuvastatin': 'Hyperlipidemia',
            'albuterol': 'Asthma',
            'fluticasone': 'Asthma',
            'sertraline': 'Depression',
            'escitalopram': 'Depression',
            'levothyroxine': 'Hypothyroidism',
            'omeprazole': 'GERD',
            'pantoprazole': 'GERD'
        }