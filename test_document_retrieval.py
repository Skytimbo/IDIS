#!/usr/bin/env python3
"""
Test script for the new get_document_details_by_id function
"""

import sys
import os
from context_store import ContextStore

def test_document_retrieval():
    """Test the new document retrieval function"""
    
    # Connect to the production database
    db_path = 'production_idis.db'
    
    if not os.path.exists(db_path):
        print(f"Database {db_path} not found. Please run the application first.")
        return
    
    try:
        context_store = ContextStore(db_path)
        
        # Get the first few documents to test with
        cursor = context_store.conn.cursor()
        cursor.execute("SELECT id, file_name, entity_id FROM documents LIMIT 5")
        documents = cursor.fetchall()
        
        if not documents:
            print("No documents found in the database.")
            return
        
        print("Testing document retrieval function:")
        print("-" * 50)
        
        for doc in documents:
            doc_id, filename, entity_id = doc
            print(f"\nTesting document ID: {doc_id}")
            print(f"Original filename: {filename}")
            
            # Test without user_id (should work)
            result = context_store.get_document_details_by_id(doc_id)
            if result:
                print(f"✅ Retrieved without user_id: {result['filename']}")
                print(f"   Entity: {result.get('entity_name', 'N/A')}")
                print(f"   Document type: {result.get('document_type', 'N/A')}")
                print(f"   Content type: {result.get('content_type', 'N/A')}")
            else:
                print("❌ Failed to retrieve without user_id")
            
            # Test with user_id (access control)
            result_with_user = context_store.get_document_details_by_id(doc_id, user_id="user_a")
            if result_with_user:
                print(f"✅ Retrieved with user_id: {result_with_user['filename']}")
            else:
                print("⚠️  Access denied with user_id (this may be expected)")
        
        # Test with non-existent document
        print(f"\nTesting non-existent document (ID: 99999):")
        result = context_store.get_document_details_by_id(99999)
        if result is None:
            print("✅ Correctly returned None for non-existent document")
        else:
            print("❌ Should have returned None for non-existent document")
            
        print("\n" + "=" * 50)
        print("Document retrieval function test completed!")
        
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_document_retrieval()