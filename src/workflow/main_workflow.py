"""Main workflow orchestrator for medical record analysis system."""
import logging
from typing import Optional, Dict, Any, Callable, List
from datetime import datetime
import asyncio
import time

from ..agents.xml_parser_agent import XMLParserAgent
from ..agents.medical_summarization_agent import MedicalSummarizationAgent
from ..agents.research_correlation_agent import ResearchCorrelationAgent
from ..agents.report_generator import ReportGenerator
from ..agents.s3_report_persister import S3ReportPersister
from ..models import (
    PatientData, MedicalSummary, ResearchAnalysis, AnalysisReport,
    AgentCommunicationError, XMLParsingError, ResearchError, ReportError, S3Error
)
from ..utils import AuditLogger
from ..utils.error_handler import ErrorHandler, ErrorContext, handle_with_context
from ..utils.enhanced_logging import initialize_logging, log_operation, get_performance_monitor
from ..utils.audit_logger import initialize_audit_logging, get_audit_logger
from ..utils.quality_assurance import (
    initialize_quality_assurance, get_quality_assurance_engine,
    QualityLevel, ValidationSeverity
)
from ..utils.hallucination_prevention import (
    initialize_hallucination_prevention, get_hallucination_prevention_system,
    HallucinationRiskLevel
)

logger = logging.getLogger(__name__)

class WorkflowProgress:
    """Tracks workflow progress and timing."""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.current_step = 0
        self.total_steps = 7
        self.step_times = {}
        self.step_names = [
            "Patient Name Input",
            "XML Parsing & Data Extraction", 
            "Medical Summarization",
            "Research Correlation",
            "Report Generation",
            "Quality Assurance & Validation",
            "Report Persistence"
        ]
    
    def start_step(self, step_index: int):
        """Start timing a workflow step."""
        self.current_step = step_index
        self.step_times[step_index] = {"start": datetime.now()}
        logger.info(f"Starting step {step_index + 1}/{self.total_steps}: {self.step_names[step_index]}")
    
    def complete_step(self, step_index: int):
        """Complete timing a workflow step."""
        if step_index in self.step_times:
            self.step_times[step_index]["end"] = datetime.now()
            duration = (self.step_times[step_index]["end"] - self.step_times[step_index]["start"]).total_seconds()
            self.step_times[step_index]["duration"] = duration
            logger.info(f"Completed step {step_index + 1}/{self.total_steps}: {self.step_names[step_index]} ({duration:.2f}s)")
    
    def get_progress_percentage(self) -> float:
        """Get current progress as percentage."""
        return (self.current_step / self.total_steps) * 100
    
    def get_total_duration(self) -> float:
        """Get total workflow duration in seconds."""
        return (datetime.now() - self.start_time).total_seconds()


