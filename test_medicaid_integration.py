#!/usr/bin/env python3
"""
Test script to verify the Medicaid Navigator integration with the backend processing pipeline.
This simulates what happens when a user uploads a file through the UI.
"""

import os
import time
import sqlite3

def create_test_document():
    """Create a test document similar to what a user might upload."""
    test_content = """
ALASKA MEDICAID APPLICATION SUPPORTING DOCUMENT

Patient: Jane Smith
Date of Birth: 1990-05-15
Social Security Number: XXX-XX-1234

INCOME VERIFICATION - PAY STUB

Pay Period: June 1-15, 2025
Employer: Alaska Healthcare Services
Gross Pay: $2,840.00
Net Pay: $2,156.40

This document serves as proof of income for Medicaid application purposes.
"""
    return test_content

def test_integration():
    """Test the complete integration flow."""
    print("Testing Medicaid Navigator Integration")
    print("=" * 50)
    
    # Create the watch folder structure (same as what UI does)
    watch_folder = os.path.join("data", "scanner_output")
    os.makedirs(watch_folder, exist_ok=True)
    
    # Create a test document
    test_filename = "medicaid_test_paystub.txt"
    test_path = os.path.join(watch_folder, test_filename)
    
    print(f"1. Creating test document: {test_path}")
    with open(test_path, "w") as f:
        f.write(create_test_document())
    
    print("2. Document saved to watch folder (simulating UI upload)")
    print(f"   Watcher service should detect and process this file...")
    
    # Wait a moment for processing
    print("3. Waiting 15 seconds for processing...")
    time.sleep(15)
    
    # Check if document was processed by looking at the database
    db_path = "production_idis.db"
    if os.path.exists(db_path):
        print("4. Checking database for processed document...")
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check for documents in the database
            cursor.execute("SELECT file_name, document_type, processing_status, extracted_data FROM documents WHERE file_name = ?", (test_filename,))
            result = cursor.fetchone()
            
            if result:
                file_name, doc_type, status, extracted_data = result
                print(f"   ✅ Document found in database!")
                print(f"   File: {file_name}")
                print(f"   Type: {doc_type}")
                print(f"   Status: {status}")
                if extracted_data:
                    print(f"   Has AI-extracted data: {len(extracted_data)} characters")
                else:
                    print("   No AI-extracted data found")
            else:
                print(f"   ❌ Document not found in database yet")
                print(f"   This might mean processing is still in progress")
            
            conn.close()
            
        except Exception as e:
            print(f"   ❌ Error checking database: {e}")
    else:
        print("4. Database not found - processing may not have started yet")
    
    # Check archive folder
    archive_folder = os.path.join("data", "archive")
    if os.path.exists(archive_folder):
        archived_files = [f for f in os.listdir(archive_folder) if test_filename in f]
        if archived_files:
            print(f"5. ✅ File archived: {archived_files[0]}")
        else:
            print("5. File not yet archived (processing may be in progress)")
    else:
        print("5. Archive folder not found")
    
    print("\nIntegration test complete!")
    print("Check the Production Watcher Service logs for detailed processing information.")

if __name__ == "__main__":
    test_integration()