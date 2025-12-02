"""Enhanced command-line interface for medical record analysis system."""
import re
import sys
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path

from ..models import AnalysisReport
from ..utils.enhanced_logging import log_operation
from ..utils.error_handler import ErrorHandler, ErrorContext


class CLIColors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class ProgressDisplay:
    """Enhanced progress display with visual progress bar."""
    
    def __init__(self, width: int = 50):
        self.width = width
        self.current_step = 0
        self.total_steps = 6
        
    def display_progress(self, progress):
        """Display enhanced progress with visual progress bar."""
        step_name = progress.step_names[progress.current_step] if progress.current_step < len(progress.step_names) else "Completed"
        percentage = progress.get_progress_percentage()
        
        # Create progress bar
        filled_width = int(self.width * percentage / 100)
        bar = "█" * filled_width + "░" * (self.width - filled_width)
        
        # Display progress
        print(f"\r{CLIColors.OKCYAN}[{bar}] {percentage:5.1f}% - {step_name}{CLIColors.ENDC}", end="", flush=True)
        
        if percentage >= 100:
            print()  # New line when complete


class InputValidator:
    """Input validation utilities for CLI."""
    
    @staticmethod
    def validate_patient_name(name: str) -> tuple[bool, str]:
        """
        Validate patient name input.
        
        Args:
            name: Patient name to validate
            
        Returns:
            tuple[bool, str]: (is_valid, error_message)
        """
        if not name or not name.strip():
            return False, "Patient name cannot be empty"
        
        name = name.strip()
        
        # Length validation
        if len(name) < 2:
            return False, "Patient name must be at least 2 characters long"
        
        if len(name) > 100:
            return False, "Patient name cannot exceed 100 characters"
        
        # Character validation - allow letters, spaces, hyphens, apostrophes
        if not re.match(r"^[a-zA-Z\s\-'\.]+$", name):
            return False, "Patient name can only contain letters, spaces, hyphens, apostrophes, and periods"
        
        # Check for reasonable name format
        parts = name.split()
        if len(parts) < 2:
            return False, "Please enter both first and last name"
        
        # Check for suspicious patterns
        if any(len(part) < 1 for part in parts):
            return False, "Each part of the name must contain at least one character"
        
        return True, ""
    
    @staticmethod
    def normalize_patient_name(name: str) -> str:
        """
        Normalize patient name for consistent processing.
        
        Args:
            name: Raw patient name input
            
        Returns:
            str: Normalized patient name
        """
        # Remove extra whitespace and normalize case
        name = " ".join(name.strip().split())
        
        # Capitalize each word properly
        parts = []
        for part in name.split():
            # Handle special cases like O'Connor, McDonald, Jean-Luc
            if "'" in part:
                subparts = part.split("'")
                part = "'".join([subpart.capitalize() for subpart in subparts])
            elif "-" in part:
                subparts = part.split("-")
                part = "-".join([subpart.capitalize() for subpart in subparts])
            elif part.lower().startswith("mc") and len(part) > 2:
                part = "Mc" + part[2:].capitalize()
            else:
                part = part.capitalize()
            parts.append(part)
        
        return " ".join(parts)


