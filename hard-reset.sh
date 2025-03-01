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

# Step 3: Delete existing venv
echo "Deleting existing virtual environment..."
if [ -d "venv" ]; then
    rm -rf venv
    echo "Cleared venv directory."
else
    echo "No venv directory found, skipping."
fi

# Step 4: Recreate venv
echo "Creating new virtual environment..."
python3 -m venv venv || {
    echo "ERROR: Failed to create virtual environment"
    exit 1
}
echo "Done."

# Step 5: Activate venv and install dependencies
echo "Activating venv and installing dependencies..."
source venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt || {
    echo "ERROR: Failed to install dependencies"
    exit 1
}
echo "Done."

# Step 6: Start Uvicorn
echo "Starting Uvicorn to reload .env..."
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
echo "If you see 'Application startup complete', the env is reloaded."
