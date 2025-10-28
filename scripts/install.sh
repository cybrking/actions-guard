#!/bin/bash
# Installation script for ActionsGuard

set -e

echo "Installing ActionsGuard..."

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "Error: Python 3.8 or higher is required"
    exit 1
fi

# Install ActionsGuard
pip3 install actionsguard

# Check if Scorecard is installed
if ! command -v scorecard &> /dev/null; then
    echo "Warning: OpenSSF Scorecard is not installed"
    echo "Install it with Homebrew:"
    echo "  brew install scorecard"
    echo ""
    echo "Don't have Homebrew? Install it first:"
    echo "  https://brew.sh"
fi

echo "ActionsGuard installed successfully!"
echo "Run 'actionsguard --help' to get started"
