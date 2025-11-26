"""Bedrock-based medical summarization using Claude models."""

import logging
from typing import Dict, Any
from datetime import datetime

from ..models import PatientData, MedicalSummary
from ..utils.bedrock_client import BedrockClient
from ..utils import AuditLogger

logger = logging.getLogger(__name__)


class BedrockMedicalSummarizer:
    """Medical summarization using AWS Bedrock Claude models."""
    
    def __init__(self, 
                 bedrock_client: BedrockClient = None,
                 audit_logger: AuditLogger = None):
        """
        Initialize Bedrock medical summarizer.
        
        Args:
            bedrock_client: Optional Bedrock client (creates default if not provided)
            audit_logger: Optional audit logger for HIPAA compliance
        """
        self.bedrock_client = bedrock_client or BedrockClient()
        self.audit_logger = audit_logger
        
        logger.info("Bedrock Medical Summarizer initialized")
    
    def generate_summary(self, patient_data: PatientData) -> Dict[str, Any]:
        """
        Generate medical summary using Claude.
        
        Args:
            patient_data: Parsed patient data from XML
            
        Returns:
            Dict containing summary text and structured data
        """
        try:
            logger.info(f"Generating medical summary for patient: {patient_data.patient_id}")
            
            # Log to audit trail
            if self.audit_logger:
                self.audit_logger.log_processing_start(
                    patient_id=patient_data.patient_id,
                    workflow_type="bedrock_summarization",
                    request_id=f"bedrock_sum_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                )
            
            # Create prompt from patient data
            prompt = self._create_summarization_prompt(patient_data)
            
            # Create system prompt for medical context
            system_prompt = self._create_system_prompt()
            
            # Invoke Claude
            response = self.bedrock_client.invoke_with_retry(
                prompt=prompt,
                system_prompt=system_prompt,
                max_retries=3
            )
            
            # Parse response
            summary_text = response['text']
            
            # Extract structured data from response
            structured_summary = self._parse_summary_response(summary_text, patient_data)
            
            logger.info(f"Medical summary generated successfully for {patient_data.patient_id}")
            
            return {
                'summary_text': summary_text,
                'structured_summary': structured_summary,
                'model_info': response.get('model_id'),
                'usage': response.get('usage', {}),
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate medical summary: {str(e)}")
            raise
    
    def _create_summarization_prompt(self, patient_data: PatientData) -> str:
        """Create prompt for medical summarization."""
        
        # Build patient information section
        patient_info = f"""
Patient Information:
- Name: {patient_data.name}
- Age: {patient_data.demographics.age if patient_data.demographics.age else 'Unknown'}
- Gender: {patient_data.demographics.gender if patient_data.demographics.gender else 'Unknown'}
- Date of Birth: {patient_data.demographics.date_of_birth if patient_data.demographics.date_of_birth else 'Unknown'}
"""
        
        # Build medications section
        medications_text = "\n".join([
            f"- {med.name} ({med.dosage}) - Status: {med.status}"
            for med in patient_data.medications[:20]  # Limit to avoid token limits
        ]) if patient_data.medications else "No medications recorded"
        
        # Build diagnoses section
        diagnoses_text = "\n".join([
            f"- {diag.condition} (ICD-10: {diag.icd_10_code if diag.icd_10_code else 'N/A'}) - Status: {diag.status}"
            for diag in patient_data.diagnoses[:20]
        ]) if patient_data.diagnoses else "No diagnoses recorded"
        
        # Build procedures section
        procedures_text = "\n".join([
            f"- {proc.name} on {proc.date}"
            for proc in patient_data.procedures[:15]
        ]) if patient_data.procedures else "No procedures recorded"
        
        # Build medical history section
        history_text = "\n".join([
            f"- {event.date}: {event.description}"
            for event in patient_data.medical_history[:10]
        ]) if patient_data.medical_history else "No medical history recorded"
        
        prompt = f"""Please analyze the following patient medical record and provide a comprehensive medical summary.

{patient_info}

Medications ({len(patient_data.medications)} total):
{medications_text}

Diagnoses/Conditions ({len(patient_data.diagnoses)} total):
{diagnoses_text}

Procedures ({len(patient_data.procedures)} total):
{procedures_text}

Medical History ({len(patient_data.medical_history)} events):
{history_text}

Please provide:
1. A comprehensive narrative summary of the patient's medical history
2. Key medical conditions identified (list the top 5-10 most significant)
3. Current medication regimen and its purpose
4. Notable procedures or interventions
5. Overall health status assessment
6. Any patterns or concerns that should be highlighted

Format your response in clear sections with headers.
"""
        
        return prompt
    
    def _create_system_prompt(self) -> str:
        """Create system prompt for medical context."""
        return """You are an expert medical analyst reviewing patient records. Your role is to:

1. Analyze medical records comprehensively and accurately
2. Identify key medical conditions and their significance
3. Summarize medication regimens and their therapeutic purposes
4. Highlight important procedures and interventions
5. Assess overall health status based on available data
6. Use proper medical terminology while remaining clear
7. Focus on clinically significant information
8. Maintain objectivity and base conclusions on documented evidence

Important guidelines:
- Only report information present in the medical record
- Do not speculate or add information not in the record
- Use standard medical terminology
- Organize information logically and clearly
- Highlight chronic conditions and ongoing treatments
- Note any concerning patterns or gaps in care"""
    
    def _parse_summary_response(self, summary_text: str, patient_data: PatientData) -> Dict[str, Any]:
        """Parse Claude's response into structured format."""
        
        # For now, return a structured format
        # In future, could use Claude to extract structured data
        return {
            'patient_id': patient_data.patient_id,
            'patient_name': patient_data.name,
            'summary_text': summary_text,
            'total_medications': len(patient_data.medications),
            'total_diagnoses': len(patient_data.diagnoses),
            'total_procedures': len(patient_data.procedures),
            'data_quality_score': self._assess_data_quality(patient_data),
            'generated_timestamp': datetime.now().isoformat()
        }
    
    def _assess_data_quality(self, patient_data: PatientData) -> float:
        """Assess quality of patient data."""
        score = 0.0
        
        # Demographics completeness
        if patient_data.demographics.age:
            score += 0.2
        if patient_data.demographics.gender:
            score += 0.2
        
        # Data presence
        if patient_data.medications:
            score += 0.2
        if patient_data.diagnoses:
            score += 0.2
        if patient_data.procedures or patient_data.medical_history:
            score += 0.2
        
        return min(score, 1.0)
