"""Main entry point for the medical record analysis system."""

import logging
import asyncio
import sys
from datetime import datetime
from typing import Optional

from src.utils.logging_config import setup_logging
from src.utils.enhanced_logging import initialize_logging, log_operation
from src.utils.audit_logger import initialize_audit_logging
from src.utils.error_handler import ErrorHandler, ErrorContext
from src.utils import AuditLogger
from src.workflow import MainWorkflow, WorkflowProgress
from src.models import AgentCommunicationError, XMLParsingError, ResearchError, ReportError, S3Error
from src.cli import EnhancedCLI

# Progress callback is now handled by EnhancedCLI

async def analyze_patient(patient_name: str, cli: EnhancedCLI) -> bool:
    """
    Analyze a patient's medical records with enhanced CLI display.
    
    Args:
        patient_name: Name of patient to analyze
        cli: Enhanced CLI interface for display
        
    Returns:
        bool: True if analysis completed successfully
    """
    with log_operation("patient_analysis", "main_application", patient_name):
        # Initialize enhanced logging and audit systems
        logging_system = initialize_logging(
            log_level="INFO",
            enable_performance_monitoring=True,
            enable_structured_logging=True
        )
        
        audit_logger = initialize_audit_logging()
        error_handler = ErrorHandler(audit_logger=audit_logger)
        
        try:
            # Display analysis start
            cli.display_analysis_start(patient_name)
            
            # Initialize workflow with enhanced capabilities
            progress_callback = cli.create_progress_callback()
            workflow = MainWorkflow(
                audit_logger=audit_logger,
                progress_callback=progress_callback,
                timeout_seconds=300,
                enable_enhanced_logging=True,
                log_level="INFO"
            )
            
            # Execute complete analysis
            start_time = datetime.now()
            analysis_report = await workflow.execute_complete_analysis(patient_name)
            end_time = datetime.now()
            
            # Calculate processing time
            processing_time = (end_time - start_time).total_seconds()
            
            # Get workflow statistics
            stats = workflow.get_workflow_statistics()
            
            # Display successful results
            cli.display_success(analysis_report, processing_time, stats)
            
            return True
            
        except XMLParsingError as e:
            context = ErrorContext("patient_analysis", patient_name, "main_application")
            result = error_handler.handle_error(e, context)
            cli.display_error("XML Parsing Error", result['user_message'], result['error_id'])
            return False
            
        except ResearchError as e:
            context = ErrorContext("patient_analysis", patient_name, "main_application")
            result = error_handler.handle_error(e, context)
            cli.display_error("Research Correlation Error", result['user_message'], result['error_id'])
            cli.display_partial_success("Medical analysis completed, but research correlation failed.")
            return False
            
        except ReportError as e:
            context = ErrorContext("patient_analysis", patient_name, "main_application")
            result = error_handler.handle_error(e, context)
            cli.display_error("Report Generation Error", result['user_message'], result['error_id'])
            cli.display_partial_success("Analysis completed, but report generation failed.")
            return False
            
        except S3Error as e:
            context = ErrorContext("patient_analysis", patient_name, "main_application")
            result = error_handler.handle_error(e, context)
            cli.display_error("S3 Storage Error", result['user_message'], result['error_id'])
            cli.display_partial_success("Analysis completed, but report storage failed.")
            return False
            
        except AgentCommunicationError as e:
            context = ErrorContext("patient_analysis", patient_name, "main_application")
            result = error_handler.handle_error(e, context)
            cli.display_error("Workflow Error", result['user_message'], result['error_id'])
            return False
            
        except Exception as e:
            context = ErrorContext("patient_analysis", patient_name, "main_application")
            result = error_handler.handle_error(e, context)
            cli.display_error("Unexpected Error", result['user_message'], result['error_id'])
            return False

# Patient name input is now handled by EnhancedCLI

async def main_async():
    """Async main function with enhanced CLI interface."""
    # Initialize enhanced logging first
    logging_system = initialize_logging(
        log_level="INFO",
        enable_performance_monitoring=True,
        enable_structured_logging=True
    )
    
    # Initialize audit logging
    audit_logger = initialize_audit_logging()
    
    # Setup basic logging for backwards compatibility
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Initialize enhanced CLI
    cli = EnhancedCLI()
    
    with log_operation("system_startup", "main_application"):
        logger.info("Medical Record Analysis System starting with enhanced CLI...")
        
        # Log system startup
        audit_logger.log_system_event(
            operation="system_startup",
            component="main_application",
            additional_context={
                "version": "1.0.0",
                "enhanced_logging": True,
                "audit_logging": True,
                "enhanced_cli": True
            }
        )
        
        try:
            # Display welcome message
            cli.display_welcome()
            
            # Main application loop
            while True:
                # Get patient name from user
                patient_name = cli.get_patient_name()
                if not patient_name:
                    break
                
                # Analyze patient
                success = await analyze_patient(patient_name, cli)
                
                # Log completion
                audit_logger.log_system_event(
                    operation="analysis_completed",
                    component="main_application",
                    additional_context={"patient_name": patient_name, "success": success}
                )
                
                # Ask if user wants to continue
                if not cli.prompt_continue():
                    break
            
            # Display goodbye message
            cli.display_goodbye()
            return 0
                
        except KeyboardInterrupt:
            cli.display_goodbye()
            audit_logger.log_system_event(
                operation="user_interruption",
                component="main_application"
            )
            return 1
        except Exception as e:
            error_handler = ErrorHandler(audit_logger=audit_logger)
            context = ErrorContext("system_operation", None, "main_application")
            result = error_handler.handle_error(e, context)
            
            logger.error(f"Unexpected error in main: {str(e)}")
            cli.display_error("System Error", result['user_message'], result['error_id'])
            return 1

def main():
    """Main entry point."""
    try:
        return asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\n\nGoodbye!")
        return 1

if __name__ == "__main__":
    sys.exit(main())