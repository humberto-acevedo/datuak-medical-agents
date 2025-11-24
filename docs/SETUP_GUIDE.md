# Medical Record Analysis System - Setup Guide

This comprehensive guide will walk you through setting up the Medical Record Analysis System from development to production deployment.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Development Setup](#development-setup)
3. [Configuration](#configuration)
4. [Testing Setup](#testing-setup)
5. [Production Deployment](#production-deployment)
6. [Troubleshooting](#troubleshooting)

## 🔧 Prerequisites

### System Requirements

- **Operating System**: Linux, macOS, or Windows 10+
- **Python**: 3.9 or higher
- **Memory**: Minimum 4GB RAM (8GB recommended)
- **Storage**: 2GB free space
- **Network**: Internet access for AWS services and research APIs

### Required Accounts & Services

1. **AWS Account** with the following services:
   - S3 (Simple Storage Service)
   - IAM (Identity and Access Management)
   - CloudWatch (optional, for monitoring)

2. **Development Tools**:
   - Git
   - Docker (optional, for containerized deployment)
   - IDE/Editor (VS Code, PyCharm, etc.)

## 🚀 Development Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd medical-record-analysis
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
# Create and activate virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
# venv\Scripts\activate  # On Windows

# Install production dependencies
python3 -m pip install -r requirements.txt

# Install development dependencies (optional)
python3 -m pip install -r requirements-dev.txt
```

**Note**: Using a virtual environment is strongly recommended, especially on macOS with Homebrew Python, to avoid `externally-managed-environment` errors.

### 4. Verify Installation

```bash
# Check Python version
python --version

# Verify key packages
python -c "import boto3, pytest, asyncio; print('All packages installed successfully')"
```

## ⚙️ Configuration

### 1. AWS Configuration

#### Create IAM User

1. Log into AWS Console
2. Navigate to IAM → Users → Create User
3. Create user with programmatic access
4. Attach the following policies:
   - `AmazonS3FullAccess` (or custom S3 policy)
   - `CloudWatchLogsFullAccess` (optional)

#### Configure AWS Credentials

**Option A: Environment Variables**
```bash
export AWS_ACCESS_KEY_ID=your_access_key_here
export AWS_SECRET_ACCESS_KEY=your_secret_key_here
export AWS_DEFAULT_REGION=us-east-1
```

**Option B: AWS CLI Configuration**
```bash
# Install AWS CLI
python3 -m pip install awscli

# Configure credentials
aws configure
```

**Option C: Credentials File**
Create `~/.aws/credentials`:
```ini
[default]
aws_access_key_id = your_access_key_here
aws_secret_access_key = your_secret_key_here
region = us-east-1
```

### 2. S3 Bucket Setup

#### Create S3 Bucket

```bash
# Create bucket (replace with your bucket name)
aws s3 mb s3://your-medical-records-bucket --region us-east-1

# Verify bucket creation
aws s3 ls
```

#### Configure Bucket Policy

Create a bucket policy for secure access:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "MedicalRecordsAccess",
            "Effect": "Allow",
            "Principal": {
                "AWS": "arn:aws:iam::YOUR_ACCOUNT_ID:user/YOUR_USERNAME"
            },
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::your-medical-records-bucket",
                "arn:aws:s3:::your-medical-records-bucket/*"
            ]
        }
    ]
}
```

#### Upload Sample Data

```bash
# Create sample patient XML file
mkdir -p sample_data
cat > sample_data/john_doe.xml << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<patient_record>
    <demographics>
        <patient_id>SAMPLE_001</patient_id>
        <name>John Doe</name>
        <age>45</age>
        <gender>Male</gender>
    </demographics>
    <medical_history>
        <diagnoses>
            <diagnosis>
                <code>E11.9</code>
                <description>Type 2 diabetes mellitus</description>
                <status>Active</status>
            </diagnosis>
        </diagnoses>
    </medical_history>
</patient_record>
EOF

# Upload to S3
aws s3 cp sample_data/john_doe.xml s3://your-medical-records-bucket/patients/john_doe.xml
```

### 3. Environment Configuration

Create `.env` file in project root:

```bash
# AWS Configuration
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
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

# Quality Assurance Configuration
QA_QUALITY_THRESHOLD_EXCELLENT=0.95
QA_QUALITY_THRESHOLD_GOOD=0.85
QA_QUALITY_THRESHOLD_ACCEPTABLE=0.70
QA_HALLUCINATION_THRESHOLD_LOW=0.2
QA_HALLUCINATION_THRESHOLD_MEDIUM=0.5
QA_HALLUCINATION_THRESHOLD_HIGH=0.8
```

### 4. Load Environment Variables

**Option A: Using python-dotenv**
```bash
python3 -m pip install python-dotenv
```

Add to your Python code:
```python
from dotenv import load_dotenv
load_dotenv()
```

**Option B: Manual Export**
```bash
# Load environment variables
source .env
```

## 🧪 Testing Setup

### 1. Install Test Dependencies

```bash
python3 -m pip install pytest pytest-cov pytest-asyncio pytest-mock
```

### 2. Configure Test Environment

Create `tests/.env.test`:
```bash
# Test Configuration
AWS_ACCESS_KEY_ID=test_key
AWS_SECRET_ACCESS_KEY=test_secret
AWS_DEFAULT_REGION=us-east-1
S3_BUCKET_NAME=test-bucket
LOG_LEVEL=DEBUG
ENABLE_AUDIT_LOGGING=false
```

### 3. Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test categories
pytest -m integration
pytest -m performance
pytest -m quality_assurance

# Run tests with verbose output
pytest -v

# Run tests in parallel
pytest -n auto
```

### 4. Test Configuration

Create `pytest.ini`:
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
markers =
    integration: Integration tests
    performance: Performance benchmark tests
    quality_assurance: Quality assurance tests
    slow: Slow running tests
addopts = 
    --strict-markers
    --disable-warnings
    --tb=short
asyncio_mode = auto
```

## 🏭 Production Deployment

### 1. Docker Deployment

#### Build Docker Images

```bash
# Build main application image
docker build -t medical-analysis:latest .

# Build with specific tag
docker build -t medical-analysis:v1.0.0 .
```

#### Docker Compose Setup

Create `docker-compose.prod.yml`:
```yaml
version: '3.8'

services:
  medical-analysis:
    image: medical-analysis:latest
    environment:
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION}
      - S3_BUCKET_NAME=${S3_BUCKET_NAME}
      - LOG_LEVEL=WARNING
      - ENABLE_AUDIT_LOGGING=true
      - QUALITY_ASSURANCE_STRICT_MODE=true
    ports:
      - "8000:8000"
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 1G
          cpus: '0.5'
        reservations:
          memory: 512M
          cpus: '0.25'
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8000/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.1'
    restart: unless-stopped

networks:
  default:
    driver: bridge
```

#### Deploy with Docker Compose

```bash
# Deploy production stack
docker-compose -f docker-compose.prod.yml up -d

# Scale services
docker-compose -f docker-compose.prod.yml up -d --scale medical-analysis=5

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Stop services
docker-compose -f docker-compose.prod.yml down
```

### 2. AWS Lambda Deployment

#### Install SAM CLI

```bash
# Install SAM CLI
python3 -m pip install aws-sam-cli

# Verify installation
sam --version
```

#### Create SAM Template

Create `template.yaml`:
```yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31

Globals:
  Function:
    Timeout: 300
    MemorySize: 1024
    Runtime: python3.9
    Environment:
      Variables:
        S3_BUCKET_NAME: !Ref MedicalRecordsBucket
        LOG_LEVEL: INFO
        ENABLE_AUDIT_LOGGING: true

Resources:
  MedicalAnalysisFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: src/
      Handler: lambda_handler.lambda_handler
      Events:
        Api:
          Type: Api
          Properties:
            Path: /analyze
            Method: post
      Policies:
        - S3FullAccessPolicy:
            BucketName: !Ref MedicalRecordsBucket
        - CloudWatchLogsFullAccess

  MedicalRecordsBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !Sub "${AWS::StackName}-medical-records"
      VersioningConfiguration:
        Status: Enabled
      PublicAccessBlockConfiguration:
        BlockPublicAcls: true
        BlockPublicPolicy: true
        IgnorePublicAcls: true
        RestrictPublicBuckets: true

Outputs:
  ApiEndpoint:
    Description: "API Gateway endpoint URL"
    Value: !Sub "https://${ServerlessRestApi}.execute-api.${AWS::Region}.amazonaws.com/Prod/analyze"
  
  S3Bucket:
    Description: "S3 bucket for medical records"
    Value: !Ref MedicalRecordsBucket
```

#### Deploy to AWS Lambda

```bash
# Build SAM application
sam build

# Deploy with guided setup
sam deploy --guided

# Deploy with parameters
sam deploy --parameter-overrides ParameterKey=Environment,ParameterValue=prod
```

### 3. ECS Deployment

#### Create ECS Task Definition

Create `ecs-task-definition.json`:
```json
{
    "family": "medical-analysis",
    "networkMode": "awsvpc",
    "requiresCompatibilities": ["FARGATE"],
    "cpu": "1024",
    "memory": "2048",
    "executionRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskExecutionRole",
    "taskRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskRole",
    "containerDefinitions": [
        {
            "name": "medical-analysis",
            "image": "your-account.dkr.ecr.us-east-1.amazonaws.com/medical-analysis:latest",
            "portMappings": [
                {
                    "containerPort": 8000,
                    "protocol": "tcp"
                }
            ],
            "environment": [
                {
                    "name": "AWS_DEFAULT_REGION",
                    "value": "us-east-1"
                },
                {
                    "name": "LOG_LEVEL",
                    "value": "INFO"
                }
            ],
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": "/ecs/medical-analysis",
                    "awslogs-region": "us-east-1",
                    "awslogs-stream-prefix": "ecs"
                }
            }
        }
    ]
}
```

#### Deploy to ECS

```bash
# Create ECS cluster
aws ecs create-cluster --cluster-name medical-analysis-cluster

# Register task definition
aws ecs register-task-definition --cli-input-json file://ecs-task-definition.json

# Create service
aws ecs create-service \
    --cluster medical-analysis-cluster \
    --service-name medical-analysis-service \
    --task-definition medical-analysis:1 \
    --desired-count 2 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[subnet-12345],securityGroups=[sg-12345],assignPublicIp=ENABLED}"
```

## 🔍 Monitoring & Observability

### 1. CloudWatch Setup

#### Create Log Groups

```bash
# Create log group for application logs
aws logs create-log-group --log-group-name /medical-analysis/application

# Create log group for audit logs
aws logs create-log-group --log-group-name /medical-analysis/audit
```

#### Configure CloudWatch Metrics

```python
import boto3

cloudwatch = boto3.client('cloudwatch')

# Put custom metric
cloudwatch.put_metric_data(
    Namespace='MedicalAnalysis',
    MetricData=[
        {
            'MetricName': 'WorkflowSuccess',
            'Value': 1,
            'Unit': 'Count'
        }
    ]
)
```

### 2. Health Checks

Create `src/health_check.py`:
```python
from fastapi import FastAPI
from src.workflow.main_workflow import MainWorkflow

app = FastAPI()

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Basic system checks
        workflow = MainWorkflow()
        stats = workflow.get_workflow_statistics()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "stats": stats
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/metrics")
async def metrics():
    """Prometheus-style metrics endpoint."""
    workflow = MainWorkflow()
    stats = workflow.get_workflow_statistics()
    
    metrics = []
    metrics.append(f"medical_analysis_total_workflows {stats.get('total_workflows', 0)}")
    metrics.append(f"medical_analysis_successful_workflows {stats.get('successful_workflows', 0)}")
    metrics.append(f"medical_analysis_failed_workflows {stats.get('failed_workflows', 0)}")
    
    return "\n".join(metrics)
```

## 🔧 Troubleshooting

### Common Issues

#### 1. AWS Credentials Not Found

**Error**: `NoCredentialsError: Unable to locate credentials`

**Solutions**:
```bash
# Check AWS configuration
aws configure list

# Verify credentials
aws sts get-caller-identity

# Set environment variables
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
```

#### 2. S3 Access Denied

**Error**: `ClientError: An error occurred (AccessDenied) when calling the GetObject operation`

**Solutions**:
```bash
# Check bucket permissions
aws s3 ls s3://your-bucket-name

# Test bucket access
aws s3 cp test.txt s3://your-bucket-name/test.txt

# Update IAM policy
aws iam attach-user-policy --user-name your-user --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
```

#### 3. Quality Assurance Failures

**Error**: `ReportError: Report failed quality assurance`

**Solutions**:
```python
# Check quality thresholds
from src.utils.quality_assurance import get_quality_assurance_engine
qa_engine = get_quality_assurance_engine()
stats = qa_engine.get_quality_statistics()
print(stats)

# Adjust thresholds
qa_engine.quality_thresholds['acceptable'] = 0.6

# Check hallucination prevention
from src.utils.hallucination_prevention import get_hallucination_prevention_system
hp_system = get_hallucination_prevention_system()
hp_stats = hp_system.get_prevention_statistics()
print(hp_stats)
```

#### 4. Performance Issues

**Error**: Slow processing or timeouts

**Solutions**:
```bash
# Run performance tests
pytest -m performance

# Check system resources
python -c "import psutil; print(f'CPU: {psutil.cpu_percent()}%, Memory: {psutil.virtual_memory().percent}%')"

# Increase timeout settings
export WORKFLOW_TIMEOUT_SECONDS=600
export XML_PARSING_TIMEOUT=30
```

#### 5. Docker Issues

**Error**: Container fails to start

**Solutions**:
```bash
# Check Docker logs
docker logs container_name

# Verify image
docker images

# Test container locally
docker run -it --rm medical-analysis:latest /bin/bash

# Check environment variables
docker run --rm medical-analysis:latest env
```

### Debug Mode

Enable debug mode for detailed troubleshooting:

```bash
# Set debug environment
export LOG_LEVEL=DEBUG
export ENABLE_DEBUG_MODE=true

# Run with debug output
python src/main.py --debug --patient "Test Patient"
```

### Log Analysis

```bash
# View application logs
tail -f logs/application.log

# Search for errors
grep -i error logs/application.log

# Analyze audit logs
grep "patient_access" logs/audit.log | jq '.'
```

## 📞 Support

If you encounter issues not covered in this guide:

1. **Check Documentation**: Review README.md and inline code documentation
2. **Search Issues**: Look for similar issues in the project repository
3. **Create Issue**: Submit detailed bug report with logs and configuration
4. **Contact Support**: Reach out to the development team

## 🔄 Updates

Keep your system updated:

```bash
# Pull latest changes
git pull origin main

# Update dependencies
python3 -m pip install -r requirements.txt --upgrade

# Run tests after updates
pytest

# Rebuild Docker images
docker build -t medical-analysis:latest .
```

---

This setup guide should get you up and running with the Medical Record Analysis System. For additional help, refer to the main README.md or contact the development team.