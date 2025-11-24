"""Tests for enhanced logging system."""
import pytest
import logging
import json
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.utils.enhanced_logging import (
    EnhancedLoggingSystem, PerformanceMonitor, StructuredFormatter,
    PerformanceMetric, initialize_logging, get_logging_system,
    get_performance_monitor, log_operation
)

class TestPerformanceMetric:
    """Test PerformanceMetric class."""
    
    def test_performance_metric_creation(self):
        """Test performance metric creation."""
        start_time = time.time()
        end_time = start_time + 1.5
        
        metric = PerformanceMetric(
            operation="test_operation",
            component="test_component",
            start_time=start_time,
            end_time=end_time,
            duration_seconds=1.5,
            success=True,
            patient_id="PATIENT123",
            additional_data={"key": "value"}
        )
        
        assert metric.operation == "test_operation"
        assert metric.component == "test_component"
        assert metric.duration_seconds == 1.5
        assert metric.success is True
        assert metric.patient_id == "PATIENT123"
    
    def test_performance_metric_to_dict(self):
        """Test performance metric dictionary conversion."""
        metric = PerformanceMetric(
            operation="test_operation",
            component="test_component",
            start_time=time.time(),
            end_time=time.time() + 1,
            duration_seconds=1.0,
            success=True
        )
        
        metric_dict = metric.to_dict()
        
        assert metric_dict["operation"] == "test_operation"
        assert metric_dict["component"] == "test_component"
        assert metric_dict["duration_seconds"] == 1.0
        assert metric_dict["success"] is True

