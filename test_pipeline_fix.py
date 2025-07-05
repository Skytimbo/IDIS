#!/usr/bin/env python3
"""
Test script to verify the two-part fix for the document processing pipeline.
"""

import os
import time
import sqlite3

def create_test_document():
    """Create a test document to verify the pipeline fixes."""
    test_content = """
ALASKA MEDICAID VERIFICATION DOCUMENT

Patient: John Doe
Date: July 5, 2025
Document Type: Income Verification

PAYROLL STATEMENT
Employer: Alaska Medical Center
Pay Period: June 15-30, 2025
Gross Income: $3,200.00
Net Income: $2,400.00
Year-to-Date: $19,200.00

This document is provided for Medicaid eligibility verification purposes.
"""
    return test_content

def test_pipeline_fixes():
    """Test the complete pipeline with both fixes applied."""
    print("Testing Pipeline Fixes")
    print("=" * 40)
    
    # Create the watch folder structure
    watch_folder = os.path.join("data", "scanner_output")
    os.makedirs(watch_folder, exist_ok=True)
    
    # Create a test document
    test_filename = "pipeline_test_verification.txt"
    test_path = os.path.join(watch_folder, test_filename)
    
    print(f"1. Creating test document: {test_path}")
    with open(test_path, "w") as f:
        f.write(create_test_document())
    
    print("2. Document saved to watch folder")
    print("   Production Watcher Service should detect and process this file...")
    print("   With our fixes:")
    print("   - Part 1: TaggerAgent should find the file and archive it properly")
    print("   - Part 2: Console should be clean with no fontTools/PDF library noise")
    
    # Wait for processing
    print("3. Waiting 20 seconds for processing...")
    time.sleep(20)
    
    # Check if document was processed
    db_path = "production_idis.db"
    if os.path.exists(db_path):
        print("4. Checking database for processed document...")
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check for the test document
            cursor.execute("SELECT file_name, processing_status, filed_path FROM documents WHERE file_name = ?", (test_filename,))
            result = cursor.fetchone()
            
            if result:
                file_name, status, filed_path = result
                print(f"   ✅ Document found in database!")
                print(f"   File: {file_name}")
                print(f"   Status: {status}")
                print(f"   Filed Path: {filed_path}")
                
                if status == "filed" and filed_path:
                    print("   ✅ TaggerAgent successfully filed the document!")
                    
                    # Check if file actually exists in archive
                    if os.path.exists(filed_path):
                        print("   ✅ File confirmed in archive location!")
                    else:
                        print("   ❌ File not found at filed path")
                else:
                    print("   ❌ Document not properly filed")
            else:
                print(f"   ❌ Document not found in database")
            
            conn.close()
            
        except Exception as e:
            print(f"   ❌ Error checking database: {e}")
    else:
        print("4. Database not found")
    
    print("\nPipeline fix test complete!")
    print("Check the Production Watcher Service logs to verify:")
    print("- Clean console output (no fontTools/PDF noise)")
    print("- Successful file path correction and archiving")

if __name__ == "__main__":
    test_pipeline_fixes()