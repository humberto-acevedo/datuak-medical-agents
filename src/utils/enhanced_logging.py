"""Enhanced logging system with structured logging and performance monitoring."""
import logging
import logging.handlers
import json
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager
from dataclasses import dataclass, asdict
import threading
from queue import Queue
import boto3
from botocore.exceptions import ClientError

@dataclass
class PerformanceMetric:
    """Performance metric data structure."""
    operation: str
    component: str
    start_time: float
    end_time: float
    duration_seconds: float
    success: bool
    patient_id: Optional[str] = None

class S3LogHandler(logging.Handler):
    """Custom log handler that uploads logs to S3."""
    
    def __init__(self, bucket_name: str, key_prefix: str = "logs/"):
        super().__init__()
        self.bucket_name = bucket_name
        self.key_prefix = key_prefix
        self.s3_client = boto3.client('s3')
        self.log_buffer = []
        self.buffer_size = 50  # Upload after 50 log entries
        
    def emit(self, record):
        """Add log record to buffer and upload when buffer is full."""
        try:
            log_entry = {
                'timestamp': datetime.fromtimestamp(record.created).isoformat(),
                'level': record.levelname,
                'logger': record.name,
                'message': record.getMessage(),
                'module': record.module,
                'function': record.funcName,
                'line': record.lineno
            }
            
            self.log_buffer.append(log_entry)
            
            if len(self.log_buffer) >= self.buffer_size:
                self._upload_logs()
                
        except Exception:
            # Don't let logging errors break the application
            pass
    
    def _upload_logs(self):
        """Upload buffered logs to S3."""
        if not self.log_buffer:
            return
            
        try:
            timestamp = datetime.now().strftime("%Y/%m/%d/%H-%M-%S")
            key = f"{self.key_prefix}agent-logs-{timestamp}.json"
            
            log_data = {
                'logs': self.log_buffer,
                'upload_time': datetime.now().isoformat(),
                'count': len(self.log_buffer)
            }
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=json.dumps(log_data, indent=2),
                ContentType='application/json'
            )
            
            self.log_buffer.clear()
            
        except ClientError:
            # Silently fail S3 uploads to avoid breaking the application
            pass
    
    def close(self):
        """Upload remaining logs when handler is closed."""
        self._upload_logs()
        super().close()
    additional_data: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return asdict(self)

class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        # Base log data
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add thread information
        log_data["thread"] = {
            "id": record.thread,
            "name": record.threadName
        }
        
        # Add process information
        log_data["process"] = {
            "id": record.process,
            "name": getattr(record, 'processName', 'MainProcess')
        }
        
        # Add exception information if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }
        
        # Add custom fields from extra
        if hasattr(record, 'patient_id'):
            log_data["patient_id"] = record.patient_id
        
        if hasattr(record, 'operation'):
            log_data["operation"] = record.operation
        
        if hasattr(record, 'component'):
            log_data["component"] = record.component
        
        if hasattr(record, 'error_record'):
            log_data["error_details"] = record.error_record
        
        if hasattr(record, 'performance_data'):
            log_data["performance"] = record.performance_data
        
        # Add any other extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 
                          'msecs', 'relativeCreated', 'thread', 'threadName', 
                          'processName', 'process', 'exc_info', 'exc_text', 
                          'stack_info', 'getMessage', 'patient_id', 'operation', 
                          'component', 'error_record', 'performance_data']:
                if not key.startswith('_'):
                    log_data["extra"] = log_data.get("extra", {})
                    log_data["extra"][key] = value
        
        return json.dumps(log_data, default=str, ensure_ascii=False)

