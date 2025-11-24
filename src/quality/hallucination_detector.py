"""Hallucination detection and data validation system for medical record analysis."""
import re
import logging
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum
import json
from datetime import datetime
import difflib

from ..models import PatientData, MedicalSummary, ResearchAnalysis
from ..utils.audit_logger import AuditLogger

logger = logging.getLogger(__name__)

class ValidationSeverity(Enum):
    """Validation issue severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class ValidationType(Enum):
    """Types of validation checks."""
    SOURCE_VERIFICATION = "source_verification"
    MEDICAL_TERMINOLOGY = "medical_terminology"
    DATA_CONSISTENCY = "data_consistency"
    LOGICAL_COHERENCE = "logical_coherence"
    COMPLETENESS = "completeness"
    ACCURACY = "accuracy"

@dataclass
class ValidationIssue:
    """Represents a validation issue found during analysis."""
    issue_id: str
    validation_type: ValidationType
    severity: ValidationSeverity
    description: str
    field_name: str
    expected_value: Optional[str] = None
    actual_value: Optional[str] = None
    source_reference: Optional[str] = None
    confidence_score: float = 0.0
    suggestions: List[str] = None
    
    def __post_init__(self):
        if self.suggestions is None:
            self.suggestions = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging and reporting."""
        return {
            "issue_id": self.issue_id,
            "validation_type": self.validation_type.value,
            "severity": self.severity.value,
            "description": self.description,
            "field_name": self.field_name,
            "expected_value": self.expected_value,
            "actual_value": self.actual_value,
            "source_reference": self.source_reference,
            "confidence_score": self.confidence_score,
            "suggestions": self.suggestions
        }

