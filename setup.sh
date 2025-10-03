#!/bin/bash
# Setup script for SysMon AI

set -e

echo "======================================"
echo "SysMon AI Setup"
echo "======================================"
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.10"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python 3.10+ required (found $python_version)"
    exit 1
fi
echo "✓ Python $python_version"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo "✓ Activated"
echo ""

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip -q
echo "✓ pip upgraded"
echo ""

# Install package
echo "Installing sysmon-ai with development dependencies..."
pip install -e ".[dev]" -q
echo "✓ Installed"
echo ""

# Install pre-commit hooks
echo "Setting up pre-commit hooks..."
pre-commit install
echo "✓ Pre-commit hooks installed"
echo ""

# Verify installation
echo "Verifying installation..."
python3 verify_installation.py

echo ""
echo "======================================"
echo "Setup Complete!"
echo "======================================"
echo ""
echo "To get started:"
echo "  1. Activate the virtual environment:"
echo "     source venv/bin/activate"
echo ""
echo "  2. Initialize SysMon:"
echo "     sysmon init"
echo ""
echo "  3. Start collecting metrics:"
echo "     sysmon start --duration 1h"
echo ""
echo "  4. Launch dashboard:"
echo "     sysmon dashboard"
echo ""
echo "For more details, see QUICKSTART.md"
echo ""
