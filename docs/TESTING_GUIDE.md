# Medical Record Analysis System - Comprehensive Testing Guide

This guide provides multiple ways to test the Medical Record Analysis System, from quick validation to comprehensive testing.

## 🎯 Quick Status Check

First, let's verify the current system status:

### Current Project Status:
- ✅ **12 out of 14 tasks completed** (85.7%)
- ✅ **Core system fully functional**
- ✅ **All 5 agents implemented and integrated**
- ✅ **Quality assurance and hallucination prevention active**
- ✅ **Comprehensive test suite created**
- ⚠️ **Syntax error in main_workflow.py fixed**
- 🚀 **Ready for testing**

## 📋 Testing Methods

### Method 1: Quick Component Validation (Fastest)

Test individual components to ensure they're working:

```bash
# Test basic imports and component loading
python3 -c "
import sys
sys.path.insert(0, 'src')

print('🏥 Component Validation')
print('=' * 50)

# Test imports
try:
    from src.models import PatientData, MedicalSummary
    print('✅ Data Models: OK')
except Exception as e:
    print(f'❌ Data Models: {e}')

try:
    from src.agents.xml_parser_agent import XMLParserAgent
    print('✅ XML Parser Agent: OK')
except Exception as e:
    print(f'❌ XML Parser Agent: {e}')

try:
    from src.agents.medical_summarization_agent import MedicalSummarizationAgent
    print('✅ Medical Summarization Agent: OK')
except Exception as e:
    print(f'❌ Medical Summarization Agent: {e}')

try:
    from src.agents.research_correlation_agent import ResearchCorrelationAgent
    print('✅ Research Correlation Agent: OK')
except Exception as e:
    print(f'❌ Research Correlation Agent: {e}')

try:
    from src.utils.quality_assurance import initialize_quality_assurance
    print('✅ Quality Assurance: OK')
except Exception as e:
    print(f'❌ Quality Assurance: {e}')

try:
    from src.utils.hallucination_prevention import initialize_hallucination_prevention
    print('✅ Hallucination Prevention: OK')
except Exception as e:
    print(f'❌ Hallucination Prevention: {e}')

print('\\n🎉 Component validation complete!')
"
```

### Method 2: Run Automated Test Suite

Run the comprehensive automated test suite:

```bash
# Run all automated tests
python3 run_tests.py
```

This will test:
- ✅ XML Parser Agent
- ✅ Medical Summarization Agent
- ✅ Research Correlation Agent
- ✅ Quality Assurance System
- ✅ Hallucination Prevention
- ✅ Complete Workflow
- ✅ Error Handling
- ✅ Performance Benchmarks

### Method 3: Interactive Testing

Run the interactive test menu for hands-on testing:

```bash
# Launch interactive testing
python3 interactive_test.py
```

Interactive menu options:
1. Test John Doe (Diabetes patient)
2. Test Jane Smith (Cancer patient)
3. Test Bob Johnson (Asthma patient)
4. Quality Assurance Demo
5. Performance Demo
6. Run All Tests

### Method 4: PyTest Test Suite

Run the comprehensive pytest test suite:

```bash
# Install pytest if needed
pip3 install pytest pytest-asyncio pytest-mock

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test categories
pytest -m integration          # Integration tests
pytest -m performance         # Performance tests
pytest -m quality_assurance   # QA tests

# Run with coverage report
pytest --cov=src --cov-report=html

# Run specific test files
pytest tests/test_quality_assurance.py
pytest tests/test_hallucination_prevention.py
pytest tests/test_integration_comprehensive.py
```

### Method 5: Individual Component Testing

Test specific components in isolation:

#### Test Quality Assurance System:
```bash
python3 -c "
import sys
sys.path.insert(0, 'src')

from src.utils.quality_assurance import initialize_quality_assurance
from src.models import PatientData, MedicalSummary, ResearchAnalysis, AnalysisReport
from datetime import datetime

print('🛡️ Testing Quality Assurance System')
print('=' * 50)

# Initialize QA
qa_engine = initialize_quality_assurance()
print('✅ QA Engine initialized')

# Create test report
patient_data = PatientData(name='Test', patient_id='T001', age=45)
medical_summary = MedicalSummary(
    summary_text='Patient has diabetes',
    key_conditions=[{'name': 'Diabetes', 'confidence_score': 0.9}],
    chronic_conditions=['diabetes'],
    medications=['metformin']
)
research_analysis = ResearchAnalysis(
    research_findings=[],
    analysis_confidence=0.8,
    insights=['Good management'],
    recommendations=['Continue treatment']
)

report = AnalysisReport(
    report_id='TEST001',
    patient_data=patient_data,
    medical_summary=medical_summary,
    research_analysis=research_analysis,
    generated_at=datetime.now()
)

# Assess quality
assessment = qa_engine.assess_analysis_quality(report)
print(f'✅ Quality Level: {assessment.quality_level.value}')
print(f'✅ Overall Score: {assessment.overall_score:.3f}')
print(f'✅ Hallucination Risk: {assessment.hallucination_risk:.3f}')
print('\\n🎉 Quality Assurance test complete!')
"
```

