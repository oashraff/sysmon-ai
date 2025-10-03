# Deployment Guide

SysMon AI can be deployed in multiple ways depending on your needs.

## Method 1: Wheel Distribution (Recommended)

Build a Python wheel that users can install with pip:

```bash
# Build the wheel
python -m build

# Distribute the wheel
# Users install with:
pip install sysmon_ai-0.1.0-py3-none-any.whl
```

### Advantages
- Smallest size (few MB)
- Respects Python environment
- Easy updates
- Native pip integration

### Requirements
- Python 3.10+ on target system
- pip installed

## Method 2: ZIP with setup script

Create a self-contained archive with setup script:

```bash
# Create distribution archive
tar -czf sysmon-ai-v0.1.0.tar.gz \
    sysmon_ai/ \
    tests/ \
    pyproject.toml \
    README.md \
    QUICKSTART.md \
    LICENSE \
    setup.sh \
    config.example.yaml

# Users extract and run:
# tar -xzf sysmon-ai-v0.1.0.tar.gz
# cd sysmon-ai
# ./setup.sh
```

### Advantages
- Simple distribution
- Automated setup via script
- Includes all documentation
- Source code available

## Method 3: Docker Container

For completely isolated deployment:

```bash
# Build Docker image
docker build -t sysmon-ai:0.1.0 .

# Run container
docker run -it --pid=host sysmon-ai:0.1.0 sysmon dashboard
```

Create a `Dockerfile`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy application
COPY . .

# Install package
RUN pip install --no-cache-dir -e .

# Create data directory
RUN mkdir -p /data
ENV SYSMON_DB_PATH=/data/sysmon.db

ENTRYPOINT ["sysmon"]
CMD ["dashboard"]
```

### Advantages
- Complete isolation
- Consistent environment
- Easy deployment to cloud
- No Python version conflicts

## Method 4: PyInstaller Executable (Advanced)

Note: PyInstaller with scipy/sklearn can be challenging. Use only if wheel distribution is not an option.

```bash
# Install PyInstaller
pip install pyinstaller

# Build executable
pyinstaller sysmon.spec

# Test
./dist/sysmon version
```

### Known Issues
- Large file size (80-120 MB)
- scipy compatibility issues on some platforms
- May require additional hidden imports
- Platform-specific builds required

### Workarounds
If build fails, try:
- Using `--exclude-module matplotlib` if plotting not needed
- Building on older OS version for compatibility
- Using conda environment instead of venv

## Recommended Deployment Strategy

**For distribution to users:**
1. Build wheel: `python -m build`
2. Upload to PyPI or internal package server
3. Users install: `pip install sysmon-ai`

**For internal deployment:**
1. Use setup.sh script with venv
2. Or use Docker for containerized deployment

**For standalone executable:**
- Only if target users don't have Python
- Build on same OS/architecture as target
- Test thoroughly before distribution

## Building for Distribution

### Install build tools

```bash
pip install build twine
```

### Build package

```bash
# Clean previous builds
rm -rf dist/ build/ *.egg-info

# Build wheel and source distribution
python -m build

# Verify contents
tar -tzf dist/sysmon_ai-0.1.0.tar.gz
unzip -l dist/sysmon_ai-0.1.0-py3-none-any.whl
```

### Test installation

```bash
# Create test environment
python -m venv test_env
source test_env/bin/activate

# Install wheel
pip install dist/sysmon_ai-0.1.0-py3-none-any.whl

# Test CLI
sysmon version
sysmon --help

deactivate
rm -rf test_env
```

### Upload to PyPI (Optional)

```bash
# Test PyPI first
twine upload --repository testpypi dist/*

# Production PyPI
twine upload dist/*
```

## Platform-Specific Notes

### macOS
- Code signing not required for personal use
- For distribution, consider notarization
- ARM64 (M1/M2) and x86_64 builds separate for PyInstaller

### Linux
- Build on oldest supported distro for compatibility
- Consider using manylinux wheels
- AppImage format alternative to PyInstaller

### Windows
- Build on Windows for Windows distribution
- May need Visual C++ redistributable
- Consider using Inno Setup for installer

## Size Comparison

| Method | Size | Notes |
|--------|------|-------|
| Wheel | ~50 KB | Dependencies downloaded separately |
| ZIP + source | ~1 MB | With docs and tests |
| Docker image | ~500 MB | Includes Python runtime |
| PyInstaller | ~80-120 MB | Self-contained |

## Summary

- **Wheel distribution** is the recommended method for Python users
- **setup.sh** is best for quick internal deployment  
- **Docker** is ideal for production/cloud deployment
- **PyInstaller** should be last resort for non-Python users