class PerformanceMonitor:
    """Performance monitoring and metrics collection."""
    
    def __init__(self, max_metrics: int = 10000):
        """
        Initialize performance monitor.
        
        Args:
            max_metrics: Maximum number of metrics to keep in memory
        """
        self.metrics: List[PerformanceMetric] = []
        self.max_metrics = max_metrics
        self._lock = threading.Lock()
        
        # Performance statistics
        self.stats = {
            "total_operations": 0,
            "successful_operations": 0,
            "failed_operations": 0,
            "average_duration": 0.0,
            "operations_by_component": {},
            "slowest_operations": []
        }
    
    @contextmanager
    def measure_operation(self, operation: str, component: str, 
                         patient_id: Optional[str] = None,
                         additional_data: Optional[Dict[str, Any]] = None):
        """Context manager for measuring operation performance."""
        start_time = time.time()
        success = False
        
        try:
            yield
            success = True
        finally:
            end_time = time.time()
            duration = end_time - start_time
            
            metric = PerformanceMetric(
                operation=operation,
                component=component,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration,
                success=success,
                patient_id=patient_id,
                additional_data=additional_data
            )
            
            self._record_metric(metric)
    
    def _record_metric(self, metric: PerformanceMetric):
        """Record performance metric."""
        with self._lock:
            self.metrics.append(metric)
            
            # Limit metrics in memory
            if len(self.metrics) > self.max_metrics:
                self.metrics = self.metrics[-self.max_metrics:]
            
            # Update statistics
            self._update_statistics(metric)
            
            # Log performance data
            logger = logging.getLogger(f"{metric.component}.performance")
            logger.info(
                f"Operation completed: {metric.operation}",
                extra={
                    "performance_data": metric.to_dict(),
                    "operation": metric.operation,
                    "component": metric.component,
                    "patient_id": metric.patient_id
                }
            )
    
    def _update_statistics(self, metric: PerformanceMetric):
        """Update performance statistics."""
        self.stats["total_operations"] += 1
        
        if metric.success:
            self.stats["successful_operations"] += 1
        else:
            self.stats["failed_operations"] += 1
        
        # Update average duration
        total_duration = sum(m.duration_seconds for m in self.metrics)
        self.stats["average_duration"] = total_duration / len(self.metrics)
        
        # Update component statistics
        component = metric.component
        if component not in self.stats["operations_by_component"]:
            self.stats["operations_by_component"][component] = {
                "count": 0,
                "total_duration": 0.0,
                "average_duration": 0.0,
                "success_rate": 0.0
            }
        
        comp_stats = self.stats["operations_by_component"][component]
        comp_stats["count"] += 1
        comp_stats["total_duration"] += metric.duration_seconds
        comp_stats["average_duration"] = comp_stats["total_duration"] / comp_stats["count"]
        
        # Calculate success rate for component
        component_metrics = [m for m in self.metrics if m.component == component]
        successful = sum(1 for m in component_metrics if m.success)
        comp_stats["success_rate"] = successful / len(component_metrics)
        
        # Update slowest operations
        self.stats["slowest_operations"] = sorted(
            self.metrics,
            key=lambda x: x.duration_seconds,
            reverse=True
        )[:10]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get current performance statistics."""
        with self._lock:
            return {
                **self.stats,
                "slowest_operations": [m.to_dict() for m in self.stats["slowest_operations"]]
            }
    
    def get_metrics_for_component(self, component: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent metrics for specific component."""
        with self._lock:
            component_metrics = [
                m.to_dict() for m in self.metrics 
                if m.component == component
            ][-limit:]
            return component_metrics
    
    def clear_metrics(self):
        """Clear all metrics (for testing or maintenance)."""
        with self._lock:
            self.metrics.clear()
            self.stats = {
                "total_operations": 0,
                "successful_operations": 0,
                "failed_operations": 0,
                "average_duration": 0.0,
                "operations_by_component": {},
                "slowest_operations": []
            }

