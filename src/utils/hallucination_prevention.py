"""Hallucination prevention system for AI-generated medical content."""
import logging
import re
from typing import Dict, Any, List, Optional, Tuple, Set, Callable
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import json

from .enhanced_logging import log_operation
from .error_handler import ErrorHandler, ErrorContext
from .audit_logger import AuditLogger
from ..models.exceptions import HallucinationDetectedError

logger = logging.getLogger(__name__)

class HallucinationRiskLevel(Enum):
    """Hallucination risk levels."""
    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class HallucinationCheck:
    """Represents a hallucination check result."""
    risk_level: HallucinationRiskLevel
    confidence: float
    detected_patterns: List[str]
    suggested_corrections: List[str]
    requires_human_review: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "risk_level": getattr(self.risk_level, 'value', str(self.risk_level)),
            "confidence": self.confidence,
            "detected_patterns": self.detected_patterns,
            "suggested_corrections": self.suggested_corrections,
            "requires_human_review": self.requires_human_review,
            "timestamp": datetime.now().isoformat()
        }

class MedicalKnowledgeValidator:
    """Validates medical content against known medical knowledge."""
    
    def __init__(self):
        # Valid medical terminology and patterns
        self.valid_medical_terms = self._load_medical_terms()
        self.valid_drug_names = self._load_drug_names()
        self.valid_condition_names = self._load_condition_names()
        self.valid_procedure_names = self._load_procedure_names()
        
        # Medical code patterns
        self.icd10_pattern = re.compile(r'^[A-Z]\d{2}(\.\d{1,3})?$')
        self.cpt_pattern = re.compile(r'^\d{5}$')
        self.ndc_pattern = re.compile(r'^\d{4,5}-\d{3,4}-\d{1,2}$')
        
        # Suspicious patterns that indicate potential hallucination
        self.hallucination_indicators = [
            # Fictional medical terms
            re.compile(r'\b(?:fictitious|imaginary|made-up|invented|fake)\s+(?:condition|disease|syndrome|disorder)\b', re.IGNORECASE),
            
            # Non-medical references
            re.compile(r'\b(?:star wars|harry potter|marvel|dc comics|pokemon|disney)\b', re.IGNORECASE),
            
            # Impossible medical scenarios
            re.compile(r'\b(?:immortal|invincible|superhuman|magical|supernatural)\s+(?:healing|recovery|treatment)\b', re.IGNORECASE),
            
            # Placeholder text
            re.compile(r'\b(?:lorem ipsum|placeholder|example|test|dummy|sample)\b', re.IGNORECASE),
            
            # Nonsensical medical combinations
            re.compile(r'\b(?:digital|virtual|cyber|robotic)\s+(?:organ|limb|brain|heart)\b', re.IGNORECASE),
        ]
        
        logger.info("Medical knowledge validator initialized")
    
    def _load_medical_terms(self) -> Set[str]:
        """Load valid medical terms (in production, this would load from a comprehensive database)."""
        return {
            # Common medical conditions
            'hypertension', 'diabetes', 'asthma', 'copd', 'pneumonia', 'bronchitis',
            'arthritis', 'osteoporosis', 'depression', 'anxiety', 'migraine', 'epilepsy',
            'cardiovascular', 'respiratory', 'gastrointestinal', 'neurological',
            'dermatological', 'orthopedic', 'psychiatric', 'oncological', 'endocrine',
            
            # Medical specialties
            'cardiology', 'neurology', 'oncology', 'psychiatry', 'dermatology',
            'orthopedics', 'gastroenterology', 'pulmonology', 'nephrology',
            
            # Common symptoms
            'fever', 'cough', 'dyspnea', 'chest pain', 'abdominal pain', 'headache',
            'nausea', 'vomiting', 'diarrhea', 'constipation', 'fatigue', 'weakness',
            
            # Medical procedures
            'biopsy', 'endoscopy', 'colonoscopy', 'mammography', 'ultrasound',
            'mri', 'ct scan', 'x-ray', 'ecg', 'ekg', 'blood test', 'urinalysis'
        }
    
    def _load_drug_names(self) -> Set[str]:
        """Load valid drug names (in production, this would load from FDA drug database)."""
        return {
            # Common medications
            'aspirin', 'ibuprofen', 'acetaminophen', 'lisinopril', 'metformin',
            'atorvastatin', 'amlodipine', 'omeprazole', 'levothyroxine', 'albuterol',
            'metoprolol', 'losartan', 'simvastatin', 'gabapentin', 'sertraline',
            'fluoxetine', 'citalopram', 'escitalopram', 'venlafaxine', 'duloxetine',
            
            # Antibiotic classes
            'penicillin', 'amoxicillin', 'azithromycin', 'ciprofloxacin', 'doxycycline',
            'cephalexin', 'clindamycin', 'vancomycin', 'gentamicin', 'tobramycin'
        }
    
    def _load_condition_names(self) -> Set[str]:
        """Load valid medical condition names."""
        return {
            'acute myocardial infarction', 'congestive heart failure', 'atrial fibrillation',
            'chronic obstructive pulmonary disease', 'type 2 diabetes mellitus',
            'essential hypertension', 'major depressive disorder', 'generalized anxiety disorder',
            'rheumatoid arthritis', 'osteoarthritis', 'chronic kidney disease',
            'irritable bowel syndrome', 'gastroesophageal reflux disease', 'peptic ulcer disease',
            'alzheimer disease', 'parkinson disease', 'multiple sclerosis', 'epilepsy',
            'breast cancer', 'lung cancer', 'colon cancer', 'prostate cancer'
        }
    
    def _load_procedure_names(self) -> Set[str]:
        """Load valid medical procedure names."""
        return {
            'coronary angioplasty', 'cardiac catheterization', 'echocardiogram',
            'electrocardiogram', 'stress test', 'holter monitor', 'chest x-ray',
            'computed tomography', 'magnetic resonance imaging', 'ultrasound',
            'colonoscopy', 'endoscopy', 'bronchoscopy', 'arthroscopy',
            'laparoscopy', 'thoracotomy', 'appendectomy', 'cholecystectomy',
            'hip replacement', 'knee replacement', 'cataract surgery'
        }
    
    def validate_medical_content(self, content: str, content_type: str = "general") -> HallucinationCheck:
        """
        Validate medical content for potential hallucinations.
        
        Args:
            content: Medical content to validate
            content_type: Type of content (condition, medication, procedure, etc.)
            
        Returns:
            HallucinationCheck: Validation results
        """
        detected_patterns = []
        risk_score = 0.0
        suggested_corrections = []
        
        if not content or not content.strip():
            return HallucinationCheck(
                risk_level=HallucinationRiskLevel.MINIMAL,
                confidence=1.0,
                detected_patterns=[],
                suggested_corrections=[],
                requires_human_review=False
            )
        
        content_lower = content.lower()
        
        # Check for hallucination indicators
        for pattern in self.hallucination_indicators:
            matches = pattern.findall(content)
            if matches:
                detected_patterns.append(f"Suspicious pattern: {', '.join(set(matches))}")
                risk_score += 0.4
        
        # Validate medical terms based on content type
        if content_type == "medication":
            risk_score += self._validate_medications(content, detected_patterns, suggested_corrections)
        elif content_type == "condition":
            risk_score += self._validate_conditions(content, detected_patterns, suggested_corrections)
        elif content_type == "procedure":
            risk_score += self._validate_procedures(content, detected_patterns, suggested_corrections)
        else:
            # General medical content validation
            risk_score += self._validate_general_medical_content(content, detected_patterns, suggested_corrections)
        
        # Check for medical code validity
        risk_score += self._validate_medical_codes(content, detected_patterns, suggested_corrections)
        
        # Check for logical consistency
        risk_score += self._check_logical_consistency(content, detected_patterns, suggested_corrections)
        
        # Normalize risk score
        risk_score = min(risk_score, 1.0)
        
        # Determine risk level
        if risk_score >= 0.8:
            risk_level = HallucinationRiskLevel.CRITICAL
        elif risk_score >= 0.6:
            risk_level = HallucinationRiskLevel.HIGH
        elif risk_score >= 0.4:
            risk_level = HallucinationRiskLevel.MEDIUM
        elif risk_score >= 0.2:
            risk_level = HallucinationRiskLevel.LOW
        else:
            risk_level = HallucinationRiskLevel.MINIMAL
        
        requires_review = risk_level in [HallucinationRiskLevel.HIGH, HallucinationRiskLevel.CRITICAL]
        
        return HallucinationCheck(
            risk_level=risk_level,
            confidence=1.0 - risk_score,
            detected_patterns=detected_patterns,
            suggested_corrections=suggested_corrections,
            requires_human_review=requires_review
        )
    
    def _validate_medications(self, content: str, detected_patterns: List[str], 
                            suggested_corrections: List[str]) -> float:
        """Validate medication-related content."""
        risk_score = 0.0
        content_lower = content.lower()
        
        # Extract potential drug names
        potential_drugs = re.findall(r'\b[a-z]{3,}\b', content_lower)
        
        unknown_drugs = []
        for drug in potential_drugs:
            if drug not in self.valid_drug_names and len(drug) > 4:
                # Check if it might be a brand name or generic variation
                if not any(known_drug in drug or drug in known_drug for known_drug in self.valid_drug_names):
                    unknown_drugs.append(drug)
        
        if unknown_drugs:
            detected_patterns.append(f"Unknown medications: {', '.join(unknown_drugs[:3])}")
            suggested_corrections.append("Verify medication names against standard drug databases")
            risk_score += 0.3 * min(len(unknown_drugs) / 5, 1.0)
        
        # Check for impossible dosages
        dosage_patterns = re.findall(r'(\d+(?:\.\d+)?)\s*(mg|g|ml|mcg|units?)', content_lower)
        for amount, unit in dosage_patterns:
            try:
                dose = float(amount)
                if unit in ['g', 'grams'] and dose > 50:  # Very high gram dosages are suspicious
                    detected_patterns.append(f"Unusually high dosage: {amount} {unit}")
                    suggested_corrections.append("Verify dosage amounts are realistic")
                    risk_score += 0.2
                elif unit in ['mg', 'milligrams'] and dose > 10000:  # Very high mg dosages
                    detected_patterns.append(f"Unusually high dosage: {amount} {unit}")
                    risk_score += 0.2
            except ValueError:
                pass
        
        return risk_score
    
    def _validate_conditions(self, content: str, detected_patterns: List[str], 
                           suggested_corrections: List[str]) -> float:
        """Validate medical condition content."""
        risk_score = 0.0
        content_lower = content.lower()
        
        # Check for known condition names
        found_conditions = []
        for condition in self.valid_condition_names:
            if condition in content_lower:
                found_conditions.append(condition)
        
        # If no known conditions found in a condition-focused content, it's suspicious
        if not found_conditions and len(content) > 20:
            detected_patterns.append("No recognized medical conditions found")
            suggested_corrections.append("Verify condition names against medical terminology")
            risk_score += 0.3
        
        # Check for contradictory statements
        contradictions = [
            (r'\basymptomatic\b.*\bsevere symptoms\b', 'asymptomatic with severe symptoms'),
            (r'\bnormal\b.*\babnormal\b', 'normal and abnormal contradiction'),
            (r'\bno history\b.*\bchronic\b', 'no history but chronic condition')
        ]
        
        for pattern, description in contradictions:
            if re.search(pattern, content_lower):
                detected_patterns.append(f"Contradiction detected: {description}")
                suggested_corrections.append("Review for logical consistency")
                risk_score += 0.4
        
        return risk_score
    
    def _validate_procedures(self, content: str, detected_patterns: List[str], 
                          suggested_corrections: List[str]) -> float:
        """Validate medical procedure content."""
        risk_score = 0.0
        content_lower = content.lower()
        
        # Check for known procedures
        found_procedures = []
        for procedure in self.valid_procedure_names:
            if procedure in content_lower:
                found_procedures.append(procedure)
        
        # Check for impossible procedure combinations
        impossible_combinations = [
            (r'\boutpatient\b.*\bmajor surgery\b', 'outpatient major surgery'),
            (r'\bminimally invasive\b.*\bopen surgery\b', 'minimally invasive open surgery')
        ]
        
        for pattern, description in impossible_combinations:
            if re.search(pattern, content_lower):
                detected_patterns.append(f"Impossible combination: {description}")
                suggested_corrections.append("Review procedure descriptions for accuracy")
                risk_score += 0.3
        
        return risk_score
    
    def _validate_general_medical_content(self, content: str, detected_patterns: List[str], 
                                        suggested_corrections: List[str]) -> float:
        """Validate general medical content."""
        risk_score = 0.0
        content_lower = content.lower()
        
        # Check for medical term density
        medical_terms_found = 0
        total_words = len(content.split())
        
        for term in self.valid_medical_terms:
            if term in content_lower:
                medical_terms_found += 1
        
        # If very few medical terms in supposedly medical content
        if total_words > 20 and medical_terms_found / total_words < 0.1:
            detected_patterns.append("Low medical terminology density")
            suggested_corrections.append("Ensure content is medically relevant")
            risk_score += 0.2
        
        return risk_score
    
    def _validate_medical_codes(self, content: str, detected_patterns: List[str], 
                              suggested_corrections: List[str]) -> float:
        """Validate medical codes in content."""
        risk_score = 0.0
        
        # Find potential medical codes
        potential_icd_codes = re.findall(r'\b[A-Z]\d{2,3}(?:\.\d+)?\b', content)
        potential_cpt_codes = re.findall(r'\b\d{5}\b', content)
        
        # Validate ICD codes
        for code in potential_icd_codes:
            if not self.icd10_pattern.match(code):
                detected_patterns.append(f"Invalid ICD code format: {code}")
                suggested_corrections.append("Verify medical code formats")
                risk_score += 0.2
        
        # Basic validation for CPT codes (more complex validation would require database lookup)
        for code in potential_cpt_codes:
            if not self.cpt_pattern.match(code):
                detected_patterns.append(f"Invalid CPT code format: {code}")
                risk_score += 0.2
        
        return risk_score
    
    def _check_logical_consistency(self, content: str, detected_patterns: List[str], 
                                 suggested_corrections: List[str]) -> float:
        """Check for logical consistency in medical content."""
        risk_score = 0.0
        content_lower = content.lower()
        
        # Check for temporal inconsistencies
        temporal_issues = [
            (r'\bbefore birth\b.*\badult\b', 'before birth but adult'),
            (r'\bpediatric\b.*\bgeriatric\b', 'pediatric and geriatric'),
            (r'\bacute\b.*\bchronic\b.*\bsame\b', 'acute and chronic same condition')
        ]
        
        for pattern, description in temporal_issues:
            if re.search(pattern, content_lower):
                detected_patterns.append(f"Temporal inconsistency: {description}")
                suggested_corrections.append("Review temporal relationships in content")
                risk_score += 0.3
        
        # Check for anatomical impossibilities
        anatomical_issues = [
            (r'\bheart\b.*\blung\b.*\bsame location\b', 'heart and lung same location'),
            (r'\bbrain\b.*\babdomen\b', 'brain in abdomen')
        ]
        
        for pattern, description in anatomical_issues:
            if re.search(pattern, content_lower):
                detected_patterns.append(f"Anatomical inconsistency: {description}")
                risk_score += 0.4
        
        return risk_score

