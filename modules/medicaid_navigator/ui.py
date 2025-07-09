import streamlit as st
import pandas as pd
import os
import logging
from context_store import ContextStore
from unified_ingestion_agent import UnifiedIngestionAgent

def load_application_checklist():
    """
    Load the application checklist from the database and format it for display.
    
    Returns:
        pd.DataFrame: Formatted checklist with columns for Document, Status, and Examples
    """
    try:
        # Get database path from session state or use default
        db_path = st.session_state.get('database_path', 'production_idis.db')
        context_store = ContextStore(db_path)
        
        # Query the application_checklists table for SOA Medicaid requirements
        cursor = context_store.conn.cursor()
        cursor.execute("""
            SELECT required_doc_name, description 
            FROM application_checklists 
            WHERE checklist_name = 'SOA Medicaid - Adult'
            ORDER BY id
        """)
        
        requirements = cursor.fetchall()
        
        if not requirements:
            return pd.DataFrame()
        
        # Format the data for display
        checklist_data = {
            "Document Required": [req[0] for req in requirements],
            "Status": ["🔴 Missing" for _ in requirements],
            "Examples": [req[1] for req in requirements]
        }
        
        return pd.DataFrame(checklist_data)
        
    except Exception as e:
        logging.error(f"Error loading application checklist: {e}")
        # Return empty DataFrame on error
        return pd.DataFrame()

def render_navigator_ui():
    """
    Renders the user interface for the Medicaid Navigator module.
    """
    st.title("🩺 Medicaid Navigator")
    st.markdown("---")
    st.markdown("This tool helps you gather, check, and prepare your documents for an Alaska Medicaid application.")

    # --- 1. Application Checklist ---
    st.header("1. Application Checklist")
    st.info("Upload your documents below. The system will automatically check them off the list.")

    # Load checklist from database
    checklist_df = load_application_checklist()
    
    if not checklist_df.empty:
        st.table(checklist_df)
    else:
        st.warning("Unable to load application checklist. Please check database connection.")

    # --- 2. Document Upload ---
    st.header("2. Upload Your Documents")
    
    # Use the unified uploader component
    from modules.shared.unified_uploader import render_unified_uploader
    
    render_unified_uploader(
        context="medicaid",
        title="Upload Medicaid Documents",
        description="Drag and drop your PDFs or images here.",
        button_text="Analyze My Documents",
        file_types=['pdf', 'png', 'jpg', 'jpeg', 'txt', 'docx'],
        accept_multiple=True
    )
    
    # --- 3. Processing ---
    st.header("3. Process and Prepare Packet")
    if False:  # This block is now handled by the unified uploader
        # This processing logic is now handled by the unified uploader
        pass