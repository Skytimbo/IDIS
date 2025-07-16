#!/usr/bin/env python3
"""
Test script to verify the document viewer fixes
"""

from context_store import ContextStore
import logging

def test_document_retrieval():
    """Test the document retrieval for different cases"""
    
    print("=== TESTING DOCUMENT RETRIEVAL FIXES ===\n")
    
    context_store = ContextStore('production_idis.db')
    cursor = context_store.conn.cursor()
    
    # Test case 1: Integer case ID (should work with both old and new formats)
    print("1. Testing integer case ID:")
    cursor.execute("""
        SELECT DISTINCT d.id, d.file_name, d.document_type, d.created_at, d.filed_path, d.full_text
        FROM documents d
        JOIN case_documents cd ON d.id = cd.document_id
        WHERE cd.case_id = ? OR cd.case_id = CAST(? AS TEXT)
        ORDER BY d.created_at DESC
    """, (1, 1))
    
    case_1_docs = cursor.fetchall()
    print(f"   Case 1 documents: {len(case_1_docs)}")
    for doc in case_1_docs:
        print(f"   - {doc[1]} ({doc[2]})")
    
    # Test case 2: String case ID (these were not working before)
    print("\n2. Testing string case ID:")
    cursor.execute("""
        SELECT DISTINCT d.id, d.file_name, d.document_type, d.created_at, d.filed_path, d.full_text
        FROM documents d
        JOIN case_documents cd ON d.id = cd.document_id
        WHERE cd.case_id = ? OR cd.case_id = CAST(? AS TEXT)
        ORDER BY d.created_at DESC
    """, ("CASE-ReplitNewEnvTest-20250716_212437", "CASE-ReplitNewEnvTest-20250716_212437"))
    
    case_string_docs = cursor.fetchall()
    print(f"   String case documents: {len(case_string_docs)}")
    for doc in case_string_docs:
        print(f"   - {doc[1]} ({doc[2]})")
    
    # Test case 3: Check specific document details
    print("\n3. Testing document details retrieval:")
    if case_string_docs:
        doc_id = case_string_docs[0][0]
        print(f"   Testing document ID: {doc_id}")
        
        # Test the secure retrieval function
        doc_details = context_store.get_document_details_by_id(doc_id, user_id="test_user")
        
        if doc_details:
            print(f"   Document details retrieved successfully:")
            print(f"   - Filename: {doc_details.get('filename')}")
            print(f"   - Document Type: {doc_details.get('document_type')}")
            print(f"   - Has Text: {doc_details.get('full_text') is not None}")
            print(f"   - Filed Path: {doc_details.get('filed_path')}")
        else:
            print("   Document details retrieval failed")
    
    # Test case 4: Check file content vs full_text
    print("\n4. Testing data structure fixes:")
    cursor.execute("SELECT id, file_name, full_text IS NOT NULL as has_text, filed_path FROM documents LIMIT 5")
    sample_docs = cursor.fetchall()
    
    for doc in sample_docs:
        print(f"   Doc {doc[0]} ({doc[1]}): Has Text: {doc[2]}, Filed Path: {doc[3]}")
    
    print("\n=== TEST COMPLETE ===")

if __name__ == "__main__":
    test_document_retrieval()