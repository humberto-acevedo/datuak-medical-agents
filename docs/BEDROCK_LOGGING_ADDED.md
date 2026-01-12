# Bedrock Logging Implementation

## Overview

Added comprehensive logging to all Bedrock-related components to verify that models are being called and producing results.

## Changes Made

### 1. `src/utils/bedrock_client.py`

Added detailed logging for every Bedrock model invocation:

**Before each model call:**
- Model ID being used
- Prompt length
- Max tokens and temperature settings

**After each model call:**
- Response length
- Stop reason
- Input tokens used
- Output tokens used

**Log Format:**
```
============================================================
BEDROCK MODEL CALL
Model: anthropic.claude-3-haiku-20240307-v1:0
Prompt length: 1234 characters
Max tokens: 4096, Temperature: 0.7
------------------------------------------------------------
BEDROCK MODEL RESPONSE
Response length: 567 characters
Stop reason: end_turn
Input tokens: 234
Output tokens: 123
============================================================
```

### 2. `src/agents/bedrock_medical_summarizer.py`

Added logging before and after Claude invocation:

**Before:**
- Prompt and system prompt character counts
- Indication that Bedrock is being called

**After:**
- Response length
- Model ID used
- Token usage statistics

**Example:**
```
Calling Bedrock Claude for medical summarization...
Prompt: 2345 chars, System: 678 chars
✓ Bedrock returned medical summary: 1234 characters
  Model: anthropic.claude-3-haiku-20240307-v1:0
  Tokens: {'input_tokens': 456, 'output_tokens': 234}
```

### 3. `src/agents/bedrock_research_analyzer.py`

Added similar logging for research analysis:

**Before:**
- Prompt and system prompt character counts
- Indication that Bedrock is being called

**After:**
- Response length
- Model ID used
- Token usage statistics

**Example:**
```
Calling Bedrock Claude for research analysis...
Prompt: 3456 chars, System: 789 chars
✓ Bedrock returned research analysis: 2345 characters
  Model: anthropic.claude-3-haiku-20240307-v1:0
  Tokens: {'input_tokens': 678, 'output_tokens': 456}
```

### 4. `src/utils/bedrock_agent_client.py`

Added logging for Bedrock Agent invocations:

**Before each agent call:**
- Agent ID
- Alias ID
- Session ID
- Input text preview (first 100 chars)

**After each agent call:**
- Response length

**Log Format:**
```
============================================================
BEDROCK AGENT CALL
Agent ID: ABCD1234
Alias ID: TSTALIASID
Session ID: 12345678-1234-1234-1234-123456789abc
Input: Analyze medical records for patient: John Doe...
------------------------------------------------------------
BEDROCK AGENT RESPONSE
Response length: 5678 characters
============================================================
```

## Testing

### Quick Test

Run the test script to verify logging is working:

```bash
python test_bedrock_logging.py
```

This will:
1. Initialize the Bedrock client
2. Make a simple test call to Claude
3. Display all logging output
4. Verify the response is received

### Full Workflow Test

Run the complete workflow to see logging in action:

```bash
python src/main_bedrock.py
```

Or use the launch prototype script:

```bash
python launch_prototype.py
```

## Log Locations

Logs are written to:
- **Console**: All INFO level logs appear in stdout
- **File**: `logs/medical_analysis.log` (if configured)

## What to Look For

When running the system, you should see:

1. **Initialization logs** showing Bedrock client setup
2. **Model call logs** with request details (model, prompt size, tokens)
3. **Response logs** with result details (response size, tokens used)
4. **Success indicators** (✓) showing each step completed
5. **Token usage** for cost tracking and performance monitoring

## Benefits

This logging provides:

1. **Verification**: Confirms models are actually being called
2. **Debugging**: Shows exactly what's being sent to and received from Bedrock
3. **Performance**: Token usage helps track costs and optimize prompts
4. **Troubleshooting**: Detailed logs help identify issues quickly
5. **Audit Trail**: Complete record of all model interactions

## Example Output

When running a complete analysis, you'll see output like:

```
2025-12-05 13:26:00 - INFO - Starting Bedrock Workflow: BEDROCK_WF_20251205_132600
2025-12-05 13:26:00 - INFO - Patient: John Doe

2025-12-05 13:26:01 - INFO - [Step 1/4] Parsing patient XML from S3...
2025-12-05 13:26:02 - INFO - ✓ Patient data extracted: P12345

2025-12-05 13:26:02 - INFO - [Step 2/4] Generating medical summary with Claude...
2025-12-05 13:26:02 - INFO - Calling Bedrock Claude for medical summarization...
2025-12-05 13:26:02 - INFO - Prompt: 2345 chars, System: 678 chars
2025-12-05 13:26:02 - INFO - ============================================================
2025-12-05 13:26:02 - INFO - BEDROCK MODEL CALL
2025-12-05 13:26:02 - INFO - Model: anthropic.claude-3-haiku-20240307-v1:0
2025-12-05 13:26:02 - INFO - Prompt length: 2345 characters
2025-12-05 13:26:02 - INFO - Max tokens: 4096, Temperature: 0.7
2025-12-05 13:26:02 - INFO - ------------------------------------------------------------
2025-12-05 13:26:05 - INFO - BEDROCK MODEL RESPONSE
2025-12-05 13:26:05 - INFO - Response length: 1234 characters
2025-12-05 13:26:05 - INFO - Stop reason: end_turn
2025-12-05 13:26:05 - INFO - Input tokens: 456
2025-12-05 13:26:05 - INFO - Output tokens: 234
2025-12-05 13:26:05 - INFO - ============================================================
2025-12-05 13:26:05 - INFO - ✓ Bedrock returned medical summary: 1234 characters
2025-12-05 13:26:05 - INFO -   Model: anthropic.claude-3-haiku-20240307-v1:0
2025-12-05 13:26:05 - INFO -   Tokens: {'input_tokens': 456, 'output_tokens': 234}

[Similar output for research analysis step...]

2025-12-05 13:26:15 - INFO - Workflow completed successfully in 15.23s
```

## Notes

- All logging uses Python's standard `logging` module
- Log level is set to INFO by default
- Sensitive patient data is not logged (only metadata like lengths and IDs)
- Token usage is logged for cost tracking
- All timestamps are included automatically by the logging framework