class MedicalTerminologyValidator:
    """Validates medical terminology against standard ontologies."""
    
    def __init__(self):
        """Initialize medical terminology validator."""
        # ICD-10 common codes (subset for demonstration)
        self.icd10_codes = {
            # Cardiovascular
            "I10": "Essential hypertension",
            "I25.9": "Chronic ischemic heart disease",
            "I50.9": "Heart failure",
            "I48.91": "Atrial fibrillation",
            
            # Endocrine
            "E11.9": "Type 2 diabetes mellitus",
            "E78.5": "Hyperlipidemia",
            "E03.9": "Hypothyroidism",
            
            # Respiratory
            "J44.1": "Chronic obstructive pulmonary disease",
            "J45.9": "Asthma",
            
            # Mental Health
            "F32.9": "Major depressive disorder",
            "F41.9": "Anxiety disorder",
            
            # Musculoskeletal
            "M79.3": "Chronic pain",
            "M25.50": "Arthritis"
        }
        
        # Common medical terms and their variations
        self.medical_terms = {
            "hypertension": ["high blood pressure", "elevated blood pressure", "htn"],
            "diabetes": ["diabetes mellitus", "dm", "high blood sugar"],
            "myocardial infarction": ["heart attack", "mi", "cardiac event"],
            "chronic obstructive pulmonary disease": ["copd", "chronic bronchitis", "emphysema"],
            "atrial fibrillation": ["afib", "a-fib", "irregular heartbeat"],
            "congestive heart failure": ["chf", "heart failure", "cardiac failure"],
            "hyperlipidemia": ["high cholesterol", "dyslipidemia", "elevated lipids"],
            "gastroesophageal reflux disease": ["gerd", "acid reflux", "heartburn"],
            "osteoarthritis": ["arthritis", "joint pain", "degenerative joint disease"],
            "depression": ["major depressive disorder", "mdd", "depressive episode"]
        }
        
        # Medication name patterns
        self.medication_patterns = {
            "ace_inhibitors": ["lisinopril", "enalapril", "captopril", "ramipril"],
            "beta_blockers": ["metoprolol", "atenolol", "propranolol", "carvedilol"],
            "statins": ["atorvastatin", "simvastatin", "rosuvastatin", "pravastatin"],
            "diabetes_medications": ["metformin", "insulin", "glipizide", "glyburide"],
            "proton_pump_inhibitors": ["omeprazole", "lansoprazole", "pantoprazole"]
        }
    
    def validate_condition_terminology(self, condition_name: str) -> Tuple[bool, float, List[str]]:
        """
        Validate medical condition terminology.
        
        Args:
            condition_name: Name of medical condition to validate
            
        Returns:
            Tuple[bool, float, List[str]]: (is_valid, confidence_score, suggestions)
        """
        if not condition_name:
            return False, 0.0, ["Condition name cannot be empty"]
        
        condition_lower = condition_name.lower().strip()
        
        # Check exact matches in medical terms
        if condition_lower in self.medical_terms:
            return True, 1.0, []
        
        # Check if it's a variation of a known term
        for standard_term, variations in self.medical_terms.items():
            if condition_lower in [v.lower() for v in variations]:
                return True, 0.9, [f"Consider using standard term: {standard_term}"]
        
        # Check for partial matches
        partial_matches = []
        for standard_term, variations in self.medical_terms.items():
            all_terms = [standard_term] + variations
            for term in all_terms:
                similarity = difflib.SequenceMatcher(None, condition_lower, term.lower()).ratio()
                if similarity > 0.7:
                    partial_matches.append((standard_term, similarity))
        
        if partial_matches:
            # Sort by similarity score
            partial_matches.sort(key=lambda x: x[1], reverse=True)
            best_match = partial_matches[0]
            suggestions = [f"Did you mean: {best_match[0]}?"]
            return True, best_match[1], suggestions
        
        # Check if it contains medical-sounding terms
        medical_keywords = ["syndrome", "disease", "disorder", "condition", "itis", "osis", "pathy", "emia"]
        if any(keyword in condition_lower for keyword in medical_keywords):
            return True, 0.6, ["Medical terminology detected but not in standard dictionary"]
        
        return False, 0.0, ["Unknown medical condition - please verify terminology"]
    
    def validate_medication_name(self, medication_name: str) -> Tuple[bool, float, List[str]]:
        """
        Validate medication name.
        
        Args:
            medication_name: Name of medication to validate
            
        Returns:
            Tuple[bool, float, List[str]]: (is_valid, confidence_score, suggestions)
        """
        if not medication_name:
            return False, 0.0, ["Medication name cannot be empty"]
        
        med_lower = medication_name.lower().strip()
        
        # Check against known medication patterns
        for category, medications in self.medication_patterns.items():
            if med_lower in [med.lower() for med in medications]:
                return True, 1.0, []
            
            # Check for partial matches
            for med in medications:
                if med_lower in med.lower() or med.lower() in med_lower:
                    return True, 0.8, [f"Possible match in {category.replace('_', ' ')}: {med}"]
        
        # Check for common medication suffixes/prefixes
        med_patterns = [
            r".*pril$",  # ACE inhibitors
            r".*olol$",  # Beta blockers
            r".*statin$",  # Statins
            r".*zole$",  # PPIs
            r".*mycin$",  # Antibiotics
        ]
        
        for pattern in med_patterns:
            if re.match(pattern, med_lower):
                return True, 0.7, ["Medication name follows standard pharmaceutical naming pattern"]
        
        return False, 0.0, ["Unknown medication name - please verify"]
    
    def validate_icd_code(self, icd_code: str) -> Tuple[bool, str, List[str]]:
        """
        Validate ICD-10 code.
        
        Args:
            icd_code: ICD-10 code to validate
            
        Returns:
            Tuple[bool, str, List[str]]: (is_valid, description, suggestions)
        """
        if not icd_code:
            return False, "", ["ICD code cannot be empty"]
        
        icd_upper = icd_code.upper().strip()
        
        # Check exact match
        if icd_upper in self.icd10_codes:
            return True, self.icd10_codes[icd_upper], []
        
        # Check format (basic ICD-10 format validation)
        icd_pattern = r"^[A-Z]\d{2}(\.\d{1,2})?$"
        if re.match(icd_pattern, icd_upper):
            return True, "Valid ICD-10 format", ["Code format is valid but not in local dictionary"]
        
        return False, "", ["Invalid ICD-10 code format"]

