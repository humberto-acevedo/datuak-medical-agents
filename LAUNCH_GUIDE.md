# Launch Guide - Medical Record Analysis System

## Quick Start

### Option 1: Python Agents (Original)

```bash
# Launch with Python-based agents
python launch_prototype.py

# Or explicitly specify Python mode
python launch_prototype.py --python
```

### Option 2: AWS Bedrock Claude AI (New)

```bash
# Launch with Bedrock Claude AI
python launch_prototype.py --bedrock
```

## Comparison

| Feature | Python Agents | Bedrock Claude |
|---------|--------------|----------------|
| **Command** | `python launch_prototype.py` | `python launch_prototype.py --bedrock` |
| **Medical Analysis** | Python algorithms | Claude 3 Sonnet AI |
| **Research** | Simulated database | Evidence-based with citations |
| **Cost** | Infrastructure only | ~$0.03 per analysis |
| **Speed** | ~30-60 seconds | ~45-90 seconds |
| **Quality** | Rule-based | AI-powered |
| **Requirements** | AWS S3 only | AWS S3 + Bedrock access |

## Prerequisites

### Both Versions Require

1. **AWS Credentials**
   ```bash
   aws configure
   # Or set environment variables
   export AWS_ACCESS_KEY_ID=your_key
   export AWS_SECRET_ACCESS_KEY=your_secret
   export AWS_DEFAULT_REGION=us-east-1
   ```

2. **S3 Bucket** with patient XML files
   - Default: `patient-records-20251024`
   - Region: `us-east-1`

3. **Python Dependencies**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

### Bedrock Version Additionally Requires

4. **Bedrock Model Access**
   - Go to AWS Console → Bedrock → Model Access
   - Enable Claude 3 Sonnet
   - Enable Claude 3 Haiku (optional)

## Usage Examples

### Basic Usage

```bash
# Python agents
python launch_prototype.py

# Bedrock Claude
python launch_prototype.py --bedrock
```

### With Verbose Output

```bash
# Show credential diagnostics
python launch_prototype.py --verbose

# Bedrock with verbose
python launch_prototype.py --bedrock --verbose
```

### Testing Workflow

```bash
# 1. Test Python agents first
python launch_prototype.py
# Enter: Jane Smith

# 2. Test Bedrock version
python launch_prototype.py --bedrock
# Enter: Jane Smith

# 3. Compare results
```

## What Each Version Does

### Python Agents Version

```
1. Parse XML from S3 (CDA support)
2. Extract conditions using Python algorithms
3. Generate summary using Python templates
4. Correlate with simulated research database
5. Generate report
6. Save to S3
7. Display in CLI
```

### Bedrock Claude Version

```
1. Parse XML from S3 (CDA support)
2. Send patient data to Claude → Medical Summary
3. Send summary to Claude → Research Analysis
4. Generate comprehensive report
5. Save to S3
6. Display in CLI
```

## Output Comparison

### Python Agents Output

```
MEDICAL SUMMARY
- Structured summary with sections
- Key conditions extracted
- Medication list
- Procedure summary

RESEARCH CORRELATION
- Simulated research papers
- Basic relevance scoring
- Generic recommendations
```

### Bedrock Claude Output

```
MEDICAL SUMMARY
- Comprehensive narrative analysis
- Clinical context and significance
- Detailed medication evaluation
- Overall health assessment

RESEARCH-BASED ANALYSIS
- Evidence-based clinical context
- Treatment evaluation vs guidelines
- Risk assessment with data
- Specific clinical guideline citations
- Research-backed recommendations
```

## Troubleshooting

### Python Agents Issues

**Problem**: Import errors
```bash
# Solution: Install dependencies
pip install -r requirements.txt
```

**Problem**: S3 access denied
```bash
# Solution: Check AWS credentials
aws s3 ls s3://patient-records-20251024/
```

### Bedrock Issues

**Problem**: `AccessDeniedException` from Bedrock
```bash
# Solution: Enable model access in AWS Console
# AWS Console → Bedrock → Model Access → Enable Claude 3
```

**Problem**: `ModelNotFound` error
```bash
# Solution: Verify region is us-east-1
export AWS_DEFAULT_REGION=us-east-1
```

**Problem**: High latency
```bash
# Solution: This is normal for Bedrock (API calls)
# Expect 45-90 seconds for complete analysis
```

## Cost Estimates

### Python Agents
- **AWS Costs**: S3 storage + data transfer only
- **Per Analysis**: ~$0.001 (S3 operations)
- **1,000 analyses**: ~$1

### Bedrock Claude
- **AWS Costs**: S3 + Bedrock API calls
- **Per Analysis**: ~$0.03 (Sonnet) or ~$0.003 (Haiku)
- **1,000 analyses**: ~$30 (Sonnet) or ~$3 (Haiku)

## Environment Variables

```bash
# Required
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=us-east-1

# Optional
export S3_BUCKET_NAME=patient-records-20251024
export LOG_LEVEL=INFO
export AWS_PROFILE=your_profile

# Bedrock-specific (optional)
export BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
```

## Command Line Options

```bash
python launch_prototype.py [OPTIONS]

Options:
  -v, --verbose    Show credential diagnostics
  --bedrock        Use AWS Bedrock Claude AI
  --python         Use Python-based agents (default)
  -h, --help       Show help message
```

## Examples

### Test Both Versions

```bash
# Test Python version
python launch_prototype.py
# Enter: Jane Smith
# Note the output

# Test Bedrock version
python launch_prototype.py --bedrock
# Enter: Jane Smith
# Compare the output quality
```

### Production Usage

```bash
# For production, use Bedrock for better quality
python launch_prototype.py --bedrock

# Or create an alias
alias analyze-patient="python launch_prototype.py --bedrock"
analyze-patient
```

## Next Steps

1. **Test Python Version**
   ```bash
   python launch_prototype.py
   ```

2. **Enable Bedrock Access**
   - AWS Console → Bedrock → Model Access
   - Enable Claude 3 Sonnet

3. **Test Bedrock Version**
   ```bash
   python launch_prototype.py --bedrock
   ```

4. **Compare Results**
   - Review quality differences
   - Evaluate cost vs benefit
   - Choose version for production

5. **Deploy to Production**
   - See `BEDROCK_IMPLEMENTATION.md` for deployment guide
   - See `DEPLOYMENT_STATUS.md` for infrastructure setup

## Support

For issues:
- **Python Agents**: Check logs in `logs/` directory
- **Bedrock**: Check CloudWatch Logs for Bedrock API errors
- **AWS**: Verify credentials with `aws sts get-caller-identity`
- **S3**: Verify bucket access with `aws s3 ls s3://your-bucket/`

## Documentation

- **`BEDROCK_IMPLEMENTATION.md`** - Complete Bedrock documentation
- **`BEDROCK_SUMMARY.md`** - Quick Bedrock reference
- **`DEPLOYMENT_STATUS.md`** - Infrastructure and deployment
- **`README.md`** - Project overview
