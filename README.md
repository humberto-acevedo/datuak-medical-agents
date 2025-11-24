# Medical Record Analysis System

A comprehensive, HIPAA-compliant medical record analysis system that uses AI agents to parse patient XML records, generate medical summaries, correlate research findings, and produce detailed analysis reports with quality assurance.

## 🏥 Overview

This system provides automated analysis of medical records through a multi-agent architecture:

1. **XML Parser Agent** - Extracts structured data from patient XML records
2. **Medical Summarization Agent** - Generates comprehensive medical summaries and identifies key conditions
3. **Research Correlation Agent** - Finds and correlates relevant medical research
4. **Report Generator** - Creates comprehensive analysis reports
5. **Quality Assurance System** - Validates output quality and prevents AI hallucinations
6. **S3 Report Persister** - Securely stores analysis reports

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- AWS Account with S3 access
- Docker (optional, for containerized deployment)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd medical-record-analysis
```

2. Create virtual environment and install dependencies:
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# venv\Scripts\activate  # On Windows

# Install dependencies
python3 -m pip install -r requirements.txt
```

**Note**: If you get an `externally-managed-environment` error (common with Homebrew Python), using a virtual environment is the recommended solution.

3. Configure AWS credentials (required for prototype):
```bash
# Option 1: Use AWS CLI (recommended)
aws configure

# Option 2: Set environment variables
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1
export S3_BUCKET_NAME=your-medical-records-bucket
```

4. Run the system:
```bash
python src/main.py
```

## 📋 System Requirements

### Functional Requirements

- **Patient Record Processing**: Parse XML medical records from S3
- **Medical Summarization**: Generate structured medical summaries
- **Research Correlation**: Find relevant medical literature
- **Quality Assurance**: Validate output quality and prevent hallucinations
- **Secure Storage**: HIPAA-compliant report storage
- **Audit Logging**: Complete audit trail for compliance

### Technical Requirements

- **AWS Integration**: S3 for data storage and retrieval
- **Performance**: Process records within 45 seconds
- **Quality**: Maintain >80% quality scores with <20% hallucination risk
- **Scalability**: Handle concurrent processing
- **Security**: HIPAA-compliant data handling

## 🏗️ Architecture

### System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│   CLI Interface │    │  Main Workflow   │    │  Quality Assurance  │
│                 │───▶│   Orchestrator   │───▶│      System         │
└─────────────────┘    └──────────────────┘    └─────────────────────┘
                                │
                ┌───────────────┼───────────────┐
                │               │               │
        ┌───────▼──────┐ ┌──────▼──────┐ ┌─────▼──────┐
        │ XML Parser   │ │  Medical    │ │ Research   │
        │    Agent     │ │Summarization│ │Correlation │
        │              │ │   Agent     │ │   Agent    │
        └──────────────┘ └─────────────┘ └────────────┘
                │               │               │
                └───────────────┼───────────────┘
                                │
                    ┌───────────▼──────────┐
                    │   Report Generator   │
                    │        &             │
                    │   S3 Persister      │
                    └─────────────────────┘
```

### Agent Architecture

Each agent follows a consistent pattern:
- **Input Validation**: Validates incoming data
- **Core Processing**: Performs agent-specific operations
- **Output Generation**: Produces structured results
- **Error Handling**: Comprehensive error management
- **Audit Logging**: HIPAA-compliant logging

## 🔧 Configuration

### Environment Variables

```bash
# AWS Configuration
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-east-1
S3_BUCKET_NAME=your-medical-records-bucket

# System Configuration
LOG_LEVEL=INFO
ENABLE_AUDIT_LOGGING=true
QUALITY_ASSURANCE_STRICT_MODE=true
WORKFLOW_TIMEOUT_SECONDS=300

