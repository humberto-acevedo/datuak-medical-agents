# Bedrock Claude Implementation

## Overview

This implementation replaces the Python-based medical summarization and research correlation agents with AWS Bedrock Claude AI models. The system now uses Claude 3 Sonnet (or Haiku) for:

1. **Medical Summarization** - Analyzing patient XML data and generating comprehensive medical summaries
2. **Research Analysis** - Providing evidence-based medical analysis with clinical research references

## Architecture

```
┌─────────────────┐
│  Patient Name   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ XML Parser      │ (Unchanged - parses XML from S3)
│ Agent           │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Bedrock Claude  │ ✨ NEW
│ Medical         │ → Generates medical summary
│ Summarizer      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Bedrock Claude  │ ✨ NEW
│ Research        │ → Generates research analysis
│ Analyzer        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ S3 Report       │ (Unchanged - saves to S3)
│ Persister       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ CLI Output      │ → Displays results
└─────────────────┘
```

## New Components

### 1. BedrockClient (`src/utils/bedrock_client.py`)

Core client for interacting with AWS Bedrock Claude models.

**Features**:
- Supports Claude 3 Sonnet and Haiku models
- Automatic retry with exponential backoff
- Token usage tracking
- Error handling for Bedrock API

**Usage**:
```python
from src.utils.bedrock_client import BedrockClient

client = BedrockClient(model_id=BedrockClient.CLAUDE_SONNET)
response = client.invoke_claude(
    prompt="Analyze this medical record...",
    system_prompt="You are a medical analyst..."
)
```

### 2. BedrockMedicalSummarizer (`src/agents/bedrock_medical_summarizer.py`)

Generates medical summaries using Claude.

**Input**: PatientData (from XML parser)
**Output**: Comprehensive medical summary with:
- Narrative summary of medical history
- Key medical conditions
- Current medication regimen
- Notable procedures
- Overall health assessment

**Features**:
- Structured prompts for medical analysis
- Handles large patient records (token management)
- HIPAA-compliant audit logging
- Data quality assessment

### 3. BedrockResearchAnalyzer (`src/agents/bedrock_research_analyzer.py`)

Generates research-based analysis using Claude.

**Input**: Medical summary from first Claude call
**Output**: Evidence-based analysis with:
- Clinical research context
- Evidence-based treatment analysis
- Risk assessment
- Research-backed recommendations
- Clinical guideline references

**Features**:
- Evidence-based medicine focus
- Clinical guideline citations
- Research literature references
- Risk stratification

### 4. BedrockWorkflow (`src/workflow/bedrock_workflow.py`)

Orchestrates the complete Bedrock-based workflow.

**Steps**:
1. Parse XML from S3 (existing XML parser)
2. Generate medical summary with Claude
3. Generate research analysis with Claude
4. Create comprehensive report
5. Persist report to S3
6. Display results in CLI

### 5. Main Entry Point (`src/main_bedrock.py`)

New CLI entry point for Bedrock-based analysis.

## Usage

### Running the Bedrock Analysis

```bash
# Run the Bedrock-based analysis
python -m src.main_bedrock

# Or make it executable
chmod +x src/main_bedrock.py
./src/main_bedrock.py
```

### Example Session

```
================================================================================
  MEDICAL RECORD ANALYSIS SYSTEM
  Powered by AWS Bedrock & Claude AI
================================================================================

Enter patient name: Jane Smith

🔍 Analyzing medical records for: Jane Smith
⏳ This may take a minute...

================================================================================
Starting Bedrock Workflow: BEDROCK_WF_20251124_140530
Patient: Jane Smith
================================================================================

[Step 1/4] Parsing patient XML from S3...
✓ Patient data extracted: MRN-9621
  - Medications: 17
  - Diagnoses: 5
  - Procedures: 3

[Step 2/4] Generating medical summary with Claude...
✓ Medical summary generated (2847 characters)
  - Model: Claude 3 Sonnet
  - Tokens used: {'input_tokens': 1523, 'output_tokens': 712}

[Step 3/4] Generating research analysis with Claude...
✓ Research analysis generated (3421 characters)
  - Model: Claude 3 Sonnet
  - Tokens used: {'input_tokens': 2156, 'output_tokens': 856}

[Step 4/4] Creating and persisting report to S3...
✓ Report saved to S3: analysis-reports/patient-MRN-9621/bedrock-analysis-...

================================================================================
Workflow completed successfully in 45.23s
================================================================================

[Results displayed...]

✅ Analysis completed successfully!
```

## Configuration

### AWS Credentials

Ensure AWS credentials are configured:

```bash
# Option 1: AWS CLI
aws configure

# Option 2: Environment variables
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=us-east-1

# Option 3: IAM role (recommended for EC2/Lambda)
```

### Model Selection

Choose between Claude models:

```python
# Use Sonnet (more capable, slower)
client = BedrockClient(model_id=BedrockClient.CLAUDE_SONNET)

# Use Haiku (faster, more cost-effective)
client = BedrockClient(model_id=BedrockClient.CLAUDE_HAIKU)
```

### Region

