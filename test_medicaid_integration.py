#!/usr/bin/env python3
"""
Test script to verify Medicaid Navigator integration with Patient Management
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from context_store import ContextStore
from modules.medicaid_navigator.ui import get_all_patients

def test_medicaid_integration():
    """Test Medicaid Navigator patient loading functionality"""
    
    print("Testing Medicaid Navigator Patient Integration...")
    
    # Test 1: Direct database access
    try:
        cs = ContextStore("production_idis.db")
        cursor = cs.conn.cursor()
        cursor.execute("SELECT id, patient_name FROM patients ORDER BY patient_name")
        patients = cursor.fetchall()
        print(f"✓ Direct database query found {len(patients)} patients:")
        for patient in patients:
            print(f"  - ID: {patient[0]}, Name: {patient[1]}")
    except Exception as e:
        print(f"✗ Direct database query failed: {e}")
        return
    
    # Test 2: Medicaid Navigator get_all_patients function
    try:
        # Mock streamlit session state
        import streamlit as st
        if not hasattr(st, 'session_state'):
            st.session_state = {}
        st.session_state['database_path'] = 'production_idis.db'
        
        patients = get_all_patients()
        print(f"✓ Medicaid Navigator get_all_patients() found {len(patients)} patients:")
        for patient in patients:
            print(f"  - ID: {patient['patient_id']}, Name: {patient['patient_name']}")
            
        if len(patients) > 0:
            print("✓ Medicaid Navigator should now display patients correctly!")
        else:
            print("✗ Medicaid Navigator function returned empty list")
            
    except Exception as e:
        print(f"✗ Medicaid Navigator get_all_patients() failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\nMedicaid Navigator integration test completed!")

if __name__ == "__main__":
    test_medicaid_integration()