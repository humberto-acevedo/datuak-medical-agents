"""Bedrock-based workflow orchestrator using Claude models or Bedrock Agents."""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
import json
import uuid

from ..agents.xml_parser_agent import XMLParserAgent
from ..agents.bedrock_medical_summarizer import BedrockMedicalSummarizer
from ..agents.bedrock_research_analyzer import BedrockResearchAnalyzer
from ..agents.s3_report_persister import S3ReportPersister
from ..utils.bedrock_client import BedrockClient
from ..utils.bedrock_agent_client import BedrockAgentClient
from ..utils import AuditLogger
from ..models import PatientData

logger = logging.getLogger(__name__)


class BedrockWorkflow:
    """Orchestrates medical analysis workflow using AWS Bedrock Claude models or Bedrock Agents."""
    
    def __init__(self,
                 xml_parser_agent: XMLParserAgent = None,
                 bedrock_client: BedrockClient = None,
                 s3_persister: S3ReportPersister = None,
                 audit_logger: AuditLogger = None,
                 use_bedrock_agent: bool = False,
                 agent_id: Optional[str] = None,
                 agent_alias_id: Optional[str] = None):
        """
        Initialize Bedrock workflow.
        
        Args:
            xml_parser_agent: Agent for parsing XML from S3
            bedrock_client: Bedrock client for Claude models
            s3_persister: Agent for persisting reports to S3
            audit_logger: Audit logger for HIPAA compliance
            use_bedrock_agent: If True, use Bedrock Agent instead of direct model calls
            agent_id: Bedrock Agent ID (required if use_bedrock_agent=True)
            agent_alias_id: Bedrock Agent Alias ID (required if use_bedrock_agent=True)
        """
        self.use_bedrock_agent = use_bedrock_agent
        self.audit_logger = audit_logger
        
        if use_bedrock_agent:
            if not agent_id or not agent_alias_id:
                raise ValueError("agent_id and agent_alias_id required when use_bedrock_agent=True")
            self.agent_client = BedrockAgentClient(agent_id, agent_alias_id)
            logger.info("Bedrock Workflow initialized with Bedrock Agent")
        else:
            self.xml_parser_agent = xml_parser_agent or XMLParserAgent()
            self.bedrock_client = bedrock_client or BedrockClient()
            self.medical_summarizer = BedrockMedicalSummarizer(self.bedrock_client, audit_logger)
            self.research_analyzer = BedrockResearchAnalyzer(self.bedrock_client, audit_logger)
            self.s3_persister = s3_persister or S3ReportPersister(audit_logger)
            logger.info("Bedrock Workflow initialized with Claude models")
    
    def _ensure_direct_model_components(self):
        """Ensure all direct model components are initialized (for fallback scenarios)."""
        if not hasattr(self, 'xml_parser_agent') or self.xml_parser_agent is None:
            logger.info("Initializing XML parser agent for fallback...")
            self.xml_parser_agent = XMLParserAgent()
        
        if not hasattr(self, 'bedrock_client') or self.bedrock_client is None:
            logger.info("Initializing Bedrock client for fallback...")
            self.bedrock_client = BedrockClient()
        
        if not hasattr(self, 'medical_summarizer') or self.medical_summarizer is None:
            logger.info("Initializing medical summarizer for fallback...")
            self.medical_summarizer = BedrockMedicalSummarizer(self.bedrock_client, self.audit_logger)
        
        if not hasattr(self, 'research_analyzer') or self.research_analyzer is None:
            logger.info("Initializing research analyzer for fallback...")
            self.research_analyzer = BedrockResearchAnalyzer(self.bedrock_client, self.audit_logger)
        
        if not hasattr(self, 's3_persister') or self.s3_persister is None:
            logger.info("Initializing S3 persister for fallback...")
            self.s3_persister = S3ReportPersister(self.audit_logger)
    
    def execute_analysis(self, patient_name: str) -> Dict[str, Any]:
        """
        Execute complete medical analysis workflow using Bedrock.
        
        Args:
            patient_name: Name of patient to analyze
            
        Returns:
            Dict containing complete analysis results
        """
        if self.use_bedrock_agent:
            return self._execute_with_bedrock_agent(patient_name)
        else:
            return self._execute_with_direct_models(patient_name)
    
    def _execute_with_bedrock_agent(self, patient_name: str) -> Dict[str, Any]:
        """Execute analysis using Bedrock Agent with fallback to direct models."""
        workflow_id = f"BEDROCK_AGENT_WF_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        start_time = datetime.now()
        
        try:
            logger.info(f"=" * 80)
            logger.info(f"Starting Bedrock Agent Workflow: {workflow_id}")
            logger.info(f"Patient: {patient_name}")
            logger.info(f"=" * 80)
            
            # Invoke Bedrock Agent - it orchestrates everything
            input_text = f"Analyze medical records for patient: {patient_name}"
            response = self.agent_client.invoke_agent(input_text)
            
            # Parse agent response (should be JSON from Lambda)
            try:
                result = json.loads(response)
            except json.JSONDecodeError:
                result = {'raw_response': response, 'patient_name': patient_name}
            
            duration = (datetime.now() - start_time).total_seconds()
            result['duration_seconds'] = duration
            result['workflow_type'] = 'bedrock_agent'
            result['workflow_id'] = workflow_id
            
            logger.info(f"\n" + "=" * 80)
            logger.info(f"Bedrock Agent workflow completed in {duration:.2f}s")
            logger.info(f"=" * 80)
            
            return result
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            error_msg = str(e)
            
            # Check if it's a Lambda permission error
            if "dependencyFailedException" in error_msg and "Access denied" in error_msg and "Lambda function" in error_msg:
                logger.warning(f"Bedrock Agent Lambda permission error after {duration:.2f}s")
                logger.warning("Falling back to direct Claude model calls...")
                
                # Fallback to direct models
                try:
                    return self._execute_with_direct_models(patient_name)
                except Exception as fallback_error:
                    logger.error(f"Fallback to direct models also failed: {str(fallback_error)}")
                    raise Exception(f"Both Bedrock Agent and direct models failed. Agent error: {error_msg}. Direct model error: {str(fallback_error)}")
            else:
                logger.error(f"Bedrock Agent workflow failed after {duration:.2f}s: {error_msg}")
                raise
    
    def _execute_with_direct_models(self, patient_name: str) -> Dict[str, Any]:
        """Execute analysis using direct Claude model calls."""
        workflow_id = f"BEDROCK_WF_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        start_time = datetime.now()
        
        try:
            logger.info(f"=" * 80)
            logger.info(f"Starting Bedrock Workflow: {workflow_id}")
            logger.info(f"Patient: {patient_name}")
            logger.info(f"=" * 80)
            
            # Initialize components if not already initialized (for fallback scenarios)
            self._ensure_direct_model_components()
            
            # Step 1: Parse XML from S3
            logger.info("\n[Step 1/4] Parsing patient XML from S3...")
            patient_data = self.xml_parser_agent.parse_patient_record(patient_name)
            logger.info(f"✓ Patient data extracted: {patient_data.patient_id}")
            logger.info(f"  - Medications: {len(patient_data.medications)}")
            logger.info(f"  - Diagnoses: {len(patient_data.diagnoses)}")
            logger.info(f"  - Procedures: {len(patient_data.procedures)}")
            
            # Step 2: Generate medical summary using Claude
            logger.info("\n[Step 2/4] Generating medical summary with Claude...")
            summary_response = self.medical_summarizer.generate_summary(patient_data)
            medical_summary_text = summary_response['summary_text']
            logger.info(f"✓ Medical summary generated ({len(medical_summary_text)} characters)")
            logger.info(f"  - Model: {summary_response.get('model_info', 'Claude')}")
            logger.info(f"  - Tokens used: {summary_response.get('usage', {})}")
            
            # Step 3: Generate research analysis using Claude
            logger.info("\n[Step 3/4] Generating research analysis with Claude...")
            research_response = self.research_analyzer.analyze_with_research(
                patient_id=patient_data.patient_id,
                medical_summary=medical_summary_text
            )
            research_analysis_text = research_response['analysis_text']
            logger.info(f"✓ Research analysis generated ({len(research_analysis_text)} characters)")
            logger.info(f"  - Model: {research_response.get('model_info', 'Claude')}")
            logger.info(f"  - Tokens used: {research_response.get('usage', {})}")
            
            # Step 4: Create and persist complete report
            logger.info("\n[Step 4/4] Creating and persisting report to S3...")
            report = self._create_report(
                patient_data=patient_data,
                medical_summary=medical_summary_text,
                research_analysis=research_analysis_text,
                summary_metadata=summary_response,
                research_metadata=research_response,
                workflow_id=workflow_id
            )
            
            # Save to S3
            s3_key = self._persist_report(report, patient_data.patient_id)
            logger.info(f"✓ Report saved to S3: {s3_key}")
            
            # Calculate total time
            duration = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"\n" + "=" * 80)
            logger.info(f"Workflow completed successfully in {duration:.2f}s")
            logger.info(f"=" * 80)
            
            return {
                'success': True,
                'workflow_id': workflow_id,
                'patient_id': patient_data.patient_id,
                'patient_name': patient_data.name,
                'medical_summary': medical_summary_text,
                'research_analysis': research_analysis_text,
                'report': report,
                's3_key': s3_key,
                'duration_seconds': duration,
                'model_info': self.bedrock_client.get_model_info()
            }
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"Workflow failed after {duration:.2f}s: {str(e)}")
            raise
    
    def _create_report(self,
                      patient_data: PatientData,
                      medical_summary: str,
                      research_analysis: str,
                      summary_metadata: Dict[str, Any],
                      research_metadata: Dict[str, Any],
                      workflow_id: str) -> Dict[str, Any]:
        """Create comprehensive report from analysis results."""
        
        report = {
            'report_id': f"RPT_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{workflow_id[-8:]}",
            'workflow_id': workflow_id,
            'generated_at': datetime.now().isoformat(),
            'patient_info': {
                'patient_id': patient_data.patient_id,
                'name': patient_data.name,
                'age': patient_data.demographics.age,
                'gender': patient_data.demographics.gender,
                'date_of_birth': patient_data.demographics.date_of_birth
            },
            'medical_summary': {
                'text': medical_summary,
                'generated_by': summary_metadata.get('model_info', 'Claude'),
                'generated_at': summary_metadata.get('generated_at'),
                'token_usage': summary_metadata.get('usage', {})
            },
            'research_analysis': {
                'text': research_analysis,
                'generated_by': research_metadata.get('model_info', 'Claude'),
                'generated_at': research_metadata.get('generated_at'),
                'token_usage': research_metadata.get('usage', {})
            },
            'data_summary': {
                'total_medications': len(patient_data.medications),
                'total_diagnoses': len(patient_data.diagnoses),
                'total_procedures': len(patient_data.procedures),
                'total_medical_events': len(patient_data.medical_history)
            },
            'metadata': {
                'workflow_type': 'bedrock_claude_analysis',
                'model_provider': 'AWS Bedrock',
                'model_name': self.bedrock_client.get_model_info()['model_name'],
                'region': self.bedrock_client.region
            }
        }
        
        return report
    
    def _persist_report(self, report: Dict[str, Any], patient_id: str) -> str:
        """Persist report to S3."""
        
        # Convert report to JSON
        report_json = json.dumps(report, indent=2, default=str)
        
        # Generate S3 key
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        s3_key = f"analysis-reports/patient-{patient_id}/bedrock-analysis-{timestamp}-{report['report_id']}.json"
        
        # Save to S3
        self.s3_persister.s3_client.put_object(
            Bucket=self.s3_persister.bucket_name,
            Key=s3_key,
            Body=report_json.encode('utf-8')
        )
        
        return s3_key
    
    def get_workflow_info(self) -> Dict[str, Any]:
        """Get information about the workflow configuration."""
        return {
            'workflow_type': 'Bedrock Claude Analysis',
            'model_info': self.bedrock_client.get_model_info(),
            'components': {
                'xml_parser': 'XMLParserAgent with CDA support',
                'medical_summarizer': 'Bedrock Claude',
                'research_analyzer': 'Bedrock Claude',
                's3_persistence': 'S3ReportPersister'
            }
        }
