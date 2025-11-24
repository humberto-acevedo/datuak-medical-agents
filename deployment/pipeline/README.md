# CI/CD Pipeline

This directory contains the CI/CD pipeline configuration for automated deployment of the Medical Record Analysis System.

## Overview

Automated deployment pipeline with:
- GitHub integration for source control
- AWS CodeBuild for building and testing
- AWS CodePipeline for orchestration
- Multi-environment deployment (dev/staging/prod)
- Manual approval gates
- Automated rollback capabilities
- Blue-green deployment support

## Architecture

```
┌─────────────┐
│   GitHub    │
│  (Source)   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  CodeBuild  │
│ (Build/Test)│
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Development │ (Auto Deploy)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Approval  │ (Manual)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Staging   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Approval  │ (Manual)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Production  │ (Blue-Green)
└─────────────┘
```

## Quick Setup

### Prerequisites

- AWS CLI configured
- GitHub repository
- GitHub Personal Access Token
- AWS account with appropriate permissions

### Deploy Pipeline

```bash
cd deployment/pipeline
./deploy_pipeline.sh
```

Follow the prompts to configure:
- GitHub repository owner
- GitHub repository name
- GitHub branch
- GitHub token
- Environment

## Pipeline Stages

### 1. Source Stage

**Trigger**: Git push to configured branch

**Actions**:
- Checkout code from GitHub
- Store source in S3 artifact bucket

### 2. Build Stage

**Actions**:
- Install dependencies
- Run linting (flake8, black)
- Run security checks (bandit)
- Execute unit tests with coverage
- Build Lambda deployment packages
- Package SAM application
- Generate deployment manifest

**Artifacts**:
- Packaged Lambda functions
- SAM templates
- Test reports
- Coverage reports

### 3. Deploy Development

**Trigger**: Automatic after successful build

**Actions**:
- Deploy Lambda functions to development
- Update API Gateway
- Configure CloudWatch Logs
- Run smoke tests

### 4. Approve Staging

**Trigger**: Manual approval required

**Actions**:
- Review development deployment
- Check test results
- Approve or reject

### 5. Deploy Staging

**Trigger**: After staging approval

**Actions**:
- Deploy Lambda functions to staging
- Update API Gateway
- Configure CloudWatch Logs
- Run integration tests

### 6. Approve Production

**Trigger**: Manual approval required

**Actions**:
- Review staging deployment
- Check integration test results
- Approve or reject

### 7. Deploy Production

**Trigger**: After production approval

**Actions**:
- Deploy Lambda functions with blue-green strategy
- Gradual traffic shift
- Monitor CloudWatch alarms
- Automatic rollback on errors

## Environment Configuration

### Configuration File

`environment_config.yaml` contains environment-specific settings:

- Lambda configuration (timeout, memory, concurrency)
- API Gateway throttling and quotas
- S3 bucket names and encryption
- CloudWatch log retention
- Monitoring and alerting
- Security and compliance settings

### Environment Variables

Each environment has specific variables:

**Development**:
- Lower resource limits
- Debug logging
- Shorter log retention
- No reserved concurrency

**Staging**:
- Medium resource limits
- Info logging
- Medium log retention
- Limited reserved concurrency

**Production**:
- High resource limits
- Info logging
- 30-day log retention
- Full reserved concurrency
- Enhanced monitoring
- Alarms and alerts

## Blue-Green Deployment

### Configuration

Blue-green deployment is enabled for production:

```yaml
blue_green:
  enabled: true
  traffic_shift_type: Linear
  traffic_shift_interval: 10
  alarm_configuration:
    enabled: true
```

### Traffic Shift Strategies

**Linear**: Gradual shift over time
- 10% every 10 minutes
- Complete in 100 minutes
- Monitor alarms at each step

**Canary**: Test with small percentage first
- 10% for 5 minutes
- Then 100% if successful
- Rollback if alarms trigger

**AllAtOnce**: Immediate switch
- Instant traffic shift
- Higher risk
- Use only for minor updates

### Rollback Triggers

Automatic rollback occurs if:
- Error rate exceeds threshold
- Duration exceeds timeout warning
- Throttling detected
- Custom alarms trigger
- Health checks fail

## Rollback Procedures

### Automatic Rollback

Configured in `environment_config.yaml`:

```yaml
rollback:
  automatic: true
  alarm_threshold: 5
  alarm_evaluation_periods: 2
  rollback_on_alarm: true
```

### Manual Rollback

Use the rollback script:

```bash
./rollback.sh production
```

**Options**:
1. Rollback entire stack to previous version
2. Rollback specific Lambda function to version
3. Cancel current update
4. Exit

### Rollback Verification

After rollback:
1. Check CloudWatch Logs for errors
2. Test Lambda functions
3. Monitor CloudWatch metrics
4. Review CloudTrail logs
5. Verify API Gateway endpoints

## Build Configuration

### buildspec.yml

CodeBuild configuration with phases:

**Install**:
- Python 3.11 runtime
- Install dependencies
- Install testing tools

**Pre-Build**:
- Run linting
- Run security checks
- Validate code quality

**Build**:
- Run unit tests
- Generate coverage reports
- Build Lambda packages
- Package SAM application

**Post-Build**:
- Generate deployment manifest
- Create build artifacts
- Upload to S3

### Build Artifacts