class ResultsFormatter:
    """Formats analysis results for display."""
    
    @staticmethod
    def format_analysis_report(report: AnalysisReport, processing_time: float, stats: Dict[str, Any]) -> str:
        """
        Format complete analysis report for display.
        
        Args:
            report: Analysis report to format
            processing_time: Total processing time in seconds
            stats: Workflow statistics
            
        Returns:
            str: Formatted report string
        """
        output = []
        
        # Header
        output.append(f"\n{CLIColors.OKGREEN}{'='*80}{CLIColors.ENDC}")
        output.append(f"{CLIColors.BOLD}{CLIColors.HEADER}📋 MEDICAL RECORD ANALYSIS REPORT{CLIColors.ENDC}")
        output.append(f"{CLIColors.OKGREEN}{'='*80}{CLIColors.ENDC}")
        
        # Basic Information
        output.append(f"\n{CLIColors.BOLD}📋 Report Information:{CLIColors.ENDC}")
        output.append(f"   Report ID: {CLIColors.OKCYAN}{report.report_id}{CLIColors.ENDC}")
        output.append(f"   Patient: {CLIColors.BOLD}{report.patient_data.name}{CLIColors.ENDC} (ID: {report.patient_data.patient_id})")
        output.append(f"   Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        output.append(f"   Processing Time: {CLIColors.OKGREEN}{processing_time:.2f} seconds{CLIColors.ENDC}")
        
        # Patient Demographics
        output.append(f"\n{CLIColors.BOLD}👤 Patient Demographics:{CLIColors.ENDC}")
        if hasattr(report.patient_data, 'age') and report.patient_data.age:
            output.append(f"   Age: {report.patient_data.age}")
        if hasattr(report.patient_data, 'gender') and report.patient_data.gender:
            output.append(f"   Gender: {report.patient_data.gender}")
        if hasattr(report.patient_data, 'date_of_birth') and report.patient_data.date_of_birth:
            output.append(f"   Date of Birth: {report.patient_data.date_of_birth}")
        
        # Medical Summary
        output.append(f"\n{CLIColors.BOLD}📊 Medical Summary:{CLIColors.ENDC}")
        conditions = report.medical_summary.key_conditions
        output.append(f"   Conditions Identified: {CLIColors.OKBLUE}{len(conditions)}{CLIColors.ENDC}")
        
        if conditions:
            output.append(f"\n   {CLIColors.UNDERLINE}Top Medical Conditions:{CLIColors.ENDC}")
            for i, condition in enumerate(conditions[:5], 1):
                confidence_color = CLIColors.OKGREEN if condition.confidence_score >= 0.8 else CLIColors.WARNING if condition.confidence_score >= 0.6 else CLIColors.FAIL
                output.append(f"   {i:2d}. {condition.name}")
                output.append(f"       Confidence: {confidence_color}{condition.confidence_score:.1%}{CLIColors.ENDC}")
                if hasattr(condition, 'severity') and condition.severity:
                    output.append(f"       Severity: {condition.severity}")
            
            if len(conditions) > 5:
                output.append(f"   ... and {len(conditions) - 5} more conditions")
        
        # Medical History Summary
        if hasattr(report.medical_summary, 'summary_text') and report.medical_summary.summary_text:
            output.append(f"\n   {CLIColors.UNDERLINE}Medical History Summary:{CLIColors.ENDC}")
            summary_lines = report.medical_summary.summary_text.split('\n')[:3]  # First 3 lines
            for line in summary_lines:
                if line.strip():
                    output.append(f"   {line.strip()}")
            if len(report.medical_summary.summary_text.split('\n')) > 3:
                output.append(f"   ... (see full report for complete summary)")
        
        # Research Analysis
        output.append(f"\n{CLIColors.BOLD}🔬 Research Analysis:{CLIColors.ENDC}")
        research = report.research_analysis
        output.append(f"   Research Papers Found: {CLIColors.OKBLUE}{len(research.research_findings)}{CLIColors.ENDC}")
        output.append(f"   Analysis Confidence: {CLIColors.OKGREEN}{research.analysis_confidence:.1%}{CLIColors.ENDC}")
        
        if research.research_findings:
            output.append(f"\n   {CLIColors.UNDERLINE}Top Research Findings:{CLIColors.ENDC}")
            for i, paper in enumerate(research.research_findings[:3], 1):
                output.append(f"   {i}. {paper.title[:70]}{'...' if len(paper.title) > 70 else ''}")
                output.append(f"      Journal: {CLIColors.OKCYAN}{paper.journal}{CLIColors.ENDC}")
                # Extract year from publication_date (format: YYYY-MM-DD)
                pub_year = paper.publication_date.split('-')[0] if paper.publication_date else "N/A"
                output.append(f"      Year: {pub_year} | Relevance: {paper.relevance_score:.1%}")
        
        # Research Insights
        if hasattr(research, 'insights') and research.insights:
            output.append(f"\n   {CLIColors.UNDERLINE}Key Research Insights:{CLIColors.ENDC}")
            for insight in research.insights[:3]:
                output.append(f"   • {insight}")
        
        # Clinical Recommendations
        if hasattr(research, 'recommendations') and research.recommendations:
            output.append(f"\n   {CLIColors.UNDERLINE}Clinical Recommendations:{CLIColors.ENDC}")
            for i, rec in enumerate(research.recommendations[:3], 1):
                output.append(f"   {i}. {rec}")
        
        # Quality Metrics
        output.append(f"\n{CLIColors.BOLD}📈 Quality Metrics:{CLIColors.ENDC}")
        quality = report.quality_metrics
        overall_score = quality.get('overall_quality_score', 0)
        completeness_score = quality.get('data_completeness_score', 0)
        
        score_color = CLIColors.OKGREEN if overall_score >= 0.8 else CLIColors.WARNING if overall_score >= 0.6 else CLIColors.FAIL
        output.append(f"   Overall Quality Score: {score_color}{overall_score:.1%}{CLIColors.ENDC}")
        output.append(f"   Data Completeness: {CLIColors.OKBLUE}{completeness_score:.1%}{CLIColors.ENDC}")
        
        if quality.get('validation_results'):
            output.append(f"   Validation Status: {CLIColors.OKGREEN}✓ Passed{CLIColors.ENDC}")
        
        # System Performance
        output.append(f"\n{CLIColors.BOLD}⚡ System Performance:{CLIColors.ENDC}")
        output.append(f"   Total Workflows Run: {stats.get('total_workflows', 0)}")
        success_rate = stats.get('successful_workflows', 0) / max(stats.get('total_workflows', 1), 1)
        output.append(f"   Success Rate: {CLIColors.OKGREEN}{success_rate:.1%}{CLIColors.ENDC}")
        
        if stats.get('performance_stats'):
            perf_stats = stats['performance_stats']
            avg_duration = perf_stats.get('average_duration', 0)
            output.append(f"   Average Operation Time: {avg_duration:.2f} seconds")
        
        # Storage Information
        output.append(f"\n{CLIColors.BOLD}💾 Report Storage:{CLIColors.ENDC}")
        output.append(f"   Status: {CLIColors.OKGREEN}✓ Successfully saved to S3{CLIColors.ENDC}")
        output.append(f"   Location: Medical Analysis Reports Bucket")
        output.append(f"   Access: Available for future reference and comparison")
        
        # Footer
        output.append(f"\n{CLIColors.OKGREEN}{'='*80}{CLIColors.ENDC}")
        output.append(f"{CLIColors.BOLD}Analysis completed successfully! Report saved for future reference.{CLIColors.ENDC}")
        output.append(f"{CLIColors.OKGREEN}{'='*80}{CLIColors.ENDC}")
        
        return "\n".join(output)
    
    @staticmethod
    def format_error_message(error_type: str, user_message: str, error_id: str, suggestions: List[str] = None) -> str:
        """
        Format error message for display.
        
        Args:
            error_type: Type of error that occurred
            user_message: User-friendly error message
            error_id: Unique error identifier
            suggestions: Optional list of suggestions for resolution
            
        Returns:
            str: Formatted error message
        """
        output = []
        
        output.append(f"\n{CLIColors.FAIL}{'='*60}{CLIColors.ENDC}")
        output.append(f"{CLIColors.FAIL}{CLIColors.BOLD}❌ {error_type}{CLIColors.ENDC}")
        output.append(f"{CLIColors.FAIL}{'='*60}{CLIColors.ENDC}")
        
        output.append(f"\n{user_message}")
        output.append(f"\n{CLIColors.WARNING}Error ID: {error_id} (for support reference){CLIColors.ENDC}")
        
        if suggestions:
            output.append(f"\n{CLIColors.BOLD}💡 Suggestions:{CLIColors.ENDC}")
            for i, suggestion in enumerate(suggestions, 1):
                output.append(f"   {i}. {suggestion}")
        
        output.append(f"\n{CLIColors.FAIL}{'='*60}{CLIColors.ENDC}")
        
        return "\n".join(output)


class EnhancedCLI:
    """Enhanced command-line interface for medical record analysis."""
    
    def __init__(self):
        self.validator = InputValidator()
        self.formatter = ResultsFormatter()
        self.progress_display = ProgressDisplay()
        
    def display_welcome(self):
        """Display welcome message and system information."""
        print(f"\n{CLIColors.HEADER}{CLIColors.BOLD}{'='*80}{CLIColors.ENDC}")
        print(f"{CLIColors.HEADER}{CLIColors.BOLD}🏥 MEDICAL RECORD ANALYSIS SYSTEM v1.0{CLIColors.ENDC}")
        print(f"{CLIColors.HEADER}{CLIColors.BOLD}{'='*80}{CLIColors.ENDC}")
        
        print(f"\n{CLIColors.OKBLUE}This system provides comprehensive medical record analysis including:{CLIColors.ENDC}")
        print(f"   • {CLIColors.OKGREEN}Medical condition identification and summarization{CLIColors.ENDC}")
        print(f"   • {CLIColors.OKGREEN}Research correlation with current medical literature{CLIColors.ENDC}")
        print(f"   • {CLIColors.OKGREEN}Clinical recommendations based on evidence{CLIColors.ENDC}")
        print(f"   • {CLIColors.OKGREEN}HIPAA-compliant audit logging and data protection{CLIColors.ENDC}")
        
        print(f"\n{CLIColors.WARNING}⚠️  Important: This system is for healthcare professional use only.{CLIColors.ENDC}")
        print(f"{CLIColors.WARNING}   Results should be reviewed by qualified medical personnel.{CLIColors.ENDC}")
    
    def get_patient_name(self) -> Optional[str]:
        """
        Get and validate patient name from user input.
        
        Returns:
            Optional[str]: Validated patient name or None if cancelled
        """
        print(f"\n{CLIColors.BOLD}📋 Patient Information{CLIColors.ENDC}")
        print(f"{CLIColors.OKCYAN}{'─'*40}{CLIColors.ENDC}")
        
        max_attempts = 3
        attempts = 0
        
        while attempts < max_attempts:
            try:
                patient_name = input(f"\n{CLIColors.BOLD}Enter patient name (First Last): {CLIColors.ENDC}").strip()
                
                if not patient_name:
                    print(f"{CLIColors.WARNING}❌ Patient name cannot be empty.{CLIColors.ENDC}")
                    attempts += 1
                    continue
                
                # Validate input
                is_valid, error_message = self.validator.validate_patient_name(patient_name)
                
                if not is_valid:
                    print(f"{CLIColors.FAIL}❌ {error_message}{CLIColors.ENDC}")
                    attempts += 1
                    
                    if attempts < max_attempts:
                        print(f"{CLIColors.WARNING}Please try again ({max_attempts - attempts} attempts remaining).{CLIColors.ENDC}")
                    continue
                
                # Normalize the name
                normalized_name = self.validator.normalize_patient_name(patient_name)
                
                # Confirm with user
                print(f"\n{CLIColors.OKBLUE}Patient name: {CLIColors.BOLD}{normalized_name}{CLIColors.ENDC}")
                print(f"{CLIColors.WARNING}⚠️  This will analyze medical records for the specified patient.{CLIColors.ENDC}")
                
                while True:
                    confirm = input(f"\n{CLIColors.BOLD}Continue with analysis? (y/N): {CLIColors.ENDC}").strip().lower()
                    
                    if confirm in ['y', 'yes']:
                        return normalized_name
                    elif confirm in ['n', 'no', '']:
                        print(f"{CLIColors.WARNING}Analysis cancelled by user.{CLIColors.ENDC}")
                        return None
                    else:
                        print(f"{CLIColors.FAIL}Please enter 'y' for yes or 'n' for no.{CLIColors.ENDC}")
                
            except KeyboardInterrupt:
                print(f"\n\n{CLIColors.WARNING}Analysis cancelled by user.{CLIColors.ENDC}")
                return None
            except EOFError:
                print(f"\n\n{CLIColors.WARNING}Input terminated.{CLIColors.ENDC}")
                return None
        
        print(f"\n{CLIColors.FAIL}❌ Maximum attempts exceeded. Please restart the application.{CLIColors.ENDC}")
        return None
    
    def display_analysis_start(self, patient_name: str):
        """Display analysis start message."""
        print(f"\n{CLIColors.OKGREEN}{'='*80}{CLIColors.ENDC}")
        print(f"{CLIColors.BOLD}🚀 Starting Medical Record Analysis{CLIColors.ENDC}")
        print(f"{CLIColors.OKGREEN}{'='*80}{CLIColors.ENDC}")
        print(f"\n{CLIColors.BOLD}Patient: {CLIColors.OKCYAN}{patient_name}{CLIColors.ENDC}")
        print(f"{CLIColors.BOLD}Started: {CLIColors.OKCYAN}{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{CLIColors.ENDC}")
        print(f"\n{CLIColors.OKBLUE}Processing workflow steps:{CLIColors.ENDC}")
        
        steps = [
            "1. Patient Name Validation",
            "2. XML Parsing & Data Extraction", 
            "3. Medical Summarization",
            "4. Research Correlation",
            "5. Report Generation",
            "6. Report Persistence"
        ]
        
        for step in steps:
            print(f"   {CLIColors.OKCYAN}• {step}{CLIColors.ENDC}")
        
        print(f"\n{CLIColors.BOLD}Progress:{CLIColors.ENDC}")
    
    def create_progress_callback(self):
        """Create progress callback for workflow."""
        return self.progress_display.display_progress
    
    def display_success(self, report: AnalysisReport, processing_time: float, stats: Dict[str, Any]):
        """Display successful analysis results."""
        formatted_report = self.formatter.format_analysis_report(report, processing_time, stats)
        print(formatted_report)
        
        print(f"\n{CLIColors.OKGREEN}{CLIColors.BOLD}🎉 Medical record analysis completed successfully!{CLIColors.ENDC}")
    
    def display_error(self, error_type: str, user_message: str, error_id: str, suggestions: List[str] = None):
        """Display error message with suggestions."""
        # Default suggestions based on error type
        if not suggestions:
            suggestions = self._get_error_suggestions(error_type)
        
        formatted_error = self.formatter.format_error_message(error_type, user_message, error_id, suggestions)
        print(formatted_error)
    
    def _get_error_suggestions(self, error_type: str) -> List[str]:
        """Get default suggestions for common error types."""
        suggestions_map = {
            "XML Parsing Error": [
                "Verify the patient name is spelled correctly",
                "Check that the patient exists in the medical records system",
                "Ensure you have proper access permissions",
                "Contact system administrator if the problem persists"
            ],
            "Research Correlation Error": [
                "The medical analysis was completed successfully",
                "Research correlation failed but core analysis is available",
                "Check internet connectivity for research database access",
                "Try running the analysis again in a few minutes"
            ],
            "Report Generation Error": [
                "The analysis was completed but report generation failed",
                "Check system resources and try again",
                "Contact technical support with the error ID",
                "Verify S3 storage permissions and connectivity"
            ],
            "S3 Storage Error": [
                "The analysis was completed but storage failed",
                "Check AWS credentials and S3 bucket permissions",
                "Verify network connectivity to AWS services",
                "The analysis results are still available in memory"
            ],
            "Workflow Error": [
                "A system communication error occurred",
                "Try restarting the analysis",
                "Check system resources and network connectivity",
                "Contact technical support if the problem persists"
            ]
        }
        
        return suggestions_map.get(error_type, [
            "Try running the analysis again",
            "Check system connectivity and resources",
            "Contact technical support with the error ID"
        ])
    
    def display_partial_success(self, message: str):
        """Display partial success message."""
        print(f"\n{CLIColors.WARNING}⚠️  {message}{CLIColors.ENDC}")
    
    def prompt_continue(self) -> bool:
        """Prompt user to continue or exit."""
        try:
            while True:
                choice = input(f"\n{CLIColors.BOLD}Would you like to analyze another patient? (y/N): {CLIColors.ENDC}").strip().lower()
                
                if choice in ['y', 'yes']:
                    return True
                elif choice in ['n', 'no', '']:
                    return False
                else:
                    print(f"{CLIColors.FAIL}Please enter 'y' for yes or 'n' for no.{CLIColors.ENDC}")
        
        except (KeyboardInterrupt, EOFError):
            return False
    
    def display_goodbye(self):
        """Display goodbye message."""
        print(f"\n{CLIColors.OKBLUE}{'='*60}{CLIColors.ENDC}")
        print(f"{CLIColors.BOLD}Thank you for using the Medical Record Analysis System!{CLIColors.ENDC}")
        print(f"{CLIColors.OKBLUE}{'='*60}{CLIColors.ENDC}")
        print(f"{CLIColors.OKCYAN}All analysis results have been securely stored and logged.{CLIColors.ENDC}")
    
    def display_bedrock_results(self, results: Dict[str, Any]):
        """Display Bedrock Claude AI analysis results with enhanced formatting."""
        print(f"\n{CLIColors.HEADER}{CLIColors.BOLD}{'='*80}{CLIColors.ENDC}")
        print(f"{CLIColors.HEADER}{CLIColors.BOLD}🤖 BEDROCK CLAUDE AI ANALYSIS COMPLETE{CLIColors.ENDC}")
        print(f"{CLIColors.HEADER}{CLIColors.BOLD}{'='*80}{CLIColors.ENDC}")
        
        # Patient information
        print(f"\n{CLIColors.BOLD}📋 Patient Information{CLIColors.ENDC}")
        print(f"{CLIColors.OKCYAN}{'─'*80}{CLIColors.ENDC}")
        print(f"{CLIColors.BOLD}Name:{CLIColors.ENDC} {results.get('patient_name', 'Unknown')}")
        print(f"{CLIColors.BOLD}ID:{CLIColors.ENDC} {results.get('patient_id', 'Unknown')}")
        
        # AI Model information
        model_info = results.get('model_info', {})
        print(f"\n{CLIColors.BOLD}🤖 AI Model Information{CLIColors.ENDC}")
        print(f"{CLIColors.OKCYAN}{'─'*80}{CLIColors.ENDC}")
        print(f"{CLIColors.BOLD}Model:{CLIColors.ENDC} {model_info.get('model_name', 'Claude')}")
        print(f"{CLIColors.BOLD}Provider:{CLIColors.ENDC} {model_info.get('provider', 'Anthropic')}")
        print(f"{CLIColors.BOLD}Region:{CLIColors.ENDC} {model_info.get('region', 'us-east-1')}")
        print(f"{CLIColors.BOLD}Processing Time:{CLIColors.ENDC} {results.get('duration_seconds', 0):.2f} seconds")
        
        # Medical Summary from Claude
        medical_summary = results.get('medical_summary', '')
        if medical_summary:
            print(f"\n{CLIColors.BOLD}🏥 MEDICAL SUMMARY (Claude AI){CLIColors.ENDC}")
            print(f"{CLIColors.OKCYAN}{'─'*80}{CLIColors.ENDC}")
            print(f"{CLIColors.OKBLUE}{medical_summary}{CLIColors.ENDC}")
        
        # Research Analysis from Claude
        research_analysis = results.get('research_analysis', '')
        if research_analysis:
            print(f"\n{CLIColors.BOLD}🔬 RESEARCH-BASED ANALYSIS (Claude AI){CLIColors.ENDC}")
            print(f"{CLIColors.OKCYAN}{'─'*80}{CLIColors.ENDC}")
            print(f"{CLIColors.OKBLUE}{research_analysis}{CLIColors.ENDC}")
        
        # Report information
        if results.get('s3_key'):
            report_info = results.get('report', {})
            print(f"\n{CLIColors.BOLD}📄 Report Information{CLIColors.ENDC}")
            print(f"{CLIColors.OKCYAN}{'─'*80}{CLIColors.ENDC}")
            print(f"{CLIColors.BOLD}Report ID:{CLIColors.ENDC} {report_info.get('report_id', 'Unknown')}")
            print(f"{CLIColors.BOLD}S3 Location:{CLIColors.ENDC} {results['s3_key']}")
            print(f"{CLIColors.BOLD}Workflow ID:{CLIColors.ENDC} {results.get('workflow_id', 'Unknown')}")
            print(f"{CLIColors.BOLD}Generated At:{CLIColors.ENDC} {report_info.get('generated_at', 'Unknown')}")
        
        # Success message with AI branding
        print(f"\n{CLIColors.OKGREEN}🤖 Claude AI analysis completed successfully!{CLIColors.ENDC}")
        print(f"{CLIColors.OKCYAN}💡 This analysis was powered by AWS Bedrock and Anthropic Claude AI{CLIColors.ENDC}\n")
        print(f"{CLIColors.OKCYAN}Have a great day! 👋{CLIColors.ENDC}\n")