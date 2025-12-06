# Bedrock Agent Quick Start

## TL;DR

```bash
# 1. Deploy agent (one time)
python deployment/bedrock/deploy_master_agent.py

# 2. Copy the agent IDs from output

# 3. Run analysis
python launch_prototype.py --bedrock-agent \
  --agent-id YOUR_AGENT_ID \
  --agent-alias-id YOUR_ALIAS_ID
```

## What You Get

- **Master Bedrock Agent** that orchestrates your entire workflow
- **Lambda function** that runs your existing Python code
- **CLI option** to use the agent instead of direct API calls

## Three Ways to Run

```bash
# Option 1: Python agents (no AWS Bedrock)
python launch_prototype.py

# Option 2: Direct Bedrock Claude API
python launch_prototype.py --bedrock

# Option 3: Bedrock Agent (requires deployment)
python launch_prototype.py --bedrock-agent --agent-id X --agent-alias-id Y
```

## Deployment (First Time Only)

```bash
# Navigate to deployment directory
cd deployment/bedrock

# Run deployment script
python deploy_master_agent.py

# Wait ~2 minutes for deployment

# Output will show:
# Agent ID: ABCD1234
# Alias ID: EFGH5678
```

## Using the Agent

```bash
# Method 1: Pass IDs directly
python launch_prototype.py --bedrock-agent \
  --agent-id ABCD1234 \
  --agent-alias-id EFGH5678

# Method 2: Load from config file
AGENT_ID=$(jq -r '.agent_id' deployment/bedrock/master_agent_deployment.json)
ALIAS_ID=$(jq -r '.agent_alias_id' deployment/bedrock/master_agent_deployment.json)

python launch_prototype.py --bedrock-agent \
  --agent-id $AGENT_ID \
  --agent-alias-id $ALIAS_ID
```

## What Happens Behind the Scenes

1. Your CLI calls Bedrock Agent API
2. Agent (Claude) receives: "Analyze patient John Doe"
3. Agent decides to call `analyzePatient` action
4. Lambda function executes your MainWorkflow
5. Workflow runs all your existing agents
6. Results return to Agent
7. Agent formats response
8. CLI displays results

## Troubleshooting

### "Agent not found"
```bash
# Verify agent exists
aws bedrock-agent list-agents --region us-east-1
```

### "Lambda timeout"
```bash
# Increase timeout
aws lambda update-function-configuration \
  --function-name MedicalAnalysisMasterWorkflow \
  --timeout 600 \
  --region us-east-1
```

### "Permission denied"
```bash
# Check your AWS credentials
aws sts get-caller-identity

# Verify you have Bedrock permissions
aws bedrock-agent list-agents --region us-east-1
```

## Cost

- **Deployment**: Free (one-time setup)
- **Per analysis**: ~$0.002
  - Bedrock Agent invocation: ~$0.001
  - Lambda execution: ~$0.0001
  - Claude API calls: ~$0.001

## When to Use

**Use Bedrock Agent if:**
- You want agent-driven orchestration
- You need conversational interface
- You want Lambda auto-scaling

**Use Direct Bedrock if:**
- You want lower cost
- You want faster response
- You want predictable workflow

**Use Python Agents if:**
- You're testing locally
- You don't need AI summarization
- You want zero AWS costs

## Files Created

- `src/utils/bedrock_agent_client.py` - Agent API client
- `deployment/lambda/master_workflow_handler.py` - Lambda handler
- `deployment/bedrock/master_agent_config.json` - Agent config
- `deployment/bedrock/deploy_master_agent.py` - Deployment script

## Need Help?

See full documentation:
- `BEDROCK_AGENT_DEPLOYMENT.md` - Complete deployment guide
- `BEDROCK_AGENT_IMPLEMENTATION.md` - Technical details
- `README.md` - Project overview
