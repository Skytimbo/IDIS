#!/usr/bin/env python3
"""
Debug script to check the checklist status and case_documents table
"""

from context_store import ContextStore
import sqlite3

def debug_checklist_status():
    """Debug the checklist status issue"""
    
    store = ContextStore("production_idis.db")
    
    print("=== CHECKLIST ITEMS ===")
    cursor = store.conn.execute("""
        SELECT id, required_doc_name, description 
        FROM application_checklists 
        WHERE checklist_name = 'SOA Medicaid - Adult'
        ORDER BY id
    """)
    
    checklist_items = cursor.fetchall()
    for item in checklist_items:
        print(f"ID: {item[0]}, Name: {item[1]}, Description: {item[2]}")
    
    print("\n=== CASE DOCUMENTS ===")
    cursor = store.conn.execute("""
        SELECT id, case_id, patient_id, checklist_item_id, document_id, status, created_at, updated_at
        FROM case_documents
        ORDER BY id DESC
    """)
    
    case_docs = cursor.fetchall()
    if case_docs:
        for doc in case_docs:
            print(f"ID: {doc[0]}, Case: {doc[1]}, Patient: {doc[2]}, Checklist Item: {doc[3]}, Document: {doc[4]}, Status: {doc[5]}")
    else:
        print("No case documents found")
    
    print("\n=== CHECKLIST WITH STATUS ===")
    cursor = store.conn.execute("""
        SELECT ac.id, ac.required_doc_name, ac.description,
               CASE 
                   WHEN cd.status = 'Submitted' THEN '🔵 Submitted'
                   ELSE '🔴 Missing'
               END as status,
               cd.document_id, cd.status as actual_status
        FROM application_checklists ac
        LEFT JOIN case_documents cd ON ac.id = cd.checklist_item_id 
            AND cd.patient_id = 1
        WHERE ac.checklist_name = 'SOA Medicaid - Adult'
        ORDER BY ac.id
    """)
    
    status_items = cursor.fetchall()
    for item in status_items:
        print(f"ID: {item[0]}, Name: {item[1]}, Status: {item[3]}, Document ID: {item[4]}, Actual Status: {item[5]}")
    
    print("\n=== RECENT DOCUMENTS ===")
    cursor = store.conn.execute("""
        SELECT ROWID, file_name, document_type, processing_status, upload_timestamp
        FROM documents
        ORDER BY ROWID DESC
        LIMIT 3
    """)
    
    recent_docs = cursor.fetchall()
    for doc in recent_docs:
        print(f"ROWID: {doc[0]}, File: {doc[1]}, Type: {doc[2]}, Status: {doc[3]}, Time: {doc[4]}")
    
    print("\n=== DATABASE SCHEMA ===")
    cursor = store.conn.execute("PRAGMA table_info(case_documents)")
    schema = cursor.fetchall()
    for col in schema:
        print(f"Column: {col[1]}, Type: {col[2]}, NotNull: {col[3]}, Default: {col[4]}")
    
    store.conn.close()

if __name__ == "__main__":
    debug_checklist_status()