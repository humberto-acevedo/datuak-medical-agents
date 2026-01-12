# Python pip Command Update

## Summary

Updated all `pip` commands to use `python3 -m pip` for consistency and reliability across different systems.

## Why This Change?

### Problem with `pip`
- On some systems, `pip` points to Python 2's pip
- Can cause version conflicts and installation issues
- Not explicit about which Python version is being used

### Benefits of `python3 -m pip`
- **Explicit**: Always uses Python 3's pip
- **Reliable**: Uses the same Python interpreter as `python3`
- **Best Practice**: Recommended by Python documentation
- **Cross-Platform**: Works consistently on all systems

## Files Updated

### Scripts
1. ✅ `deployment/lambda/deploy.sh` - Lambda deployment script
2. ✅ `deployment/pipeline/buildspec.yml` - CodeBuild configuration
3. ✅ `launch_prototype.py` - Prototype launcher
4. ✅ `Dockerfile` - Docker image build

### Documentation
1. ✅ `README.md` - Main project README
2. ✅ `PROTOTYPE_LAUNCH_GUIDE.md` - Prototype guide
3. ✅ `deployment/lambda/README.md` - Lambda deployment docs
4. ✅ `deployment/lambda/DEPLOYMENT_GUIDE.md` - Lambda quick guide
5. ✅ `deployment/bedrock/README.md` - Bedrock deployment docs
6. ✅ `deployment/pipeline/PIPELINE_GUIDE.md` - Pipeline guide
7. ✅ `docs/SETUP_GUIDE.md` - Setup documentation

## Examples

### Before
```bash
pip install -r requirements.txt
pip install aws-sam-cli
pip install boto3
```

### After
```bash
python3 -m pip install -r requirements.txt
python3 -m pip install aws-sam-cli
python3 -m pip install boto3
```

## Verification

All instances of `pip install` have been updated to `python3 -m pip install` in:
- Shell scripts (`.sh`)
- Python scripts (`.py`)
- YAML configuration files (`.yml`)
- Dockerfiles
- Markdown documentation (`.md`)

## Impact

### Users
- More reliable installation instructions
- Consistent behavior across different systems
- Clearer which Python version is being used

### CI/CD
- CodeBuild continues to work correctly
- More explicit about Python version
- Better compatibility with different build environments

### Docker
- Dockerfile explicitly uses Python 3's pip
- No ambiguity in container builds

## Virtual Environment Recommendation

All documentation now recommends using virtual environments to avoid `externally-managed-environment` errors:

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # On macOS/Linux
# venv\Scripts\activate  # On Windows

# Install packages
python3 -m pip install -r requirements.txt
```

This is especially important on:
- macOS with Homebrew Python
- Modern Linux distributions (Ubuntu 23.04+, Fedora 38+)
- Any system with PEP 668 externally-managed-environment

## Testing

To verify the changes work correctly:

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Test installation
python3 -m pip install -r requirements.txt

# Verify Python version
python3 --version

# Verify pip is using Python 3
python3 -m pip --version
```

## Additional Notes

- The `python: 3.11` in buildspec.yml is correct AWS CodeBuild syntax
- Lambda runtime `python3.11` is correct AWS Lambda runtime identifier
- All Python script shebangs already use `#!/usr/bin/env python3`

## References

- [Python Packaging User Guide](https://packaging.python.org/en/latest/tutorials/installing-packages/)
- [pip documentation](https://pip.pypa.io/en/stable/cli/pip/)
- [Python Module Invocation](https://docs.python.org/3/using/cmdline.html#cmdoption-m)
