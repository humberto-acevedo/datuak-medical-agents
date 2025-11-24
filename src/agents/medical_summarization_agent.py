"""Medical Summarization Agent - Complete integration of condition extraction and medical summarization."""

import logging
from typing import Optional
from datetime import datetime

from ..models import PatientData, MedicalSummary
from ..models.exceptions import DataValidationError
from ..utils import AuditLogger, setup_logging
from .condition_extractor import ConditionExtractor
from .medical_summarizer import MedicalSummarizer


logger = logging.getLogger(__name__)


class MedicalSummarizationAgent:
    """
    Complete Medical Summarization Agent that handles the full workflow:
    1. Accept structured patient data from XML Parser Agent
    2. Extract and identify medical conditions
    3. Generate comprehensive medical summary
    4. Return structured MedicalSummary with narrative and chronological organization
    """
    
    def __init__(self, audit_logger: Optional[AuditLogger] = None):
        """
        Initialize Medical Summarization Agent.
        
        Args:
            audit_logger: Optional audit logger (will create default if not provided)
        """
        self.audit_logger = audit_logger or setup_logging()
        self.condition_extractor = ConditionExtractor()
        self.medical_summarizer = MedicalSummarizer()
        
        logger.info("Medical Summarization Agent initialized")
    
    def generate_summary(self, patient_data: PatientData) -> MedicalSummary:
        """
        Complete workflow to generate medical summary from structured patient data.
        
        Args:
            patient_data: Structured patient medical data from XML Parser Agent
            
        Returns:
            MedicalSummary: Comprehensive medical summary with conditions and narrative
            
        Raises:
            DataValidationError: If patient data validation fails
        """
        request_id = self._generate_request_id()
        start_time = datetime.now()
        
        try:
            # Log workflow start
            self.audit_logger.log_processing_start(
                patient_id=patient_data.patient_id,
                workflow_type="medical_summarization",
                request_id=request_id
            )
            
            logger.info(f"Starting medical summarization for patient {patient_data.patient_id}")
            
            # Step 1: Validate input patient data
            validation_errors = patient_data.validate()
            if validation_errors:
                logger.warning(f"Patient data validation warnings: {validation_errors}")
                # Continue processing but log the issues
                self.audit_logger.log_data_access(
                    patient_id=patient_data.patient_id,
                    operation="data_validation_warnings",
                    details={"validation_warnings": validation_errors},
                    request_id=request_id
                )
            
            # Step 2: Extract and identify medical conditions
            logger.info("Extracting medical conditions...")
            conditions = self.condition_extractor.extract_conditions(patient_data)
            
            # Log condition extraction
            self.audit_logger.log_data_access(
                patient_id=patient_data.patient_id,
                operation="condition_extraction",
                details={
                    "conditions_identified": len(conditions),
                    "condition_names": [c.name for c in conditions[:5]],  # Log top 5
                    "high_confidence_conditions": len([c for c in conditions if c.confidence_score >= 0.8])
                },
                request_id=request_id
            )
            
            # Step 3: Generate comprehensive medical summary
            logger.info("Generating medical summary...")
            medical_summary = self.medical_summarizer.generate_summary(patient_data, conditions)
            
            # Step 4: Validate and enhance the summary
            summary_validation_errors = medical_summary.validate()
            if summary_validation_errors:
                logger.warning(f"Medical summary validation warnings: {summary_validation_errors}")
            
            # Step 5: Log completion and return
            processing_time = (datetime.now() - start_time).total_seconds()
            
            self.audit_logger.log_processing_complete(
                patient_id=patient_data.patient_id,
                workflow_type="medical_summarization",
                duration_seconds=processing_time,
                request_id=request_id
            )
            
            # Log summary generation details
            self.audit_logger.log_data_access(
                patient_id=patient_data.patient_id,
                operation="summary_generation_complete",
                details={
                    "conditions_count": len(medical_summary.key_conditions),
                    "chronological_events_count": len(medical_summary.chronological_events),
                    "data_quality_score": medical_summary.data_quality_score,
                    "missing_data_indicators_count": len(medical_summary.missing_data_indicators),
                    "summary_length": len(medical_summary.summary_text)
                },
                request_id=request_id
            )
            
            logger.info(f"Successfully generated medical summary for patient {patient_data.patient_id} "
                       f"with {len(conditions)} conditions in {processing_time:.2f}s")
            
            return medical_summary
            
        except Exception as e:
            error_msg = f"Error generating medical summary for patient {patient_data.patient_id}: {str(e)}"
            logger.error(error_msg)
            self.audit_logger.log_error(
                patient_id=patient_data.patient_id,
                operation="medical_summarization",
                error=e,
                request_id=request_id
            )
            raise DataValidationError(error_msg)
    
    def analyze_condition_trends(self, patient_data: PatientData) -> dict:
        """
        Analyze trends in patient conditions over time.
        
        Args:
            patient_data: Structured patient medical data
            
        Returns:
            dict: Analysis of condition trends and patterns
        """
        try:
            conditions = self.condition_extractor.extract_conditions(patient_data)
            
            # Analyze condition patterns
            chronic_conditions = [c for c in conditions if self._is_chronic_condition(c.name)]
            acute_conditions = [c for c in conditions if not self._is_chronic_condition(c.name)]
            
            # Analyze severity distribution
            severity_distribution = {}
            for condition in conditions:
                severity = condition.severity or "unknown"
                severity_distribution[severity] = severity_distribution.get(severity, 0) + 1
            
            # Analyze medication alignment with conditions
            medication_alignment = self._analyze_medication_condition_alignment(patient_data, conditions)
            
            return {
                "total_conditions": len(conditions),
                "chronic_conditions": len(chronic_conditions),
                "acute_conditions": len(acute_conditions),
                "severity_distribution": severity_distribution,
                "high_confidence_conditions": len([c for c in conditions if c.confidence_score >= 0.8]),
                "medication_alignment": medication_alignment,
                "condition_names": [c.name for c in conditions],
                "analysis_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing condition trends: {str(e)}")
            return {"error": str(e)}
    
    def get_summary_quality_metrics(self, medical_summary: MedicalSummary) -> dict:
        """
        Get quality metrics for a generated medical summary.
        
        Args:
            medical_summary: Generated medical summary
            
        Returns:
            dict: Quality metrics and assessment
        """
        try:
            # Calculate various quality metrics
            condition_confidence_avg = (
                sum(c.confidence_score for c in medical_summary.key_conditions) / 
                len(medical_summary.key_conditions)
            ) if medical_summary.key_conditions else 0.0
            
            # Assess narrative quality
            narrative_quality = self._assess_narrative_quality(medical_summary.summary_text)
            
            # Assess completeness
            completeness_score = self._assess_completeness(medical_summary)
            
            return {
                "overall_data_quality": medical_summary.data_quality_score,
                "condition_confidence_average": condition_confidence_avg,
                "narrative_quality_score": narrative_quality,
                "completeness_score": completeness_score,
                "conditions_count": len(medical_summary.key_conditions),
                "chronological_events_count": len(medical_summary.chronological_events),
                "missing_data_count": len(medical_summary.missing_data_indicators),
                "summary_word_count": len(medical_summary.summary_text.split()),
                "quality_assessment": self._get_quality_assessment(
                    medical_summary.data_quality_score, 
                    condition_confidence_avg, 
                    completeness_score
                )
            }
            
        except Exception as e:
            logger.error(f"Error calculating quality metrics: {str(e)}")
            return {"error": str(e)}
    
    def get_condition_insights(self, patient_data: PatientData) -> dict:
        """
        Get detailed insights about identified conditions.
        
        Args:
            patient_data: Structured patient medical data
            
        Returns:
            dict: Detailed condition insights and recommendations
        """
        try:
            conditions = self.condition_extractor.extract_conditions(patient_data)
            
            insights = {
                "primary_conditions": [],
                "chronic_disease_burden": 0,
                "medication_condition_gaps": [],
                "condition_interactions": [],
                "risk_factors": []
            }
            
            # Identify primary conditions (high confidence, high severity)
            for condition in conditions:
                if condition.confidence_score >= 0.8 and condition.severity in ["high", "moderate"]:
                    insights["primary_conditions"].append({
                        "name": condition.name,
                        "severity": condition.severity,
                        "confidence": condition.confidence_score,
                        "status": condition.status,
                        "first_diagnosed": condition.first_diagnosed
                    })
            
            # Calculate chronic disease burden
            chronic_conditions = [c for c in conditions if self._is_chronic_condition(c.name)]
            insights["chronic_disease_burden"] = len(chronic_conditions)
            
            # Identify potential medication gaps
            insights["medication_condition_gaps"] = self._identify_medication_gaps(patient_data, conditions)
            
            # Identify potential condition interactions
            insights["condition_interactions"] = self._identify_condition_interactions(conditions)
            
            return insights
            
        except Exception as e:
            logger.error(f"Error generating condition insights: {str(e)}")
            return {"error": str(e)}
    
    def _analyze_medication_condition_alignment(self, patient_data: PatientData, conditions: list) -> dict:
        """Analyze how well medications align with identified conditions."""
        alignment = {
            "well_managed_conditions": [],
            "potentially_unmanaged_conditions": [],
            "medications_without_clear_indication": []
        }
        
        condition_names = [c.name.lower() for c in conditions]
        
        # Check medications with clear indications
        for medication in patient_data.medications:
            if medication.indication:
                indication_lower = medication.indication.lower()
                if any(cond in indication_lower or indication_lower in cond for cond in condition_names):
                    alignment["well_managed_conditions"].append({
                        "condition": medication.indication,
                        "medication": medication.name
                    })
                else:
                    alignment["medications_without_clear_indication"].append(medication.name)
        
        # Check conditions without corresponding medications
        medicated_conditions = [med.indication for med in patient_data.medications if med.indication]
        for condition in conditions:
            if condition.name not in medicated_conditions and self._is_chronic_condition(condition.name):
                alignment["potentially_unmanaged_conditions"].append(condition.name)
        
        return alignment
    
    def _assess_narrative_quality(self, narrative_text: str) -> float:
        """Assess the quality of the narrative summary."""
        if not narrative_text:
            return 0.0
        
        quality_score = 0.0
        
        # Length assessment (reasonable length gets points)
        word_count = len(narrative_text.split())
        if 50 <= word_count <= 300:
            quality_score += 0.3
        elif 30 <= word_count <= 500:
            quality_score += 0.2
        
        # Structure assessment (paragraphs, sentences)
        sentence_count = narrative_text.count('.') + narrative_text.count('!') + narrative_text.count('?')
        if sentence_count >= 3:
            quality_score += 0.2
        
        # Content assessment (mentions key medical terms)
        medical_terms = ['condition', 'medication', 'diagnosis', 'treatment', 'patient', 'history']
        term_mentions = sum(1 for term in medical_terms if term in narrative_text.lower())
        quality_score += min(term_mentions * 0.1, 0.3)
        
        # Coherence assessment (basic checks)
        if narrative_text[0].isupper() and narrative_text.endswith('.'):
            quality_score += 0.2
        
        return min(quality_score, 1.0)
    
    def _assess_completeness(self, medical_summary: MedicalSummary) -> float:
        """Assess completeness of the medical summary."""
        completeness_score = 0.0
        
        # Has conditions
        if medical_summary.key_conditions:
            completeness_score += 0.25
        
        # Has chronological events
        if medical_summary.chronological_events:
            completeness_score += 0.25
        
        # Has medication summary
        if medical_summary.medication_summary and "No medications" not in medical_summary.medication_summary:
            completeness_score += 0.25
        
        # Has procedure summary
        if medical_summary.procedure_summary and "No procedures" not in medical_summary.procedure_summary:
            completeness_score += 0.25
        
        return completeness_score
    
    def _get_quality_assessment(self, data_quality: float, condition_confidence: float, completeness: float) -> str:
        """Get overall quality assessment."""
        overall_score = (data_quality + condition_confidence + completeness) / 3
        
        if overall_score >= 0.8:
            return "Excellent"
        elif overall_score >= 0.6:
            return "Good"
        elif overall_score >= 0.4:
            return "Fair"
        else:
            return "Poor"
    
    def _is_chronic_condition(self, condition_name: str) -> bool:
        """Check if condition is chronic."""
        chronic_conditions = {
            'diabetes mellitus', 'diabetes', 'hypertension', 'hyperlipidemia',
            'coronary artery disease', 'chronic kidney disease', 'copd', 'asthma',
            'arthritis', 'depression', 'anxiety', 'hypothyroidism'
        }
        return condition_name.lower() in chronic_conditions
    
    def _identify_medication_gaps(self, patient_data: PatientData, conditions: list) -> list:
        """Identify potential gaps in medication management."""
        gaps = []
        
        # Common condition-medication expectations
        expected_medications = {
            'diabetes mellitus': ['metformin', 'insulin', 'glipizide'],
            'hypertension': ['lisinopril', 'amlodipine', 'losartan', 'atenolol'],
            'hyperlipidemia': ['atorvastatin', 'simvastatin', 'rosuvastatin']
        }
        
        current_medications = [med.name.lower() for med in patient_data.medications if med.status == "active"]
        
        for condition in conditions:
            condition_lower = condition.name.lower()
            if condition_lower in expected_medications:
                expected_meds = expected_medications[condition_lower]
                if not any(med in current_medications for med in expected_meds):
                    gaps.append(f"No typical medication found for {condition.name}")
        
        return gaps
    
    def _identify_condition_interactions(self, conditions: list) -> list:
        """Identify potential condition interactions."""
        interactions = []
        
        condition_names = [c.name.lower() for c in conditions]
        
        # Common condition interactions
        if 'diabetes mellitus' in condition_names and 'hypertension' in condition_names:
            interactions.append("Diabetes and hypertension often co-occur and require coordinated management")
        
        if 'diabetes mellitus' in condition_names and 'hyperlipidemia' in condition_names:
            interactions.append("Diabetes and high cholesterol increase cardiovascular risk")
        
        return interactions
    
    def _generate_request_id(self) -> str:
        """Generate unique request ID for audit trail."""
        import uuid
        return str(uuid.uuid4())
    
    def get_agent_status(self) -> dict:
        """
        Get current status and health of the Medical Summarization Agent.
        
        Returns:
            dict: Agent status information
        """
        try:
            return {
                'agent_name': 'Medical Summarization Agent',
                'status': 'healthy',
                'components': {
                    'condition_extractor': 'operational',
                    'medical_summarizer': 'operational',
                    'audit_logger': 'operational'
                },
                'capabilities': [
                    'condition_extraction',
                    'medical_summarization',
                    'chronological_organization',
                    'narrative_generation',
                    'quality_assessment'
                ],
                'initialized_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'agent_name': 'Medical Summarization Agent',
                'status': 'error',
                'error': str(e),
                'initialized_at': datetime.now().isoformat()
            }
    

    # Alias for backward compatibility
    def generate_medical_summary(self, patient_data: PatientData) -> MedicalSummary:
        """
        Alias for generate_summary() for backward compatibility.
        
        Args:
            patient_data: Structured patient medical data from XML Parser Agent
            
        Returns:
            MedicalSummary: Comprehensive medical summary with conditions and narrative
        """
        return self.generate_summary(patient_data)
