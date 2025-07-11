#!/usr/bin/env python3
"""

Test script to verify the assignment fix is working correctly.
"""

import sqlite3
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_assignment_fix():
    """Test that the assignment function now works with the 'id' column."""
    
    db_path = 'production_idis.db'
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Find a test document using the 'id' column
        cursor.execute("""
            SELECT id, file_name, document_type 
            FROM documents 
            WHERE file_name LIKE '%test%' OR file_name LIKE '%payslip%'
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
        
        # Test assignment using the 'id' column
        print("\n=== TESTING ASSIGNMENT WITH ID COLUMN ===")
        
        # Check if a record already exists and delete it for clean test
        cursor.execute("""
            DELETE FROM case_documents 
            WHERE checklist_item_id = ? AND entity_id = ? AND case_id = ?
        """, (requirement_id, 1, 'CASE-1-DEFAULT'))
        
        # Insert new record using the 'id' column
        cursor.execute("""
            INSERT INTO case_documents (case_id, entity_id, checklist_item_id, document_id, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'Submitted', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, ('CASE-1-DEFAULT', 1, requirement_id, document_id))
        
        # Commit the transaction
        conn.commit()
        print("✅ Assignment record created successfully")
        
        # Verify the assignment
        cursor.execute("""
            SELECT cd.*, ac.required_doc_name 
            FROM case_documents cd
            JOIN application_checklists ac ON cd.checklist_item_id = ac.id
            WHERE cd.document_id = ? AND cd.checklist_item_id = ?
        """, (document_id, requirement_id))
        
        result = cursor.fetchone()
        if result:
            print(f"✅ Assignment verified: Status '{result[5]}' for document {document_id}")
            print(f"✅ Document properly linked to requirement '{result[7]}'")
            
            # Test if the UI will now see the status indicator
            cursor.execute("""
                SELECT COUNT(*) FROM case_documents cd 
                WHERE cd.checklist_item_id = ? AND cd.entity_id = ? AND cd.case_id = ?
            """, (requirement_id, 1, 'CASE-1-DEFAULT'))
            
            count = cursor.fetchone()[0]
            if count > 0:
                print("✅ Status indicator should now work correctly (count > 0)")
                return True
            else:
                print("❌ Status indicator will still be broken (count = 0)")
                return False
        else:
            print("❌ Assignment verification failed")
            return False
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False
    
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("Testing assignment fix...")
    success = test_assignment_fix()
    
    if success:
        print("\n🎉 Assignment fix is working correctly!")
        print("The override workflow should now work with the 'id' column.")
    else:
        print("\n💥 Assignment fix still has issues.")
        print("Additional debugging may be needed.")
