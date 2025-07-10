#!/usr/bin/env python3
"""
Debug script to test the unified uploader processing
"""

import os
import sys
from context_store import ContextStore
from unified_ingestion_agent import UnifiedIngestionAgent

def debug_process_file():
    """Debug processing of a simple text file"""
    
    # Create test file
    test_content = """
    Alaska Department of Health & Social Services
    Medicaid Payslip
    
    Employee: John Doe
    Date: 2025-07-10
    Amount: $1,234.56
    
    This is a test payslip for debugging the upload functionality.
    """
    
    test_file = "test_payslip.txt"
    
    # Write test file
    with open(test_file, 'w') as f:
        f.write(test_content)
    
    print(f"Created test file: {test_file}")
    
    # Initialize components
    context_store = ContextStore("production_idis.db")
    temp_folder = "data/temp_debug"
    holding_folder = "data/holding"
    
    # Create directories
    os.makedirs(temp_folder, exist_ok=True)
    os.makedirs(holding_folder, exist_ok=True)
    
    # Initialize agent
    agent = UnifiedIngestionAgent(
        context_store=context_store,
        watch_folder=temp_folder,
        holding_folder=holding_folder
    )
    
    print("Initialized UnifiedIngestionAgent")
    
    # Process file
    print(f"Processing file: {test_file}")
    result = agent._process_single_file(test_file, test_file, patient_id=1, session_id=1)
    
    print(f"Processing result: {result}")
    
    # Clean up
    if os.path.exists(test_file):
        os.remove(test_file)
    
    return result

if __name__ == "__main__":
    debug_process_file()