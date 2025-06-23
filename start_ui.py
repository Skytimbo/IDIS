#!/usr/bin/env python3
"""
Custom UI startup script that bypasses Streamlit's email prompt
and starts the QuantaIQ interface properly.
"""

import subprocess
import sys
import os

def start_streamlit():
    """Start Streamlit with proper configuration to bypass email prompt."""
    
    # Change to the quanta_ui directory
    os.chdir('quanta_ui')
    
    # Start Streamlit with echo to handle email prompt automatically
    cmd = 'echo "" | streamlit run app.py --server.port 5000 --server.address 0.0.0.0'
    
    print("Starting QuantaIQ UI...")
    print(f"Command: {cmd}")
    
    # Execute the command with shell=True to handle the pipe properly
    process = subprocess.run(cmd, shell=True)
    
if __name__ == '__main__':
    start_streamlit()