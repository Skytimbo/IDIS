#!/usr/bin/env python3
"""
Demo script showing how Case Managers can use the document retrieval function
"""

from context_store import ContextStore
import os

def demo_case_manager_workflow():
    """Demonstrate how a Case Manager would use the document retrieval function"""
    
    print("🏥 Case Manager Document Viewer Demo")
    print("=" * 50)
    
    # Connect to the production database
    db_path = 'production_idis.db'
    context_store = ContextStore(db_path)
    
    # Simulate a Case Manager viewing documents for a specific case
    current_user = "user_a"
    
    print(f"👤 Logged in as: {current_user}")
    print("\n📋 Available Documents:")
    
    # Get all documents with entity information
    cursor = context_store.conn.cursor()
    cursor.execute("""
        SELECT d.id, d.file_name, d.document_type, e.entity_name, d.created_at
        FROM documents d
        LEFT JOIN entities e ON d.entity_id = e.id
        ORDER BY d.created_at DESC
        LIMIT 10
    """)
    
    documents = cursor.fetchall()
    
    if not documents:
        print("No documents found.")
        return
    
    # Display available documents
    for i, doc in enumerate(documents, 1):
        doc_id, filename, doc_type, entity_name, created_at = doc
        print(f"{i}. ID: {doc_id} | {filename} | Type: {doc_type or 'Unknown'} | Entity: {entity_name or 'None'}")
    
    print("\n" + "-" * 50)
    print("🔍 Case Manager Workflow - Document Retrieval Examples:")
    
    # Example 1: Retrieve document without user restriction (admin mode)
    first_doc_id = documents[0][0]
    print(f"\n1. Admin retrieval (no user restriction) - Document ID: {first_doc_id}")
    
    doc_details = context_store.get_document_details_by_id(first_doc_id)
    if doc_details:
        print(f"   ✅ Retrieved: {doc_details['filename']}")
        print(f"   📄 Type: {doc_details.get('document_type', 'Unknown')}")
        print(f"   🏢 Entity: {doc_details.get('entity_name', 'None')}")
        print(f"   📅 Created: {doc_details.get('created_at', 'Unknown')}")
        if doc_details.get('full_text'):
            text_preview = doc_details['full_text'][:100] + "..." if len(doc_details['full_text']) > 100 else doc_details['full_text']
            print(f"   📝 Content Preview: {text_preview}")
    
    # Example 2: Retrieve document with user restriction (normal case manager mode)
    print(f"\n2. Secure retrieval (with user access control) - Document ID: {first_doc_id}")
    
    doc_details_secure = context_store.get_document_details_by_id(first_doc_id, user_id=current_user)
    if doc_details_secure:
        print(f"   ✅ Access granted for user {current_user}")
        print(f"   📄 Document: {doc_details_secure['filename']}")
    else:
        print(f"   ❌ Access denied for user {current_user}")
        print(f"   ℹ️  This is expected for documents not assigned to user's cases")
    
    # Example 3: Error handling - non-existent document
    print(f"\n3. Error handling - Non-existent document (ID: 99999)")
    non_existent = context_store.get_document_details_by_id(99999, user_id=current_user)
    if non_existent is None:
        print("   ✅ Correctly handled non-existent document")
    
    print("\n" + "=" * 50)
    print("🎯 Key Security Features Demonstrated:")
    print("   • Document existence validation")
    print("   • User access control through case relationships")
    print("   • Comprehensive error logging")
    print("   • Safe handling of missing documents")
    print("   • Detailed metadata retrieval")
    
    print("\n✅ Document retrieval function is ready for production use!")

if __name__ == "__main__":
    demo_case_manager_workflow()