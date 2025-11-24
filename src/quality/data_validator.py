"""Comprehensive data validation service for medical record analysis."""
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import json

from .hallucination_detector import (
    HallucinationDetector,
    ValidationIssue,
    ValidationSeverity,
    ValidationType,
)
from ..models import PatientData, MedicalSummary, ResearchAnalysis, AnalysisReport
from ..utils.audit_logger import AuditLogger
from ..utils.error_handler import ErrorHandler, ErrorContext

logger = logging.getLogger(__name__)

class DataValidationService:
    """Comprehensive data validation service for medical analysis."""
    
    def __init__(self, 
                 audit_logger: Optional[AuditLogger] = None,
                 error_handler: Optional[ErrorHandler] = None,
                 enable_strict_validation: bool = True):
        """
        Initialize data validation service.
        
        Args:
            audit_logger: Optional audit logger for compliance
            error_handler: Optional error handler for validation errors
            enable_strict_validation: Whether to enable strict validation mode
        """
        self.audit_logger = audit_logger
        self.error_handler = error_handler
        self.enable_strict_validation = enable_strict_validation
        
        # Initialize hallucination detector
        self.hallucination_detector = HallucinationDetector(audit_logger=audit_logger)
        
        # Validation statistics
        self.validation_stats = {
            "total_validations": 0,
            "passed_validations": 0,
            "failed_validations": 0,
            "warnings_generated": 0,
            "critical_issues_found": 0
        }
        
        logger.info(f"Data validation service initialized (strict_mode: {enable_strict_validation})")
    
    def validate_complete_analysis(self, 
                                 analysis_report: AnalysisReport,
                                 source_xml: Optional[str] = None) -> Dict[str, Any]:
        """
        Perform comprehensive validation of complete analysis.
        
        Args:
            analysis_report: Complete analysis report to validate
            source_xml: Optional source XML for verification
            
        Returns:
            Dict[str, Any]: Comprehensive validation results
        """
        validation_start_time = datetime.now()
        patient_id = analysis_report.patient_data.patient_id
        
        try:
            # Log validation start
            if self.audit_logger:
                self.audit_logger.log_patient_access(
                    patient_id=patient_id,
                    operation="comprehensive_validation",
                    component="data_validator",
                    additional_context={
                        "report_id": analysis_report.report_id,
                        "strict_mode": self.enable_strict_validation
                    }
                )
            
            all_issues = []
            validation_sections = {}
            
            # 1. Validate patient data
            logger.info(f"Validating patient data for {patient_id}")
            patient_issues = self._validate_patient_data(analysis_report.patient_data)
            all_issues.extend(patient_issues)
            validation_sections["patient_data"] = {
                "issues_count": len(patient_issues),
                "issues": [issue.to_dict() for issue in patient_issues]
            }
            
            # 2. Validate medical summary
            logger.info(f"Validating medical summary for {patient_id}")
            medical_issues = self._validate_medical_summary(analysis_report.medical_summary)
            all_issues.extend(medical_issues)
            validation_sections["medical_summary"] = {
                "issues_count": len(medical_issues),
                "issues": [issue.to_dict() for issue in medical_issues]
            }
            
            # 3. Validate research analysis
            logger.info(f"Validating research analysis for {patient_id}")
            research_issues = self.hallucination_detector.validate_research_accuracy(analysis_report.research_analysis)
            all_issues.extend(research_issues)
            validation_sections["research_analysis"] = {
                "issues_count": len(research_issues),
                "issues": [issue.to_dict() for issue in research_issues]
            }
            
            # 4. Validate against source if available
            if source_xml:
                logger.info(f"Validating against source XML for {patient_id}")
                source_issues = self.hallucination_detector.validate_against_source(
                    self._analysis_report_to_dict(analysis_report),
                    source_xml,
                    patient_id
                )
                all_issues.extend(source_issues)
                validation_sections["source_verification"] = {
                    "issues_count": len(source_issues),
                    "issues": [issue.to_dict() for issue in source_issues]
                }
            
            # 5. Validate completeness
            logger.info(f"Validating completeness for {patient_id}")
            completeness_issues = self.hallucination_detector.validate_analysis_completeness(
                self._analysis_report_to_dict(analysis_report)
            )
            all_issues.extend(completeness_issues)
            validation_sections["completeness"] = {
                "issues_count": len(completeness_issues),
                "issues": [issue.to_dict() for issue in completeness_issues]
            }
            
            # 6. Cross-validation checks
            logger.info(f"Performing cross-validation for {patient_id}")
            cross_validation_issues = self._perform_cross_validation(analysis_report)
            all_issues.extend(cross_validation_issues)
            validation_sections["cross_validation"] = {
                "issues_count": len(cross_validation_issues),
                "issues": [issue.to_dict() for issue in cross_validation_issues]
            }
            
            # Generate comprehensive validation report
            validation_report = self.hallucination_detector.generate_validation_report(all_issues)
            
            # Add detailed sections
            validation_report["validation_sections"] = validation_sections
            validation_report["validation_duration"] = (datetime.now() - validation_start_time).total_seconds()
            validation_report["patient_id"] = patient_id
            validation_report["report_id"] = analysis_report.report_id
            validation_report["strict_mode"] = self.enable_strict_validation
            
            # Update statistics
            self._update_validation_statistics(validation_report)
            
            # Log validation completion
            if self.audit_logger:
                self.audit_logger.log_patient_access(
                    patient_id=patient_id,
                    operation="validation_completed",
                    component="data_validator",
                    additional_context={
                        "validation_status": validation_report["validation_status"],
                        "total_issues": validation_report["total_issues"],
                        "duration_seconds": validation_report["validation_duration"]
                    }
                )
            
            logger.info(f"Validation completed for {patient_id}: {validation_report['validation_status']} "
                       f"({len(all_issues)} issues found)")
            
            return validation_report
            
        except Exception as e:
            error_msg = f"Validation failed for patient {patient_id}: {str(e)}"
            logger.error(error_msg)
            
            if self.error_handler:
                context = ErrorContext("data_validation", patient_id, "data_validator")
                self.error_handler.handle_error(e, context)
            
            return {
                "validation_status": "ERROR",
                "error_message": error_msg,
                "patient_id": patient_id,
                "validation_duration": (datetime.now() - validation_start_time).total_seconds()
            }
    
    def _validate_patient_data(self, patient_data: PatientData) -> List[ValidationIssue]:
        """Validate patient data integrity."""
        issues = []
        
        # Validate required fields
        if not patient_data.name or len(patient_data.name.strip()) < 2:
            issues.append(ValidationIssue(
                issue_id=f"VAL_{datetime.now().strftime('%Y%m%d_%H%M%S')}_PAT_001",
                validation_type=ValidationType.COMPLETENESS,
                severity=ValidationSeverity.ERROR,
                description="Patient name is missing or too short",
                field_name="patient_data.name",
                actual_value=patient_data.name,
                suggestions=["Ensure patient name is properly extracted from source"]
            ))
        
        if not patient_data.patient_id:
            issues.append(ValidationIssue(
                issue_id=f"VAL_{datetime.now().strftime('%Y%m%d_%H%M%S')}_PAT_002",
                validation_type=ValidationType.COMPLETENESS,
                severity=ValidationSeverity.ERROR,
                description="Patient ID is missing",
                field_name="patient_data.patient_id",
                suggestions=["Ensure patient ID is generated or extracted"]
            ))
        
        # Validate age if present
        if hasattr(patient_data, 'age') and patient_data.age:
            try:
                age = int(patient_data.age)
                if age < 0 or age > 150:
                    issues.append(ValidationIssue(
                        issue_id=f"VAL_{datetime.now().strftime('%Y%m%d_%H%M%S')}_PAT_003",
                        validation_type=ValidationType.LOGICAL_COHERENCE,
                        severity=ValidationSeverity.WARNING,
                        description=f"Patient age seems unrealistic: {age}",
                        field_name="patient_data.age",
                        actual_value=str(age),
                        suggestions=["Verify age extraction accuracy"]
                    ))
            except ValueError:
                issues.append(ValidationIssue(
                    issue_id=f"VAL_{datetime.now().strftime('%Y%m%d_%H%M%S')}_PAT_004",
                    validation_type=ValidationType.DATA_CONSISTENCY,
                    severity=ValidationSeverity.WARNING,
                    description=f"Patient age is not a valid number: {patient_data.age}",
                    field_name="patient_data.age",
                    actual_value=str(patient_data.age),
                    suggestions=["Ensure age is extracted as a numeric value"]
                ))
        
        return issues
    
    def _validate_medical_summary(self, medical_summary: MedicalSummary) -> List[ValidationIssue]:
        """Validate medical summary data."""
        issues = []
        
        # Validate key conditions
        if not medical_summary.key_conditions:
            issues.append(ValidationIssue(
                issue_id=f"VAL_{datetime.now().strftime('%Y%m%d_%H%M%S')}_MED_001",
                validation_type=ValidationType.COMPLETENESS,
                severity=ValidationSeverity.WARNING,
                description="No medical conditions identified",
                field_name="medical_summary.key_conditions",
                suggestions=["Verify condition extraction from medical records"]
            ))
        else:
            # Validate individual conditions
            for i, condition in enumerate(medical_summary.key_conditions):
                if isinstance(condition, dict):
                    condition_name = condition.get('name', '')
                    confidence_score = condition.get('confidence_score', 0)
                    
                    # Validate condition name
                    is_valid, term_confidence, suggestions = self.hallucination_detector.terminology_validator.validate_condition_terminology(condition_name)
                    
                    if not is_valid or term_confidence < 0.7:
                        issues.append(ValidationIssue(
                            issue_id=f"VAL_{datetime.now().strftime('%Y%m%d_%H%M%S')}_MED_COND_{i:03d}",
                            validation_type=ValidationType.MEDICAL_TERMINOLOGY,
                            severity=ValidationSeverity.WARNING if term_confidence > 0.5 else ValidationSeverity.ERROR,
                            description=f"Medical condition terminology issue: {condition_name}",
                            field_name=f"medical_summary.key_conditions[{i}].name",
                            actual_value=condition_name,
                            confidence_score=term_confidence,
                            suggestions=suggestions
                        ))
                    
                    # Validate confidence score
                    if confidence_score < 0.3:
                        issues.append(ValidationIssue(
                            issue_id=f"VAL_{datetime.now().strftime('%Y%m%d_%H%M%S')}_MED_CONF_{i:03d}",
                            validation_type=ValidationType.ACCURACY,
                            severity=ValidationSeverity.WARNING,
                            description=f"Low confidence score for condition: {condition_name} ({confidence_score:.2%})",
                            field_name=f"medical_summary.key_conditions[{i}].confidence_score",
                            actual_value=f"{confidence_score:.2%}",
                            suggestions=["Review condition extraction accuracy"]
                        ))
        
        # Validate summary text
        if not medical_summary.summary_text or len(medical_summary.summary_text.strip()) < 10:
            issues.append(ValidationIssue(
                issue_id=f"VAL_{datetime.now().strftime('%Y%m%d_%H%M%S')}_MED_002",
                validation_type=ValidationType.COMPLETENESS,
                severity=ValidationSeverity.WARNING,
                description="Medical summary text is missing or too short",
                field_name="medical_summary.summary_text",
                suggestions=["Ensure comprehensive medical summary is generated"]
            ))
        
        # Validate medications if present
        if hasattr(medical_summary, 'medications') and medical_summary.medications:
            for i, medication in enumerate(medical_summary.medications):
                med_name = medication if isinstance(medication, str) else medication.get('name', '')
                
                is_valid, med_confidence, suggestions = self.hallucination_detector.terminology_validator.validate_medication_name(med_name)
                
                if not is_valid or med_confidence < 0.7:
                    issues.append(ValidationIssue(
                        issue_id=f"VAL_{datetime.now().strftime('%Y%m%d_%H%M%S')}_MED_MED_{i:03d}",
                        validation_type=ValidationType.MEDICAL_TERMINOLOGY,
                        severity=ValidationSeverity.INFO if med_confidence > 0.5 else ValidationSeverity.WARNING,
                        description=f"Medication name validation issue: {med_name}",
                        field_name=f"medical_summary.medications[{i}]",
                        actual_value=med_name,
                        confidence_score=med_confidence,
                        suggestions=suggestions
                    ))
        
        return issues
    
    def _perform_cross_validation(self, analysis_report: AnalysisReport) -> List[ValidationIssue]:
        """Perform cross-validation between different analysis components."""
        issues = []
        
        # Validate consistency between medical conditions and research findings
        conditions = analysis_report.medical_summary.key_conditions
        research_findings = analysis_report.research_analysis.research_findings
        
        if conditions and research_findings:
            # Check if research findings are relevant to identified conditions
            condition_names = []
            for condition in conditions:
                if isinstance(condition, dict):
                    condition_names.append(condition.get('name', '').lower())
                else:
                    condition_names.append(str(condition).lower())
            
            relevant_research_count = 0
            for finding in research_findings:
                if isinstance(finding, dict):
                    title = finding.get('title', '').lower()
                    # Simple relevance check
                    if any(condition in title for condition in condition_names):
                        relevant_research_count += 1
            
            relevance_ratio = relevant_research_count / len(research_findings) if research_findings else 0
            
            if relevance_ratio < 0.3:
                issues.append(ValidationIssue(
                    issue_id=f"VAL_{datetime.now().strftime('%Y%m%d_%H%M%S')}_CROSS_001",
                    validation_type=ValidationType.LOGICAL_COHERENCE,
                    severity=ValidationSeverity.WARNING,
                    description=f"Low relevance between conditions and research findings ({relevance_ratio:.1%})",
                    field_name="research_condition_relevance",
                    actual_value=f"{relevance_ratio:.1%}",
                    suggestions=["Review research correlation algorithm accuracy"]
                ))
        
        # Validate research analysis confidence against findings quality
        research_confidence = analysis_report.research_analysis.analysis_confidence
        findings_count = len(research_findings) if research_findings else 0
        
        if research_confidence > 0.8 and findings_count < 3:
            issues.append(ValidationIssue(
                issue_id=f"VAL_{datetime.now().strftime('%Y%m%d_%H%M%S')}_CROSS_002",
                validation_type=ValidationType.LOGICAL_COHERENCE,
                severity=ValidationSeverity.INFO,
                description=f"High research confidence ({research_confidence:.1%}) with few findings ({findings_count})",
                field_name="research_confidence_consistency",
                actual_value=f"confidence: {research_confidence:.1%}, findings: {findings_count}",
                suggestions=["Verify research confidence calculation methodology"]
            ))
        
        return issues
    
    def _analysis_report_to_dict(self, analysis_report: AnalysisReport) -> Dict[str, Any]:
        """Convert analysis report to dictionary for validation."""
        return {
            "patient_data": {
                "name": analysis_report.patient_data.name,
                "patient_id": analysis_report.patient_data.patient_id,
                "age": getattr(analysis_report.patient_data, 'age', None),
                "gender": getattr(analysis_report.patient_data, 'gender', None),
                "date_of_birth": getattr(analysis_report.patient_data, 'date_of_birth', None)
            },
            "medical_summary": {
                "key_conditions": analysis_report.medical_summary.key_conditions,
                "summary_text": analysis_report.medical_summary.summary_text,
                "chronic_conditions": getattr(analysis_report.medical_summary, 'chronic_conditions', []),
                "medications": getattr(analysis_report.medical_summary, 'medications', [])
            },
            "research_analysis": {
                "research_findings": analysis_report.research_analysis.research_findings,
                "analysis_confidence": analysis_report.research_analysis.analysis_confidence,
                "insights": getattr(analysis_report.research_analysis, 'insights', []),
                "recommendations": getattr(analysis_report.research_analysis, 'recommendations', [])
            }
        }
    
    def _update_validation_statistics(self, validation_report: Dict[str, Any]):
        """Update validation statistics."""
        self.validation_stats["total_validations"] += 1
        
        status = validation_report.get("validation_status", "UNKNOWN")
        if status == "PASSED":
            self.validation_stats["passed_validations"] += 1
        elif status in ["FAILED", "ERROR"]:
            self.validation_stats["failed_validations"] += 1
        elif status in ["WARNING", "PASSED_WITH_WARNINGS"]:
            self.validation_stats["warnings_generated"] += 1
        
        # Count critical issues
        issues_by_severity = validation_report.get("issues_by_severity", {})
        critical_count = len(issues_by_severity.get("critical", []))
        self.validation_stats["critical_issues_found"] += critical_count
    
    def get_validation_statistics(self) -> Dict[str, Any]:
        """Get current validation statistics."""
        stats = self.validation_stats.copy()
        
        # Calculate success rate
        total = stats["total_validations"]
        if total > 0:
            stats["success_rate"] = stats["passed_validations"] / total
            stats["warning_rate"] = stats["warnings_generated"] / total
            stats["failure_rate"] = stats["failed_validations"] / total
        else:
            stats["success_rate"] = 0.0
            stats["warning_rate"] = 0.0
            stats["failure_rate"] = 0.0
        
        return stats
    
    def clear_statistics(self):
        """Clear validation statistics."""
        self.validation_stats = {
            "total_validations": 0,
            "passed_validations": 0,
            "failed_validations": 0,
            "warnings_generated": 0,
            "critical_issues_found": 0
        }
        logger.info("Validation statistics cleared")