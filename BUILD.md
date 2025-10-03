# Building Executable Distribution

This document describes how to build a standalone executable for SysMon AI.

## Prerequisites

Install PyInstaller in your virtual environment:

```bash
source venv/bin/activate
pip install pyinstaller
```

## Building the Executable

### Option 1: Using PyInstaller spec file (Recommended)

```bash
pyinstaller sysmon.spec
```

This will create a single executable in `dist/sysmon`.

### Option 2: One-command build

```bash
pyinstaller --onefile \
    --name sysmon \
    --add-data "sysmon_ai/data/schema.sql:sysmon_ai/data" \
    --add-data "config.example.yaml:." \
    --hidden-import sklearn.utils._weight_vector \
    --hidden-import sklearn.neighbors._partition_nodes \
    --hidden-import sklearn.tree._utils \
    sysmon_ai/cli.py
```

## Testing the Executable

After building:

```bash
# Test the executable
./dist/sysmon version
./dist/sysmon init
./dist/sysmon --help
```

## Distribution

The standalone executable will be located at:
- macOS/Linux: `dist/sysmon`
- Windows: `dist/sysmon.exe`

### Size
Typical executable size: 50-80 MB (includes Python runtime and all dependencies)

### Distribution Package

Create a distributable archive:

```bash
# For macOS/Linux
tar -czf sysmon-macos-arm64.tar.gz -C dist sysmon README.md LICENSE config.example.yaml

# For Windows
zip -r sysmon-windows.zip dist/sysmon.exe README.md LICENSE config.example.yaml
```

## Platform-Specific Notes

### macOS
- First run may require: System Preferences > Security & Privacy > Allow
- For distribution, consider code signing with Apple Developer certificate

### Linux
- Executable built on one Linux distro should work on similar distros
- For wider compatibility, build on older distro (e.g., Ubuntu 18.04)

### Windows
- Build on Windows for Windows distribution
- Antivirus may flag PyInstaller executables (false positive)

## Troubleshooting

### Import errors at runtime
Add missing modules to `hiddenimports` in `sysmon.spec`

### File not found errors
Add missing data files to `datas` in `sysmon.spec`

### Executable too large
Use `--exclude-module` to remove unnecessary packages

### Runtime errors
Test in virtual environment first before building
