#!/usr/bin/env python3
"""
Simple test script to verify the Medicaid Navigator integration without Streamlit dependencies.
"""

import sys
import os
from context_store import ContextStore

# Add the modules path to enable imports
sys.path.append('./modules/medicaid_navigator')

def test_medicaid_assignment():
    """Test the Medicaid Navigator assignment functionality."""
    
    print("=== MEDICAID NAVIGATOR ASSIGNMENT TEST ===")
    
    # Initialize the database connection
    context_store = ContextStore('production_idis.db')
    
    # Import the assignment function
    from ui import assign_document_to_requirement
    
    # Get test data
    cursor = context_store.conn.cursor()
    
    # Find a test document
    cursor.execute("""
        SELECT id, file_name, document_type 
        FROM documents 
        WHERE file_name LIKE '%test%' 
        ORDER BY upload_timestamp DESC 
        LIMIT 1
    """)
    
    doc_result = cursor.fetchone()
    if not doc_result:
        print("ERROR: No test document found")
        return False
    
    document_id, filename, doc_type = doc_result
    print(f"Test document: {filename} (ID: {document_id}, Type: {doc_type})")
    
    # Get requirement
    cursor.execute("""
        SELECT id, required_doc_name FROM application_checklists 
        WHERE required_doc_name = 'Proof of Income'
        LIMIT 1
    """)
    
    req_result = cursor.fetchone()
    if not req_result:
        print("ERROR: 'Proof of Income' requirement not found")
        return False
    
    requirement_id, req_name = req_result
    print(f"Requirement: {req_name} (ID: {requirement_id})")
    
    # Clean up any existing assignment
    cursor.execute("""
        DELETE FROM case_documents 
        WHERE checklist_item_id = ? AND entity_id = ? AND case_id = ?
    """, (requirement_id, 1, 'CASE-1-DEFAULT'))
    context_store.conn.commit()
    
    # Test the assignment with override
    print("\nTesting override assignment...")
    success = assign_document_to_requirement(
        document_id=document_id,
        requirement_id=requirement_id,
        patient_id=1,
        case_id='CASE-1-DEFAULT',
        override=True,
        override_reason=f"Test: {doc_type} → {req_name}"
    )
    
    if success:
        print("✅ Assignment successful!")
        
        # Verify the status indicator logic
        cursor.execute("""
            SELECT COUNT(*) FROM case_documents 
            WHERE checklist_item_id = ? AND entity_id = ? AND case_id = ?
        """, (requirement_id, 1, 'CASE-1-DEFAULT'))
        
        count = cursor.fetchone()[0]
        print(f"Status indicator check: {count} record(s) found")
        
        if count > 0:
            print("✅ Status indicator will show '🔵 Submitted'")
            
            # Check the actual assignment
            cursor.execute("""
                SELECT cd.status, d.file_name, ac.required_doc_name
                FROM case_documents cd
                JOIN documents d ON cd.document_id = d.id
                JOIN application_checklists ac ON cd.checklist_item_id = ac.id
                WHERE cd.document_id = ? AND cd.checklist_item_id = ?
            """, (document_id, requirement_id))
            
            result = cursor.fetchone()
            if result:
                status, doc_name, req_name = result
                print(f"✅ Assignment verified: '{doc_name}' → '{req_name}' (Status: {status})")
                
                print("\n🎉 MEDICAID NAVIGATOR INTEGRATION SUCCESSFUL!")
                print("The override functionality is working correctly.")
                return True
            else:
                print("❌ Assignment verification failed")
                return False
        else:
            print("❌ Status indicator will not work properly")
            return False
    else:
        print("❌ Assignment failed")
        return False

if __name__ == "__main__":
    success = test_medicaid_assignment()
    
    if success:
        print("\n✅ All tests passed! The Medicaid Navigator is ready for use.")
    else:
        print("\n❌ Tests failed. Check the implementation.")
    
    sys.exit(0 if success else 1)