# Performance Configuration
MAX_CONCURRENT_WORKFLOWS=5
RESEARCH_SEARCH_TIMEOUT=30
XML_PARSING_TIMEOUT=15
```

### Quality Assurance Configuration

The system includes configurable quality thresholds:

```python
QUALITY_THRESHOLDS = {
    "excellent": 0.95,
    "good": 0.85,
    "acceptable": 0.70,
    "poor": 0.50,
    "unacceptable": 0.0
}

HALLUCINATION_RISK_THRESHOLDS = {
    "low": 0.2,
    "medium": 0.5,
    "high": 0.8
}
```

## 📊 Usage Examples

### Basic Usage

```python
from src.workflow.main_workflow import MainWorkflow

# Initialize workflow
workflow = MainWorkflow()

# Process patient record
result = await workflow.execute_complete_analysis("John Doe")

# Access results
print(f"Patient: {result.patient_data.name}")
print(f"Summary: {result.medical_summary.summary_text}")
print(f"Quality Score: {result.processing_metadata['quality_assessment']['overall_score']}")
```

### Command Line Interface

```bash
# Interactive mode
python src/main.py

# Direct patient analysis
python src/main.py --patient "John Doe"

# Batch processing
python src/main.py --batch patients.txt
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
print(f"Quality Level: {assessment.quality_level}")
print(f"Hallucination Risk: {assessment.hallucination_risk}")
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test categories
pytest -m integration          # Integration tests
pytest -m performance         # Performance tests
pytest -m quality_assurance   # QA tests

# Run with coverage
pytest --cov=src --cov-report=html
```

### Test Categories

1. **Unit Tests**: Individual component testing
2. **Integration Tests**: End-to-end workflow testing
3. **Performance Tests**: Scalability and benchmark testing
4. **Quality Assurance Tests**: Hallucination detection and validation
5. **Security Tests**: Adversarial testing and input validation

### Performance Benchmarks

| Component | Max Time | Memory Limit |
|-----------|----------|--------------|
| XML Parsing | 5s | 50MB |
| Medical Summarization | 10s | 100MB |
| Research Correlation | 15s | 150MB |
| Quality Assurance | 10s | 75MB |
| Complete Workflow | 45s | 300MB |

## 🔒 Security & Compliance

### HIPAA Compliance

- **Audit Logging**: Complete audit trail for all operations
- **Data Encryption**: Encrypted data transmission and storage
- **Access Controls**: Role-based access to patient data
- **Data Minimization**: Only necessary data is processed
- **Secure Disposal**: Automatic cleanup of temporary data

### Security Features

- **Input Validation**: Comprehensive input sanitization
- **XML Security**: Protection against XXE and injection attacks
- **Hallucination Prevention**: AI output validation and filtering
- **Error Handling**: Secure error messages without data leakage
- **Rate Limiting**: Protection against abuse

### Quality Assurance

- **Multi-Layer Validation**: Data, medical, and output validation
- **Confidence Scoring**: Reliability metrics for all outputs
- **Hallucination Detection**: AI-generated content verification
- **Medical Accuracy**: Validation against medical knowledge bases
- **Continuous Monitoring**: Real-time quality metrics

## 📈 Monitoring & Observability

### Metrics Collection

The system collects comprehensive metrics:

```python
# Workflow statistics
stats = workflow.get_workflow_statistics()
print(f"Success Rate: {stats['successful_workflows'] / stats['total_workflows']}")
print(f"Average Processing Time: {stats['average_processing_time']}")

# Quality assurance metrics
qa_stats = qa_engine.get_quality_statistics()
print(f"Quality Distribution: {qa_stats['quality_distribution']}")

# Performance metrics
perf_stats = performance_monitor.get_statistics()
print(f"Memory Usage: {perf_stats['peak_memory_usage']}")
```

### Logging

Structured logging with multiple levels:

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Audit logging
audit_logger.log_patient_access(
    patient_id="P12345",
    operation="analysis_complete",
    component="main_workflow"
)
```

## 🚀 Deployment

### Docker Deployment

```bash
# Build images
docker-compose build

# Run system
docker-compose up -d

# Scale agents
docker-compose up --scale medical-summarizer=3
```