class MainWorkflow:
    """
    Main workflow orchestrator that coordinates all agents to perform complete medical record analysis.
    
    This class manages the end-to-end workflow:
    1. Patient name input and validation
    2. XML parsing and data extraction
    3. Medical summarization and condition extraction
    4. Research correlation and literature analysis
    5. Comprehensive report generation
    6. Secure report persistence to S3
    """
    
    def __init__(self, 
                 audit_logger: Optional[AuditLogger] = None,
                 progress_callback: Optional[Callable[[WorkflowProgress], None]] = None,
                 timeout_seconds: int = 300,
                 enable_enhanced_logging: bool = True,
                 log_level: str = "INFO"):
        """
        Initialize main workflow orchestrator.
        
        Args:
            audit_logger: Optional audit logger for HIPAA compliance
            progress_callback: Optional callback function for progress updates
            timeout_seconds: Maximum time allowed for complete workflow
            enable_enhanced_logging: Whether to enable enhanced logging system
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        # Initialize enhanced logging and error handling
        if enable_enhanced_logging:
            self.logging_system = initialize_logging(
                log_level=log_level,
                enable_performance_monitoring=True,
                enable_structured_logging=True
            )
        else:
            self.logging_system = None
        
        # Initialize audit logging
        if not audit_logger:
            audit_logger = initialize_audit_logging()
        self.audit_logger = audit_logger
        
        # Initialize error handler
        self.error_handler = ErrorHandler(audit_logger=self.audit_logger)
        
        # Initialize quality assurance systems
        self.qa_engine = initialize_quality_assurance(
            audit_logger=self.audit_logger,
            error_handler=self.error_handler
        )
        self.hallucination_prevention = initialize_hallucination_prevention(
            audit_logger=self.audit_logger,
            error_handler=self.error_handler,
            strict_mode=True  # Enable strict mode for medical safety
        )
        
        self.progress_callback = progress_callback
        self.timeout_seconds = timeout_seconds
        
        # Initialize all agents
        self.xml_parser = XMLParserAgent(audit_logger=audit_logger)
        self.medical_summarizer = MedicalSummarizationAgent(audit_logger=audit_logger)
        self.research_correlator = ResearchCorrelationAgent(audit_logger=audit_logger)
        self.report_generator = ReportGenerator(audit_logger=audit_logger)
        self.s3_persister = S3ReportPersister(audit_logger=audit_logger)
        
        # Workflow state
        self.current_workflow_id = None
        self.progress = None
        
        # Workflow statistics
        self.stats = {
            "total_workflows": 0,
            "successful_workflows": 0,
            "failed_workflows": 0,
            "average_processing_time": 0.0,
            "last_workflow_time": None,
            "error_statistics": {}
        }
        
        # Register error callbacks
        self._setup_error_callbacks()
        
        logger.info("Main workflow orchestrator initialized with enhanced error handling and logging")
        
        if self.audit_logger:
            self.audit_logger.log_system_event(
                operation="workflow_initialization",
                component="main_workflow",
                outcome="success",
                additional_context={
                    "enhanced_logging": enable_enhanced_logging,
                    "log_level": log_level,
                    "timeout_seconds": timeout_seconds
                }
            )
    
    def _setup_error_callbacks(self):
        """Setup error callbacks for workflow monitoring."""
        def workflow_error_callback(error_record):
            """Handle workflow errors."""
            self.stats["error_statistics"][error_record["error_type"]] = \
                self.stats["error_statistics"].get(error_record["error_type"], 0) + 1
            
            # Log critical errors for immediate attention
            if error_record["severity"] == "critical":
                logger.critical(f"Critical workflow error: {error_record['error_id']}")
        
        # Register callbacks for different error types
        self.error_handler.register_error_callback("XMLParsingError", workflow_error_callback)
        self.error_handler.register_error_callback("ResearchError", workflow_error_callback)
        self.error_handler.register_error_callback("ReportError", workflow_error_callback)
        self.error_handler.register_error_callback("S3Error", workflow_error_callback)
        self.error_handler.register_error_callback("AgentCommunicationError", workflow_error_callback)
        self.error_handler.register_error_callback("*", workflow_error_callback)  # Catch all
    
    async def execute_complete_analysis(self, patient_name: str) -> AnalysisReport:
        """
        Execute complete medical record analysis workflow with comprehensive error handling.
        
        Args:
            patient_name: Name of patient to analyze
            
        Returns:
            AnalysisReport: Complete analysis report
            
        Raises:
            AgentCommunicationError: If agent coordination fails
            XMLParsingError: If XML parsing fails
            ResearchError: If research correlation fails (non-recoverable)
            ReportError: If report generation fails
            S3Error: If report persistence fails (non-recoverable)
        """
        # Generate unique workflow ID
        self.current_workflow_id = f"WF_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(patient_name) % 10000:04d}"
        self.progress = WorkflowProgress()
        
        # Update statistics
        self.stats["total_workflows"] += 1
        workflow_start_time = time.time()
        
        with log_operation("complete_analysis_workflow", "main_workflow", patient_name):
            logger.info(f"Starting complete analysis workflow {self.current_workflow_id} for patient: {patient_name}")
            
            try:
                # Log workflow start
                if self.audit_logger:
                    self.audit_logger.log_patient_access(
                        patient_id=patient_name,
                        operation="workflow_start",
                        component="main_workflow",
                        additional_context={
                            "workflow_id": self.current_workflow_id,
                            "start_timestamp": datetime.now().isoformat()
                        }
                    )
                
                # Step 1: Validate patient name input
                self.progress.start_step(0)
                validated_name = await self._execute_with_error_handling(
                    self._validate_patient_name,
                    patient_name,
                    operation="patient_name_validation",
                    patient_id=patient_name
                )
                self.progress.complete_step(0)
                self._update_progress()
                
                # Step 2: XML parsing and data extraction
                self.progress.start_step(1)
                patient_data = await self._execute_with_error_handling(
                    self._execute_xml_parsing,
                    validated_name,
                    operation="xml_parsing_extraction",
                    patient_id=patient_name
                )
                self.progress.complete_step(1)
                self._update_progress()
                
                # Step 3: Medical summarization
                self.progress.start_step(2)
                medical_summary = await self._execute_medical_summarization(patient_data)
                self.progress.complete_step(2)
                self._update_progress()
                
                # Step 4: Research correlation
                self.progress.start_step(3)
                research_analysis = await self._execute_research_correlation(patient_data, medical_summary)
                self.progress.complete_step(3)
                self._update_progress()
                
                # Step 5: Report generation
                self.progress.start_step(4)
                analysis_report = await self._execute_report_generation(patient_data, medical_summary, research_analysis)
                self.progress.complete_step(4)
                self._update_progress()
                
                # Step 6: Quality assurance and validation
                self.progress.start_step(5)
                quality_assessment = await self._execute_quality_assurance(analysis_report)
                self.progress.complete_step(5)
                self._update_progress()
                
                # Step 7: Report persistence
                self.progress.start_step(6)
                s3_key = await self._execute_report_persistence(analysis_report)
                self.progress.complete_step(6)
                self._update_progress()
            
                # Add S3 key to report metadata
                if hasattr(analysis_report, 'processing_metadata'):
                    analysis_report.processing_metadata['s3_key'] = s3_key
                
                # Log successful completion
                total_duration = self.progress.get_total_duration()
                if self.audit_logger:
                    self.audit_logger.log_patient_access(
                        patient_id=patient_data.patient_id,
                        operation="workflow_complete",
                        component="main_workflow",
                        additional_context={
                            "workflow_id": self.current_workflow_id,
                            "total_duration_seconds": total_duration,
                            "report_id": analysis_report.report_id,
                            "s3_key": s3_key,
                            "step_durations": {name: self.progress.step_times.get(i, {}).get("duration", 0) 
                                             for i, name in enumerate(self.progress.step_names)}
                        }
                    )
                
                # Update workflow statistics
                self._update_workflow_statistics(True, total_duration)
                
                logger.info(f"Workflow {self.current_workflow_id} completed successfully in {total_duration:.2f}s")
                logger.info(f"Generated report: {analysis_report.report_id}")
                logger.info(f"Saved to S3: {s3_key}")
                
                return analysis_report
                
            except asyncio.TimeoutError:
                error_msg = f"Workflow {self.current_workflow_id} timed out after {self.timeout_seconds}s"
                logger.error(error_msg)
                if self.audit_logger:
                    self.audit_logger.log_error(
                        operation="workflow_timeout",
                        component="main_workflow",
                        error=Exception(error_msg),
                        patient_id=getattr(patient_data, 'patient_id', 'UNKNOWN') if 'patient_data' in locals() else 'UNKNOWN'
                    )
                self._update_workflow_statistics(False, workflow_start_time)
                raise AgentCommunicationError(error_msg)
                
            except Exception as e:
                error_msg = f"Workflow {self.current_workflow_id} failed: {str(e)}"
                logger.error(error_msg)
                if self.audit_logger:
                    self.audit_logger.log_error(
                        operation="workflow_error",
                        component="main_workflow",
                        error=e,
                        patient_id=getattr(patient_data, 'patient_id', 'UNKNOWN') if 'patient_data' in locals() else 'UNKNOWN'
                    )
                self._update_workflow_statistics(False, workflow_start_time)
                raise AgentCommunicationError(error_msg)
    
    def _validate_patient_name(self, patient_name: str) -> str:
        """
        Validate and normalize patient name input.
        
        Args:
            patient_name: Raw patient name input
            
        Returns:
            str: Validated and normalized patient name
            
        Raises:
            AgentCommunicationError: If name validation fails
        """
        if not patient_name or not patient_name.strip():
            raise AgentCommunicationError("Patient name cannot be empty")
        
        # Normalize name
        normalized_name = patient_name.strip()
        
        # Basic validation
        if len(normalized_name) < 2:
            raise AgentCommunicationError("Patient name must be at least 2 characters")
        
        if len(normalized_name) > 100:
            raise AgentCommunicationError("Patient name cannot exceed 100 characters")
        
        # Check for valid characters (letters, spaces, hyphens, apostrophes)
        import re
        if not re.match(r"^[a-zA-Z\s\-'\.]+$", normalized_name):
            raise AgentCommunicationError("Patient name contains invalid characters")
        
        logger.info(f"Patient name validated: {normalized_name}")
        return normalized_name
    
    async def _execute_xml_parsing(self, patient_name: str) -> PatientData:
        """Execute XML parsing agent with timeout and validation."""
        try:
            logger.info(f"Executing XML parsing for patient: {patient_name}")
            
            # Execute with timeout
            patient_data = await asyncio.wait_for(
                asyncio.to_thread(self.xml_parser.parse_patient_record, patient_name),
                timeout=60  # 1 minute timeout for XML parsing
            )
            
            # Validate agent output
            if not isinstance(patient_data, PatientData):
                raise AgentCommunicationError("XML Parser returned invalid data type")
            
            validation_errors = patient_data.validate()
            if validation_errors:
                logger.warning(f"Patient data validation warnings: {validation_errors}")
            
            logger.info(f"XML parsing completed for patient ID: {patient_data.patient_id}")
            return patient_data
            
        except asyncio.TimeoutError:
            raise XMLParsingError(f"XML parsing timed out for patient: {patient_name}")
        except Exception as e:
            raise XMLParsingError(f"XML parsing failed for patient {patient_name}: {str(e)}")
    
    async def _execute_medical_summarization(self, patient_data: PatientData) -> MedicalSummary:
        """Execute medical summarization agent with timeout and validation."""
        try:
            logger.info(f"Executing medical summarization for patient: {patient_data.patient_id}")
            
            # Execute with timeout
            medical_summary = await asyncio.wait_for(
                asyncio.to_thread(self.medical_summarizer.generate_medical_summary, patient_data),
                timeout=90  # 1.5 minute timeout for medical summarization
            )
            
            # Validate agent output
            if not isinstance(medical_summary, MedicalSummary):
                raise AgentCommunicationError("Medical Summarizer returned invalid data type")
            
            validation_errors = medical_summary.validate()
            if validation_errors:
                logger.warning(f"Medical summary validation warnings: {validation_errors}")
            
            # Validate patient ID consistency
            if medical_summary.patient_id != patient_data.patient_id:
                raise AgentCommunicationError(
                    f"Patient ID mismatch: XML={patient_data.patient_id}, Summary={medical_summary.patient_id}"
                )
            
            logger.info(f"Medical summarization completed: {len(medical_summary.key_conditions)} conditions identified")
            return medical_summary
            
        except asyncio.TimeoutError:
            raise AgentCommunicationError(f"Medical summarization timed out for patient: {patient_data.patient_id}")
        except Exception as e:
            raise AgentCommunicationError(f"Medical summarization failed: {str(e)}")
    
    async def _execute_research_correlation(self, patient_data: PatientData, 
                                          medical_summary: MedicalSummary) -> ResearchAnalysis:
        """Execute research correlation agent with timeout and validation."""
        try:
            logger.info(f"Executing research correlation for patient: {patient_data.patient_id}")
            
            # Execute with timeout
            research_analysis = await asyncio.wait_for(
                asyncio.to_thread(self.research_correlator.analyze_patient_research, patient_data, medical_summary),
                timeout=120  # 2 minute timeout for research correlation
            )
            
            # Validate agent output
            if not isinstance(research_analysis, ResearchAnalysis):
                raise AgentCommunicationError("Research Correlator returned invalid data type")
            
            validation_errors = research_analysis.validate()
            if validation_errors:
                logger.warning(f"Research analysis validation warnings: {validation_errors}")
            
            # Validate patient ID consistency
            if research_analysis.patient_id != patient_data.patient_id:
                raise AgentCommunicationError(
                    f"Patient ID mismatch: Expected={patient_data.patient_id}, Research={research_analysis.patient_id}"
                )
            
            logger.info(f"Research correlation completed: {len(research_analysis.research_findings)} papers found")
            return research_analysis
            
        except asyncio.TimeoutError:
            raise ResearchError(f"Research correlation timed out for patient: {patient_data.patient_id}")
        except Exception as e:
            raise ResearchError(f"Research correlation failed: {str(e)}")
    
    async def _execute_report_generation(self, patient_data: PatientData,
                                       medical_summary: MedicalSummary,
                                       research_analysis: ResearchAnalysis) -> AnalysisReport:
        """Execute report generation with timeout and validation."""
        try:
            logger.info(f"Executing report generation for patient: {patient_data.patient_id}")
            
            # Execute with timeout
            analysis_report = await asyncio.wait_for(
                asyncio.to_thread(self.report_generator.generate_analysis_report, 
                                patient_data, medical_summary, research_analysis),
                timeout=60  # 1 minute timeout for report generation
            )
            
            # Validate agent output
            if not isinstance(analysis_report, AnalysisReport):
                raise AgentCommunicationError("Report Generator returned invalid data type")
            
            validation_errors = analysis_report.validate()
            if validation_errors:
                logger.warning(f"Analysis report validation warnings: {validation_errors}")
            
            # Validate patient ID consistency
            if analysis_report.patient_data.patient_id != patient_data.patient_id:
                raise AgentCommunicationError(
                    f"Patient ID mismatch in report: Expected={patient_data.patient_id}, Report={analysis_report.patient_data.patient_id}"
                )
            
            logger.info(f"Report generation completed: {analysis_report.report_id}")
            return analysis_report
            
        except asyncio.TimeoutError:
            raise ReportError(f"Report generation timed out for patient: {patient_data.patient_id}")
        except Exception as e:
            raise ReportError(f"Report generation failed: {str(e)}")
    
    async def _execute_quality_assurance(self, analysis_report: AnalysisReport) -> Dict[str, Any]:
        """Execute quality assurance and hallucination prevention checks."""
        try:
            logger.info(f"Executing quality assurance for report: {analysis_report.report_id}")
            
            # Perform comprehensive quality assessment
            quality_assessment = await asyncio.wait_for(
                asyncio.to_thread(self.qa_engine.assess_analysis_quality, analysis_report),
                timeout=60  # 60 second timeout for QA
            )
            
            # Log quality assessment results
            qlevel = getattr(quality_assessment.quality_level, 'value', str(quality_assessment.quality_level))
            logger.info(f"Quality assessment completed: {qlevel} "
                       f"(score: {quality_assessment.overall_score:.3f})")
            
            # Check for critical quality issues
            critical_issues = [issue for issue in quality_assessment.validation_issues 
                             if issue.severity == ValidationSeverity.CRITICAL]
            
            if critical_issues:
                error_msg = f"Critical quality issues detected: {[issue.message for issue in critical_issues]}"
                logger.error(error_msg)
                
                if self.audit_logger:
                    self.audit_logger.log_system_event(
                        operation="critical_quality_issues",
                        component="quality_assurance",
                        additional_context={
                            "report_id": analysis_report.report_id,
                            "patient_id": analysis_report.patient_data.patient_id,
                            "critical_issues": [issue.to_dict() for issue in critical_issues],
                            "quality_level": getattr(quality_assessment.quality_level, 'value', str(quality_assessment.quality_level)),
                            "overall_score": quality_assessment.overall_score
                        }
                    )
                
                raise ReportError(f"Report failed quality assurance: {error_msg}")
            
            # Check hallucination risk
            if quality_assessment.hallucination_risk > 0.8:
                error_msg = f"High hallucination risk detected: {quality_assessment.hallucination_risk:.3f}"
                logger.error(error_msg)
                
                if self.audit_logger:
                    self.audit_logger.log_system_event(
                        operation="high_hallucination_risk",
                        component="quality_assurance",
                        additional_context={
                            "report_id": analysis_report.report_id,
                            "patient_id": analysis_report.patient_data.patient_id,
                            "hallucination_risk": quality_assessment.hallucination_risk,
                            "quality_level": getattr(quality_assessment.quality_level, 'value', str(quality_assessment.quality_level))
                        }
                    )
                
                raise ReportError(f"Report failed hallucination check: {error_msg}")
            
            # Check if quality level is acceptable
            if quality_assessment.quality_level == QualityLevel.UNACCEPTABLE:
                error_msg = f"Report quality is unacceptable: {quality_assessment.overall_score:.3f}"
                logger.error(error_msg)
                
                if self.audit_logger:
                    self.audit_logger.log_system_event(
                        operation="unacceptable_quality",
                        component="quality_assurance",
                        additional_context={
                            "report_id": analysis_report.report_id,
                            "patient_id": analysis_report.patient_data.patient_id,
                            "quality_level": getattr(quality_assessment.quality_level, 'value', str(quality_assessment.quality_level)),
                            "overall_score": quality_assessment.overall_score,
                            "recommendations": quality_assessment.recommendations
                        }
                    )
                
                raise ReportError(f"Report quality is unacceptable: {error_msg}")
            
            # Add quality assessment to report metadata
            if hasattr(analysis_report, 'processing_metadata'):
                analysis_report.processing_metadata['quality_assessment'] = quality_assessment.to_dict()
            else:
                analysis_report.processing_metadata = {'quality_assessment': quality_assessment.to_dict()}
            
            # Log successful quality assurance
            if self.audit_logger:
                self.audit_logger.log_system_event(
                    operation="quality_assurance_passed",
                    component="quality_assurance",
                    additional_context={
                        "report_id": analysis_report.report_id,
                        "patient_id": analysis_report.patient_data.patient_id,
                            "quality_level": getattr(quality_assessment.quality_level, 'value', str(quality_assessment.quality_level)),
                        "overall_score": quality_assessment.overall_score,
                        "hallucination_risk": quality_assessment.hallucination_risk,
                        "validation_issues_count": len(quality_assessment.validation_issues)
                    }
                )
            
            logger.info(f"Quality assurance passed for report: {analysis_report.report_id}")
            return quality_assessment.to_dict()
            
        except asyncio.TimeoutError:
            raise ReportError(f"Quality assurance timed out for report: {analysis_report.report_id}")
        except Exception as e:
            if isinstance(e, ReportError):
                raise  # Re-raise ReportError as-is
            raise ReportError(f"Quality assurance failed: {str(e)}")
    
    async def _execute_report_persistence(self, analysis_report: AnalysisReport) -> str:
        """Execute report persistence to S3 with timeout and validation."""
        try:
            logger.info(f"Executing report persistence for report: {analysis_report.report_id}")
            
            # Execute with timeout
            s3_key = await asyncio.wait_for(
                asyncio.to_thread(self.s3_persister.save_analysis_report, analysis_report),
                timeout=30  # 30 second timeout for S3 upload
            )
            
            # Validate S3 key
            if not s3_key or not isinstance(s3_key, str):
                raise AgentCommunicationError("S3 Persister returned invalid S3 key")
            
            logger.info(f"Report persistence completed: {s3_key}")
            return s3_key
            
        except asyncio.TimeoutError:
            raise S3Error(f"Report persistence timed out for report: {analysis_report.report_id}")
        except Exception as e:
            raise S3Error(f"Report persistence failed: {str(e)}")
    
    def _update_progress(self):
        """Update progress and call progress callback if provided."""
        if self.progress_callback and self.progress:
            try:
                self.progress_callback(self.progress)
            except Exception as e:
                logger.warning(f"Progress callback failed: {str(e)}")
    
    def get_workflow_status(self) -> Dict[str, Any]:
        """
        Get current workflow status and progress information.
        
        Returns:
            Dict[str, Any]: Workflow status information
        """
        if not self.progress:
            return {"status": "not_started"}
        
        return {
            "status": "running" if self.progress.current_step < self.progress.total_steps else "completed",
            "workflow_id": self.current_workflow_id,
            "current_step": self.progress.current_step + 1,
            "total_steps": self.progress.total_steps,
            "current_step_name": self.progress.step_names[self.progress.current_step] if self.progress.current_step < len(self.progress.step_names) else "Completed",
            "progress_percentage": self.progress.get_progress_percentage(),
            "total_duration_seconds": self.progress.get_total_duration(),
            "step_durations": {
                name: self.progress.step_times.get(i, {}).get("duration", 0)
                for i, name in enumerate(self.progress.step_names)
            }
        }
    
    async def cancel_workflow(self) -> bool:
        """
        Cancel the current workflow if running.
        
        Returns:
            bool: True if workflow was cancelled, False if no workflow running
        """
        if not self.current_workflow_id:
            return False
        
        logger.info(f"Cancelling workflow: {self.current_workflow_id}")
        
        if self.audit_logger:
            self.audit_logger.log_data_access(
                patient_id="WORKFLOW_CANCEL",
                operation="workflow_cancel",
                details={
                    "workflow_id": self.current_workflow_id,
                    "cancelled_at_step": self.progress.current_step if self.progress else 0,
                    "cancel_timestamp": datetime.now().isoformat()
                }
            )
        
        # Reset workflow state
        self.current_workflow_id = None
        self.progress = None
        
        return True
    
    async def _execute_with_error_handling(self, func, *args, operation: str, patient_id: str, **kwargs):
        """
        Execute a function with comprehensive error handling.
        
        Args:
            func: Function to execute
            *args: Function arguments
            operation: Operation name for logging
            patient_id: Patient ID for audit logging
            **kwargs: Function keyword arguments
            
        Returns:
            Function result or None if recoverable error occurred
            
        Raises:
            Exception: If non-recoverable error occurred
        """
        context = ErrorContext(
            operation=operation,
            patient_id=patient_id,
            component="main_workflow"
        )
        
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        except Exception as e:
            result = self.error_handler.handle_error(e, context)
            
            if result["is_recoverable"]:
                logger.warning(f"Recovered from error in {operation}: {result['user_message']}")
                return None
            else:
                logger.error(f"Non-recoverable error in {operation}: {result['user_message']}")
                raise
    
    def _update_workflow_statistics(self, success: bool, processing_time: float):
        """Update workflow statistics."""
        if success:
            self.stats["successful_workflows"] += 1
        else:
            self.stats["failed_workflows"] += 1
        
        # Update average processing time
        total_time = (self.stats["average_processing_time"] * (self.stats["total_workflows"] - 1)) + processing_time
        self.stats["average_processing_time"] = total_time / self.stats["total_workflows"]
        self.stats["last_workflow_time"] = datetime.now().isoformat()
    
    def get_workflow_statistics(self) -> Dict[str, Any]:
        """Get current workflow statistics."""
        stats = self.stats.copy()
        
        # Add error handler statistics
        if self.error_handler:
            stats["error_handler_stats"] = self.error_handler.get_error_statistics()
        
        # Add performance statistics
        if self.logging_system:
            perf_monitor = self.logging_system.get_performance_monitor()
            if perf_monitor:
                stats["performance_stats"] = perf_monitor.get_statistics()
        
        # Add quality assurance statistics
        if self.qa_engine:
            stats["quality_assurance_stats"] = self.qa_engine.get_quality_statistics()
        
        # Add hallucination prevention statistics
        if self.hallucination_prevention:
            stats["hallucination_prevention_stats"] = self.hallucination_prevention.get_prevention_statistics()
        
        return stats
    
    def get_recent_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent workflow errors."""
        if self.error_handler:
            return self.error_handler.get_recent_errors(limit)
        return []
    
    def clear_statistics(self):
        """Clear workflow statistics (for testing or maintenance)."""
        self.stats = {
            "total_workflows": 0,
            "successful_workflows": 0,
            "failed_workflows": 0,
            "average_processing_time": 0.0,
            "last_workflow_time": None,
            "error_statistics": {}
        }
        
        if self.error_handler:
            self.error_handler.clear_error_statistics()
        
        if self.logging_system:
            perf_monitor = self.logging_system.get_performance_monitor()
            if perf_monitor:
                perf_monitor.clear_metrics()
        
        logger.info("Workflow statistics cleared")