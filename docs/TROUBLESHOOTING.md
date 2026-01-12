# Troubleshooting Guide

Common issues and solutions for the Medical Record Analysis System.

## Python and Pip Issues

### Error: externally-managed-environment

**Problem**: When trying to install packages with pip on macOS (especially with Homebrew Python), you get:
```
error: externally-managed-environment

× This environment is externally managed
╰─> To install Python packages system-wide, try brew install
    xyz, where xyz is the package you are trying to
    install.
```

**Solution 1: Use Virtual Environment (Recommended)**
```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # On macOS/Linux
# venv\Scripts\activate  # On Windows

# Now install packages
python3 -m pip install -r requirements.txt
```

**Solution 2: Use --break-system-packages (Not Recommended)**
```bash
python3 -m pip install -r requirements.txt --break-system-packages
```
⚠️ **Warning**: This can cause conflicts with system packages. Use virtual environment instead.

**Why This Happens**:
- Homebrew Python (and some Linux distributions) mark Python as "externally managed"
- This prevents accidental system-wide package installations
- Virtual environments are the recommended solution

### Error: ModuleNotFoundError

**Problem**: 
```python
ModuleNotFoundError: No module named 'boto3'
```

**Solution**:
```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Install dependencies
python3 -m pip install -r requirements.txt

# Verify installation
python3 -c "import boto3; print('boto3 installed successfully')"
```

### Error: pip not found

**Problem**:
```bash
python3 -m pip: No module named pip
```

**Solution**:
```bash
# On macOS with Homebrew
brew install python3

# On Ubuntu/Debian
sudo apt-get install python3-pip python3-venv

# On CentOS/RHEL
sudo yum install python3-pip

# Verify
python3 -m pip --version
```

## Virtual Environment Issues

### Virtual Environment Not Activating

**Problem**: `source venv/bin/activate` doesn't work

**Solution**:
```bash
# Make sure venv was created successfully
python3 -m venv venv

# Try different activation methods
source venv/bin/activate          # bash/zsh
. venv/bin/activate               # sh
source venv/bin/activate.fish     # fish
source venv/bin/activate.csh      # csh/tcsh

# On Windows
venv\Scripts\activate.bat         # cmd
venv\Scripts\Activate.ps1         # PowerShell
```

### Wrong Python Version in Virtual Environment

**Problem**: Virtual environment uses wrong Python version

**Solution**:
```bash
# Specify Python version explicitly
python3.11 -m venv venv

# Or use specific Python path
/usr/local/bin/python3 -m venv venv

# Verify version
source venv/bin/activate
python --version
```

### Deactivating Virtual Environment

**Problem**: How to exit virtual environment

**Solution**:
```bash
# Simply run
deactivate
```

## AWS Configuration Issues

### Error: Unable to locate credentials

**Problem**:
```
botocore.exceptions.NoCredentialsError: Unable to locate credentials
```

**Solution**:
```bash
# Configure AWS credentials
aws configure

# Or set environment variables
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1

# Verify
aws sts get-caller-identity
```

### Error: InvalidAccessKeyId

**Problem**:
```
S3Error: The AWS Access Key Id you provided does not exist in our records
```

**Solution**:

This error occurs when:
1. AWS credentials are not configured
2. AWS credentials are invalid or expired
3. Using test credentials with real AWS services

**Fix**:
```bash
# Option 1: Configure real AWS credentials
aws configure
# Enter your actual AWS access key and secret key

# Option 2: For testing without AWS, use the test suite
pytest tests/
# Tests use mocked AWS services (moto)

# Option 3: Verify current credentials
aws sts get-caller-identity
```

**Note**: The `launch_prototype.py` script requires real AWS credentials and an actual S3 bucket. For testing without AWS, use `pytest tests/` which uses mocked services.

### Error: Access Denied to S3

**Problem**:
```
botocore.exceptions.ClientError: An error occurred (AccessDenied)
```

**Solution**:
1. Verify IAM permissions include S3 access
2. Check bucket policy allows your IAM user/role
3. Verify bucket exists and region is correct
4. Check KMS key permissions if bucket is encrypted

## Docker Issues

### Error: Cannot connect to Docker daemon

**Problem**:
```
Cannot connect to the Docker daemon at unix:///var/run/docker.sock
```

**Solution**:
```bash
# Start Docker Desktop (macOS/Windows)
# Or start Docker service (Linux)
sudo systemctl start docker

# Verify
docker ps
```

