"""Bedrock-based research analysis using Claude models."""

import logging
from typing import Dict, Any
from datetime import datetime

from ..utils.bedrock_client import BedrockClient
from ..utils import AuditLogger

logger = logging.getLogger(__name__)


class BedrockResearchAnalyzer:
    """Research analysis using AWS Bedrock Claude models."""
    
    def __init__(self,
                 bedrock_client: BedrockClient = None,
                 audit_logger: AuditLogger = None):
        """
        Initialize Bedrock research analyzer.
        
        Args:
            bedrock_client: Optional Bedrock client
            audit_logger: Optional audit logger for HIPAA compliance
        """
        self.bedrock_client = bedrock_client or BedrockClient()
        self.audit_logger = audit_logger
        
        logger.info("Bedrock Research Analyzer initialized")
    
    def analyze_with_research(self, 
                            patient_id: str,
                            medical_summary: str) -> Dict[str, Any]:
        """
        Generate research-based medical analysis using Claude.
        
        Args:
            patient_id: Patient identifier
            medical_summary: Medical summary from first Claude call
            
        Returns:
            Dict containing research analysis and recommendations
        """
        try:
            logger.info(f"Generating research analysis for patient: {patient_id}")
            
            # Log to audit trail
            if self.audit_logger:
                self.audit_logger.log_processing_start(
                    patient_id=patient_id,
                    workflow_type="bedrock_research_analysis",
                    request_id=f"bedrock_res_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                )
            
            # Create research analysis prompt
            prompt = self._create_research_prompt(medical_summary)
            
            # Create system prompt for research context
            system_prompt = self._create_research_system_prompt()
            
            logger.info(f"Calling Bedrock Claude for research analysis...")
            logger.info(f"Prompt: {len(prompt)} chars, System: {len(system_prompt)} chars")
            
            # Invoke Claude
            response = self.bedrock_client.invoke_with_retry(
                prompt=prompt,
                system_prompt=system_prompt,
                max_retries=3
            )
            
            # Parse response
            analysis_text = response['text']
            
            logger.info(f"✓ Bedrock returned research analysis: {len(analysis_text)} characters")
            logger.info(f"  Model: {response.get('model_id')}")
            logger.info(f"  Tokens: {response.get('usage', {})}")
            
            logger.info(f"Research analysis generated successfully for {patient_id}")
            
            return {
                'analysis_text': analysis_text,
                'patient_id': patient_id,
                'model_info': response.get('model_id'),
                'usage': response.get('usage', {}),
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate research analysis: {str(e)}")
            raise
    
    def _create_research_prompt(self, medical_summary: str) -> str:
        """Create prompt for research-based analysis."""
        
        prompt = f"""Based on the following patient medical summary, provide a comprehensive research-based medical analysis with clinical references.

PATIENT MEDICAL SUMMARY:
{medical_summary}

Please provide:

1. **Clinical Research Context**
   - Identify the key medical conditions and their clinical significance
   - Reference current clinical guidelines and evidence-based practices
   - Cite relevant medical literature and research findings

2. **Evidence-Based Treatment Analysis**
   - Evaluate current medications against evidence-based guidelines
   - Identify any gaps in treatment based on current research
   - Suggest evidence-based treatment considerations

3. **Risk Assessment**
   - Identify potential health risks based on current conditions
   - Reference epidemiological data and risk factors
   - Highlight areas requiring clinical attention

4. **Research-Backed Recommendations**
   - Provide evidence-based recommendations for care
   - Reference clinical practice guidelines
   - Suggest areas for further evaluation or monitoring

5. **References**
   - Cite relevant clinical guidelines (e.g., AHA, ADA, ACC)
   - Reference major clinical trials or meta-analyses
   - Include evidence levels for recommendations

Format your response with clear sections and include specific references to clinical research, guidelines, and evidence-based practices. Use standard medical citation format where applicable.
"""
        
        return prompt
    
    def _create_research_system_prompt(self) -> str:
        """Create system prompt for research analysis."""
        return """You are a clinical research analyst with expertise in evidence-based medicine. Your role is to:

1. Analyze patient medical summaries through the lens of current clinical research
2. Reference evidence-based clinical guidelines and best practices
3. Cite relevant medical literature and research findings
4. Provide research-backed recommendations and insights
5. Assess treatments against current evidence-based standards
6. Identify areas where clinical research provides guidance

Guidelines for your analysis:
- Base all recommendations on published clinical evidence
- Reference specific clinical guidelines (AHA, ADA, ACC, USPSTF, etc.)
- Cite major clinical trials and meta-analyses when relevant
- Use evidence grading (Level A, B, C) where appropriate
- Distinguish between strong evidence and expert opinion
- Focus on clinically actionable insights
- Maintain objectivity and scientific rigor
- Use standard medical citation formats

Important:
- Only reference well-established clinical guidelines and research
- Indicate the strength of evidence for recommendations
- Note when evidence is limited or conflicting
- Do not make specific treatment recommendations (defer to treating physician)
- Focus on evidence-based insights and considerations"""
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the Bedrock model being used."""
        return self.bedrock_client.get_model_info()
