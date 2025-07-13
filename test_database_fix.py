#!/usr/bin/env python3
"""
Test script to verify the database assignment functionality works correctly.
This script tests the database operations directly without streamlit dependencies.
"""

import sqlite3
import logging

def test_database_assignment():
    """Test the database assignment functionality directly."""
    
    # Test parameters - simulating a real scenario
    document_id = 5  # From the schema debug, we know document_id 5 exists
    requirement_id = 1  # Proof of Identity (typically requirement id 1)
    entity_id = 1  # Entity ID 1 from our existing test
    case_id = "1"  # From the schema debug, we know case_id "1" exists
    
    print(f"Testing database assignment with:")
    print(f"  document_id: {document_id}")
    print(f"  requirement_id: {requirement_id}")
    print(f"  entity_id: {entity_id}")
    print(f"  case_id: {case_id}")
    print()
    
    try:
        # Setup database connection
        db_path = 'production_idis.db'
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if a record already exists for this requirement
        cursor.execute("""
            SELECT id FROM case_documents 
            WHERE checklist_item_id = ? AND entity_id = ? AND case_id = ?
        """, (requirement_id, entity_id, case_id))
        
        existing_record = cursor.fetchone()
        
        if existing_record:
            print(f"Found existing record with ID: {existing_record[0]}")
            # Update existing record
            cursor.execute("""
                UPDATE case_documents 
                SET document_id = ?, status = 'Submitted', updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (document_id, existing_record[0]))
            print("Updated existing record")
        else:
            print("No existing record found, inserting new record")
            # Insert new record
            cursor.execute("""
                INSERT INTO case_documents (case_id, entity_id, checklist_item_id, document_id, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'Submitted', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (case_id, entity_id, requirement_id, document_id))
            print("Inserted new record")
        
        conn.commit()
        print("✅ Database assignment successful!")
        
        # Verify the assignment was saved
        cursor.execute("""
            SELECT cd.id, cd.case_id, cd.entity_id, cd.checklist_item_id, cd.document_id, cd.status
            FROM case_documents cd
            WHERE cd.checklist_item_id = ? AND cd.entity_id = ? AND cd.case_id = ?
        """, (requirement_id, entity_id, case_id))
        
        result = cursor.fetchone()
        
        if result:
            print(f"✅ Database verification: Record found")
            print(f"   ID: {result[0]}, Case: {result[1]}, Entity: {result[2]}")
            print(f"   Requirement: {result[3]}, Document: {result[4]}, Status: {result[5]}")
        else:
            print(f"❌ Database verification: No record found")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error during database assignment: {e}")
        logging.error(f"Error assigning document {document_id} to requirement {requirement_id}: {e}")
        return False

if __name__ == "__main__":
    test_database_assignment()