"""Report generation functionality for medical record analysis."""
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime
import json
import uuid

from ..models import (
    PatientData, MedicalSummary, ResearchAnalysis, AnalysisReport,
    ReportError
)
from ..utils import AuditLogger

logger = logging.getLogger(__name__)

class ReportGenerator:
    """
    Generates comprehensive analysis reports by combining outputs from all agents.
    
    This class takes the results from XML Parser Agent, Medical Summarization Agent,
    and Research Correlation Agent to create unified, comprehensive analysis reports.
    """
    
    def __init__(self, audit_logger: Optional[AuditLogger] = None):
        """
        Initialize report generator.
        
        Args:
            audit_logger: Optional audit logger for HIPAA compliance
        """
        self.audit_logger = audit_logger
        self.report_version = "1.0"
        self.system_info = {
            "system_name": "Medical Record Analysis System",
            "version": "1.0.0",
            "components": ["XML Parser", "Medical Summarizer", "Research Correlator"]
        }
        
        logger.info("Report generator initialized")
    
    def generate_analysis_report(self, 
                               patient_data: PatientData,
                               medical_summary: MedicalSummary,
                               research_analysis: ResearchAnalysis) -> AnalysisReport:
        """
        Generate comprehensive analysis report from all agent outputs.
        
        Args:
            patient_data: Patient data from XML Parser Agent
            medical_summary: Medical summary from Medical Summarization Agent
            research_analysis: Research analysis from Research Correlation Agent
            
        Returns:
            AnalysisReport: Comprehensive analysis report
            
        Raises:
            ReportError: If report generation fails
        """
        logger.info(f"Generating analysis report for patient {patient_data.patient_id}")
        
        try:
            # Log report generation start
            if self.audit_logger:
                self.audit_logger.log_data_access(
                    patient_id=patient_data.patient_id,
                    operation="report_generation_start",
                    details={
                        "report_type": "comprehensive_analysis",
                        "generation_timestamp": datetime.now().isoformat()
                    }
                )
            
            # Generate unique report ID
            report_id = self._generate_report_id()
            
            # Create executive summary
            executive_summary = self._create_executive_summary(
                patient_data, medical_summary, research_analysis
            )
            
            # Generate quality metrics
            quality_metrics = self._calculate_quality_metrics(
                patient_data, medical_summary, research_analysis
            )
            
            # Create recommendations summary
            recommendations = self._compile_recommendations(
                medical_summary, research_analysis
            )
            
            # Generate report metadata
            metadata = self._create_report_metadata(
                patient_data, medical_summary, research_analysis
            )
            
            # Create comprehensive analysis report
            start_time = datetime.now()
            analysis_report = AnalysisReport(
                report_id=report_id,
                patient_data=patient_data,
                medical_summary=medical_summary,
                research_analysis=research_analysis,
                generated_timestamp=start_time,
                processing_time_seconds=0.0,  # Will be calculated later
                agent_versions={
                    "xml_parser": "1.0",
                    "medical_summarizer": "1.0", 
                    "research_correlator": "1.0",
                    "report_generator": self.report_version
                },
                quality_metrics=quality_metrics
            )
            
            # Add additional report attributes
            analysis_report.executive_summary = executive_summary
            analysis_report.key_findings = self._extract_key_findings(medical_summary, research_analysis)
            analysis_report.recommendations = recommendations
            analysis_report.data_sources = self._compile_data_sources(research_analysis)
            analysis_report.processing_metadata = metadata
            analysis_report.report_version = self.report_version
            
            # Validate report completeness
            validation_errors = analysis_report.validate()
            if validation_errors:
                logger.warning(f"Report validation warnings: {validation_errors}")
            
            # Calculate processing time
            end_time = datetime.now()
            analysis_report.processing_time_seconds = (end_time - start_time).total_seconds()
            
            # Log successful completion
            if self.audit_logger:
                self.audit_logger.log_data_access(
                    patient_id=patient_data.patient_id,
                    operation="report_generation_complete",
                    details={
                        "report_id": report_id,
                        "report_size_kb": len(json.dumps(analysis_report.to_dict(), default=str)) / 1024,
                        "quality_score": quality_metrics.get("overall_quality_score", 0),
                        "processing_time_seconds": analysis_report.processing_time_seconds
                    }
                )
            
            logger.info(f"Analysis report generated successfully: {report_id}")
            return analysis_report
            
        except Exception as e:
            error_msg = f"Report generation failed for patient {patient_data.patient_id}: {str(e)}"
            logger.error(error_msg)
            
            if self.audit_logger:
                self.audit_logger.log_error(
                    patient_id=patient_data.patient_id,
                    operation="report_generation",
                    error=e
                )
            
            raise ReportError(error_msg)
    
    def _generate_report_id(self) -> str:
        """Generate unique report ID with timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"RPT_{timestamp}_{unique_id}"
    
    def _create_executive_summary(self, 
                                patient_data: PatientData,
                                medical_summary: MedicalSummary,
                                research_analysis: ResearchAnalysis) -> str:
        """Create executive summary of the analysis."""
        # Patient demographics
        demographics = patient_data.demographics
        age_info = f"{demographics.age}-year-old" if demographics.age else "Adult"
        gender_info = demographics.gender if demographics.gender else "patient"
        
        # Key conditions summary
        conditions = medical_summary.key_conditions
        condition_count = len(conditions)
        
        if condition_count == 0:
            conditions_summary = "no significant medical conditions identified"
        elif condition_count == 1:
            conditions_summary = f"primary diagnosis of {conditions[0].name}"
        else:
            primary_conditions = [c.name for c in conditions[:3]]  # Top 3
            conditions_summary = f"multiple conditions including {', '.join(primary_conditions)}"
        
        # Research findings summary
        research_count = len(research_analysis.research_findings)
        research_summary = f"{research_count} relevant research papers" if research_count > 0 else "limited research literature"
        
        # Analysis confidence
        confidence_level = "high" if research_analysis.analysis_confidence >= 0.8 else \
                          "moderate" if research_analysis.analysis_confidence >= 0.6 else "limited"
        
        executive_summary = (
            f"Analysis of {age_info} {gender_info} reveals {conditions_summary}. "
            f"Medical record analysis identified {condition_count} documented conditions "
            f"with {confidence_level} confidence based on available clinical data. "
            f"Research correlation found {research_summary} supporting evidence-based "
            f"treatment approaches. The analysis provides comprehensive insights for "
            f"clinical decision-making and patient care optimization."
        )
        
        return executive_summary
    
    def _calculate_quality_metrics(self, 
                                 patient_data: PatientData,
                                 medical_summary: MedicalSummary,
                                 research_analysis: ResearchAnalysis) -> Dict[str, Any]:
        """Calculate quality metrics for the analysis."""
        metrics = {}
        
        # Data completeness metrics
        total_fields = 10  # Expected key fields
        completed_fields = 0
        
        if patient_data.patient_id:
            completed_fields += 1
        if patient_data.name:
            completed_fields += 1
        if patient_data.demographics.age:
            completed_fields += 1
        if patient_data.demographics.gender:
            completed_fields += 1
        if len(patient_data.medical_history) > 0:
            completed_fields += 1
        if len(patient_data.medications) > 0:
            completed_fields += 1
        if len(patient_data.procedures) > 0:
            completed_fields += 1
        if len(patient_data.diagnoses) > 0:
            completed_fields += 1
        if medical_summary.summary_text:
            completed_fields += 1
        if len(medical_summary.key_conditions) > 0:
            completed_fields += 1
        
        metrics["data_completeness_score"] = completed_fields / total_fields
        
        # Medical summary quality
        metrics["medical_summary_quality"] = {
            "conditions_identified": len(medical_summary.key_conditions),
            "data_quality_score": medical_summary.data_quality_score,
            "missing_data_indicators": len(medical_summary.missing_data_indicators),
            "summary_length": len(medical_summary.summary_text)
        }
        
        # Research analysis quality
        metrics["research_analysis_quality"] = {
            "papers_found": len(research_analysis.research_findings),
            "analysis_confidence": research_analysis.analysis_confidence,
            "conditions_with_research": len([c for c in research_analysis.condition_research_correlations.values() if c]),
            "high_quality_papers": len(research_analysis.get_high_quality_findings()),
            "recent_papers": len(research_analysis.get_recent_findings())
        }
        
        # Overall quality score
        quality_components = [
            metrics["data_completeness_score"] * 0.3,
            medical_summary.data_quality_score * 0.4,
            research_analysis.analysis_confidence * 0.3
        ]
        metrics["overall_quality_score"] = sum(quality_components)
        
        # Quality assessment
        if metrics["overall_quality_score"] >= 0.8:
            metrics["quality_assessment"] = "High quality analysis with comprehensive data"
        elif metrics["overall_quality_score"] >= 0.6:
            metrics["quality_assessment"] = "Good quality analysis with adequate data"
        elif metrics["overall_quality_score"] >= 0.4:
            metrics["quality_assessment"] = "Moderate quality analysis with some data limitations"
        else:
            metrics["quality_assessment"] = "Limited quality analysis due to insufficient data"
        
        return metrics
    
    def _compile_recommendations(self, 
                               medical_summary: MedicalSummary,
                               research_analysis: ResearchAnalysis) -> List[str]:
        """Compile recommendations from medical summary and research analysis."""
        recommendations = []
        
        # Add research-based clinical recommendations
        recommendations.extend(research_analysis.clinical_recommendations)
        
        # Add condition-specific recommendations
        high_priority_conditions = [
            c for c in medical_summary.key_conditions 
            if c.severity in ["severe", "critical"] or c.status == "chronic"
        ]
        
        if high_priority_conditions:
            recommendations.append(
                f"Priority monitoring recommended for {len(high_priority_conditions)} "
                f"high-severity conditions: {', '.join([c.name for c in high_priority_conditions[:3]])}"
            )
        
        # Add data quality recommendations
        if medical_summary.missing_data_indicators:
            recommendations.append(
                f"Consider obtaining additional clinical data for: "
                f"{', '.join(medical_summary.missing_data_indicators[:3])}"
            )
        
        # Add research gap recommendations
        conditions_without_research = [
            c.name for c in medical_summary.key_conditions
            if c.name not in research_analysis.condition_research_correlations or 
            not research_analysis.condition_research_correlations[c.name]
        ]
        
        if conditions_without_research:
            recommendations.append(
                f"Consult clinical guidelines for conditions with limited research: "
                f"{', '.join(conditions_without_research[:2])}"
            )
        
        return recommendations[:10]  # Limit to top 10 recommendations
    
    def _extract_key_findings(self, 
                            medical_summary: MedicalSummary,
                            research_analysis: ResearchAnalysis) -> List[str]:
        """Extract key findings from medical summary and research analysis."""
        key_findings = []
        
        # Medical findings
        if medical_summary.key_conditions:
            primary_condition = medical_summary.key_conditions[0]
            key_findings.append(
                f"Primary condition: {primary_condition.name} "
                f"(Confidence: {primary_condition.confidence_score:.1%})"
            )
        
        # Condition severity findings
        severe_conditions = [
            c for c in medical_summary.key_conditions 
            if c.severity in ["severe", "critical"]
        ]
        if severe_conditions:
            key_findings.append(
                f"High-severity conditions identified: {len(severe_conditions)} conditions "
                f"requiring priority attention"
            )
        
        # Research findings
        if research_analysis.research_findings:
            top_research = research_analysis.get_top_findings(limit=1)[0]
            key_findings.append(
                f"Top research evidence: {top_research.title[:100]}... "
                f"(Relevance: {top_research.relevance_score:.1%})"
            )
        
        # Research insights
        key_findings.extend(research_analysis.research_insights[:3])
        
        return key_findings[:8]  # Limit to top 8 findings
    
    def _compile_data_sources(self, research_analysis: ResearchAnalysis) -> List[str]:
        """Compile list of data sources used in the analysis."""
        sources = [
            "Patient XML medical record",
            "Medical terminology databases (ICD-10)",
            "Clinical data extraction algorithms"
        ]
        
        # Add research sources
        if research_analysis.research_findings:
            research_sources = set()
            for finding in research_analysis.research_findings:
                if finding.journal:
                    research_sources.add(finding.journal)
            
            sources.extend([f"Medical literature: {source}" for source in list(research_sources)[:5]])
        
        return sources
    
    def _create_report_metadata(self, 
                              patient_data: PatientData,
                              medical_summary: MedicalSummary,
                              research_analysis: ResearchAnalysis) -> Dict[str, Any]:
        """Create processing metadata for the report."""
        return {
            "system_info": self.system_info,
            "processing_timestamps": {
                "xml_extraction": patient_data.extraction_timestamp.isoformat(),
                "medical_summary": medical_summary.generated_timestamp.isoformat(),
                "research_analysis": research_analysis.analysis_timestamp.isoformat(),
                "report_generation": datetime.now().isoformat()
            },
            "data_statistics": {
                "xml_size_chars": len(patient_data.raw_xml),
                "conditions_extracted": len(medical_summary.key_conditions),
                "research_papers_found": len(research_analysis.research_findings),
                "total_processing_agents": 3
            },
            "quality_indicators": {
                "medical_summary_confidence": medical_summary.data_quality_score,
                "research_analysis_confidence": research_analysis.analysis_confidence,
                "data_completeness": len([f for f in [
                    patient_data.patient_id, patient_data.name,
                    patient_data.demographics.age, patient_data.demographics.gender
                ] if f]) / 4
            }
        }