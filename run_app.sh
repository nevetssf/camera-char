#!/bin/bash
# Quick start script for Camera Sensor Analyzer Desktop App

echo "Camera Sensor Analyzer - Desktop Application"
echo "=============================================="
echo ""

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    echo "ERROR: main.py not found"
    echo "Please run this script from the camera-char directory"
    exit 1
fi

if [ ! -f "aggregate_analysis.csv" ]; then
    echo "ERROR: aggregate_analysis.csv not found"
    echo "Please ensure you're in the camera-char project directory"
    exit 1
fi

# Check if virtual environment exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Run the application
echo "Starting Camera Sensor Analyzer..."
echo ""
python3 main.py

# Deactivate virtual environment if it was activated
if [ -n "$VIRTUAL_ENV" ]; then
    deactivate
fi