class HallucinationPreventionSystem:
    """Main hallucination prevention system."""
    
    def __init__(self, 
                 audit_logger: Optional[AuditLogger] = None,
                 error_handler: Optional[ErrorHandler] = None,
                 strict_mode: bool = True):
        """
        Initialize hallucination prevention system.
        
        Args:
            audit_logger: Optional audit logger for compliance
            error_handler: Optional error handler for issues
            strict_mode: If True, raises exceptions for high-risk hallucinations
        """
        self.audit_logger = audit_logger
        self.error_handler = error_handler
        self.strict_mode = strict_mode
        
        self.medical_validator = MedicalKnowledgeValidator()
        
        # Prevention statistics
        self.prevention_stats = {
            "total_checks": 0,
            "hallucinations_detected": 0,
            "high_risk_blocked": 0,
            "human_reviews_required": 0,
            "by_risk_level": {getattr(level, 'value', str(level)): 0 for level in HallucinationRiskLevel}
        }
        
        logger.info(f"Hallucination prevention system initialized (strict_mode: {strict_mode})")
    
    def check_content(self, content: str, content_type: str = "general", 
                     patient_id: Optional[str] = None, 
                     operation: str = "content_validation") -> HallucinationCheck:
        """
        Check content for potential hallucinations.
        
        Args:
            content: Content to check for hallucinations
            content_type: Type of content (general, medication, condition, procedure)
            patient_id: Optional patient ID for logging
            operation: Operation name for logging
            
        Returns:
            HallucinationCheck: Check results
            
        Raises:
            HallucinationDetectedError: If strict_mode is True and high-risk hallucination detected
        """
        with log_operation(operation, "hallucination_prevention", patient_id or "UNKNOWN"):
            
            self.prevention_stats["total_checks"] += 1
            
            # Perform validation
            check_result = self.medical_validator.validate_medical_content(content, content_type)
            
            # Update statistics
            key = getattr(check_result.risk_level, 'value', str(check_result.risk_level))
            self.prevention_stats["by_risk_level"][key] += 1
            
            if check_result.risk_level in [HallucinationRiskLevel.HIGH, HallucinationRiskLevel.CRITICAL]:
                self.prevention_stats["hallucinations_detected"] += 1
                
                if check_result.requires_human_review:
                    self.prevention_stats["human_reviews_required"] += 1
                
                # Log high-risk detection
                if self.audit_logger:
                    self.audit_logger.log_system_event(
                        operation="hallucination_detected",
                        component="hallucination_prevention",
                        additional_context={
                            "patient_id": patient_id,
                            "content_type": content_type,
                            "risk_level": getattr(check_result.risk_level, 'value', str(check_result.risk_level)),
                            "confidence": check_result.confidence,
                            "detected_patterns": check_result.detected_patterns,
                            "requires_human_review": check_result.requires_human_review
                        }
                    )
                
                # In strict mode, raise exception for high-risk hallucinations
                if self.strict_mode and check_result.risk_level == HallucinationRiskLevel.CRITICAL:
                    self.prevention_stats["high_risk_blocked"] += 1
                    
                    error_context = ErrorContext(
                        operation=operation,
                        component="hallucination_prevention",
                        patient_id=patient_id,
                        additional_data={
                            "content_type": content_type,
                            "detected_patterns": check_result.detected_patterns,
                            "risk_level": getattr(check_result.risk_level, 'value', str(check_result.risk_level))
                        }
                    )
                    
                    if self.error_handler:
                        self.error_handler.handle_error(
                            HallucinationDetectedError(
                                f"Critical hallucination risk detected in {content_type} content",
                                check_result.detected_patterns
                            ),
                            error_context
                        )
                    
                    raise HallucinationDetectedError(
                        f"Critical hallucination risk detected in {content_type} content: {', '.join(check_result.detected_patterns)}",
                        check_result.detected_patterns
                    )
            
            rl = getattr(check_result.risk_level, 'value', str(check_result.risk_level))
            logger.info(f"Hallucination check completed: {rl} risk (confidence: {check_result.confidence:.3f})")
            
            return check_result
    
    def get_prevention_statistics(self) -> Dict[str, Any]:
        """Get hallucination prevention statistics."""
        stats = self.prevention_stats.copy()
        
        # Calculate rates
        if stats["total_checks"] > 0:
            stats["hallucination_rate"] = stats["hallucinations_detected"] / stats["total_checks"]
            stats["human_review_rate"] = stats["human_reviews_required"] / stats["total_checks"]
            stats["block_rate"] = stats["high_risk_blocked"] / stats["total_checks"]
        else:
            stats["hallucination_rate"] = 0.0
            stats["human_review_rate"] = 0.0
            stats["block_rate"] = 0.0
        
        return stats

# Global hallucination prevention system instance
_prevention_system: Optional[HallucinationPreventionSystem] = None

def initialize_hallucination_prevention(audit_logger: Optional[AuditLogger] = None,
                                      error_handler: Optional[ErrorHandler] = None,
                                      strict_mode: bool = True) -> HallucinationPreventionSystem:
    """Initialize global hallucination prevention system."""
    global _prevention_system
    _prevention_system = HallucinationPreventionSystem(
        audit_logger=audit_logger,
        error_handler=error_handler,
        strict_mode=strict_mode
    )
    return _prevention_system

def get_hallucination_prevention_system() -> Optional[HallucinationPreventionSystem]:
    """Get global hallucination prevention system instance."""
    return _prevention_system