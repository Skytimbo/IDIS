"""
Patient Management UI for IDIS
Allows users to create and manage patient records for case management.
"""

import streamlit as st
import sqlite3
from datetime import datetime
import logging
from context_store import ContextStore

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def render_patient_management_page():
    """Main function to render the patient management interface."""
    st.title("Patient Management")
    st.markdown("---")
    
    # Initialize context store
    try:
        cs = ContextStore("production_idis.db")
    except Exception as e:
        st.error(f"Database connection failed: {str(e)}")
        return
    
    # Display existing patients
    st.subheader("Existing Patients")
    
    try:
        # Get all patients from the database
        patients = get_all_patients(cs)
        
        if patients:
            # Display patients in a table format
            st.dataframe(
                patients,
                column_config={
                    "patient_id": "Patient ID",
                    "patient_name": "Patient Name",
                    "created_at": "Created Date"
                },
                use_container_width=True
            )
        else:
            st.info("No patients found in the system.")
    
    except Exception as e:
        st.error(f"Error loading patients: {str(e)}")
        logger.error(f"Error loading patients: {str(e)}")
    
    st.markdown("---")
    
    # Add new patient section
    st.subheader("Add New Patient")
    
    with st.form("add_patient_form"):
        patient_name = st.text_input(
            "Patient Name",
            placeholder="Enter patient's full name",
            help="Enter the full name of the patient"
        )
        
        submitted = st.form_submit_button("Add New Patient")
        
        if submitted:
            if patient_name.strip():
                try:
                    # Create new patient record
                    patient_data = {
                        "patient_name": patient_name.strip()
                    }
                    
                    patient_id = cs.add_patient(patient_data)
                    
                    st.success(f"Patient '{patient_name}' added successfully with ID: {patient_id}")
                    logger.info(f"Created new patient: {patient_name} (ID: {patient_id})")
                    
                    # Rerun to refresh the patient list
                    st.experimental_rerun()
                    
                except Exception as e:
                    st.error(f"Error adding patient: {str(e)}")
                    logger.error(f"Error adding patient {patient_name}: {str(e)}")
            else:
                st.warning("Please enter a valid patient name.")

def get_all_patients(context_store):
    """
    Retrieve all patients from the database.
    
    Args:
        context_store: ContextStore instance
        
    Returns:
        List of patient dictionaries
    """
    try:
        cursor = context_store.conn.cursor()
        cursor.execute("""
            SELECT id, patient_name, creation_timestamp 
            FROM patients 
            ORDER BY creation_timestamp DESC
        """)
        
        patients = []
        for row in cursor.fetchall():
            patients.append({
                "patient_id": row[0],
                "patient_name": row[1],
                "created_at": row[2]
            })
        
        return patients
        
    except Exception as e:
        logger.error(f"Error retrieving patients: {str(e)}")
        raise

if __name__ == "__main__":
    render_patient_management_page()