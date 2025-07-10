#!/usr/bin/env python3
"""
Fix foreign key constraint issues by ensuring required patient and session records exist
"""

from context_store import ContextStore

def fix_foreign_keys():
    """Create required patient and session records for the upload functionality"""
    
    store = ContextStore("production_idis.db")
    
    # Create patient record if it doesn't exist
    try:
        existing_patient = store.get_patient(1)
        if not existing_patient:
            print("Creating patient record with ID 1...")
            patient_data = {
                'patient_name': 'Default Patient',
                'patient_metadata': '{"source": "unified_uploader", "type": "default"}'
            }
            patient_id = store.add_patient(patient_data)
            print(f"Created patient with ID: {patient_id}")
        else:
            print(f"Patient 1 already exists: {existing_patient['patient_name']}")
    except Exception as e:
        print(f"Error handling patient: {e}")
    
    # Create session record if it doesn't exist
    try:
        existing_session = store.get_session(1)
        if not existing_session:
            print("Creating session record with ID 1...")
            session_id = store.create_session(
                user_id="unified_uploader",
                session_metadata={"source": "unified_uploader", "type": "default"}
            )
            print(f"Created session with ID: {session_id}")
        else:
            print(f"Session 1 already exists: {existing_session['status']}")
    except Exception as e:
        print(f"Error handling session: {e}")
    
    print("Foreign key setup complete!")

if __name__ == "__main__":
    fix_foreign_keys()