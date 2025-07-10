#!/usr/bin/env python3
"""
Test script to verify the assignment fix works correctly
"""

from context_store import ContextStore
import sqlite3

def test_assignment_fix():
    """Test the assignment fix by manually inserting a record"""
    
    store = ContextStore("production_idis.db")
    
    # First, let's find the GCI invoice document ID
    cursor = store.conn.execute("""
        SELECT ROWID, file_name, document_type 
        FROM documents 
        WHERE file_name = 'GCI invoice.pdf'
    """)
    
    doc_result = cursor.fetchone()
    if doc_result:
        document_id = doc_result[0]
        print(f"Found document: ID={document_id}, File={doc_result[1]}, Type={doc_result[2]}")
        
        # Test inserting a case_documents record for "Proof of Alaska Residency" (ID=3)
        requirement_id = 3
        patient_id = 1
        case_id = "1"  # Use string as required by schema
        
        try:
            cursor.execute("""
                INSERT INTO case_documents (case_id, patient_id, checklist_item_id, document_id, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'Submitted', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (case_id, patient_id, requirement_id, document_id))
            
            store.conn.commit()
            print(f"✅ Successfully inserted case_documents record")
            
            # Verify the record was inserted
            cursor.execute("""
                SELECT id, case_id, patient_id, checklist_item_id, document_id, status
                FROM case_documents
                WHERE checklist_item_id = ? AND patient_id = ?
            """, (requirement_id, patient_id))
            
            result = cursor.fetchone()
            if result:
                print(f"✅ Record verified: ID={result[0]}, Case={result[1]}, Patient={result[2]}, Checklist={result[3]}, Document={result[4]}, Status={result[5]}")
            else:
                print("❌ Record not found after insertion")
                
        except Exception as e:
            print(f"❌ Error inserting record: {e}")
            
    else:
        print("❌ GCI invoice document not found")
    
    # Now test the status query
    print("\n=== TESTING STATUS QUERY ===")
    cursor = store.conn.execute("""
        SELECT ac.id, ac.required_doc_name, ac.description,
               CASE 
                   WHEN cd.status = 'Submitted' THEN '🔵 Submitted'
                   ELSE '🔴 Missing'
               END as status,
               cd.document_id
        FROM application_checklists ac
        LEFT JOIN case_documents cd ON ac.id = cd.checklist_item_id 
            AND cd.patient_id = 1
        WHERE ac.checklist_name = 'SOA Medicaid - Adult'
        ORDER BY ac.id
    """)
    
    status_items = cursor.fetchall()
    for item in status_items:
        print(f"ID: {item[0]}, Name: {item[1]}, Status: {item[3]}, Document ID: {item[4]}")
    
    store.conn.close()

if __name__ == "__main__":
    test_assignment_fix()