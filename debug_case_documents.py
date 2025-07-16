#!/usr/bin/env python3
"""
Debug script to investigate case document issues:
1. Document count mismatch between checklist and case documents
2. File retrieval errors 
3. Document-case linking problems
"""

import sqlite3
from context_store import ContextStore

def debug_case_documents():
    """Debug the case documents issues"""
    
    # Connect to the production database
    db_path = 'production_idis.db'
    context_store = ContextStore(db_path)
    
    print("=== DEBUGGING CASE DOCUMENTS ===\n")
    
    # 1. Check all tables structure
    print("1. DATABASE SCHEMA:")
    cursor = context_store.conn.cursor()
    
    # Check documents table
    cursor.execute("PRAGMA table_info(documents)")
    doc_columns = cursor.fetchall()
    print("Documents table columns:")
    for col in doc_columns:
        print(f"  - {col[1]} ({col[2]})")
    
    # Check case_documents table
    cursor.execute("PRAGMA table_info(case_documents)")
    case_doc_columns = cursor.fetchall()
    print("\nCase_documents table columns:")
    for col in case_doc_columns:
        print(f"  - {col[1]} ({col[2]})")
    
    # Check cases table
    cursor.execute("PRAGMA table_info(cases)")
    case_columns = cursor.fetchall()
    print("\nCases table columns:")
    for col in case_columns:
        print(f"  - {col[1]} ({col[2]})")
    
    # 2. Check all documents in the system
    print("\n2. ALL DOCUMENTS IN SYSTEM:")
    cursor.execute("SELECT id, file_name, document_type, entity_id, filed_path FROM documents ORDER BY id")
    all_docs = cursor.fetchall()
    print(f"Total documents: {len(all_docs)}")
    for doc in all_docs:
        print(f"  Doc ID: {doc[0]}, File: {doc[1]}, Type: {doc[2]}, Entity: {doc[3]}, Filed Path: {doc[4]}")
    
    # 3. Check all cases in the system
    print("\n3. ALL CASES IN SYSTEM:")
    cursor.execute("SELECT id, entity_id, case_type, status FROM cases ORDER BY id")
    all_cases = cursor.fetchall()
    print(f"Total cases: {len(all_cases)}")
    for case in all_cases:
        print(f"  Case ID: {case[0]}, Entity: {case[1]}, Type: {case[2]}, Status: {case[3]}")
    
    # 4. Check case_documents linking table
    print("\n4. CASE-DOCUMENT LINKS:")
    cursor.execute("SELECT case_id, document_id, checklist_item_id FROM case_documents ORDER BY case_id")
    case_doc_links = cursor.fetchall()
    print(f"Total case-document links: {len(case_doc_links)}")
    for link in case_doc_links:
        print(f"  Case: {link[0]}, Document: {link[1]}, Checklist Item: {link[2]}")
    
    # 5. For each case, show detailed document information
    print("\n5. DETAILED CASE-DOCUMENT ANALYSIS:")
    for case in all_cases:
        case_id = case[0]
        print(f"\nCase ID {case_id}:")
        
        # Get documents using the current query
        cursor.execute("""
            SELECT DISTINCT d.id, d.file_name, d.document_type, d.created_at, d.filed_path, d.full_text
            FROM documents d
            JOIN case_documents cd ON d.id = cd.document_id
            WHERE cd.case_id = ?
            ORDER BY d.created_at DESC
        """, (case_id,))
        
        case_docs = cursor.fetchall()
        print(f"  Documents found: {len(case_docs)}")
        for doc in case_docs:
            print(f"    ID: {doc[0]}, File: {doc[1]}, Type: {doc[2]}, Created: {doc[3]}")
            print(f"    Filed Path: {doc[4]}, Has Text: {doc[5] is not None}")
    
    # 6. Check file content storage - documents table doesn't have file_content column
    print("\n6. FILE CONTENT ANALYSIS:")
    cursor.execute("SELECT id, file_name, full_text IS NOT NULL as has_text, LENGTH(full_text) as text_size FROM documents")
    content_analysis = cursor.fetchall()
    for doc in content_analysis:
        print(f"  Doc {doc[0]} ({doc[1]}): Has Text: {doc[2]}, Text Size: {doc[3]} chars")
    
    # 7. Check if files exist at filed_path
    print("\n7. FILE PATH VERIFICATION:")
    import os
    for doc in all_docs:
        doc_id, file_name, doc_type, entity_id, filed_path = doc
        if filed_path:
            exists = os.path.exists(filed_path)
            print(f"  Doc {doc_id} ({file_name}): Path exists: {exists}")
            if exists:
                file_size = os.path.getsize(filed_path)
                print(f"    File size: {file_size} bytes")
        else:
            print(f"  Doc {doc_id} ({file_name}): No filed path")

if __name__ == "__main__":
    debug_case_documents()