#### Test Hallucination Prevention:
```bash
python3 -c "
import sys
sys.path.insert(0, 'src')

from src.utils.hallucination_prevention import initialize_hallucination_prevention

print('🛡️ Testing Hallucination Prevention')
print('=' * 50)

# Initialize prevention system
prevention = initialize_hallucination_prevention(strict_mode=False)
print('✅ Prevention system initialized')

# Test cases
test_cases = [
    ('Clean', 'Patient has diabetes and takes metformin'),
    ('Suspicious', 'Patient has magical healing powers'),
]

for name, content in test_cases:
    result = prevention.check_content(content, 'general')
    print(f'\\n{name} Content:')
    print(f'  Risk Level: {result.risk_level.value}')
    print(f'  Confidence: {result.confidence:.3f}')

print('\\n🎉 Hallucination prevention test complete!')
"
```

### Method 6: End-to-End Workflow Test

Test the complete workflow with mock data:

```bash
python3 -c "
import sys
import asyncio
from unittest.mock import patch, Mock
sys.path.insert(0, 'src')

async def test_workflow():
    from src.workflow.main_workflow import MainWorkflow
    from tests.fixtures.sample_patient_data import SAMPLE_PATIENT_XML_GOOD
    
    print('🏥 Testing Complete Workflow')
    print('=' * 50)
    
    # Create mock S3 client
    mock_s3 = Mock()
    mock_s3.get_object.return_value = {
        'Body': Mock(read=Mock(return_value=SAMPLE_PATIENT_XML_GOOD.encode('utf-8')))
    }
    mock_s3.put_object.return_value = {'ETag': '\"test\"'}
    
    with patch('src.agents.xml_parser_agent.boto3.client', return_value=mock_s3):
        workflow = MainWorkflow(enable_enhanced_logging=False)
        
        with patch.object(workflow.s3_persister, 'save_analysis_report', return_value='s3://test/report.json'):
            result = await workflow.execute_complete_analysis('John Doe')
            
            print(f'✅ Analysis completed')
            print(f'✅ Patient: {result.patient_data.name}')
            print(f'✅ Conditions: {len(result.medical_summary.key_conditions)}')
            print(f'✅ Quality: {result.processing_metadata[\"quality_assessment\"][\"quality_level\"]}')
            print('\\n🎉 Workflow test complete!')

asyncio.run(test_workflow())
"
```

### Method 7: Performance Testing

Run performance benchmarks:

```bash
# Run performance tests
pytest tests/test_performance_benchmarks.py -v

# Or run the performance demo
python3 -c "
import sys
import asyncio
import time
from unittest.mock import patch, Mock
sys.path.insert(0, 'src')

async def perf_test():
    from src.workflow.main_workflow import MainWorkflow
    from tests.fixtures.sample_patient_data import SAMPLE_PATIENT_XML_GOOD
    
    print('⚡ Performance Test')
    print('=' * 50)
    
    mock_s3 = Mock()
    mock_s3.get_object.return_value = {
        'Body': Mock(read=Mock(return_value=SAMPLE_PATIENT_XML_GOOD.encode('utf-8')))
    }
    mock_s3.put_object.return_value = {'ETag': '\"test\"'}
    
    with patch('src.agents.xml_parser_agent.boto3.client', return_value=mock_s3):
        workflow = MainWorkflow(enable_enhanced_logging=False)
        
        with patch.object(workflow.s3_persister, 'save_analysis_report', return_value='s3://test/report.json'):
            start = time.time()
            result = await workflow.execute_complete_analysis('John Doe')
            duration = time.time() - start
            
            print(f'✅ Execution time: {duration:.2f}s')
            print(f'✅ Target: <60s')
            print(f'✅ Status: {\"PASS\" if duration < 60 else \"FAIL\"}')

asyncio.run(perf_test())
"
```

### Method 8: Security & Adversarial Testing

Test security and hallucination detection:

```bash
python3 -c "
import sys
sys.path.insert(0, 'src')

from src.utils.hallucination_prevention import initialize_hallucination_prevention

print('🔒 Security & Adversarial Testing')
print('=' * 50)

prevention = initialize_hallucination_prevention(strict_mode=False)

# Adversarial test cases
test_cases = [
    ('Fictional Disease', 'Patient has Kryptonian Syndrome from Superman'),
    ('Impossible Scenario', 'Patient has magical healing with unicorn tears'),
    ('Fake Medication', 'Patient takes fictionaldrugamine 500mg'),
    ('Invalid Code', 'Patient diagnosed with XYZ999.ABC'),
    ('Contradiction', 'Patient is asymptomatic but has severe pain'),
]

print('\\nTesting adversarial inputs:')
for name, content in test_cases:
    result = prevention.check_content(content, 'general')
    detected = result.risk_level.value not in ['minimal', 'low']
    status = '✅ DETECTED' if detected else '❌ MISSED'
    print(f'{status} {name}: {result.risk_level.value}')

print('\\n🎉 Security testing complete!')
"
```

