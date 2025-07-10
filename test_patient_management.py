#!/usr/bin/env python3
"""
Test script to verify Patient Management functionality
"""

import sqlite3
from context_store import ContextStore

def test_patient_management():
    """Test patient management functions"""
    
    # Test database connection
    try:
        cs = ContextStore("production_idis.db")
        print("✓ Database connection successful")
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return
    
    # Check existing patients
    try:
        cursor = cs.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM patients")
        count = cursor.fetchone()[0]
        print(f"✓ Found {count} existing patients in database")
        
        # Show existing patients
        cursor.execute("SELECT id, patient_name, creation_timestamp FROM patients ORDER BY creation_timestamp DESC")
        patients = cursor.fetchall()
        
        if patients:
            print("Existing patients:")
            for patient in patients:
                print(f"  ID: {patient[0]}, Name: {patient[1]}, Created: {patient[2]}")
        else:
            print("No existing patients found")
            
    except Exception as e:
        print(f"✗ Error checking existing patients: {e}")
        return
    
    # Test adding a new patient
    try:
        patient_data = {"patient_name": "Test Patient"}
        patient_id = cs.add_patient(patient_data)
        print(f"✓ Successfully added new patient with ID: {patient_id}")
        
        # Clean up test patient
        cursor.execute("DELETE FROM patients WHERE id = ?", (patient_id,))
        cs.conn.commit()
        print("✓ Test patient cleaned up")
        
    except Exception as e:
        print(f"✗ Error adding new patient: {e}")
    
    print("\nPatient Management test completed!")

if __name__ == "__main__":
    test_patient_management()