### Error: Permission denied (Docker)

**Problem**:
```
permission denied while trying to connect to the Docker daemon socket
```

**Solution**:
```bash
# Add user to docker group (Linux)
sudo usermod -aG docker $USER

# Log out and back in, or run
newgrp docker

# Verify
docker ps
```

## Testing Issues

### Tests Fail with Import Errors

**Problem**:
```
ImportError: cannot import name 'XMLParserAgent'
```

**Solution**:
```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Install in development mode
python3 -m pip install -e .

# Or set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:${PWD}/src"

# Run tests
pytest tests/
```

### Tests Fail with AWS Errors

**Problem**: Tests fail trying to connect to real AWS services

**Solution**:
```bash
# Tests should use moto for mocking
# Verify moto is installed
python3 -m pip install moto

# Run tests with mocking
pytest tests/
```

## Lambda Deployment Issues

### Error: SAM CLI not found

**Problem**:
```bash
sam: command not found
```

**Solution**:
```bash
# Install SAM CLI in virtual environment
source venv/bin/activate
python3 -m pip install aws-sam-cli

# Verify
sam --version
```

### Error: Docker required for SAM build

**Problem**:
```
Error: Running AWS SAM projects locally requires Docker
```

**Solution**:
1. Install Docker Desktop (macOS/Windows)
2. Start Docker
3. Verify: `docker ps`
4. Try SAM build again

## Performance Issues

### Slow Package Installation

**Problem**: `pip install` takes very long

**Solution**:
```bash
# Use pip cache
python3 -m pip install -r requirements.txt --cache-dir ~/.cache/pip

# Or upgrade pip
python3 -m pip install --upgrade pip

# Use faster resolver
python3 -m pip install -r requirements.txt --use-feature=fast-deps
```

### High Memory Usage

**Problem**: System runs out of memory during tests

**Solution**:
```bash
# Run tests in smaller batches
pytest tests/test_xml_parser.py
pytest tests/test_medical_summarization.py

# Or limit parallel execution
pytest tests/ -n 2  # Use 2 workers instead of auto
```

## macOS Specific Issues

### Error: xcrun: error: invalid active developer path

**Problem**:
```
xcrun: error: invalid active developer path
```

**Solution**:
```bash
# Install Xcode Command Line Tools
xcode-select --install
```

### Error: SSL Certificate Verification Failed

**Problem**:
```
ssl.SSLCertVerificationError: certificate verify failed
```

**Solution**:
```bash
# Install certificates (macOS)
/Applications/Python\ 3.11/Install\ Certificates.command

# Or use certifi
python3 -m pip install --upgrade certifi
```

## Getting Help

### Check Logs

```bash
# Application logs
tail -f logs/medical_analysis.log

# Error logs
tail -f logs/errors.log

# Audit logs
tail -f logs/audit.log
```

### Verify Installation

```bash
# Check Python version
python3 --version

# Check pip version
python3 -m pip --version

# Check installed packages
python3 -m pip list

# Check AWS configuration
aws configure list

# Check Docker
docker --version
docker ps
```

### Run Diagnostics

```bash
# Run system check
python3 -c "
import sys
import platform
print(f'Python: {sys.version}')
print(f'Platform: {platform.platform()}')
print(f'Architecture: {platform.machine()}')
"

# Check dependencies
python3 -m pip check
```

### Common Commands

```bash
# Recreate virtual environment
rm -rf venv
python3 -m venv venv
source venv/bin/activate
python3 -m pip install -r requirements.txt

# Clear pip cache
python3 -m pip cache purge

# Reinstall package
python3 -m pip uninstall boto3
python3 -m pip install boto3

# Update all packages
python3 -m pip list --outdated
python3 -m pip install --upgrade -r requirements.txt
```

## Still Having Issues?

1. **Check the logs** in the `logs/` directory
2. **Review error messages** carefully
3. **Search GitHub issues** for similar problems
4. **Check AWS service status** at https://status.aws.amazon.com/
5. **Verify system requirements** in README.md
6. **Try with a fresh virtual environment**
7. **Contact support** with detailed error messages and logs

## Useful Resources

- [Python Virtual Environments](https://docs.python.org/3/tutorial/venv.html)
- [pip User Guide](https://pip.pypa.io/en/stable/user_guide/)
- [AWS CLI Configuration](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html)
- [Docker Documentation](https://docs.docker.com/)
- [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html)
