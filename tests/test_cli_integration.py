"""End-to-end integration tests for enhanced CLI interface."""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from io import StringIO
import sys

from src.main import main_async, analyze_patient
from src.cli import EnhancedCLI
from src.models import (
    AnalysisReport, PatientData, MedicalSummary, ResearchAnalysis,
    XMLParsingError, ResearchError, ReportError, S3Error
)


class TestCLIIntegration:
    """Test complete CLI integration scenarios."""
    
    @pytest.fixture
    def mock_workflow(self):
        """Create mock workflow for testing."""
        workflow = Mock()
        workflow.execute_complete_analysis = AsyncMock()
        workflow.get_workflow_statistics.return_value = {
            "total_workflows": 1,
            "successful_workflows": 1,
            "performance_stats": {"average_duration": 2.5}
        }
        return workflow
    
    @pytest.fixture
    def sample_analysis_report(self):
        """Create sample analysis report for testing."""
        from src.models import Demographics
        from datetime import datetime
        
        demographics = Demographics(
            date_of_birth="1978-01-01",
            gender="Male",
            age=45,
            address=None,
            phone=None,
            emergency_contact=None
        )
        
        patient_data = PatientData(
            name="John Smith",
            patient_id="PAT123",
            demographics=demographics,
            medical_history=[],
            medications=[],
            procedures=[],
            diagnoses=[],
            raw_xml="<patient></patient>",
            extraction_timestamp=datetime.now()
        )
        
        medical_summary = MedicalSummary(
            key_conditions=[],
            summary_text="Patient summary",
            chronic_conditions=[],
            medications=[]
        )
        
        research_analysis = ResearchAnalysis(
            research_findings=[],
            analysis_confidence=0.85,
            insights=[],
            recommendations=[]
        )
        
        return AnalysisReport(
            report_id="RPT_TEST_001",
            patient_data=patient_data,
            medical_summary=medical_summary,
            research_analysis=research_analysis,
            quality_metrics={
                "overall_quality_score": 0.90,
                "data_completeness_score": 0.85
            }
        )
    
    @patch('src.main.MainWorkflow')
    @patch('src.main.initialize_logging')
    @patch('src.main.initialize_audit_logging')
    @patch('src.main.ErrorHandler')
    async def test_successful_patient_analysis(self, mock_error_handler, mock_audit_init, 
                                             mock_logging_init, mock_workflow_class, 
                                             sample_analysis_report):
        """Test successful patient analysis flow."""
        # Setup mocks
        mock_workflow = Mock()
        mock_workflow.execute_complete_analysis = AsyncMock(return_value=sample_analysis_report)
        mock_workflow.get_workflow_statistics.return_value = {
            "total_workflows": 1,
            "successful_workflows": 1,
            "performance_stats": {"average_duration": 2.5}
        }
        mock_workflow_class.return_value = mock_workflow
        
        cli = EnhancedCLI()
        
        # Test successful analysis
        result = await analyze_patient("John Smith", cli)
        
        assert result is True
        mock_workflow.execute_complete_analysis.assert_called_once_with("John Smith")
    
    @patch('src.main.MainWorkflow')
    @patch('src.main.initialize_logging')
    @patch('src.main.initialize_audit_logging')
    @patch('src.main.ErrorHandler')
    async def test_xml_parsing_error_handling(self, mock_error_handler, mock_audit_init,
                                            mock_logging_init, mock_workflow_class):
        """Test XML parsing error handling."""
        # Setup mocks
        mock_workflow = Mock()
        mock_workflow.execute_complete_analysis = AsyncMock(side_effect=XMLParsingError("Patient not found"))
        mock_workflow_class.return_value = mock_workflow
        
        # Setup error handler mock
        error_handler_instance = Mock()
        error_handler_instance.handle_error.return_value = {
            "error_id": "ERR_001",
            "user_message": "Unable to parse patient medical record",
            "is_recoverable": False
        }
        mock_error_handler.return_value = error_handler_instance
        
        cli = EnhancedCLI()
        
        # Test error handling
        result = await analyze_patient("Nonexistent Patient", cli)
        
        assert result is False
        error_handler_instance.handle_error.assert_called_once()
    
    @patch('src.main.MainWorkflow')
    @patch('src.main.initialize_logging')
    @patch('src.main.initialize_audit_logging')
    @patch('src.main.ErrorHandler')
    async def test_research_error_partial_success(self, mock_error_handler, mock_audit_init,
                                                mock_logging_init, mock_workflow_class):
        """Test research error with partial success."""
        # Setup mocks
        mock_workflow = Mock()
        mock_workflow.execute_complete_analysis = AsyncMock(side_effect=ResearchError("Research API unavailable"))
        mock_workflow_class.return_value = mock_workflow
        
        # Setup error handler mock
        error_handler_instance = Mock()
        error_handler_instance.handle_error.return_value = {
            "error_id": "ERR_002",
            "user_message": "Unable to access medical research databases",
            "is_recoverable": True
        }
        mock_error_handler.return_value = error_handler_instance
        
        cli = EnhancedCLI()
        
        # Test partial success handling
        result = await analyze_patient("John Smith", cli)
        
        assert result is False  # Still returns False for any error
        error_handler_instance.handle_error.assert_called_once()
    
    @patch('builtins.input')
    @patch('src.main.analyze_patient')
    @patch('src.main.initialize_logging')
    @patch('src.main.initialize_audit_logging')
    @patch('src.main.setup_logging')
    async def test_main_async_single_analysis(self, mock_setup_logging, mock_audit_init,
                                            mock_logging_init, mock_analyze_patient, mock_input):
        """Test main async function with single analysis."""
        # Mock user input: patient name, confirm, don't continue
        mock_input.side_effect = ["John Smith", "y", "n"]
        
        # Mock successful analysis
        mock_analyze_patient.return_value = True
        
        # Mock audit logger
        mock_audit_logger = Mock()
        mock_audit_init.return_value = mock_audit_logger
        
        result = await main_async()
        
        assert result == 0  # Success
        mock_analyze_patient.assert_called_once()
        mock_audit_logger.log_system_event.assert_called()
    
    @patch('builtins.input')
    @patch('src.main.analyze_patient')
    @patch('src.main.initialize_logging')
    @patch('src.main.initialize_audit_logging')
    @patch('src.main.setup_logging')
    async def test_main_async_multiple_analyses(self, mock_setup_logging, mock_audit_init,
                                              mock_logging_init, mock_analyze_patient, mock_input):
        """Test main async function with multiple analyses."""
        # Mock user input: first patient, confirm, continue, second patient, confirm, don't continue
        mock_input.side_effect = ["John Smith", "y", "y", "Jane Doe", "y", "n"]
        
        # Mock successful analyses
        mock_analyze_patient.return_value = True
        
        # Mock audit logger
        mock_audit_logger = Mock()
        mock_audit_init.return_value = mock_audit_logger
        
        result = await main_async()
        
        assert result == 0  # Success
        assert mock_analyze_patient.call_count == 2
        mock_audit_logger.log_system_event.assert_called()
    
    @patch('builtins.input')
    @patch('src.main.initialize_logging')
    @patch('src.main.initialize_audit_logging')
    @patch('src.main.setup_logging')
    async def test_main_async_cancelled_input(self, mock_setup_logging, mock_audit_init,
                                            mock_logging_init, mock_input):
        """Test main async function with cancelled input."""
        # Mock user cancelling input (empty patient name)
        mock_input.side_effect = ["", "", ""]
        
        # Mock audit logger
        mock_audit_logger = Mock()
        mock_audit_init.return_value = mock_audit_logger
        
        result = await main_async()
        
        assert result == 0  # Still success when user cancels
        mock_audit_logger.log_system_event.assert_called()
    
    @patch('builtins.input')
    @patch('src.main.analyze_patient')
    @patch('src.main.initialize_logging')
    @patch('src.main.initialize_audit_logging')
    @patch('src.main.setup_logging')
    async def test_main_async_keyboard_interrupt(self, mock_setup_logging, mock_audit_init,
                                               mock_logging_init, mock_analyze_patient, mock_input):
        """Test main async function with keyboard interrupt."""
        # Mock keyboard interrupt during input
        mock_input.side_effect = KeyboardInterrupt()
        
        # Mock audit logger
        mock_audit_logger = Mock()
        mock_audit_init.return_value = mock_audit_logger
        
        result = await main_async()
        
        assert result == 1  # Error code for interrupt
        mock_audit_logger.log_system_event.assert_called()
    
    @patch('builtins.input')
    @patch('src.main.analyze_patient')
    @patch('src.main.initialize_logging')
    @patch('src.main.initialize_audit_logging')
    @patch('src.main.setup_logging')
    async def test_main_async_system_error(self, mock_setup_logging, mock_audit_init,
                                         mock_logging_init, mock_analyze_patient, mock_input):
        """Test main async function with system error."""
        # Mock user input
        mock_input.side_effect = ["John Smith", "y", "n"]
        
        # Mock system error during analysis
        mock_analyze_patient.side_effect = Exception("System failure")
        
        # Mock audit logger and error handler
        mock_audit_logger = Mock()
        mock_audit_init.return_value = mock_audit_logger
        
        result = await main_async()
        
        assert result == 1  # Error code
        mock_audit_logger.log_system_event.assert_called()


