#!/bin/bash
# Chief of Staff Hub - Quick Start Script
# Usage: ./start.sh

cd "$(dirname "$0")"

# Activate virtual environment
source .venv/bin/activate

# Run the app
echo "Starting Chief of Staff Hub..."
echo "Open http://localhost:8000 in your browser"
echo ""
python run.py
