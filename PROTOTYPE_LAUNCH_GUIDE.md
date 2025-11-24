# 🏥 Medical Record Analysis System - Prototype Launch Guide

This guide will help you quickly launch and test the Medical Record Analysis System prototype.

## ⚠️ Important: AWS Requirements

The prototype launcher (`launch_prototype.py`) requires:
- **Real AWS credentials** configured
- **Actual S3 bucket** with patient records
- **Network access** to AWS services

**For testing without AWS**, use the test suite instead:
```bash
pytest tests/  # Uses mocked AWS services
```

## 🚀 Quick Start (4 Steps)

### Step 1: Install Dependencies

```bash
# Create and activate virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
# venv\Scripts\activate  # On Windows

# Install Python dependencies
python3 -m pip install -r requirements.txt
```

### Step 2: Configure AWS Credentials

#### Option A: AWS SSO (Recommended for SSO users)

```bash
# Use the helper script (easiest method)
./run_with_sso.sh default

# Or manually:
aws sso login --profile default
export AWS_PROFILE=default
export AWS_SDK_LOAD_CONFIG=1
python launch_prototype.py
```

**📖 For detailed SSO setup, see [AWS_SSO_SETUP.md](AWS_SSO_SETUP.md)**

#### Option B: Standard AWS Credentials

```bash
# Option 1: Use AWS CLI
aws configure
# Enter your AWS Access Key ID, Secret Access Key, and region (us-east-1)

# Option 2: Set environment variables
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1

# Verify credentials
aws sts get-caller-identity
```

### Step 3: Setup Test Data

```bash
# View available test patients
python setup_test_data.py
```

### Step 4: Launch Prototype

```bash
# Launch the system
python launch_prototype.py
```

## 📋 Available Test Patients

The prototype comes with pre-configured test patients:

| Patient Name | Description | Medical Conditions |
|--------------|-------------|-------------------|
| **John Doe** | 45-year-old male | Diabetes, Hypertension |
| **Jane Smith** | 58-year-old female | Breast Cancer, Depression |
| **Bob Johnson** | 33-year-old male | Asthma |
| **Test Patient** | Sample patient | Diabetes, Hypertension |
| **Demo Patient** | Demo patient | Diabetes, Hypertension |

## 🎯 How to Test

1. **Launch the system**: `python launch_prototype.py`
2. **Enter a patient name** when prompted (e.g., "John Doe")
3. **Watch the analysis progress** through 7 steps:
   - Patient Name Input
   - XML Parsing & Data Extraction
   - Medical Summarization
   - Research Correlation
   - Report Generation
   - Quality Assurance & Validation
   - Report Persistence
4. **Review the results** including:
   - Patient demographics
   - Medical summary
   - Key conditions identified
   - Research findings
   - Quality assessment scores

## 🔧 Alternative Launch Methods

### Method 1: Direct Python Execution

```bash
# Run the main application directly
python src/main.py
```

### Method 2: Using the CLI Module

```bash
# Run using Python module syntax
python -m src.main
```

### Method 3: Interactive Python Session

```python
import asyncio
from src.main import main_async

# Run in interactive Python
asyncio.run(main_async())
```

## 🧪 Testing Different Scenarios

### Test Normal Operation
```bash
python launch_prototype.py
# Enter: "John Doe"
```

### Test Complex Medical Case
```bash
python launch_prototype.py
# Enter: "Jane Smith"
```

### Test Minimal Data
```bash
python launch_prototype.py
# Enter: "Bob Johnson"
```

### Test Error Handling
```bash
python launch_prototype.py
# Enter: "Nonexistent Patient"
```

## 📊 What You'll See

### 1. Welcome Screen
```
🏥 Medical Record Analysis System
=====================================
Welcome to the Medical Record Analysis System!
This system analyzes patient medical records and provides comprehensive insights.
```

### 2. Progress Tracking
```
🔍 Analyzing patient: John Doe
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% Complete

✅ Step 1/7: Patient Name Input (0.1s)
✅ Step 2/7: XML Parsing & Data Extraction (2.3s)
✅ Step 3/7: Medical Summarization (3.1s)
✅ Step 4/7: Research Correlation (5.2s)
✅ Step 5/7: Report Generation (1.8s)
✅ Step 6/7: Quality Assurance & Validation (2.1s)
✅ Step 7/7: Report Persistence (0.9s)
```

