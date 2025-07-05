#!/bin/bash
#
# Production Watcher Service for Medicaid Navigator Integration
# This script starts the watcher service monitoring the data/scanner_output folder
# where the Medicaid Navigator UI saves uploaded files.
#

# Create necessary directories if they don't exist
mkdir -p data/scanner_output
mkdir -p data/inbox
mkdir -p data/holding
mkdir -p data/archive
mkdir -p data/coversheets

# Set logging level for clean output (can be overridden with environment variable)
export LOGGING_LEVEL="${LOGGING_LEVEL:-WARNING}"

echo "Starting IDIS Watcher Service for Medicaid Navigator Integration..."
echo "Watch folder: data/scanner_output"
echo "Database: production_idis.db"
echo "Logging level: $LOGGING_LEVEL"
echo ""

# Start the watcher service with production configuration
python watcher_service.py \
    --watch-folder ./data/scanner_output \
    --inbox-folder ./data/inbox \
    --holding-folder ./data/holding \
    --archive-folder ./data/archive \
    --cover-sheets-folder ./data/coversheets \
    --db-path ./production_idis.db \
    --openai \
    --user-id medicaid_navigator_system