class TestStructuredFormatter:
    """Test StructuredFormatter class."""
    
    def test_basic_formatting(self):
        """Test basic log record formatting."""
        formatter = StructuredFormatter()
        
        # Create log record
        logger = logging.getLogger("test")
        record = logger.makeRecord(
            name="test.logger",
            level=logging.INFO,
            fn="test.py",
            lno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        log_data = json.loads(formatted)
        
        assert log_data["level"] == "INFO"
        assert log_data["logger"] == "test.logger"
        assert log_data["message"] == "Test message"
        assert log_data["line"] == 10
        assert "timestamp" in log_data
    
    def test_formatting_with_extra_fields(self):
        """Test formatting with extra fields."""
        formatter = StructuredFormatter()
        
        logger = logging.getLogger("test")
        record = logger.makeRecord(
            name="test.logger",
            level=logging.INFO,
            fn="test.py",
            lno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        # Add extra fields
        record.patient_id = "PATIENT123"
        record.operation = "test_operation"
        record.component = "test_component"
        
        formatted = formatter.format(record)
        log_data = json.loads(formatted)
        
        assert log_data["patient_id"] == "PATIENT123"
        assert log_data["operation"] == "test_operation"
        assert log_data["component"] == "test_component"
    
    def test_formatting_with_exception(self):
        """Test formatting with exception information."""
        formatter = StructuredFormatter()
        
        try:
            raise ValueError("Test exception")
        except ValueError:
            logger = logging.getLogger("test")
            record = logger.makeRecord(
                name="test.logger",
                level=logging.ERROR,
                fn="test.py",
                lno=10,
                msg="Error occurred",
                args=(),
                exc_info=True
            )
            
            formatted = formatter.format(record)
            log_data = json.loads(formatted)
            
            assert "exception" in log_data
            assert log_data["exception"]["type"] == "ValueError"
            assert log_data["exception"]["message"] == "Test exception"
            assert "traceback" in log_data["exception"]

class TestPerformanceMonitor:
    """Test PerformanceMonitor class."""
    
    @pytest.fixture
    def performance_monitor(self):
        """Create performance monitor."""
        return PerformanceMonitor(max_metrics=100)
    
    def test_performance_monitor_initialization(self, performance_monitor):
        """Test performance monitor initialization."""
        assert len(performance_monitor.metrics) == 0
        assert performance_monitor.max_metrics == 100
        assert performance_monitor.stats["total_operations"] == 0
    
    def test_measure_operation_success(self, performance_monitor):
        """Test measuring successful operation."""
        with performance_monitor.measure_operation("test_op", "test_component", "PATIENT123"):
            time.sleep(0.1)  # Simulate work
        
        assert len(performance_monitor.metrics) == 1
        metric = performance_monitor.metrics[0]
        assert metric.operation == "test_op"
        assert metric.component == "test_component"
        assert metric.patient_id == "PATIENT123"
        assert metric.success is True
        assert metric.duration_seconds >= 0.1
    
    def test_measure_operation_failure(self, performance_monitor):
        """Test measuring failed operation."""
        with pytest.raises(ValueError):
            with performance_monitor.measure_operation("test_op", "test_component"):
                raise ValueError("Test error")
        
        assert len(performance_monitor.metrics) == 1
        metric = performance_monitor.metrics[0]
        assert metric.success is False
    
    def test_statistics_update(self, performance_monitor):
        """Test statistics updates."""
        # Successful operation
        with performance_monitor.measure_operation("op1", "comp1"):
            time.sleep(0.05)
        
        # Failed operation
        with pytest.raises(ValueError):
            with performance_monitor.measure_operation("op2", "comp1"):
                raise ValueError("Error")
        
        stats = performance_monitor.get_statistics()
        assert stats["total_operations"] == 2
        assert stats["successful_operations"] == 1
        assert stats["failed_operations"] == 1
        assert "comp1" in stats["operations_by_component"]
        assert stats["operations_by_component"]["comp1"]["count"] == 2
    
    def test_component_metrics_filtering(self, performance_monitor):
        """Test filtering metrics by component."""
        # Add metrics for different components
        with performance_monitor.measure_operation("op1", "comp1"):
            pass
        with performance_monitor.measure_operation("op2", "comp2"):
            pass
        with performance_monitor.measure_operation("op3", "comp1"):
            pass
        
        comp1_metrics = performance_monitor.get_metrics_for_component("comp1")
        assert len(comp1_metrics) == 2
        
        comp2_metrics = performance_monitor.get_metrics_for_component("comp2")
        assert len(comp2_metrics) == 1
    
    def test_metrics_limit(self):
        """Test metrics memory limit."""
        monitor = PerformanceMonitor(max_metrics=5)
        
        # Add more metrics than limit
        for i in range(10):
            with monitor.measure_operation(f"op{i}", "test"):
                pass
        
        assert len(monitor.metrics) == 5
        # Should keep the most recent metrics
        assert monitor.metrics[-1].operation == "op9"
    
    def test_slowest_operations_tracking(self, performance_monitor):
        """Test slowest operations tracking."""
        # Add operations with different durations
        durations = [0.1, 0.05, 0.2, 0.03, 0.15]
        for i, duration in enumerate(durations):
            with performance_monitor.measure_operation(f"op{i}", "test"):
                time.sleep(duration)
        
        stats = performance_monitor.get_statistics()
        slowest = stats["slowest_operations"]
        
        # Should be sorted by duration (descending)
        assert len(slowest) == 5
        assert slowest[0]["operation"] == "op2"  # 0.2 seconds
        assert slowest[1]["operation"] == "op4"  # 0.15 seconds
    
    def test_clear_metrics(self, performance_monitor):
        """Test clearing metrics."""
        with performance_monitor.measure_operation("test_op", "test_comp"):
            pass
        
        assert len(performance_monitor.metrics) == 1
        
        performance_monitor.clear_metrics()
        
        assert len(performance_monitor.metrics) == 0
        assert performance_monitor.stats["total_operations"] == 0

class TestEnhancedLoggingSystem:
    """Test EnhancedLoggingSystem class."""
    
    @pytest.fixture
    def temp_log_dir(self):
        """Create temporary log directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def logging_system(self, temp_log_dir):
        """Create enhanced logging system."""
        return EnhancedLoggingSystem(
            log_dir=temp_log_dir,
            log_level="INFO",
            enable_performance_monitoring=True,
            enable_structured_logging=True
        )
    
    def test_logging_system_initialization(self, logging_system, temp_log_dir):
        """Test logging system initialization."""
        assert logging_system.log_dir == Path(temp_log_dir)
        assert logging_system.log_level == logging.INFO
        assert logging_system.enable_performance_monitoring is True
        assert logging_system.enable_structured_logging is True
        assert hasattr(logging_system, 'performance_monitor')
    
    def test_log_directory_creation(self, temp_log_dir):
        """Test log directory creation."""
        log_dir = Path(temp_log_dir) / "custom_logs"
        assert not log_dir.exists()
        
        EnhancedLoggingSystem(log_dir=str(log_dir))
        
        assert log_dir.exists()
    
    def test_performance_monitor_integration(self, logging_system):
        """Test performance monitor integration."""
        perf_monitor = logging_system.get_performance_monitor()
        assert perf_monitor is not None
        assert isinstance(perf_monitor, PerformanceMonitor)
    
    def test_operation_logging(self, logging_system):
        """Test operation start/end logging."""
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            logging_system.log_operation_start(
                "test_operation", 
                "test_component", 
                "PATIENT123",
                {"key": "value"}
            )
            
            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args
            assert "Starting operation: test_operation" in call_args[0][0]
            assert call_args[1]["extra"]["operation"] == "test_operation"
            assert call_args[1]["extra"]["patient_id"] == "PATIENT123"
    
    def test_log_statistics(self, logging_system, temp_log_dir):
        """Test log statistics collection."""
        # Create some log files
        log_file = Path(temp_log_dir) / "test.log"
        log_file.write_text("test log content")
        
        stats = logging_system.get_log_statistics()
        
        assert "log_files" in stats
        assert "performance_stats" in stats
        
        if logging_system.enable_performance_monitoring:
            assert "total_operations" in stats["performance_stats"]

class TestLoggingGlobalFunctions:
    """Test global logging functions."""
    
    def test_initialize_logging(self):
        """Test global logging initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system = initialize_logging(
                log_dir=temp_dir,
                log_level="DEBUG",
                enable_performance_monitoring=True
            )
            
            assert isinstance(system, EnhancedLoggingSystem)
            assert get_logging_system() is system
            
            perf_monitor = get_performance_monitor()
            assert perf_monitor is not None
    
    def test_log_operation_context_manager(self):
        """Test log_operation context manager."""
        with tempfile.TemporaryDirectory() as temp_dir:
            initialize_logging(log_dir=temp_dir, enable_performance_monitoring=True)
            
            with log_operation("test_operation", "test_component", "PATIENT123"):
                time.sleep(0.05)  # Simulate work
            
            perf_monitor = get_performance_monitor()
            assert len(perf_monitor.metrics) == 1
            
            metric = perf_monitor.metrics[0]
            assert metric.operation == "test_operation"
            assert metric.component == "test_component"
            assert metric.patient_id == "PATIENT123"
            assert metric.success is True
    
    def test_log_operation_with_error(self):
        """Test log_operation context manager with error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            initialize_logging(log_dir=temp_dir, enable_performance_monitoring=True)
            
            with pytest.raises(ValueError):
                with log_operation("test_operation", "test_component"):
                    raise ValueError("Test error")
            
            perf_monitor = get_performance_monitor()
            assert len(perf_monitor.metrics) == 1
            
            metric = perf_monitor.metrics[0]
            assert metric.success is False
    
    def test_log_operation_without_logging_system(self):
        """Test log_operation without initialized logging system."""
        # Reset global logging system
        import src.utils.enhanced_logging
        src.utils.enhanced_logging._logging_system = None
        
        # Should work without error
        with log_operation("test_operation", "test_component"):
            pass

class TestLoggingIntegration:
    """Test logging system integration scenarios."""
    
    def test_structured_logging_output(self):
        """Test structured logging output format."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system = EnhancedLoggingSystem(
                log_dir=temp_dir,
                enable_structured_logging=True
            )
            
            logger = logging.getLogger("test.component")
            logger.info(
                "Test message",
                extra={
                    "patient_id": "PATIENT123",
                    "operation": "test_operation",
                    "component": "test_component"
                }
            )
            
            # Check if log file was created and contains structured data
            log_files = list(Path(temp_dir).glob("*.log"))
            assert len(log_files) > 0
    
    def test_performance_logging_integration(self):
        """Test performance logging integration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system = EnhancedLoggingSystem(
                log_dir=temp_dir,
                enable_performance_monitoring=True
            )
            
            perf_monitor = system.get_performance_monitor()
            
            with perf_monitor.measure_operation("test_op", "test_comp", "PATIENT123"):
                time.sleep(0.05)
            
            # Performance data should be logged
            assert len(perf_monitor.metrics) == 1
    
    def test_multiple_log_handlers(self):
        """Test multiple log handlers setup."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system = EnhancedLoggingSystem(log_dir=temp_dir)
            
            root_logger = logging.getLogger()
            
            # Should have multiple handlers (console, main log, error log, etc.)
            assert len(root_logger.handlers) >= 3
            
            # Check for different handler types
            handler_types = [type(handler).__name__ for handler in root_logger.handlers]
            assert "StreamHandler" in handler_types  # Console
            assert "RotatingFileHandler" in handler_types  # File handlers
    
    @patch('logging.getLogger')
    def test_component_logger_setup(self, mock_get_logger):
        """Test component-specific logger setup."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            system = EnhancedLoggingSystem(log_dir=temp_dir)
            
            # Should setup loggers for each component
            expected_components = [
                'xml_parser', 'condition_extractor', 'medical_summarizer',
                'research_searcher', 'relevance_ranker', 'research_correlation',
                'report_generator', 's3_persister', 'workflow'
            ]
            
            for component in expected_components:
                expected_logger_name = f"medical_analysis.{component}"
                mock_get_logger.assert_any_call(expected_logger_name)