#!/bin/bash

# IDIS Watcher Service Startup Script
# This script provides a standardized way to launch the continuous document processing service
# with all the required Dell testing setup paths and environment checks.

set -e  # Exit on any error

# Navigate to the script's directory (project root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 Starting IDIS Watcher Service from: $SCRIPT_DIR"

# Check and activate Python virtual environment
if [ -d "venv" ]; then
    echo "📦 Activating Python virtual environment..."
    source venv/bin/activate
else
    echo "❌ ERROR: Python virtual environment (venv) not found!"
    echo "Please create a virtual environment first:"
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

# Check OpenAI API Key
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  WARNING: OPENAI_API_KEY environment variable is not set!"
    echo "   The watcher service will run but OpenAI features will be disabled."
    echo "   To enable OpenAI features, set your API key:"
    echo "   export OPENAI_API_KEY='your-api-key-here'"
    echo ""
else
    echo "✅ OpenAI API key is configured"
fi

# Create Dell testing directories if they don't exist
echo "📁 Ensuring Dell testing directories exist..."
mkdir -p ~/IDIS_Dell_Scan_Test/scanner_output
mkdir -p ~/IDIS_Dell_Scan_Test/idis_inbox
mkdir -p ~/IDIS_Dell_Scan_Test/idis_holding
mkdir -p ~/IDIS_Dell_Scan_Test/idis_archive
mkdir -p ~/IDIS_Dell_Scan_Test/idis_coversheets
mkdir -p ~/IDIS_Dell_Scan_Test/idis_db_storage

echo "🔄 Launching IDIS Watcher Service with Triage Architecture..."
echo "   Watch folder: ~/IDIS_Dell_Scan_Test/scanner_output"
echo "   Inbox folder: ~/IDIS_Dell_Scan_Test/idis_inbox"
echo "   Holding folder: ~/IDIS_Dell_Scan_Test/idis_holding"
echo "   Archive folder: ~/IDIS_Dell_Scan_Test/idis_archive"
echo "   Cover sheets: ~/IDIS_Dell_Scan_Test/idis_coversheets"
echo "   Database: ~/IDIS_Dell_Scan_Test/idis_db_storage/idis_live_test.db"
echo ""

# Launch the watcher service with Dell testing paths and triage architecture
python3 watcher_service.py \
    --watch-folder ~/IDIS_Dell_Scan_Test/scanner_output \
    --inbox-folder ~/IDIS_Dell_Scan_Test/idis_inbox \
    --holding-folder ~/IDIS_Dell_Scan_Test/idis_holding \
    --archive-folder ~/IDIS_Dell_Scan_Test/idis_archive \
    --cover-sheets-folder ~/IDIS_Dell_Scan_Test/idis_coversheets \
    --db-path ~/IDIS_Dell_Scan_Test/idis_db_storage/idis_live_test.db \
    --openai