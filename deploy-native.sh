#!/bin/bash

# IDIS Native Replit Deployment Script
# This script runs the IDIS application directly in Replit's environment without Docker

echo "Starting IDIS Native Deployment..."
echo "=================================="

# Check if required environment variables are set
if [ -z "$OPENAI_API_KEY" ]; then
    echo "Warning: OPENAI_API_KEY environment variable is not set"
    echo "The application will not be able to use AI-powered features"
fi

# Create necessary directories
echo "Creating required directories..."
mkdir -p data/scanner_output
mkdir -p data/inbox  
mkdir -p data/holding
mkdir -p data/archive
mkdir -p data/coversheets

# Ensure the production database file exists
if [ ! -f "production_idis.db" ]; then
    echo "Initializing database with proper schema..."
    python3 -c "
from context_store import ContextStore
print('Creating database with proper schema...')
cs = ContextStore('production_idis.db')
print('Database initialized successfully')
"
    # Also add case management tables if the script exists
    if [ -f "init_case_management_db.py" ]; then
        echo "Adding case management tables..."
        python3 init_case_management_db.py production_idis.db
    fi
fi

# Install/update Python dependencies (skip if already installed)
echo "Checking Python dependencies..."
pip install -r requirements.txt --quiet

# Check if port 5000 is already in use
if lsof -i:5000 >/dev/null 2>&1; then
    echo "Port 5000 is already in use - application may already be running"
    echo "Check your existing workflows or use a different port"
    echo "You can access the application at the existing URL"
    exit 0
fi

# Check if watcher service is already running
if pgrep -f "watcher_service.py" > /dev/null; then
    echo "✅ Document watcher service is already running"
else
    echo "Starting document watcher service..."
    python3 watcher_service.py \
      --watch-folder ./data/scanner_output \
      --inbox-folder ./data/inbox \
      --holding-folder ./data/holding \
      --archive-folder ./data/archive \
      --cover-sheets-folder ./data/coversheets \
      --db-path ./production_idis.db \
      --openai &
    
    # Give the watcher service a moment to start
    sleep 2
    echo "✅ Document watcher service started"
fi

# Start the main Streamlit application
echo "Starting IDIS application..."
echo "✅ Access the application at the URL provided by Replit"
echo "✅ Database: production_idis.db"
echo ""

# Use the same configuration as the working workflow
STREAMLIT_SERVER_HEADLESS=true streamlit run app.py \
  --server.port 5000 \
  --server.address 0.0.0.0 \
  -- --database-path production_idis.db \
  --archive-path data/archive