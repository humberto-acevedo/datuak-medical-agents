# Medical Record Analysis System - API Reference

This document provides comprehensive API reference for all components of the Medical Record Analysis System.

## 📋 Table of Contents

1. [Main Workflow API](#main-workflow-api)
2. [Agent APIs](#agent-apis)
3. [Quality Assurance API](#quality-assurance-api)
4. [Data Models](#data-models)
5. [Error Handling](#error-handling)
6. [Utilities](#utilities)

## 🔄 Main Workflow API

### MainWorkflow Class

The central orchestrator for the medical record analysis system.

```python
from src.workflow.main_workflow import MainWorkflow
```

#### Constructor

```python
def __init__(self, 
             audit_logger: Optional[AuditLogger] = None,
             progress_callback: Optional[Callable[[WorkflowProgress], None]] = None,
             timeout_seconds: int = 300,
             enable_enhanced_logging: bool = True,
             log_level: str = "INFO")
```

**Parameters:**
- `audit_logger`: Optional audit logger for HIPAA compliance
- `progress_callback`: Optional callback for progress updates
- `timeout_seconds`: Maximum workflow execution time (default: 300)
- `enable_enhanced_logging`: Enable structured logging (default: True)
- `log_level`: Logging level (default: "INFO")

#### Methods

##### execute_complete_analysis

```python
async def execute_complete_analysis(self, patient_name: str) -> AnalysisReport
```

Execute complete medical record analysis workflow.

**Parameters:**
- `patient_name` (str): Name of patient to analyze

**Returns:**
- `AnalysisReport`: Complete analysis report with quality assessment

**Raises:**
- `AgentCommunicationError`: If agent coordination fails
- `XMLParsingError`: If XML parsing fails
- `ResearchError`: If research correlation fails
- `ReportError`: If report generation or quality assurance fails
- `S3Error`: If report persistence fails

**Example:**
```python
workflow = MainWorkflow()
result = await workflow.execute_complete_analysis("John Doe")
print(f"Analysis complete: {result.report_id}")
```

##### get_workflow_statistics

```python
def get_workflow_statistics(self) -> Dict[str, Any]
```

Get comprehensive workflow statistics including quality assurance metrics.

**Returns:**
- `Dict[str, Any]`: Statistics including success rates, performance metrics, and QA data

**Example:**
```python
stats = workflow.get_workflow_statistics()
print(f"Success rate: {stats['successful_workflows'] / stats['total_workflows']}")
print(f"Average time: {stats['average_processing_time']}s")
print(f"QA stats: {stats['quality_assurance_stats']}")
```

##### get_workflow_status

```python
def get_workflow_status(self) -> Dict[str, Any]
```

Get current workflow execution status and progress.

**Returns:**
- `Dict[str, Any]`: Current status, progress percentage, and step information

##### cancel_workflow

```python
async def cancel_workflow(self) -> bool
```

Cancel currently running workflow.

**Returns:**
- `bool`: True if workflow was cancelled, False if no workflow running

### WorkflowProgress Class

Tracks workflow execution progress.

```python
class WorkflowProgress:
    def __init__(self)
    def start_step(self, step_index: int)
    def complete_step(self, step_index: int)
    def get_progress_percentage(self) -> float
    def get_total_duration(self) -> float
```

**Properties:**
- `current_step`: Current step index (0-6)
- `total_steps`: Total number of steps (7)
- `step_names`: List of step names
- `step_times`: Dictionary of step timing information

## 🤖 Agent APIs

### XMLParserAgent

Parses patient XML records from S3.

```python
from src.agents.xml_parser_agent import XMLParserAgent
```

#### Methods

##### parse_patient_record

```python
def parse_patient_record(self, patient_name: str) -> PatientData
```

Parse patient XML record from S3.

**Parameters:**
- `patient_name` (str): Patient name for S3 path resolution

**Returns:**
- `PatientData`: Structured patient data

**Raises:**
- `XMLParsingError`: If XML parsing fails
- `S3Error`: If S3 access fails

### MedicalSummarizationAgent

Generates medical summaries and extracts conditions.

```python
from src.agents.medical_summarization_agent import MedicalSummarizationAgent
```

#### Methods

##### generate_summary

```python
def generate_summary(self, patient_data: PatientData) -> MedicalSummary
```

Generate comprehensive medical summary.

**Parameters:**
- `patient_data` (PatientData): Patient data from XML parser

**Returns:**
- `MedicalSummary`: Medical summary with conditions and medications

### ResearchCorrelationAgent

Correlates medical research with patient conditions.

```python
from src.agents.research_correlation_agent import ResearchCorrelationAgent
```

#### Methods

##### correlate_research

```python
def correlate_research(self, patient_data: PatientData, medical_summary: MedicalSummary) -> ResearchAnalysis
```

Correlate research findings with patient conditions.

**Parameters:**
- `patient_data` (PatientData): Patient data
- `medical_summary` (MedicalSummary): Medical summary with conditions

**Returns:**
- `ResearchAnalysis`: Research findings and correlations

### ReportGenerator

Generates comprehensive analysis reports.

```python
from src.agents.report_generator import ReportGenerator
```

#### Methods

##### generate_report

```python
def generate_report(self, patient_data: PatientData, medical_summary: MedicalSummary, research_analysis: ResearchAnalysis) -> AnalysisReport
```

Generate complete analysis report.

**Parameters:**
- `patient_data` (PatientData): Patient data
- `medical_summary` (MedicalSummary): Medical summary
- `research_analysis` (ResearchAnalysis): Research analysis

**Returns:**
- `AnalysisReport`: Complete analysis report

### S3ReportPersister

Persists analysis reports to S3.

```python
from src.agents.s3_report_persister import S3ReportPersister
```

#### Methods

##### save_analysis_report

```python
def save_analysis_report(self, analysis_report: AnalysisReport) -> str
```

Save analysis report to S3.

**Parameters:**
- `analysis_report` (AnalysisReport): Report to save

**Returns:**
- `str`: S3 key of saved report

## 🛡️ Quality Assurance API

### QualityAssuranceEngine

Main quality assurance system.

```python
from src.utils.quality_assurance import QualityAssuranceEngine, initialize_quality_assurance
```

#### Initialization

```python
qa_engine = initialize_quality_assurance(
    audit_logger=audit_logger,
    error_handler=error_handler
)
```

#### Methods

##### assess_analysis_quality

```python
def assess_analysis_quality(self, analysis_report: AnalysisReport) -> QualityAssessment
```

Perform comprehensive quality assessment.

**Parameters:**
- `analysis_report` (AnalysisReport): Report to assess

**Returns:**
- `QualityAssessment`: Detailed quality assessment results

**Example:**
```python
assessment = qa_engine.assess_analysis_quality(report)
print(f"Quality Level: {assessment.quality_level}")
print(f"Overall Score: {assessment.overall_score}")
print(f"Hallucination Risk: {assessment.hallucination_risk}")
```

##### get_quality_statistics

```python
def get_quality_statistics(self) -> Dict[str, Any]
```

Get quality assurance system statistics.

**Returns:**
- `Dict[str, Any]`: QA system configuration and thresholds

### HallucinationPreventionSystem

Prevents AI hallucinations in medical content.

```python
from src.utils.hallucination_prevention import HallucinationPreventionSystem, initialize_hallucination_prevention
```

#### Initialization

```python
prevention_system = initialize_hallucination_prevention(
    audit_logger=audit_logger,
    error_handler=error_handler,
    strict_mode=True
)
```

#### Methods

##### check_content

```python
def check_content(self, content: str, content_type: str = "general", patient_id: Optional[str] = None) -> HallucinationCheck
```

Check content for potential hallucinations.

**Parameters:**
- `content` (str): Content to check
- `content_type` (str): Type of content ("general", "medication", "condition", "procedure")
- `patient_id` (Optional[str]): Patient ID for logging

**Returns:**
- `HallucinationCheck`: Hallucination check results

**Raises:**
- `HallucinationDetectedError`: If critical hallucination detected in strict mode

**Example:**
```python
result = prevention_system.check_content(
    "Patient prescribed aspirin 81mg daily",
    "medication",
    "P12345"
)
print(f"Risk Level: {result.risk_level}")
print(f"Confidence: {result.confidence}")
```

##### get_prevention_statistics

```python
def get_prevention_statistics(self) -> Dict[str, Any]
```

Get hallucination prevention statistics.

**Returns:**
- `Dict[str, Any]`: Prevention statistics including detection rates

## 📊 Data Models

### PatientData

```python
@dataclass
class PatientData:
    name: str
    patient_id: str
    age: Optional[int] = None
    gender: Optional[str] = None
    date_of_birth: Optional[str] = None
    medical_history: Optional[Dict[str, Any]] = None
    
    def validate(self) -> bool
    def to_dict(self) -> Dict[str, Any]
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PatientData'
```

### MedicalSummary

```python
@dataclass
class MedicalSummary:
    summary_text: str
    key_conditions: List[Dict[str, Any]]
    chronic_conditions: List[str]
    medications: List[str]
    procedures: Optional[List[str]] = None
    allergies: Optional[List[str]] = None
    
    def validate(self) -> bool
    def to_dict(self) -> Dict[str, Any]
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MedicalSummary'
```

### ResearchAnalysis

```python
@dataclass
class ResearchAnalysis:
    research_findings: List[Dict[str, Any]]
    analysis_confidence: float
    insights: List[str]
    recommendations: List[str]
    summary_text: Optional[str] = None
    
    def validate(self) -> bool
    def to_dict(self) -> Dict[str, Any]
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ResearchAnalysis'
```

### AnalysisReport

```python
@dataclass
class AnalysisReport:
    report_id: str
    patient_data: PatientData
    medical_summary: MedicalSummary
    research_analysis: ResearchAnalysis
    generated_at: datetime
    processing_metadata: Optional[Dict[str, Any]] = None
    
    def validate(self) -> bool
    def to_dict(self) -> Dict[str, Any]
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AnalysisReport'
```

### QualityAssessment

```python
@dataclass
class QualityAssessment:
    overall_score: float
    quality_level: QualityLevel
    data_completeness: float
    consistency_score: float
    accuracy_score: float
    validation_issues: List[ValidationIssue]
    hallucination_risk: float
    confidence_metrics: Dict[str, float]
    recommendations: List[str]
    
    def to_dict(self) -> Dict[str, Any]
```

### HallucinationCheck

```python
@dataclass
class HallucinationCheck:
    risk_level: HallucinationRiskLevel
    confidence: float
    detected_patterns: List[str]
    suggested_corrections: List[str]
    requires_human_review: bool
    
    def to_dict(self) -> Dict[str, Any]
```

## ⚠️ Error Handling

### Exception Hierarchy

```python
# Base exceptions
class MedicalAnalysisError(Exception): pass

# Agent-specific exceptions
class XMLParsingError(MedicalAnalysisError): pass
class AgentCommunicationError(MedicalAnalysisError): pass
class ResearchError(MedicalAnalysisError): pass
class ReportError(MedicalAnalysisError): pass
class S3Error(MedicalAnalysisError): pass

# Quality assurance exceptions
class HallucinationDetectedError(MedicalAnalysisError):
    def __init__(self, message: str, detected_patterns: List[str])
```

### Error Context

```python
@dataclass
class ErrorContext:
    operation: str
    component: str
    patient_id: Optional[str] = None
    additional_context: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.now)
```

### Error Handler

```python
from src.utils.error_handler import ErrorHandler

error_handler = ErrorHandler(audit_logger=audit_logger)

# Handle error with context
try:
    result = some_operation()
except Exception as e:
    context = ErrorContext(
        operation="some_operation",
        component="component_name",
        patient_id="P12345"
    )
    error_result = error_handler.handle_error(e, context)
    
    if error_result["is_recoverable"]:
        # Handle recoverable error
        pass
    else:
        # Handle non-recoverable error
        raise
```

## 🔧 Utilities

### Audit Logger

```python
from src.utils.audit_logger import AuditLogger, initialize_audit_logging

audit_logger = initialize_audit_logging()

# Log patient access
audit_logger.log_patient_access(
    patient_id="P12345",
    operation="analysis_start",
    component="main_workflow"
)

# Log data access
audit_logger.log_data_access(
    patient_id="P12345",
    operation="xml_parsing",
    details={"s3_key": "patients/john_doe.xml"}
)

# Log system event
audit_logger.log_system_event(
    operation="quality_assessment",
    component="quality_assurance",
    additional_context={"quality_level": "good"}
)

# Log error
audit_logger.log_error(
    operation="research_correlation",
    component="research_agent",
    error=exception,
    patient_id="P12345"
)
```

### Enhanced Logging

```python
from src.utils.enhanced_logging import initialize_logging, log_operation

# Initialize logging system
logging_system = initialize_logging(
    log_level="INFO",
    enable_performance_monitoring=True,
    enable_structured_logging=True
)

# Use operation logging context
with log_operation("patient_analysis", "main_workflow", "P12345"):
    # Operations within this context are automatically logged
    result = perform_analysis()
```

### Performance Monitor

```python
from src.utils.enhanced_logging import get_performance_monitor

perf_monitor = get_performance_monitor()
stats = perf_monitor.get_statistics()

print(f"Average response time: {stats['avg_response_time']}")
print(f"Peak memory usage: {stats['peak_memory_usage']}")
print(f"Total operations: {stats['total_operations']}")
```

## 📝 Usage Examples

### Basic Workflow Execution

```python
import asyncio
from src.workflow.main_workflow import MainWorkflow

async def analyze_patient():
    workflow = MainWorkflow()
    
    try:
        result = await workflow.execute_complete_analysis("John Doe")
        
        print(f"Analysis Report ID: {result.report_id}")
        print(f"Patient: {result.patient_data.name}")
        print(f"Conditions: {len(result.medical_summary.key_conditions)}")
        print(f"Research Findings: {len(result.research_analysis.research_findings)}")
        
        # Check quality assessment
        qa_data = result.processing_metadata.get('quality_assessment', {})
        print(f"Quality Level: {qa_data.get('quality_level')}")
        print(f"Overall Score: {qa_data.get('overall_score')}")
        
    except Exception as e:
        print(f"Analysis failed: {e}")

# Run analysis
asyncio.run(analyze_patient())
```

### Quality Assurance Integration

```python
from src.utils.quality_assurance import initialize_quality_assurance
from src.utils.hallucination_prevention import initialize_hallucination_prevention

# Initialize QA systems
qa_engine = initialize_quality_assurance()
prevention_system = initialize_hallucination_prevention(strict_mode=True)

# Assess report quality
assessment = qa_engine.assess_analysis_quality(analysis_report)

if assessment.quality_level == QualityLevel.UNACCEPTABLE:
    print("Report quality is unacceptable")
    for issue in assessment.validation_issues:
        print(f"- {issue.severity}: {issue.message}")

# Check for hallucinations
hallucination_check = prevention_system.check_content(
    medical_summary.summary_text,
    "general",
    patient_data.patient_id
)

if hallucination_check.requires_human_review:
    print("Content requires human review")
    for pattern in hallucination_check.detected_patterns:
        print(f"- Detected: {pattern}")
```

### Batch Processing

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def process_patients_batch(patient_names):
    workflow = MainWorkflow()
    
    async def process_single_patient(name):
        try:
            return await workflow.execute_complete_analysis(name)
        except Exception as e:
            return {"error": str(e), "patient": name}
    
    # Process patients concurrently
    tasks = [process_single_patient(name) for name in patient_names]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    return results

# Process batch
patient_names = ["John Doe", "Jane Smith", "Bob Johnson"]
results = asyncio.run(process_patients_batch(patient_names))

for result in results:
    if isinstance(result, dict) and "error" in result:
        print(f"Failed to process {result['patient']}: {result['error']}")
    else:
        print(f"Successfully processed: {result.patient_data.name}")
```

## 🔒 Security Considerations

### Input Validation

All API methods perform input validation:

```python
# Patient name validation
def _validate_patient_name(self, name: str) -> str:
    if not name or len(name.strip()) < 2:
        raise ValueError("Patient name must be at least 2 characters")
    
    if len(name) > 100:
        raise ValueError("Patient name too long")
    
    # Sanitize input
    sanitized = re.sub(r'[^\w\s\-\.]', '', name.strip())
    return sanitized
```

### Error Message Sanitization

Error messages are sanitized to prevent information leakage:

```python
# Safe error messages for external consumption
def get_safe_error_message(self, error: Exception) -> str:
    if isinstance(error, XMLParsingError):
        return "Unable to process patient record"
    elif isinstance(error, S3Error):
        return "Data access error"
    else:
        return "System error occurred"
```

### Audit Logging

All operations are logged for compliance:

```python
# Automatic audit logging for all patient data access
@audit_patient_access
def process_patient_data(self, patient_id: str):
    # Operation is automatically logged
    pass
```

---

This API reference provides comprehensive documentation for all system components. For additional examples and use cases, refer to the test files and main README.md.