### AWS Deployment

```bash
# Deploy to AWS Lambda
sam build
sam deploy --guided

# Deploy to ECS
aws ecs create-cluster --cluster-name medical-analysis
aws ecs create-service --cluster medical-analysis --service-name analysis-service
```

### Production Configuration

```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  medical-analysis:
    image: medical-analysis:latest
    environment:
      - LOG_LEVEL=WARNING
      - ENABLE_PERFORMANCE_MONITORING=true
      - QUALITY_ASSURANCE_STRICT_MODE=true
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 1G
          cpus: '0.5'
```

## 🔧 Troubleshooting

### Common Issues

1. **AWS Credentials Error**
   ```bash
   # Verify credentials
   aws sts get-caller-identity
   
   # Configure credentials
   aws configure
   ```

2. **S3 Access Denied**
   ```bash
   # Check bucket permissions
   aws s3 ls s3://your-bucket-name
   
   # Update IAM policy
   aws iam attach-user-policy --user-name your-user --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
   ```

3. **Quality Assurance Failures**
   ```python
   # Check quality thresholds
   qa_stats = qa_engine.get_quality_statistics()
   
   # Adjust thresholds if needed
   qa_engine.quality_thresholds['acceptable'] = 0.6
   ```

4. **Performance Issues**
   ```bash
   # Run performance tests
   pytest -m performance
   
   # Monitor system resources
   python -c "import psutil; print(f'CPU: {psutil.cpu_percent()}%, Memory: {psutil.virtual_memory().percent}%')"
   ```

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Run with detailed output
python src/main.py --debug --patient "Test Patient"
```

## 📚 API Reference

### Main Workflow

```python
class MainWorkflow:
    async def execute_complete_analysis(self, patient_name: str) -> AnalysisReport
    def get_workflow_statistics(self) -> Dict[str, Any]
    def get_workflow_status(self) -> Dict[str, Any]
    async def cancel_workflow(self) -> bool
```

### Quality Assurance

```python
class QualityAssuranceEngine:
    def assess_analysis_quality(self, report: AnalysisReport) -> QualityAssessment
    def get_quality_statistics(self) -> Dict[str, Any]

class HallucinationPreventionSystem:
    def check_content(self, content: str, content_type: str) -> HallucinationCheck
    def get_prevention_statistics(self) -> Dict[str, Any]
```

## 🤝 Contributing

### Development Setup

```bash
# Clone repository
git clone <repository-url>
cd medical-record-analysis

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies (in the same virtual environment)
python3 -m pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install
```

### Code Standards

- **Python Style**: Follow PEP 8 with Black formatting
- **Type Hints**: Use type hints for all functions
- **Documentation**: Comprehensive docstrings for all classes and methods
- **Testing**: Minimum 90% test coverage
- **Security**: Security review for all changes

### Pull Request Process

1. Create feature branch from `main`
2. Implement changes with tests
3. Run full test suite: `pytest`
4. Update documentation
5. Submit pull request with detailed description

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For support and questions:

- **Documentation**: Check this README and inline documentation
- **Issues**: Create GitHub issues for bugs and feature requests
- **Security**: Report security issues privately to security@company.com
- **Performance**: Use performance benchmarks to identify bottlenecks

## 🔄 Changelog

### Version 1.0.0 (Current)

- ✅ Complete multi-agent medical analysis system
- ✅ HIPAA-compliant audit logging
- ✅ Comprehensive quality assurance
- ✅ Hallucination prevention system
- ✅ Performance benchmarking
- ✅ Docker containerization
- ✅ AWS integration

### Planned Features

- 🔄 Real-time processing dashboard
- 🔄 Advanced ML model integration
- 🔄 Multi-language support
- 🔄 Enhanced research correlation
- 🔄 Automated report generation improvements

---

**⚠️ Important**: This system processes medical data. Ensure compliance with all applicable healthcare regulations (HIPAA, GDPR, etc.) in your jurisdiction before deployment.