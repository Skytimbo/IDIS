#!/usr/bin/env python3
"""
Test script to verify override functionality works at the database level.
This helps isolate whether the issue is with UI interaction or database operations.
"""

import logging
import sys
from context_store import ContextStore

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_override_assignment():
    """Test the assign_document_to_requirement function directly."""
    
    # Import the function from the Medicaid Navigator module
    sys.path.append('./modules/medicaid_navigator')
    from ui import assign_document_to_requirement
    
    # Get the database
    db_path = 'production_idis.db'
    context_store = ContextStore(db_path)
    
    # Find a test document (look for recent uploads)
    cursor = context_store.conn.cursor()
    cursor.execute("""
        SELECT document_id, file_name, document_type 
        FROM documents 
        WHERE document_type = 'Correspondence' OR document_type LIKE '%payslip%'
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
    
    # Test the assignment function with override
    print("\n=== TESTING OVERRIDE ASSIGNMENT ===")
    print(f"Assigning document {document_id} to requirement {requirement_id} with override=True")
    
    success = assign_document_to_requirement(
        document_id=document_id,
        requirement_id=requirement_id,
        patient_id=1,  # Default patient
        case_id='CASE-1-DEFAULT',  # Default case
        override=True,
        override_reason=f"Test override: {doc_type} → {req_name}"
    )
    
    if success:
        print("✅ Override assignment succeeded!")
        
        # Verify the assignment in the database
        cursor.execute("""
            SELECT cd.*, ac.required_doc_name 
            FROM case_documents cd
            JOIN application_checklists ac ON cd.checklist_item_id = ac.id
            WHERE cd.document_id = ? AND cd.checklist_item_id = ?
        """, (document_id, requirement_id))
        
        result = cursor.fetchone()
        if result:
            print(f"✅ Database verification: Found assignment with status '{result[5]}'")
            return True
        else:
            print("❌ Database verification: Assignment not found in database")
            return False
    else:
        print("❌ Override assignment failed!")
        return False

if __name__ == "__main__":
    print("Testing override functionality...")
    success = test_override_assignment()
    
    if success:
        print("\n🎉 Override functionality is working correctly!")
    else:
        print("\n💥 Override functionality has issues that need to be fixed.")
    
    sys.exit(0 if success else 1)