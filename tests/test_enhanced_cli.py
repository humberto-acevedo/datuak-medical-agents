"""Tests for enhanced command-line interface."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from io import StringIO
import sys

from src.cli.interface import (
    EnhancedCLI, CLIColors, ProgressDisplay, InputValidator, 
    ResultsFormatter
)
from src.models import (
    AnalysisReport, PatientData, MedicalSummary, ResearchAnalysis
)


class TestInputValidator:
    """Test InputValidator class."""
    
    def test_validate_patient_name_valid(self):
        """Test validation of valid patient names."""
        validator = InputValidator()
        
        valid_names = [
            "John Smith",
            "Mary Jane Watson",
            "O'Connor Patrick",
            "Jean-Luc Picard",
            "Dr. Sarah Johnson",
            "Maria Elena Rodriguez-Garcia"
        ]
        
        for name in valid_names:
            is_valid, error_msg = validator.validate_patient_name(name)
            assert is_valid, f"'{name}' should be valid but got error: {error_msg}"
    
    def test_validate_patient_name_invalid(self):
        """Test validation of invalid patient names."""
        validator = InputValidator()
        
        invalid_names = [
            "",  # Empty
            "   ",  # Whitespace only
            "J",  # Too short
            "John",  # Single name
            "John123",  # Contains numbers
            "John@Smith",  # Contains special characters
            "A" * 101,  # Too long
        ]
        
        for name in invalid_names:
            is_valid, error_msg = validator.validate_patient_name(name)
            assert not is_valid, f"'{name}' should be invalid but was accepted"
            assert error_msg, "Error message should be provided for invalid names"
    
    def test_normalize_patient_name(self):
        """Test patient name normalization."""
        validator = InputValidator()
        
        test_cases = [
            ("john smith", "John Smith"),
            ("MARY JANE", "Mary Jane"),
            ("o'connor patrick", "O'Connor Patrick"),
            ("mcdonald ronald", "McDonald Ronald"),
            ("jean-luc  picard", "Jean-Luc Picard"),
            ("  sarah   johnson  ", "Sarah Johnson")
        ]
        
        for input_name, expected in test_cases:
            result = validator.normalize_patient_name(input_name)
            assert result == expected, f"Expected '{expected}' but got '{result}'"


class TestProgressDisplay:
    """Test ProgressDisplay class."""
    
    def test_progress_display_initialization(self):
        """Test progress display initialization."""
        display = ProgressDisplay(width=40)
        assert display.width == 40
        assert display.current_step == 0
        assert display.total_steps == 6
    
    @patch('builtins.print')
    def test_display_progress(self, mock_print):
        """Test progress display output."""
        display = ProgressDisplay(width=20)
        
        # Mock workflow progress
        progress = Mock()
        progress.step_names = ["Step 1", "Step 2", "Step 3"]
        progress.current_step = 1
        progress.get_progress_percentage.return_value = 50.0
        
        display.display_progress(progress)
        
        # Verify print was called with progress bar
        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]
        assert "50.0%" in call_args
        assert "Step 2" in call_args
        assert "█" in call_args  # Progress bar filled portion
        assert "░" in call_args  # Progress bar empty portion


class TestResultsFormatter:
    """Test ResultsFormatter class."""
    
    @pytest.fixture
    def sample_report(self):
        """Create sample analysis report for testing."""
        # Create sample medical conditions (using dict format)
        conditions = [
            {
                "name": "Hypertension",
                "confidence_score": 0.95,
                "severity": "moderate",
                "icd_code": "I10"
            },
            {
                "name": "Type 2 Diabetes",
                "confidence_score": 0.88,
                "severity": "mild",
                "icd_code": "E11"
            }
        ]
        
        # Create sample research findings (using dict format)
        research_findings = [
            {
                "title": "Hypertension Management in Primary Care",
                "authors": ["Smith, J.", "Johnson, M."],
                "journal": "Journal of Medicine",
                "publication_year": 2023,
                "relevance_score": 0.92,
                "study_type": "systematic_review"
            }
        ]
        
        # Create sample patient data
        from src.models import Demographics
        from datetime import datetime
        
        demographics = Demographics(
            date_of_birth="1978-05-15",
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
        
        # Create sample medical summary
        from src.models.medical_summary import Condition
        
        medical_summary = MedicalSummary(
            patient_id="PAT123",
            key_conditions=[
                Condition(name="Hypertension", confidence_score=0.95, status="chronic"),
                Condition(name="Type 2 Diabetes", confidence_score=0.90, status="chronic")
            ],
            summary_text="Patient presents with hypertension and type 2 diabetes.",
            medication_summary="Patient takes Lisinopril and Metformin",
            procedure_summary="No recent procedures",
            chronological_events=[],
            generated_timestamp=datetime.now(),
            data_quality_score=0.9,
            missing_data_indicators=[]
        )
        
        # Create sample research analysis
        from src.models.research_analysis import ResearchFinding
        
        research_analysis = ResearchAnalysis(
            patient_id="PAT123",
            analysis_timestamp=datetime.now(),
            conditions_analyzed=[
                Condition(name="Hypertension", confidence_score=0.95, status="chronic"),
                Condition(name="Type 2 Diabetes", confidence_score=0.90, status="chronic")
            ],
            research_findings=[
                ResearchFinding(
                    title="Hypertension Management in Primary Care",
                    authors=["Smith, J.", "Johnson, M."],
                    journal="Journal of Medicine",
                    publication_date="2023-01-15",
                    relevance_score=0.92,
                    study_type="systematic_review",
                    key_findings="ACE inhibitors effective",
                    citation="Smith et al. (2023)"
                )
            ],
            condition_research_correlations={},
            categorized_findings={},
            research_insights=["Strong evidence for ACE inhibitor therapy"],
            clinical_recommendations=["Consider lifestyle modifications", "Monitor blood pressure regularly"],
            analysis_confidence=0.85,
            total_papers_reviewed=30,
            relevant_papers_found=1
        )
        
        # Create analysis report
        report = AnalysisReport(
            patient_data=patient_data,
            medical_summary=medical_summary,
            research_analysis=research_analysis,
            generated_timestamp=datetime.now(),
            report_id="RPT_20241110_001",
            processing_time_seconds=2.5,
            agent_versions={"xml_parser": "1.0", "summarizer": "1.0", "research": "1.0"},
            quality_metrics={
                "overall_quality_score": 0.90,
                "data_completeness_score": 0.85,
                "validation_results": True
            }
        )
        
        return report
    
    def test_format_analysis_report(self, sample_report):
        """Test analysis report formatting."""
        formatter = ResultsFormatter()
        stats = {
            "total_workflows": 5,
            "successful_workflows": 4,
            "performance_stats": {
                "average_duration": 2.5
            }
        }
        
        formatted_report = formatter.format_analysis_report(sample_report, 3.2, stats)
        
        # Check that key information is included
        assert "John Smith" in formatted_report
        assert "RPT_20241110_001" in formatted_report
        assert "Hypertension" in formatted_report
        assert "Type 2 Diabetes" in formatted_report
        assert "3.20 seconds" in formatted_report or "3.2 seconds" in formatted_report
        assert "90.0%" in formatted_report  # Quality score
        assert "85.0%" in formatted_report  # Data completeness
        assert "Successfully saved to S3" in formatted_report
    
    def test_format_error_message(self):
        """Test error message formatting."""
        formatter = ResultsFormatter()
        
        error_message = formatter.format_error_message(
            "XML Parsing Error",
            "Unable to parse patient medical record",
            "ERR_20241110_001",
            ["Check patient name spelling", "Verify system access"]
        )
        
        assert "XML Parsing Error" in error_message
        assert "Unable to parse patient medical record" in error_message
        assert "ERR_20241110_001" in error_message
        assert "Check patient name spelling" in error_message
        assert "Verify system access" in error_message


class TestEnhancedCLI:
    """Test EnhancedCLI class."""
    
    @pytest.fixture
    def cli(self):
        """Create EnhancedCLI instance for testing."""
        return EnhancedCLI()
    
    @patch('builtins.print')
    def test_display_welcome(self, mock_print, cli):
        """Test welcome message display."""
        cli.display_welcome()
        
        # Verify multiple print calls were made
        assert mock_print.call_count > 5
        
        # Check that key information is displayed
        printed_text = " ".join([str(call[0][0]) for call in mock_print.call_args_list])
        assert "MEDICAL RECORD ANALYSIS SYSTEM" in printed_text
        assert "Medical condition identification" in printed_text
        assert "HIPAA-compliant" in printed_text
    
    @patch('builtins.input')
    def test_get_patient_name_valid(self, mock_input, cli):
        """Test valid patient name input."""
        # Mock user input sequence
        mock_input.side_effect = ["John Smith", "y"]
        
        result = cli.get_patient_name()
        
        assert result == "John Smith"
    
    @patch('builtins.input')
    def test_get_patient_name_cancelled(self, mock_input, cli):
        """Test cancelled patient name input."""
        # Mock user input sequence
        mock_input.side_effect = ["John Smith", "n"]
        
        result = cli.get_patient_name()
        
        assert result is None
    
    @patch('builtins.input')
    @patch('builtins.print')
    def test_get_patient_name_invalid_then_valid(self, mock_print, mock_input, cli):
        """Test invalid input followed by valid input."""
        # Mock user input sequence: invalid, then valid, then confirm
        mock_input.side_effect = ["J", "John Smith", "y"]
        
        result = cli.get_patient_name()
        
        assert result == "John Smith"
        
        # Check that error message was displayed
        printed_text = " ".join([str(call[0][0]) for call in mock_print.call_args_list])
        assert "must be at least 2 characters" in printed_text
    
    @patch('builtins.input')
    def test_get_patient_name_max_attempts(self, mock_input, cli):
        """Test maximum attempts exceeded."""
        # Mock user input sequence: 3 invalid attempts
        mock_input.side_effect = ["J", "K", "L"]
        
        result = cli.get_patient_name()
        
        assert result is None
    
    @patch('builtins.print')
    def test_display_analysis_start(self, mock_print, cli):
        """Test analysis start display."""
        cli.display_analysis_start("John Smith")
        
        # Verify print was called multiple times
        assert mock_print.call_count > 5
        
        # Check that key information is displayed
        printed_text = " ".join([str(call[0][0]) for call in mock_print.call_args_list])
        assert "John Smith" in printed_text
        assert "Starting Medical Record Analysis" in printed_text
        assert "XML Parsing" in printed_text
        assert "Research Correlation" in printed_text
    
    def test_create_progress_callback(self, cli):
        """Test progress callback creation."""
        callback = cli.create_progress_callback()
        
        assert callable(callback)
        assert callback == cli.progress_display.display_progress
    
    @patch('builtins.print')
    def test_display_success(self, mock_print, cli):
        """Test success display."""
        # Create minimal report for testing
        from src.models import Demographics
        from datetime import datetime
        
        demographics = Demographics(
            age=45,
            gender="Male",
            date_of_birth="1978-01-01"
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
            patient_id="PAT123",
            key_conditions=[],
            summary_text="Test summary",
            medication_summary="No medications",
            procedure_summary="No procedures",
            chronological_events=[],
            generated_timestamp=datetime.now(),
            data_quality_score=0.9,
            missing_data_indicators=[]
        )
        research_analysis = ResearchAnalysis(
            patient_id="PAT123",
            analysis_timestamp=datetime.now(),
            conditions_analyzed=[],
            research_findings=[],
            condition_research_correlations={},
            categorized_findings={},
            research_insights=[],
            clinical_recommendations=[],
            analysis_confidence=0.8,
            total_papers_reviewed=10,
            relevant_papers_found=0
        )
        
        report = AnalysisReport(
            patient_data=patient_data,
            medical_summary=medical_summary,
            research_analysis=research_analysis,
            generated_timestamp=datetime.now(),
            report_id="RPT_001",
            processing_time_seconds=1.5,
            agent_versions={"xml_parser": "1.0", "summarizer": "1.0", "research": "1.0"},
            quality_metrics={"overall_quality_score": 0.9}
        )
        
        stats = {"total_workflows": 1, "successful_workflows": 1}
        
        cli.display_success(report, 2.5, stats)
        
        # Verify success message was displayed
        assert mock_print.call_count >= 1
        printed_text = " ".join([str(call[0][0]) for call in mock_print.call_args_list])
        assert "completed successfully" in printed_text or "Analysis Complete" in printed_text
    
    @patch('builtins.print')
    def test_display_error(self, mock_print, cli):
        """Test error display."""
        cli.display_error(
            "XML Parsing Error",
            "Unable to parse patient record",
            "ERR_001",
            ["Check patient name", "Verify access"]
        )
        
        # Verify error message was displayed
        assert mock_print.call_count >= 1
        printed_text = " ".join([str(call[0][0]) for call in mock_print.call_args_list])
        assert "XML Parsing Error" in printed_text
        assert "Unable to parse patient record" in printed_text
        assert "ERR_001" in printed_text
        assert "Check patient name" in printed_text
    
    @patch('builtins.input')
    def test_prompt_continue_yes(self, mock_input, cli):
        """Test continue prompt with yes response."""
        mock_input.return_value = "y"
        
        result = cli.prompt_continue()
        
        assert result is True
    
    @patch('builtins.input')
    def test_prompt_continue_no(self, mock_input, cli):
        """Test continue prompt with no response."""
        mock_input.return_value = "n"
        
        result = cli.prompt_continue()
        
        assert result is False
    
    @patch('builtins.input')
    def test_prompt_continue_default(self, mock_input, cli):
        """Test continue prompt with default (empty) response."""
        mock_input.return_value = ""
        
        result = cli.prompt_continue()
        
        assert result is False
    
    @patch('builtins.print')
    def test_display_goodbye(self, mock_print, cli):
        """Test goodbye message display."""
        cli.display_goodbye()
        
        # Verify goodbye message was displayed
        assert mock_print.call_count > 3
        printed_text = " ".join([str(call[0][0]) for call in mock_print.call_args_list])
        assert "Thank you" in printed_text
        assert "securely stored" in printed_text
    
    @patch('builtins.print')
    def test_display_partial_success(self, mock_print, cli):
        """Test partial success message display."""
        cli.display_partial_success("Analysis completed with warnings")
        
        mock_print.assert_called_once()
        printed_text = str(mock_print.call_args[0][0])
        assert "Analysis completed with warnings" in printed_text


class TestCLIIntegration:
    """Test CLI integration scenarios."""
    
    @pytest.fixture
    def cli(self):
        """Create EnhancedCLI instance for testing."""
        return EnhancedCLI()
    
    @patch('builtins.input')
    @patch('builtins.print')
    def test_complete_user_interaction_flow(self, mock_print, mock_input, cli):
        """Test complete user interaction flow."""
        # Mock user input sequence: name input, confirm, continue prompt
        mock_input.side_effect = ["John Smith", "y", "n"]
        
        # Test patient name input
        patient_name = cli.get_patient_name()
        assert patient_name == "John Smith"
        
        # Test analysis start display
        cli.display_analysis_start(patient_name)
        
        # Test continue prompt
        continue_analysis = cli.prompt_continue()
        assert continue_analysis is False
        
        # Test goodbye display
        cli.display_goodbye()
        
        # Verify multiple interactions occurred
        assert mock_print.call_count > 15
        assert mock_input.call_count == 3
    
    def test_error_suggestions_mapping(self, cli):
        """Test error suggestions mapping."""
        # Test that different error types get appropriate suggestions
        xml_suggestions = cli._get_error_suggestions("XML Parsing Error")
        assert any("patient name" in suggestion.lower() for suggestion in xml_suggestions)
        
        research_suggestions = cli._get_error_suggestions("Research Correlation Error")
        assert any("connectivity" in suggestion.lower() for suggestion in research_suggestions)
        
        unknown_suggestions = cli._get_error_suggestions("Unknown Error")
        assert any("try running" in suggestion.lower() for suggestion in unknown_suggestions)
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_color_output_formatting(self, mock_stdout, cli):
        """Test that color codes are properly included in output."""
        cli.display_welcome()
        output = mock_stdout.getvalue()
        
        # Check that ANSI color codes are present
        assert CLIColors.HEADER in output or CLIColors.BOLD in output
    
    def test_input_validation_edge_cases(self, cli):
        """Test input validation edge cases."""
        validator = cli.validator
        
        # Test edge cases
        edge_cases = [
            ("A B", True),  # Minimal valid name
            ("A" * 49 + " " + "B" * 50, True),  # Maximum length valid name (100 chars)
            ("O'Connor McDonald-Smith", True),  # Complex valid name
            ("Dr. John Smith Jr.", True),  # Name with title and suffix
        ]
        
        for name, should_be_valid in edge_cases:
            is_valid, _ = validator.validate_patient_name(name)
            assert is_valid == should_be_valid, f"'{name}' validation failed"