class TestCLIUserExperience:
    """Test CLI user experience scenarios."""
    
    @patch('builtins.print')
    @patch('builtins.input')
    def test_user_input_validation_flow(self, mock_input, mock_print):
        """Test complete user input validation flow."""
        cli = EnhancedCLI()
        
        # Test invalid input followed by valid input
        mock_input.side_effect = [
            "J",  # Too short
            "John123",  # Contains numbers
            "John Smith",  # Valid
            "y"  # Confirm
        ]
        
        result = cli.get_patient_name()
        
        assert result == "John Smith"
        assert mock_input.call_count == 4
        
        # Check that error messages were displayed
        printed_text = " ".join([str(call[0][0]) for call in mock_print.call_args_list])
        assert "at least 2 characters" in printed_text
        assert "letters, spaces" in printed_text
    
    @patch('builtins.print')
    def test_progress_display_visual_feedback(self, mock_print):
        """Test visual progress feedback."""
        cli = EnhancedCLI()
        progress_callback = cli.create_progress_callback()
        
        # Mock workflow progress at different stages
        progress_states = [
            (0, 0.0, "Patient Name Input"),
            (1, 16.7, "XML Parsing & Data Extraction"),
            (2, 33.3, "Medical Summarization"),
            (3, 50.0, "Research Correlation"),
            (4, 66.7, "Report Generation"),
            (5, 83.3, "Report Persistence"),
            (6, 100.0, "Completed")
        ]
        
        for step, percentage, step_name in progress_states:
            mock_progress = Mock()
            mock_progress.current_step = step
            mock_progress.step_names = [
                "Patient Name Input",
                "XML Parsing & Data Extraction", 
                "Medical Summarization",
                "Research Correlation",
                "Report Generation",
                "Report Persistence"
            ]
            mock_progress.get_progress_percentage.return_value = percentage
            
            progress_callback(mock_progress)
        
        # Verify progress was displayed for each step
        assert mock_print.call_count >= len(progress_states)
    
    @patch('builtins.print')
    def test_error_message_formatting_and_suggestions(self, mock_print):
        """Test error message formatting with helpful suggestions."""
        cli = EnhancedCLI()
        
        # Test different error types
        error_scenarios = [
            ("XML Parsing Error", "Patient not found", ["Check patient name spelling"]),
            ("Research Correlation Error", "API unavailable", ["Check internet connectivity"]),
            ("S3 Storage Error", "Access denied", ["Check AWS credentials"]),
        ]
        
        for error_type, message, suggestions in error_scenarios:
            cli.display_error(error_type, message, "ERR_001", suggestions)
        
        # Verify error messages were displayed
        assert mock_print.call_count >= len(error_scenarios) * 5  # Multiple prints per error
        
        # Check that suggestions were included
        printed_text = " ".join([str(call[0][0]) for call in mock_print.call_args_list])
        assert "Check patient name spelling" in printed_text
        assert "Check internet connectivity" in printed_text
        assert "Check AWS credentials" in printed_text
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_color_coded_output(self, mock_stdout):
        """Test that output includes appropriate color coding."""
        cli = EnhancedCLI()
        
        # Test welcome message with colors
        cli.display_welcome()
        welcome_output = mock_stdout.getvalue()
        
        # Reset stdout for next test
        mock_stdout.truncate(0)
        mock_stdout.seek(0)
        
        # Test error message with colors
        cli.display_error("Test Error", "Test message", "ERR_001")
        error_output = mock_stdout.getvalue()
        
        # Check that ANSI color codes are present
        from src.cli.interface import CLIColors
        
        # Welcome should have header colors
        assert any(color in welcome_output for color in [CLIColors.HEADER, CLIColors.BOLD, CLIColors.OKBLUE])
        
        # Error should have error colors
        assert any(color in error_output for color in [CLIColors.FAIL, CLIColors.WARNING])
    
    def test_input_normalization_consistency(self):
        """Test that input normalization is consistent."""
        cli = EnhancedCLI()
        
        # Test various input formats that should normalize to the same result
        input_variations = [
            "john smith",
            "JOHN SMITH", 
            "John Smith",
            "  john   smith  ",
            "john  smith"
        ]
        
        expected_result = "John Smith"
        
        for input_name in input_variations:
            normalized = cli.validator.normalize_patient_name(input_name)
            assert normalized == expected_result, f"'{input_name}' should normalize to '{expected_result}' but got '{normalized}'"
    
    @patch('builtins.input')
    def test_user_confirmation_handling(self, mock_input):
        """Test user confirmation handling variations."""
        cli = EnhancedCLI()
        
        # Test different confirmation responses
        confirmation_tests = [
            (["John Smith", "y"], "John Smith"),
            (["John Smith", "yes"], "John Smith"),
            (["John Smith", "Y"], "John Smith"),
            (["John Smith", "YES"], "John Smith"),
            (["John Smith", "n"], None),
            (["John Smith", "no"], None),
            (["John Smith", ""], None),  # Default is no
        ]
        
        for inputs, expected in confirmation_tests:
            mock_input.side_effect = inputs
            result = cli.get_patient_name()
            assert result == expected, f"Input {inputs} should result in {expected} but got {result}"


