#!/bin/bash

# Set project directory to the directory where this script is located
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR" || {
    echo "ERROR: Could not change to project directory $PROJECT_DIR"
    exit 1
}

# Step 1: Stop any running Uvicorn processes
echo "Stopping any running Python processes..."
pkill -f "uvicorn" 2>/dev/null && echo "Stopped running Uvicorn processes."

# Step 2: Clear __pycache__ directories
echo "Clearing __pycache__ directories..."
find . -type d -name "__pycache__" -exec rm -rf {} +
echo "Done."

# Step 3: Activate venv (assumes venv exists)
echo "Activating virtual environment..."
if [ ! -d "venv" ]; then
    echo "ERROR: venv directory not found. Creating one..."
    python3 -m venv venv
fi
source venv/bin/activate || {
    echo "ERROR: Failed to activate virtual environment"
    exit 1
}
echo "Done."

# Step 4: Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt || {
    echo "ERROR: Failed to install dependencies"
    exit 1
}
echo "Done."

# Step 5: Run Uvicorn with no cache
echo "Starting Uvicorn with cleared cache..."
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
echo "If you see 'Application startup complete', Uvicorn is running."