class EnhancedLoggingSystem:
    """Enhanced logging system with structured logging and performance monitoring."""
    
    def __init__(self, 
                 log_dir: str = "/tmp/logs",
                 log_level: str = "INFO",
                 enable_performance_monitoring: bool = True,
                 enable_structured_logging: bool = True):
        """
        Initialize enhanced logging system.
        
        Args:
            log_dir: Directory for log files
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            enable_performance_monitoring: Enable performance monitoring
            enable_structured_logging: Enable structured JSON logging
        """
        self.log_dir = Path(log_dir)
        self.log_level = getattr(logging, log_level.upper())
        self.enable_performance_monitoring = enable_performance_monitoring
        self.enable_structured_logging = enable_structured_logging
        
        # Create log directory (skip in restricted environments)
        self.use_file_logging = self._can_create_log_directory()
        if self.use_file_logging:
            self.log_dir.mkdir(exist_ok=True)
        
        # Initialize performance monitor
        if self.enable_performance_monitoring:
            self.performance_monitor = PerformanceMonitor()
        
        # Setup logging
        self._setup_logging()
        
        logging.info("Enhanced logging system initialized")
    
    def _can_create_log_directory(self) -> bool:
        """Check if we can create log directory (skip in restricted environments)."""
        import os
        # Skip file logging in Lambda/Bedrock Agent environments
        if (os.environ.get('AWS_LAMBDA_FUNCTION_NAME') or 
            os.environ.get('AWS_EXECUTION_ENV', '').startswith('AWS_Lambda')):
            return False
        try:
            # Test if we can create the directory without actually creating it yet
            test_path = self.log_dir / '.test'
            test_path.parent.mkdir(parents=True, exist_ok=True)
            test_path.touch()
            test_path.unlink()
            return True
        except (PermissionError, OSError):
            return False
    
    def _setup_logging(self):
        """Setup logging configuration."""
        # Clear existing handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Set root logger level
        root_logger.setLevel(self.log_level)
        
        # Create formatters
        if self.enable_structured_logging:
            formatter = StructuredFormatter()
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.log_level)
        if not self.enable_structured_logging:
            console_handler.setFormatter(formatter)
        else:
            # Use simple formatter for console
            console_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        
        # File handlers (only if file logging is available)
        if self.use_file_logging:
            self._setup_file_handlers(formatter)
        
        # Setup specific loggers
        self._setup_component_loggers()
    
    def _setup_file_handlers(self, formatter: logging.Formatter):
        """Setup file handlers for different log types."""
        # Main application log
        main_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "medical_analysis.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        main_handler.setLevel(self.log_level)
        main_handler.setFormatter(formatter)
        logging.getLogger().addHandler(main_handler)
        
        # Error log
        error_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "errors.log",
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        logging.getLogger().addHandler(error_handler)
        
        # Performance log
        if self.enable_performance_monitoring:
            performance_handler = logging.handlers.RotatingFileHandler(
                self.log_dir / "performance.log",
                maxBytes=5*1024*1024,  # 5MB
                backupCount=3
            )
            performance_handler.setLevel(logging.INFO)
            performance_handler.setFormatter(formatter)
            
            # Add filter to only log performance messages
            performance_handler.addFilter(lambda record: hasattr(record, 'performance_data'))
            logging.getLogger().addHandler(performance_handler)
        
        # Audit log (HIPAA compliance)
        audit_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "audit.log",
            maxBytes=20*1024*1024,  # 20MB
            backupCount=10
        )
        audit_handler.setLevel(logging.INFO)
        audit_handler.setFormatter(formatter)
        
        # Add filter for audit messages
        audit_handler.addFilter(lambda record: 'audit' in record.name.lower())
        logging.getLogger().addHandler(audit_handler)
        
        # S3 log handler for cloud storage
        try:
            s3_handler = S3LogHandler(
                bucket_name="patient-records-20251024",
                key_prefix="agent-logs/"
            )
            s3_handler.setLevel(logging.INFO)
            s3_handler.setFormatter(formatter)
            logging.getLogger().addHandler(s3_handler)
        except Exception:
            # S3 handler is optional - don't fail if it can't be created
            pass
    
    def _setup_component_loggers(self):
        """Setup loggers for specific components."""
        components = [
            'xml_parser', 'condition_extractor', 'medical_summarizer',
            'research_searcher', 'relevance_ranker', 'research_correlation',
            'report_generator', 's3_persister', 'workflow'
        ]
        
        for component in components:
            logger = logging.getLogger(f"medical_analysis.{component}")
            logger.setLevel(self.log_level)
            
            # Performance logger for each component
            if self.enable_performance_monitoring:
                perf_logger = logging.getLogger(f"medical_analysis.{component}.performance")
                perf_logger.setLevel(logging.INFO)
    
    def get_performance_monitor(self) -> Optional[PerformanceMonitor]:
        """Get performance monitor instance."""
        return getattr(self, 'performance_monitor', None)
    
    def log_operation_start(self, operation: str, component: str, 
                           patient_id: Optional[str] = None,
                           additional_data: Optional[Dict[str, Any]] = None):
        """Log operation start."""
        logger = logging.getLogger(f"medical_analysis.{component}")
        logger.info(
            f"Starting operation: {operation}",
            extra={
                "operation": operation,
                "component": component,
                "patient_id": patient_id,
                "phase": "start",
                **(additional_data or {})
            }
        )
    
    def log_operation_end(self, operation: str, component: str,
                         success: bool = True,
                         patient_id: Optional[str] = None,
                         additional_data: Optional[Dict[str, Any]] = None):
        """Log operation end."""
        logger = logging.getLogger(f"medical_analysis.{component}")
        level = logging.INFO if success else logging.ERROR
        status = "completed successfully" if success else "failed"
        
        logger.log(
            level,
            f"Operation {status}: {operation}",
            extra={
                "operation": operation,
                "component": component,
                "patient_id": patient_id,
                "phase": "end",
                "success": success,
                **(additional_data or {})
            }
        )
    
    def get_log_statistics(self) -> Dict[str, Any]:
        """Get logging statistics."""
        stats = {
            "log_files": {},
            "performance_stats": {}
        }
        
        # Get log file sizes
        for log_file in self.log_dir.glob("*.log"):
            stats["log_files"][log_file.name] = {
                "size_bytes": log_file.stat().st_size,
                "modified": datetime.fromtimestamp(log_file.stat().st_mtime).isoformat()
            }
        
        # Get performance statistics
        if self.enable_performance_monitoring and hasattr(self, 'performance_monitor'):
            stats["performance_stats"] = self.performance_monitor.get_statistics()
        
        return stats