### 3. Analysis Results
```
📋 Analysis Results for John Doe
================================

👤 Patient Information:
   • Name: John Doe
   • Age: 45
   • Gender: Male
   • Patient ID: TEST_P001

🏥 Medical Summary:
   • Key Conditions: Type 2 diabetes mellitus, Essential hypertension
   • Medications: Metformin, Lisinopril, Atorvastatin
   • Summary: Patient has well-controlled type 2 diabetes and hypertension...

🔬 Research Analysis:
   • Research Findings: 3 relevant studies found
   • Analysis Confidence: 85%
   • Key Insights: Early intervention improves outcomes...

✅ Quality Assessment:
   • Quality Level: Good
   • Overall Score: 0.87
   • Hallucination Risk: 0.12 (Low)
```

## 🛠️ Troubleshooting

### Common Issues

#### 1. Import Errors
```bash
# Error: ModuleNotFoundError: No module named 'src'
# Solution: Make sure you're in the project root directory
cd /path/to/medical-record-analysis
python launch_prototype.py
```

#### 2. Missing Dependencies
```bash
# Error: ModuleNotFoundError: No module named 'boto3'
# Solution: Create virtual environment and install dependencies
python3 -m venv venv
source venv/bin/activate
python3 -m pip install -r requirements.txt

# Error: externally-managed-environment (Homebrew Python)
# Solution: Use virtual environment (recommended) or use --break-system-packages flag
python3 -m venv venv
source venv/bin/activate
python3 -m pip install -r requirements.txt
```

#### 3. AWS Credentials Issues

**Error: "Invalid AWS Access Key ID"**
```bash
# If using AWS SSO, your session may have expired
# Solution: Re-login and use the helper script
aws sso login --profile default
./run_with_sso.sh default

# Or set environment variables manually
export AWS_PROFILE=default
export AWS_SDK_LOAD_CONFIG=1
python launch_prototype.py
```

**See [AWS_SSO_SETUP.md](AWS_SSO_SETUP.md) for detailed troubleshooting**

#### 4. Patient Not Found
```bash
# Error: Patient record not found
# Solution: Use one of the available test patients:
# "John Doe", "Jane Smith", "Bob Johnson", "Test Patient", "Demo Patient"
```

### Debug Mode

For detailed debugging information:

```bash
# Set debug environment variable
export LOG_LEVEL=DEBUG

# Launch with debug output
python launch_prototype.py
```

### Verbose Testing

```bash
# Run with verbose output
python -c "
import asyncio
import os
os.environ['LOG_LEVEL'] = 'DEBUG'
from src.main import main_async
asyncio.run(main_async())
"
```

## 🔍 System Validation

### Performance Testing
The system should complete analysis within these timeframes:
- **XML Parsing**: < 5 seconds
- **Medical Summarization**: < 10 seconds
- **Research Correlation**: < 15 seconds
- **Quality Assurance**: < 10 seconds
- **Total Workflow**: < 45 seconds

### Quality Validation
Expected quality metrics:
- **Quality Level**: Good or Excellent
- **Overall Score**: > 0.70
- **Hallucination Risk**: < 0.30

### Feature Validation
✅ **Core Features to Test**:
- Patient data extraction from XML
- Medical condition identification
- Medication list generation
- Research correlation
- Quality assurance validation
- Hallucination prevention
- Audit logging
- Error handling

## 📈 Advanced Testing

### Batch Testing
```python
# Test multiple patients
import asyncio
from src.workflow.main_workflow import MainWorkflow

async def test_batch():
    workflow = MainWorkflow()
    patients = ["John Doe", "Jane Smith", "Bob Johnson"]
    
    for patient in patients:
        try:
            result = await workflow.execute_complete_analysis(patient)
            print(f"✅ {patient}: Success")
        except Exception as e:
            print(f"❌ {patient}: {e}")

asyncio.run(test_batch())
```

### Performance Benchmarking
```bash
# Run performance tests
python -m pytest tests/test_performance_benchmarks.py -v
```

### Quality Assurance Testing
```bash
# Run QA tests
python -m pytest tests/test_quality_assurance.py -v
```

## 🎉 Success Indicators

You'll know the prototype is working correctly when you see:

1. ✅ **System starts without errors**
2. ✅ **Patient analysis completes all 7 steps**
3. ✅ **Quality assessment shows "Good" or "Excellent"**
4. ✅ **Medical conditions are accurately identified**
5. ✅ **Research findings are relevant**
6. ✅ **No critical hallucination risks detected**
7. ✅ **Audit logs are generated**

## 🔄 Next Steps

After testing the prototype:

1. **Review the generated reports** in the logs
2. **Test different patient scenarios**
3. **Examine the quality assessment results**
4. **Check the audit logs for compliance**
5. **Explore the research correlations**

## 📞 Support

If you encounter issues:

1. **Check the troubleshooting section** above
2. **Review the logs** for detailed error information
3. **Verify test patient names** are spelled correctly
4. **Ensure all dependencies** are installed
5. **Run from the project root directory**

---

**🏥 Ready to test? Run `python launch_prototype.py` and enter "John Doe" when prompted!**