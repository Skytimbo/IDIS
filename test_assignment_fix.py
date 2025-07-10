#!/usr/bin/env python3
"""
Test script to verify the override assignment functionality works correctly.
This script simulates the exact flow that happens when the Override button is clicked.
"""

import sys
sys.path.append('modules/medicaid_navigator')
from ui import assign_document_to_requirement
import sqlite3

def test_override_assignment():
    """Test the override assignment functionality."""
    
    # Test parameters - simulating a real scenario
    document_id = 5  # From the schema debug, we know document_id 5 exists
    requirement_id = 1  # Proof of Identity (typically requirement id 1)
    patient_id = 1  # Entity ID 1 from our existing test
    case_id = "1"  # From the schema debug, we know case_id "1" exists
    override = True
    override_reason = "TEST: User override: Payslip → Proof of Residency"
    
    print(f"Testing override assignment with:")
    print(f"  document_id: {document_id}")
    print(f"  requirement_id: {requirement_id}")
    print(f"  patient_id (entity_id): {patient_id}")
    print(f"  case_id: {case_id}")
    print(f"  override: {override}")
    print(f"  override_reason: {override_reason}")
    print()
    
    # Test the assignment
    success = assign_document_to_requirement(
        document_id=document_id,
        requirement_id=requirement_id,
        patient_id=patient_id,
        case_id=case_id,
        override=override,
        override_reason=override_reason
    )
    
    print(f"Assignment result: {'SUCCESS' if success else 'FAILED'}")
    
    if success:
        # Check if the assignment was actually saved to the database
        conn = sqlite3.connect('production_idis.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT cd.id, cd.case_id, cd.entity_id, cd.checklist_item_id, cd.document_id, cd.status
            FROM case_documents cd
            WHERE cd.checklist_item_id = ? AND cd.entity_id = ? AND cd.case_id = ?
        """, (requirement_id, patient_id, case_id))
        
        result = cursor.fetchone()
        
        if result:
            print(f"✅ Database verification: Record found")
            print(f"   ID: {result[0]}, Case: {result[1]}, Entity: {result[2]}")
            print(f"   Requirement: {result[3]}, Document: {result[4]}, Status: {result[5]}")
        else:
            print(f"❌ Database verification: No record found")
        
        conn.close()
    
    return success

if __name__ == "__main__":
    test_override_assignment()