# Global logging system instance
_logging_system: Optional[EnhancedLoggingSystem] = None

def initialize_logging(log_dir: str = "logs",
                      log_level: str = "INFO",
                      enable_performance_monitoring: bool = True,
                      enable_structured_logging: bool = True) -> EnhancedLoggingSystem:
    """Initialize global logging system."""
    global _logging_system
    _logging_system = EnhancedLoggingSystem(
        log_dir=log_dir,
        log_level=log_level,
        enable_performance_monitoring=enable_performance_monitoring,
        enable_structured_logging=enable_structured_logging
    )
    return _logging_system

def get_logging_system() -> Optional[EnhancedLoggingSystem]:
    """Get global logging system instance."""
    return _logging_system

def get_performance_monitor() -> Optional[PerformanceMonitor]:
    """Get global performance monitor instance."""
    if _logging_system:
        return _logging_system.get_performance_monitor()
    return None

@contextmanager
def log_operation(operation: str, component: str,
                 patient_id: Optional[str] = None,
                 additional_data: Optional[Dict[str, Any]] = None):
    """Context manager for logging operations with performance monitoring."""
    if _logging_system:
        _logging_system.log_operation_start(operation, component, patient_id, additional_data)
        
        if _logging_system.enable_performance_monitoring:
            perf_monitor = _logging_system.get_performance_monitor()
            if perf_monitor:
                with perf_monitor.measure_operation(operation, component, patient_id, additional_data):
                    try:
                        yield
                        _logging_system.log_operation_end(operation, component, True, patient_id, additional_data)
                    except Exception as e:
                        _logging_system.log_operation_end(operation, component, False, patient_id, additional_data)
                        raise
            else:
                try:
                    yield
                    _logging_system.log_operation_end(operation, component, True, patient_id, additional_data)
                except Exception as e:
                    _logging_system.log_operation_end(operation, component, False, patient_id, additional_data)
                    raise
        else:
            try:
                yield
                _logging_system.log_operation_end(operation, component, True, patient_id, additional_data)
            except Exception as e:
                _logging_system.log_operation_end(operation, component, False, patient_id, additional_data)
                raise
    else:
        yield
