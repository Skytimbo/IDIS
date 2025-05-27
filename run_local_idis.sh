#!/usr/bin/env bash

# IDIS Local Runner Script
# This script simplifies running the IDIS MVP pipeline on a local Linux machine

# Change to the script's directory (project root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate the Python Virtual Environment
if [ -f "./venv/bin/activate" ]; then
    echo "Activating Python virtual environment..."
    source ./venv/bin/activate
else
    echo "Error: Virtual environment 'venv' not found in ./venv. Please set it up first."
    exit 1
fi

# Check for OPENAI_API_KEY
if [ -z "$OPENAI_API_KEY" ]; then
    echo "WARNING: OPENAI_API_KEY is not set. Summarization features requiring OpenAI will be skipped or may fail. You can set it by running 'export OPENAI_API_KEY=your_key' or by sourcing your .bashrc/.zshrc if configured there."
fi

# Execute run_mvp.py with default arguments and pass through any additional arguments
echo "Starting IDIS MVP Pipeline..."
python3 run_mvp.py \
    --watch-folder "$HOME/IDIS_Dell_Scan_Test/scanner_output" \
    --holding-folder "$HOME/IDIS_Dell_Scan_Test/idis_holding" \
    --archive-folder "$HOME/IDIS_Dell_Scan_Test/idis_archive" \
    --cover-sheets-folder "$HOME/IDIS_Dell_Scan_Test/idis_coversheets" \
    --db-path "$HOME/IDIS_Dell_Scan_Test/idis_db_storage/idis_live_test.db" \
    --openai \
    --keep-temp-files \
    "$@"

# Post-execution message
echo ""
echo "IDIS pipeline run initiated. Check console output from run_mvp.py for details."
echo "Output folders (if defaults were used):"
echo "  watch_folder=$HOME/IDIS_Dell_Scan_Test/scanner_output"
echo "  archive_folder=$HOME/IDIS_Dell_Scan_Test/idis_archive"
echo "  cover_sheets_folder=$HOME/IDIS_Dell_Scan_Test/idis_coversheets"
echo "  db_path=$HOME/IDIS_Dell_Scan_Test/idis_db_storage/idis_live_test.db"