Default region is `us-east-1` for HIPAA compliance:

```python
client = BedrockClient(region="us-east-1")
```

## Benefits

### Advantages Over Python Agents

1. **Advanced AI Capabilities**
   - Claude's medical knowledge is extensive and up-to-date
   - Better natural language understanding
   - More nuanced medical analysis

2. **Evidence-Based Analysis**
   - Claude can reference clinical guidelines
   - Cites research literature
   - Provides evidence-graded recommendations

3. **Reduced Maintenance**
   - No need to maintain medical knowledge bases
   - No need to update research databases
   - Claude models are continuously improved by Anthropic

4. **Scalability**
   - AWS Bedrock handles scaling automatically
   - No infrastructure to manage
   - Pay-per-use pricing

5. **Quality**
   - More comprehensive summaries
   - Better clinical insights
   - Professional medical writing

### Comparison

| Feature | Python Agents | Bedrock Claude |
|---------|--------------|----------------|
| Medical Knowledge | Static, requires updates | Dynamic, continuously updated |
| Research Citations | Simulated database | Real clinical guidelines |
| Analysis Quality | Rule-based | AI-powered, contextual |
| Maintenance | High (code + data) | Low (API calls only) |
| Scalability | Manual | Automatic |
| Cost | Infrastructure | Pay-per-use |

## Cost Considerations

### Claude 3 Pricing (Approximate)

**Sonnet**:
- Input: $3 per million tokens
- Output: $15 per million tokens

**Haiku**:
- Input: $0.25 per million tokens
- Output: $1.25 per million tokens

### Typical Analysis Cost

For a patient with moderate medical history:
- Input tokens: ~3,500 (XML data + prompts)
- Output tokens: ~1,500 (summaries + analysis)

**Sonnet**: ~$0.03 per analysis
**Haiku**: ~$0.003 per analysis

### Monthly Estimates

- 100 analyses/month with Sonnet: ~$3
- 1,000 analyses/month with Sonnet: ~$30
- 100 analyses/month with Haiku: ~$0.30
- 1,000 analyses/month with Haiku: ~$3

## HIPAA Compliance

### Bedrock HIPAA Features

✅ **BAA Available**: AWS offers Business Associate Agreement for Bedrock
✅ **Encryption**: Data encrypted in transit and at rest
✅ **Region Control**: Can restrict to us-east-1
✅ **Audit Logging**: CloudTrail logs all API calls
✅ **No Training**: Patient data not used for model training

### Compliance Checklist

- [ ] Sign AWS BAA for Bedrock
- [ ] Configure CloudTrail logging
- [ ] Restrict to us-east-1 region
- [ ] Enable encryption for S3 storage
- [ ] Implement access controls (IAM)
- [ ] Set up audit logging
- [ ] Document data flows
- [ ] Train staff on HIPAA requirements

## Limitations

1. **API Dependency**: Requires internet connectivity and AWS Bedrock access
2. **Cost**: Per-use pricing (though very affordable)
3. **Latency**: Network calls add ~30-60 seconds per analysis
4. **Rate Limits**: Subject to AWS Bedrock rate limits
5. **Model Availability**: Requires Bedrock access in your AWS account

## Migration Path

### From Python Agents to Bedrock

**Phase 1**: Test Bedrock implementation
```bash
python -m src.main_bedrock  # New Bedrock version
python -m src.main          # Old Python version
```

**Phase 2**: Compare results
- Run both versions on same patients
- Compare quality and accuracy
- Validate HIPAA compliance

**Phase 3**: Gradual rollout
- Start with non-critical analyses
- Monitor costs and performance
- Gather user feedback

**Phase 4**: Full migration
- Switch default to Bedrock
- Keep Python agents as fallback
- Update documentation

## Troubleshooting

### Common Issues

**1. Bedrock Access Denied**
```
Error: AccessDeniedException
```
**Solution**: Enable Bedrock model access in AWS Console → Bedrock → Model Access

**2. Region Not Supported**
```
Error: Bedrock not available in region
```
**Solution**: Use us-east-1 or another supported region

**3. Token Limit Exceeded**
```
Error: Input too long
```
**Solution**: Reduce patient data sent to Claude (limit medications/procedures)

**4. Rate Limiting**
```
Error: ThrottlingException
```
**Solution**: Implement exponential backoff (already built-in)

## Future Enhancements

1. **Streaming Responses**: Stream Claude output for real-time display
2. **Multi-Model**: Use different models for different tasks
3. **Caching**: Cache common analyses to reduce costs
4. **Batch Processing**: Process multiple patients in parallel
5. **Fine-Tuning**: Custom fine-tuned models for specific use cases

## Support

For issues or questions:
- Check CloudWatch Logs for Bedrock API errors
- Review AWS Bedrock documentation
- Verify IAM permissions
- Check model availability in your region

## Resources

- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Claude API Reference](https://docs.anthropic.com/claude/reference)
- [Bedrock Pricing](https://aws.amazon.com/bedrock/pricing/)
- [HIPAA on AWS](https://aws.amazon.com/compliance/hipaa-compliance/)