Generated artifacts:
- `packaged.yaml` - SAM template
- `deployment_manifest.json` - Build metadata
- `coverage.xml` - Test coverage
- `htmlcov/` - Coverage HTML report

## Monitoring Pipeline

### CodePipeline Metrics

Monitor in CloudWatch:
- Pipeline execution time
- Stage success/failure rates
- Approval wait times
- Deployment frequency

### CodeBuild Metrics

Monitor in CloudWatch:
- Build duration
- Build success rate
- Test pass rate
- Code coverage percentage

### Deployment Metrics

Track deployments:
- Deployment frequency
- Lead time for changes
- Mean time to recovery
- Change failure rate

## Security

### IAM Roles

Three service roles created:

**CodeBuildServiceRole**:
- CloudWatch Logs access
- S3 artifact access
- ECR access for Docker

**CodePipelineServiceRole**:
- S3 artifact access
- CodeBuild invocation
- CloudFormation access

**CloudFormationServiceRole**:
- Full deployment permissions
- Lambda function management
- API Gateway management

### Secrets Management

GitHub token stored securely:
- Encrypted in CloudFormation
- Not logged or exposed
- Rotated regularly

### Compliance

Pipeline meets HIPAA requirements:
- All artifacts encrypted
- Audit logging enabled
- Access controls enforced
- Data residency in us-east-1

## Cost Optimization

### Estimated Monthly Costs

**CodePipeline**: $1.00 per active pipeline  
**CodeBuild**: $0.005 per build minute  
**S3 Storage**: $0.023 per GB  
**CloudWatch Logs**: $0.50 per GB

**Typical Monthly Cost**: $10-30

### Cost Reduction Tips

1. **Build Optimization**: Cache dependencies
2. **Artifact Cleanup**: 30-day lifecycle policy
3. **Build Triggers**: Limit to main branch
4. **Resource Sizing**: Use appropriate build instance

## Troubleshooting

### Build Failures

**Issue**: Build fails during test phase

**Solutions**:
1. Check CodeBuild logs
2. Run tests locally
3. Verify dependencies
4. Check Python version

### Deployment Failures

**Issue**: CloudFormation deployment fails

**Solutions**:
1. Check CloudFormation events
2. Verify IAM permissions
3. Check resource limits
4. Review stack parameters

### Approval Timeout

**Issue**: Approval stage times out

**Solutions**:
1. Check SNS notifications
2. Verify email subscriptions
3. Review approval settings
4. Extend timeout if needed

### Rollback Issues

**Issue**: Rollback fails

**Solutions**:
1. Check CloudFormation status
2. Verify previous version exists
3. Check Lambda versions
4. Manual intervention may be needed

## Best Practices

### Code Quality

- Run linting before commit
- Maintain >80% test coverage
- Fix security vulnerabilities
- Document code changes

### Deployment Strategy

- Deploy to dev first
- Test thoroughly in staging
- Use blue-green for production
- Monitor after deployment

### Approval Process

- Review test results
- Check code changes
- Verify staging deployment
- Document approval decision

### Monitoring

- Watch pipeline metrics
- Review build logs
- Monitor deployments
- Track failure rates

## Maintenance

### Weekly Tasks

- [ ] Review pipeline executions
- [ ] Check build success rates
- [ ] Review approval times
- [ ] Monitor costs

### Monthly Tasks

- [ ] Update dependencies
- [ ] Review IAM permissions
- [ ] Optimize build times
- [ ] Clean up old artifacts

### Quarterly Tasks

- [ ] Rotate GitHub token
- [ ] Review pipeline configuration
- [ ] Update documentation
- [ ] Audit security settings

## Advanced Features

### Custom Build Steps

Add custom steps to `buildspec.yml`:

```yaml
post_build:
  commands:
    - echo "Running custom validation..."
    - python scripts/validate_deployment.py
```

### Parallel Deployments

Deploy to multiple regions:

```yaml
- Name: DeployProduction
  Actions:
    - Name: DeployUSEast1
      Region: us-east-1
    - Name: DeployUSWest2
      Region: us-west-2
```

### Integration Tests

Add integration test stage:

```yaml
- Name: IntegrationTests
  Actions:
    - Name: RunTests
      ActionTypeId:
        Category: Test
        Owner: AWS
        Provider: CodeBuild
```

## Support

### Pipeline Issues

```bash
# View pipeline status
aws codepipeline get-pipeline-state \
  --name MedicalRecordAnalysisPipeline

# View execution history
aws codepipeline list-pipeline-executions \
  --pipeline-name MedicalRecordAnalysisPipeline
```

### Build Issues

```bash
# View build logs
aws codebuild batch-get-builds \
  --ids <build-id>

# Start manual build
aws codebuild start-build \
  --project-name MedicalRecordAnalysisBuild
```

### Deployment Issues

```bash
# View CloudFormation events
aws cloudformation describe-stack-events \
  --stack-name medical-record-analysis-lambda-production

# View stack status
aws cloudformation describe-stacks \
  --stack-name medical-record-analysis-lambda-production
```

## Resources

- [AWS CodePipeline Documentation](https://docs.aws.amazon.com/codepipeline/)
- [AWS CodeBuild Documentation](https://docs.aws.amazon.com/codebuild/)
- [AWS SAM Documentation](https://docs.aws.amazon.com/serverless-application-model/)
- [Blue-Green Deployments](https://docs.aws.amazon.com/lambda/latest/dg/lambda-traffic-shifting-using-aliases.html)