### Method 9: Data Validation Testing

Test data models and validation:

```bash
python3 -c "
import sys
sys.path.insert(0, 'src')

from src.models import PatientData, MedicalSummary, ResearchAnalysis, AnalysisReport
from datetime import datetime
import json

print('📊 Data Validation Testing')
print('=' * 50)

# Test PatientData
patient = PatientData(name='John Doe', patient_id='P001', age=45, gender='Male')
assert patient.validate(), 'Patient validation failed'
print('✅ PatientData validation: PASS')

# Test serialization
patient_dict = patient.to_dict()
patient_restored = PatientData.from_dict(patient_dict)
assert patient_restored.patient_id == patient.patient_id
print('✅ PatientData serialization: PASS')

# Test JSON serialization
patient_json = json.dumps(patient_dict)
assert len(patient_json) > 0
print('✅ JSON serialization: PASS')

# Test MedicalSummary
summary = MedicalSummary(
    summary_text='Test summary',
    key_conditions=[{'name': 'Test', 'confidence_score': 0.9}],
    chronic_conditions=['test'],
    medications=['test_med']
)
assert summary.validate(), 'Summary validation failed'
print('✅ MedicalSummary validation: PASS')

print('\\n🎉 Data validation testing complete!')
"
```

### Method 10: Integration Testing with Real Scenarios

Test with realistic patient scenarios:

```bash
# Run integration tests
pytest tests/test_integration_comprehensive.py -v

# Or run specific scenarios
pytest tests/test_integration_comprehensive.py::TestComprehensiveIntegration::test_end_to_end_good_patient_data -v
pytest tests/test_integration_comprehensive.py::TestComprehensiveIntegration::test_end_to_end_complex_patient_data -v
```

## 🐛 Debugging & Troubleshooting

### Check for Syntax Errors:
```bash
# Check Python syntax
python3 -m py_compile src/workflow/main_workflow.py
python3 -m py_compile src/utils/quality_assurance.py
python3 -m py_compile src/utils/hallucination_prevention.py
```

### Check Dependencies:
```bash
# Verify all dependencies are installed
pip3 list | grep -E "boto3|lxml|pydantic|pytest"

# Install missing dependencies
pip3 install -r requirements.txt
```

### View Logs:
```bash
# Check if logs directory exists
ls -la logs/

# View recent logs
tail -f logs/application.log
tail -f logs/audit.log
```

## 📈 Test Coverage Analysis

Generate test coverage report:

```bash
# Install coverage tools
pip3 install pytest-cov coverage

# Run tests with coverage
pytest --cov=src --cov-report=html --cov-report=term

# View coverage report
open htmlcov/index.html  # On macOS
# or
xdg-open htmlcov/index.html  # On Linux
```

## 🎯 Recommended Testing Sequence

For first-time testing, follow this sequence:

1. **Quick Validation** (30 seconds)
   ```bash
   python3 run_tests.py
   ```

2. **Interactive Testing** (5 minutes)
   ```bash
   python3 interactive_test.py
   ```

3. **Full Test Suite** (10 minutes)
   ```bash
   pytest -v
   ```

4. **Performance Testing** (5 minutes)
   ```bash
   pytest tests/test_performance_benchmarks.py -v
   ```

5. **Security Testing** (2 minutes)
   ```bash
   pytest tests/test_hallucination_prevention.py -v
   ```

## 🚀 Next Steps After Testing

Once testing is complete:

1. ✅ Review test results and fix any failures
2. ✅ Check test coverage (aim for >80%)
3. ✅ Review quality assurance metrics
4. ✅ Validate performance benchmarks
5. ✅ Document any issues found
6. 🔄 Move to Task 13: Production Deployment

## 📞 Getting Help

If you encounter issues:

1. Check the error messages carefully
2. Review the SETUP_GUIDE.md for configuration
3. Check the API_REFERENCE.md for usage examples
4. Review test files for working examples
5. Check logs in the `logs/` directory

## 🎉 Success Criteria

Your system is working correctly if:

- ✅ All component imports succeed
- ✅ Automated tests pass (>90%)
- ✅ Quality assurance system validates reports
- ✅ Hallucination prevention detects suspicious content
- ✅ Complete workflow executes successfully
- ✅ Performance meets benchmarks (<60s total)
- ✅ No critical errors in logs

---

**Happy Testing! 🏥✨**