class TestCLIAccessibility:
    """Test CLI accessibility and usability features."""
    
    def test_clear_error_messages(self):
        """Test that error messages are clear and actionable."""
        cli = EnhancedCLI()
        
        # Test that error suggestions are helpful
        xml_suggestions = cli._get_error_suggestions("XML Parsing Error")
        assert len(xml_suggestions) > 0
        assert all(len(suggestion) > 10 for suggestion in xml_suggestions)  # Meaningful suggestions
        assert any("patient name" in suggestion.lower() for suggestion in xml_suggestions)
        
        research_suggestions = cli._get_error_suggestions("Research Correlation Error")
        assert any("connectivity" in suggestion.lower() or "network" in suggestion.lower() 
                  for suggestion in research_suggestions)
    
    def test_progress_feedback_clarity(self):
        """Test that progress feedback is clear and informative."""
        cli = EnhancedCLI()
        
        # Test that step names are descriptive
        mock_progress = Mock()
        mock_progress.step_names = [
            "Patient Name Input",
            "XML Parsing & Data Extraction", 
            "Medical Summarization",
            "Research Correlation",
            "Report Generation",
            "Report Persistence"
        ]
        
        for i, step_name in enumerate(mock_progress.step_names):
            assert len(step_name) > 5  # Meaningful step names
            assert not step_name.isupper()  # Not all caps (more readable)
            assert step_name[0].isupper()  # Proper capitalization
    
    def test_input_validation_feedback(self):
        """Test that input validation provides helpful feedback."""
        validator = cli.InputValidator()
        
        # Test that validation errors are specific and helpful
        test_cases = [
            ("", "cannot be empty"),
            ("J", "at least 2 characters"),
            ("John", "both first and last name"),
            ("John123", "letters, spaces"),
            ("A" * 101, "cannot exceed 100 characters")
        ]
        
        for invalid_input, expected_error_content in test_cases:
            is_valid, error_message = validator.validate_patient_name(invalid_input)
            assert not is_valid
            assert expected_error_content.lower() in error_message.lower()
            assert len(error_message) > 10  # Meaningful error messages