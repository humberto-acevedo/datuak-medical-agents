# AWS Bedrock Agent Deployment

This directory contains configuration files and deployment scripts for deploying the Medical Record Analysis System to AWS Bedrock.

## Overview

The system consists of three specialized Bedrock agents:

1. **XML Parser Agent** - Retrieves and parses patient XML records from S3
2. **Medical Summarization Agent** - Generates comprehensive medical summaries
3. **Research Correlation Agent** - Searches and correlates medical research

## Prerequisites

### AWS Requirements
- AWS Account ID: 539247495490
- AWS Region: us-east-1 (HIPAA compliance requirement)
- AWS CLI configured with appropriate credentials
- Python 3.9+ with boto3 installed

### IAM Permissions
The deployment user/role needs the following permissions:
- `bedrock:CreateAgent`
- `bedrock:UpdateAgent`
- `bedrock:PrepareAgent`
- `bedrock:CreateAgentAlias`
- `bedrock:UpdateAgentAlias`
- `bedrock:CreateAgentActionGroup`
- `bedrock:UpdateAgentActionGroup`
- `iam:CreateRole`
- `iam:PutRolePolicy`
- `iam:UpdateAssumeRolePolicy`

### S3 Bucket
Ensure the S3 bucket exists:
- Bucket name: `patient-records-20251024`
- Region: us-east-1
- Encryption: AWS KMS with us-east-1 key
- Access logging enabled

## Directory Structure

```
deployment/bedrock/
├── README.md                                    # This file
├── deploy_agents.py                             # Main deployment script
├── xml_parser_agent_config.json                 # XML Parser agent configuration
├── medical_summarization_agent_config.json      # Medical Summarization agent config
├── research_correlation_agent_config.json       # Research Correlation agent config
├── iam_policy.json                              # IAM policy for agent execution
├── trust_policy.json                            # IAM trust policy for Bedrock
├── action_groups/
│   ├── xml_parser_actions.json                  # XML Parser action group API
│   ├── medical_summarization_actions.json       # Summarization action group API
│   └── research_correlation_actions.json        # Research action group API
└── deployment_results.json                      # Generated after deployment
```

## Configuration Files

### Agent Configurations
Each agent has a JSON configuration file with:
- Agent name and description
- Foundation model (Claude 3 Sonnet)
- Detailed instructions for agent behavior
- IAM role ARN
- Session timeout settings
- HIPAA compliance tags

### Action Groups
Each agent has an OpenAPI schema defining:
- API endpoints for agent actions
- Request/response schemas
- Lambda function ARNs for execution

### IAM Policies
- **iam_policy.json**: Permissions for S3 access, KMS encryption, CloudWatch logging, and Bedrock model invocation
- **trust_policy.json**: Trust relationship allowing Bedrock to assume the role

## Deployment Instructions

### Step 1: Review Configuration

Review and update the configuration files if needed:

```bash
# Review agent configurations
cat xml_parser_agent_config.json
cat medical_summarization_agent_config.json
cat research_correlation_agent_config.json

# Review IAM policies
cat iam_policy.json
cat trust_policy.json
```

### Step 2: Install Dependencies

```bash
python3 -m pip install boto3
```

### Step 3: Configure AWS Credentials

```bash
# Configure AWS CLI
aws configure

# Verify credentials
aws sts get-caller-identity

# Verify region is set to us-east-1
aws configure get region
```

### Step 4: Run Deployment Script

```bash
# Make script executable
chmod +x deploy_agents.py

# Run deployment
python deploy_agents.py
```

The script will:
1. Create/update the IAM role with proper permissions
2. Deploy the XML Parser Agent
3. Deploy the Medical Summarization Agent
4. Deploy the Research Correlation Agent
5. Create production aliases for each agent
6. Save deployment results to `deployment_results.json`

### Step 5: Verify Deployment

```bash
# List deployed agents
aws bedrock-agent list-agents --region us-east-1

# Get agent details
aws bedrock-agent get-agent --agent-id <agent-id> --region us-east-1

# View deployment results
cat deployment_results.json
```

## Agent Configuration Details

### XML Parser Agent
- **Model**: Claude 3 Sonnet
- **Purpose**: Parse patient XML records from S3
- **Action Group**: XML parsing and S3 operations
- **Lambda**: MedicalRecordXMLParser

### Medical Summarization Agent
- **Model**: Claude 3 Sonnet
- **Purpose**: Generate medical summaries and extract conditions
- **Action Group**: Medical summarization operations
- **Lambda**: MedicalSummarization

### Research Correlation Agent
- **Model**: Claude 3 Sonnet
- **Purpose**: Search and correlate medical research
- **Action Group**: Research search and correlation
- **Lambda**: ResearchCorrelation

## HIPAA Compliance

All agents are configured for HIPAA compliance:

- **Region Restriction**: All resources in us-east-1
- **Encryption**: KMS encryption for S3 data
- **Audit Logging**: CloudWatch and CloudTrail logging enabled
- **Access Control**: IAM policies restrict cross-region access
- **Data Residency**: Patient data never leaves US borders

## Monitoring and Logging

### CloudWatch Logs
Agent execution logs are stored in:
```
/aws/bedrock/agents/medical-record-analysis/<agent-name>
```

### CloudTrail
All API calls are logged in CloudTrail for audit purposes.

### Metrics
Monitor agent performance:
- Invocation count
- Error rate
- Latency
- Token usage

## Updating Agents

To update an existing agent:

1. Modify the configuration file
2. Run the deployment script again
3. The script will detect existing agents and update them

```bash
python deploy_agents.py
```

## Troubleshooting

### IAM Role Issues
If you encounter IAM role errors:
```bash
# Verify role exists
aws iam get-role --role-name MedicalRecordAnalysisBedrockAgentRole

# Check role policies
aws iam list-role-policies --role-name MedicalRecordAnalysisBedrockAgentRole
```

### Agent Preparation Timeout
If agent preparation times out:
- Check CloudWatch logs for errors
- Verify foundation model access
- Ensure IAM role has proper permissions

### S3 Access Issues
Verify S3 bucket configuration:
```bash
# Check bucket exists
aws s3 ls s3://patient-records-20251024/ --region us-east-1

# Verify bucket encryption
aws s3api get-bucket-encryption --bucket patient-records-20251024 --region us-east-1
```

## Next Steps

After deploying the Bedrock agents:

1. **Deploy Lambda Functions** (Task 13.2)
   - Create Lambda functions for each action group
   - Configure Lambda to invoke Python agent code
   - Set up API Gateway endpoints

2. **Configure Monitoring** (Task 13.3)
   - Set up CloudWatch dashboards
   - Configure alarms and alerts
   - Enable detailed logging

3. **Test Agents**
   - Invoke agents with test data
   - Verify end-to-end workflow
   - Validate HIPAA compliance

## Support

For issues or questions:
- Review CloudWatch logs
- Check AWS Bedrock documentation
- Verify IAM permissions
- Ensure all resources are in us-east-1 region
