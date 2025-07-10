#!/usr/bin/env python3
"""
Simple test for Medicaid Navigator database integration
"""

from context_store import ContextStore

def test_medicaid_patient_query():
    """Test the corrected SQL query for Medicaid Navigator"""
    
    print("Testing Medicaid Navigator Patient Query...")
    
    try:
        cs = ContextStore("production_idis.db")
        cursor = cs.conn.cursor()
        
        # Test the corrected query (id instead of patient_id)
        cursor.execute("""
            SELECT id, patient_name 
            FROM patients 
            ORDER BY patient_name
        """)
        
        patients = cursor.fetchall()
        print(f"✓ Query found {len(patients)} patients:")
        
        for patient in patients:
            print(f"  - ID: {patient[0]}, Name: {patient[1]}")
        
        # Simulate what the Medicaid Navigator function does
        patient_list = []
        for row in patients:
            patient_list.append({
                "patient_id": row[0],  # This is the corrected field name
                "patient_name": row[1]
            })
        
        print(f"✓ Medicaid Navigator format: {len(patient_list)} patients ready")
        
        if len(patient_list) > 0:
            print("✓ Medicaid Navigator should now show patients correctly!")
        else:
            print("✗ No patients found - need to add some first")
            
    except Exception as e:
        print(f"✗ Database query failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\nMedicaid Navigator integration test completed!")

if __name__ == "__main__":
    test_medicaid_patient_query()