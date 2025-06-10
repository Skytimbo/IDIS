#!/bin/bash

# QuantaIQ Document Search UI Launcher
# This script runs the Streamlit interface for the IDIS system

echo "Starting QuantaIQ Document Search Interface..."
echo "Database: idis_live_test.db"
echo "Interface: Streamlit Web Application"
echo ""

# Check if database exists
if [ ! -f "idis_live_test.db" ]; then
    echo "Warning: Database file 'idis_live_test.db' not found."
    echo "You may need to run the IDIS pipeline first to create documents."
    echo ""
fi

# Launch Streamlit application
echo "Launching web interface on http://localhost:8501"
echo "Press Ctrl+C to stop the server"
echo ""

streamlit run app.py --server.port 8501 --server.address 0.0.0.0