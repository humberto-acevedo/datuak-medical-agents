# CI/CD Pipeline Quick Start

## 5-Minute Setup

### Prerequisites
- [ ] AWS CLI configured
- [ ] GitHub repository created
- [ ] GitHub Personal Access Token generated
- [ ] Code pushed to GitHub

### Deploy Pipeline

```bash
cd deployment/pipeline
./deploy_pipeline.sh
```

**You'll be prompted for**:
- GitHub owner (your username/org)
- GitHub repository name
- GitHub branch (default: main)
- GitHub token (will be hidden)
- Environment (default: production)

## What You Get

### Automated Pipeline
- **Source**: GitHub webhook triggers on push
- **Build**: Automated testing and packaging
- **Deploy Dev**: Automatic deployment to development
- **Approve Staging**: Manual approval gate
- **Deploy Staging**: Deployment to staging environment
- **Approve Production**: Manual approval gate
- **Deploy Production**: Blue-green deployment

### Build Process
- Linting (flake8, black)
- Security scanning (bandit)
- Unit tests with coverage
- Lambda packaging
- SAM deployment

### Deployment Strategy
- **Development**: Auto-deploy on every commit
- **Staging**: Manual approval required
- **Production**: Manual approval + blue-green deployment

## Pipeline Flow

```
Push to GitHub
    ↓
Build & Test (Auto)
    ↓
Deploy to Dev (Auto)
    ↓
Approve Staging (Manual) ← You review here
    ↓
Deploy to Staging
    ↓
Approve Production (Manual) ← You review here
    ↓
Deploy to Production (Blue-Green)
```

## Using the Pipeline

### 1. Trigger Deployment

```bash
# Make changes
git add .
git commit -m "Update feature"
git push origin main
```

Pipeline automatically starts!

### 2. Monitor Build

View in AWS Console:
```
https://console.aws.amazon.com/codesuite/codepipeline/pipelines/
```

Or via CLI:
```bash
aws codepipeline get-pipeline-state \
  --name MedicalRecordAnalysisPipeline
```

### 3. Approve Staging

When notified:
1. Review development deployment
2. Check test results
3. Click "Review" in AWS Console
4. Approve or Reject

### 4. Approve Production

When notified:
1. Review staging deployment
2. Verify integration tests
3. Click "Review" in AWS Console
4. Approve or Reject

## Rollback

If something goes wrong:

```bash
./rollback.sh production
```

**Options**:
1. Rollback entire stack
2. Rollback specific Lambda function
3. Cancel current update

## Environment Configuration

Edit `environment_config.yaml` to customize:

- Lambda settings (memory, timeout, concurrency)
- API Gateway throttling
- CloudWatch log retention
- Monitoring and alarms
- Security settings

## Monitoring Pipeline

### View Pipeline Status

```bash
# Get pipeline state
aws codepipeline get-pipeline-state \
  --name MedicalRecordAnalysisPipeline

# List recent executions
aws codepipeline list-pipeline-executions \
  --pipeline-name MedicalRecordAnalysisPipeline \
  --max-results 5
```

### View Build Logs

```bash
# Get recent builds
aws codebuild list-builds-for-project \
  --project-name MedicalRecordAnalysisBuild \
  --max-items 5
```

### View Deployment Status

```bash
# Check CloudFormation stack
aws cloudformation describe-stacks \
  --stack-name medical-record-analysis-lambda-production
```

## Common Tasks

### Update Pipeline Configuration

```bash
# Edit pipeline.yaml
vim pipeline.yaml

# Redeploy pipeline
./deploy_pipeline.sh
```

### Add Build Step

Edit `buildspec.yml`:

```yaml
post_build:
  commands:
    - echo "Custom step"
    - python scripts/custom_validation.py
```

### Change Approval Notifications

Update SNS topic in pipeline configuration.

### Modify Deployment Strategy

Edit `environment_config.yaml`:

```yaml
blue_green:
  traffic_shift_type: Canary  # or Linear, AllAtOnce
  traffic_shift_interval: 5
```

## Troubleshooting

### Build Fails

1. Check CodeBuild logs in AWS Console
2. Run tests locally: `pytest tests/`
3. Verify dependencies: `python3 -m pip install -r requirements.txt`

### Deployment Fails

1. Check CloudFormation events
2. Verify IAM permissions
3. Check resource limits
4. Review error messages

### Approval Not Received

1. Check email for SNS notification
2. Verify SNS subscription confirmed
3. Check spam folder
4. Manually approve in AWS Console

## Cost Estimate

**Monthly Pipeline Cost**: $10-30

- CodePipeline: $1/month
- CodeBuild: ~$5-10/month (depends on builds)
- S3 Storage: ~$2-5/month
- CloudWatch: ~$2-5/month

## Best Practices

### Before Pushing Code

- [ ] Run tests locally
- [ ] Run linting
- [ ] Update documentation
- [ ] Review changes

### Before Approving Staging

- [ ] Review dev deployment
- [ ] Check test results
- [ ] Verify functionality
- [ ] Review code changes

### Before Approving Production

- [ ] Review staging deployment
- [ ] Run integration tests
- [ ] Check monitoring dashboards
- [ ] Notify team

### After Production Deployment

- [ ] Monitor CloudWatch metrics
- [ ] Check error logs
- [ ] Verify functionality
- [ ] Document deployment

## Next Steps

1. ✅ Pipeline deployed
2. ⏭️ Push code to trigger first build
3. ⏭️ Monitor build and deployment
4. ⏭️ Set up approval notifications
5. ⏭️ Configure monitoring dashboards

## Support

**Pipeline URL**: Check `pipeline_config.json` for your pipeline URL

**Documentation**: See README.md for detailed information

**AWS Console**: 
- CodePipeline: https://console.aws.amazon.com/codesuite/codepipeline/
- CodeBuild: https://console.aws.amazon.com/codesuite/codebuild/
- CloudFormation: https://console.aws.amazon.com/cloudformation/

**CLI Help**:
```bash
aws codepipeline help
aws codebuild help
aws cloudformation help
```
