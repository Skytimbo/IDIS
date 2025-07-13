#!/usr/bin/env python3
"""
Direct database test for override functionality - no Streamlit dependencies.
"""

import sqlite3
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_direct_database_override():
    """Test assignment directly via database operations."""
    
    db_path = 'production_idis.db'
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Find a test document
        cursor.execute("""
            SELECT document_id, file_name, document_type 
            FROM documents 
            WHERE document_type = 'Correspondence' OR document_type LIKE '%payslip%' OR file_name LIKE '%test%'
            ORDER BY upload_timestamp DESC 
            LIMIT 1
        """)
        
        doc_result = cursor.fetchone()
        if not doc_result:
            print("ERROR: No test document found")
            return False
        
        document_id, filename, doc_type = doc_result
        print(f"Found test document: ID={document_id}, filename={filename}, type={doc_type}")
        
        # Find the "Proof of Income" requirement
        cursor.execute("""
            SELECT id, required_doc_name 
            FROM application_checklists 
            WHERE required_doc_name = 'Proof of Income'
            LIMIT 1
        """)
        
        req_result = cursor.fetchone()
        if not req_result:
            print("ERROR: 'Proof of Income' requirement not found")
            return False
        
        requirement_id, req_name = req_result
        print(f"Found requirement: ID={requirement_id}, name={req_name}")
        
        # Test direct database assignment
        print("\n=== TESTING DIRECT DATABASE ASSIGNMENT ===")
        
        # Check if a record already exists
        cursor.execute("""
            SELECT id FROM case_documents 
            WHERE checklist_item_id = ? AND entity_id = ? AND case_id = ?
        """, (requirement_id, 1, 'CASE-1-DEFAULT'))
        
        existing_record = cursor.fetchone()
        
        if existing_record:
            print(f"Found existing record: {existing_record[0]}")
            # Update existing record
            cursor.execute("""
                UPDATE case_documents 
                SET document_id = ?, status = 'Submitted', updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (document_id, existing_record[0]))
            print("Updated existing record")
        else:
            # Insert new record
            cursor.execute("""
                INSERT INTO case_documents (case_id, entity_id, checklist_item_id, document_id, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'Submitted', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, ('CASE-1-DEFAULT', 1, requirement_id, document_id))
            print("Inserted new record")
        
        # Commit the transaction
        conn.commit()
        print("✅ Database transaction committed successfully")
        
        # Verify the assignment
        cursor.execute("""
            SELECT cd.*, ac.required_doc_name 
            FROM case_documents cd
            JOIN application_checklists ac ON cd.checklist_item_id = ac.id
            WHERE cd.document_id = ? AND cd.checklist_item_id = ?
        """, (document_id, requirement_id))
        
        result = cursor.fetchone()
        if result:
            print(f"✅ Verification successful: Assignment found with status '{result[5]}'")
            return True
        else:
            print("❌ Verification failed: Assignment not found")
            return False
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False
    
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("Testing direct database override functionality...")
    success = test_direct_database_override()
    
    if success:
        print("\n🎉 Direct database assignment is working correctly!")
        print("This suggests the issue is with the Streamlit UI interaction, not the database logic.")
    else:
        print("\n💥 Direct database assignment failed!")
        print("The issue is at the database level.")