class HallucinationDetector:
    """Detects potential hallucinations in medical analysis results."""
    
    def __init__(self, audit_logger: Optional[AuditLogger] = None):
        """
        Initialize hallucination detector.
        
        Args:
            audit_logger: Optional audit logger for compliance
        """
        self.audit_logger = audit_logger
        self.terminology_validator = MedicalTerminologyValidator()
        self.validation_issues: List[ValidationIssue] = []
        
        # Confidence thresholds
        self.confidence_thresholds = {
            "critical": 0.3,  # Below this is critical
            "error": 0.5,     # Below this is error
            "warning": 0.7,   # Below this is warning
            "info": 0.9       # Below this is info
        }
        
        logger.info("Hallucination detector initialized")
    
    def validate_against_source(self, extracted_data: Dict[str, Any], 
                               source_xml: str, patient_id: str) -> List[ValidationIssue]:
        """
        Validate extracted data against source XML.
        
        Args:
            extracted_data: Data extracted by analysis agents
            source_xml: Original XML source data
            patient_id: Patient identifier for audit logging
            
        Returns:
            List[ValidationIssue]: List of validation issues found
        """
        issues = []
        
        try:
            # Log validation start
            if self.audit_logger:
                self.audit_logger.log_patient_access(
                    patient_id=patient_id,
                    operation="source_validation",
                    component="hallucination_detector",
                    additional_context={"validation_type": "source_verification"}
                )
            
            # Validate patient demographics
            issues.extend(self._validate_demographics(extracted_data, source_xml))
            
            # Validate medical conditions
            issues.extend(self._validate_conditions(extracted_data, source_xml))
            
            # Validate medications
            issues.extend(self._validate_medications(extracted_data, source_xml))
            
            # Validate dates and temporal consistency
            issues.extend(self._validate_temporal_consistency(extracted_data))
            
            logger.info(f"Source validation completed for patient {patient_id}: {len(issues)} issues found")
            
        except Exception as e:
            logger.error(f"Error during source validation: {str(e)}")
            issues.append(ValidationIssue(
                issue_id=f"VAL_{datetime.now().strftime('%Y%m%d_%H%M%S')}_001",
                validation_type=ValidationType.SOURCE_VERIFICATION,
                severity=ValidationSeverity.ERROR,
                description=f"Source validation failed: {str(e)}",
                field_name="validation_process"
            ))
        
        return issues
    
    def _validate_demographics(self, extracted_data: Dict[str, Any], 
                              source_xml: str) -> List[ValidationIssue]:
        """Validate demographic data against source."""
        issues = []
        
        # Extract patient name from source XML (simplified)
        name_match = re.search(r'<patient[^>]*name[^>]*>([^<]+)</patient>', source_xml, re.IGNORECASE)
        source_name = name_match.group(1).strip() if name_match else None
        
        extracted_name = extracted_data.get('patient_data', {}).get('name')
        
        if source_name and extracted_name:
            # Compare names (allowing for minor variations)
            similarity = difflib.SequenceMatcher(None, source_name.lower(), extracted_name.lower()).ratio()
            
            if similarity < 0.8:
                issues.append(ValidationIssue(
                    issue_id=f"VAL_{datetime.now().strftime('%Y%m%d_%H%M%S')}_DEM_001",
                    validation_type=ValidationType.SOURCE_VERIFICATION,
                    severity=ValidationSeverity.ERROR,
                    description="Patient name mismatch between source and extracted data",
                    field_name="patient_name",
                    expected_value=source_name,
                    actual_value=extracted_name,
                    confidence_score=similarity,
                    suggestions=["Verify patient name extraction accuracy"]
                ))
        
        return issues
    
    def _validate_conditions(self, extracted_data: Dict[str, Any], 
                           source_xml: str) -> List[ValidationIssue]:
        """Validate medical conditions against source and terminology."""
        issues = []
        
        conditions = extracted_data.get('medical_summary', {}).get('key_conditions', [])
        
        for i, condition in enumerate(conditions):
            condition_name = condition.get('name') if isinstance(condition, dict) else str(condition)
            
            # Validate terminology
            is_valid, confidence, suggestions = self.terminology_validator.validate_condition_terminology(condition_name)
            
            if not is_valid or confidence < self.confidence_thresholds['warning']:
                severity = self._determine_severity(confidence)
                
                issues.append(ValidationIssue(
                    issue_id=f"VAL_{datetime.now().strftime('%Y%m%d_%H%M%S')}_COND_{i:03d}",
                    validation_type=ValidationType.MEDICAL_TERMINOLOGY,
                    severity=severity,
                    description=f"Medical condition terminology validation failed: {condition_name}",
                    field_name=f"conditions[{i}].name",
                    actual_value=condition_name,
                    confidence_score=confidence,
                    suggestions=suggestions
                ))
            
            # Check if condition appears in source XML
            if not self._condition_in_source(condition_name, source_xml):
                issues.append(ValidationIssue(
                    issue_id=f"VAL_{datetime.now().strftime('%Y%m%d_%H%M%S')}_SRC_{i:03d}",
                    validation_type=ValidationType.SOURCE_VERIFICATION,
                    severity=ValidationSeverity.WARNING,
                    description=f"Condition not found in source XML: {condition_name}",
                    field_name=f"conditions[{i}].name",
                    actual_value=condition_name,
                    suggestions=["Verify condition extraction from source document"]
                ))
        
        return issues
    
    def _validate_medications(self, extracted_data: Dict[str, Any], 
                            source_xml: str) -> List[ValidationIssue]:
        """Validate medications against source and terminology."""
        issues = []
        
        medications = extracted_data.get('medical_summary', {}).get('medications', [])
        
        for i, medication in enumerate(medications):
            med_name = medication if isinstance(medication, str) else medication.get('name', '')
            
            # Validate medication terminology
            is_valid, confidence, suggestions = self.terminology_validator.validate_medication_name(med_name)
            
            if not is_valid or confidence < self.confidence_thresholds['warning']:
                severity = self._determine_severity(confidence)
                
                issues.append(ValidationIssue(
                    issue_id=f"VAL_{datetime.now().strftime('%Y%m%d_%H%M%S')}_MED_{i:03d}",
                    validation_type=ValidationType.MEDICAL_TERMINOLOGY,
                    severity=severity,
                    description=f"Medication name validation failed: {med_name}",
                    field_name=f"medications[{i}]",
                    actual_value=med_name,
                    confidence_score=confidence,
                    suggestions=suggestions
                ))
        
        return issues
    
    def _validate_temporal_consistency(self, extracted_data: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate temporal consistency in the data."""
        issues = []
        
        # Check for logical date consistency
        patient_data = extracted_data.get('patient_data', {})
        birth_date = patient_data.get('date_of_birth')
        age = patient_data.get('age')
        
        if birth_date and age:
            try:
                # Simple age validation (would need more sophisticated logic in production)
                current_year = datetime.now().year
                birth_year = int(birth_date.split('-')[0]) if '-' in birth_date else None
                
                if birth_year:
                    calculated_age = current_year - birth_year
                    age_diff = abs(calculated_age - int(age))
                    
                    if age_diff > 1:  # Allow 1 year difference for birthday timing
                        issues.append(ValidationIssue(
                            issue_id=f"VAL_{datetime.now().strftime('%Y%m%d_%H%M%S')}_TEMP_001",
                            validation_type=ValidationType.LOGICAL_COHERENCE,
                            severity=ValidationSeverity.WARNING,
                            description=f"Age inconsistency: calculated age {calculated_age} vs reported age {age}",
                            field_name="age_consistency",
                            expected_value=str(calculated_age),
                            actual_value=str(age),
                            suggestions=["Verify birth date and age accuracy"]
                        ))
            except (ValueError, IndexError) as e:
                logger.warning(f"Error validating age consistency: {str(e)}")
        
        return issues
    
    def _condition_in_source(self, condition_name: str, source_xml: str) -> bool:
        """Check if condition appears in source XML."""
        condition_lower = condition_name.lower()
        source_lower = source_xml.lower()
        
        # Direct match
        if condition_lower in source_lower:
            return True
        
        # Check for variations
        variations = self.terminology_validator.medical_terms.get(condition_lower, [])
        for variation in variations:
            if variation.lower() in source_lower:
                return True
        
        return False
    
    def _determine_severity(self, confidence_score: float) -> ValidationSeverity:
        """Determine validation severity based on confidence score."""
        if confidence_score < self.confidence_thresholds['critical']:
            return ValidationSeverity.CRITICAL
        elif confidence_score < self.confidence_thresholds['error']:
            return ValidationSeverity.ERROR
        elif confidence_score < self.confidence_thresholds['warning']:
            return ValidationSeverity.WARNING
        else:
            return ValidationSeverity.INFO
    
    def validate_analysis_completeness(self, analysis_data: Dict[str, Any]) -> List[ValidationIssue]:
        """
        Validate completeness of analysis results.
        
        Args:
            analysis_data: Complete analysis data to validate
            
        Returns:
            List[ValidationIssue]: Completeness validation issues
        """
        issues = []
        
        # Required fields for complete analysis
        required_fields = {
            'patient_data': ['name', 'patient_id'],
            'medical_summary': ['key_conditions', 'summary_text'],
            'research_analysis': ['research_findings', 'analysis_confidence']
        }
        
        for section, fields in required_fields.items():
            section_data = analysis_data.get(section, {})
            
            if not section_data:
                issues.append(ValidationIssue(
                    issue_id=f"VAL_{datetime.now().strftime('%Y%m%d_%H%M%S')}_COMP_001",
                    validation_type=ValidationType.COMPLETENESS,
                    severity=ValidationSeverity.ERROR,
                    description=f"Missing required section: {section}",
                    field_name=section,
                    suggestions=[f"Ensure {section} is properly generated"]
                ))
                continue
            
            for field in fields:
                if field not in section_data or not section_data[field]:
                    issues.append(ValidationIssue(
                        issue_id=f"VAL_{datetime.now().strftime('%Y%m%d_%H%M%S')}_COMP_{field}",
                        validation_type=ValidationType.COMPLETENESS,
                        severity=ValidationSeverity.WARNING,
                        description=f"Missing or empty required field: {section}.{field}",
                        field_name=f"{section}.{field}",
                        suggestions=[f"Ensure {field} is properly extracted/generated"]
                    ))
        
        return issues
    
    def validate_research_accuracy(self, research_analysis: ResearchAnalysis) -> List[ValidationIssue]:
        """
        Validate research analysis accuracy and coherence.
        
        Args:
            research_analysis: Research analysis to validate
            
        Returns:
            List[ValidationIssue]: Research validation issues
        """
        issues = []
        
        # Check research findings quality
        findings = research_analysis.research_findings
        
        if not findings:
            issues.append(ValidationIssue(
                issue_id=f"VAL_{datetime.now().strftime('%Y%m%d_%H%M%S')}_RES_001",
                validation_type=ValidationType.COMPLETENESS,
                severity=ValidationSeverity.WARNING,
                description="No research findings available",
                field_name="research_findings",
                suggestions=["Verify research search functionality"]
            ))
        else:
            # Validate individual research findings
            for i, finding in enumerate(findings):
                if isinstance(finding, dict):
                    # Check required fields
                    required_fields = ['title', 'authors', 'journal', 'publication_year']
                    for field in required_fields:
                        if field not in finding or not finding[field]:
                            issues.append(ValidationIssue(
                                issue_id=f"VAL_{datetime.now().strftime('%Y%m%d_%H%M%S')}_RES_{i:03d}",
                                validation_type=ValidationType.COMPLETENESS,
                                severity=ValidationSeverity.INFO,
                                description=f"Missing research field: {field}",
                                field_name=f"research_findings[{i}].{field}",
                                suggestions=[f"Ensure {field} is extracted from research source"]
                            ))
                    
                    # Validate publication year
                    pub_year = finding.get('publication_year')
                    if pub_year:
                        current_year = datetime.now().year
                        if pub_year > current_year or pub_year < 1900:
                            issues.append(ValidationIssue(
                                issue_id=f"VAL_{datetime.now().strftime('%Y%m%d_%H%M%S')}_RES_YEAR_{i:03d}",
                                validation_type=ValidationType.LOGICAL_COHERENCE,
                                severity=ValidationSeverity.WARNING,
                                description=f"Invalid publication year: {pub_year}",
                                field_name=f"research_findings[{i}].publication_year",
                                actual_value=str(pub_year),
                                suggestions=["Verify publication year accuracy"]
                            ))
        
        # Check analysis confidence
        confidence = research_analysis.analysis_confidence
        if confidence < 0.3:
            issues.append(ValidationIssue(
                issue_id=f"VAL_{datetime.now().strftime('%Y%m%d_%H%M%S')}_RES_CONF",
                validation_type=ValidationType.ACCURACY,
                severity=ValidationSeverity.WARNING,
                description=f"Low research analysis confidence: {confidence:.2%}",
                field_name="analysis_confidence",
                actual_value=f"{confidence:.2%}",
                suggestions=["Review research correlation quality and relevance"]
            ))
        
        return issues
    
    def generate_validation_report(self, issues: List[ValidationIssue]) -> Dict[str, Any]:
        """
        Generate comprehensive validation report.
        
        Args:
            issues: List of validation issues
            
        Returns:
            Dict[str, Any]: Validation report
        """
        if not issues:
            return {
                "validation_status": "PASSED",
                "total_issues": 0,
                "issues_by_severity": {},
                "issues_by_type": {},
                "overall_confidence": 1.0,
                "recommendations": ["Analysis passed all validation checks"]
            }
        
        # Categorize issues
        issues_by_severity = {}
        issues_by_type = {}
        
        for issue in issues:
            # By severity
            severity = issue.severity.value
            if severity not in issues_by_severity:
                issues_by_severity[severity] = []
            issues_by_severity[severity].append(issue.to_dict())
            
            # By type
            val_type = issue.validation_type.value
            if val_type not in issues_by_type:
                issues_by_type[val_type] = []
            issues_by_type[val_type].append(issue.to_dict())
        
        # Determine overall status
        has_critical = any(issue.severity == ValidationSeverity.CRITICAL for issue in issues)
        has_error = any(issue.severity == ValidationSeverity.ERROR for issue in issues)
        
        if has_critical:
            status = "FAILED"
            confidence = 0.0
        elif has_error:
            status = "WARNING"
            confidence = 0.5
        else:
            status = "PASSED_WITH_WARNINGS"
            confidence = 0.8
        
        # Generate recommendations
        recommendations = []
        if has_critical:
            recommendations.append("Critical validation issues found - analysis results may be unreliable")
        if has_error:
            recommendations.append("Validation errors found - review and verify analysis accuracy")
        if issues_by_type.get('medical_terminology'):
            recommendations.append("Medical terminology issues detected - verify condition and medication names")
        if issues_by_type.get('source_verification'):
            recommendations.append("Source verification issues found - check data extraction accuracy")
        
        return {
            "validation_status": status,
            "total_issues": len(issues),
            "issues_by_severity": issues_by_severity,
            "issues_by_type": issues_by_type,
            "overall_confidence": confidence,
            "recommendations": recommendations,
            "validation_timestamp": datetime.now().isoformat()
        }
    
    def get_validation_statistics(self) -> Dict[str, Any]:
        """Get validation statistics."""
        return {
            "total_validations": len(self.validation_issues),
            "issues_by_severity": {
                severity.value: len([i for i in self.validation_issues if i.severity == severity])
                for severity in ValidationSeverity
            },
            "issues_by_type": {
                val_type.value: len([i for i in self.validation_issues if i.validation_type == val_type])
                for val_type in ValidationType
            }
        }