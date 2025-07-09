import streamlit as st
import pandas as pd
import os
import logging
from context_store import ContextStore
from unified_ingestion_agent import UnifiedIngestionAgent

def render_navigator_ui():
    """
    Renders the user interface for the Medicaid Navigator module.
    """
    st.title("🩺 Medicaid Navigator")
    st.markdown("---")
    st.markdown("This tool helps you gather, check, and prepare your documents for an Alaska Medicaid application.")

    # --- 1. Document Checklist ---
    st.header("1. Application Checklist")
    st.info("Upload your documents below. The system will automatically check them off the list.")

    # Placeholder for the checklist logic
    checklist_data = {
        "Document Category": [
            "Proof of Identity",
            "Proof of Citizenship/Immigration Status",
            "Proof of Alaska Residency",
            "Proof of Income",
            "Proof of Resources/Assets"
        ],
        "Status": [
            "❌ Missing",
            "❌ Missing",
            "❌ Missing",
            "❌ Missing",
            "❌ Missing"
        ],
        "Examples": [
            "Driver's License, State ID",
            "Birth Certificate, Passport, Green Card",
            "Utility Bill, Lease Agreement",
            "Pay Stubs (last 30 days), Tax Return",
            "Bank Statements (last 60 days)"
        ]
    }
    checklist_df = pd.DataFrame(checklist_data)
    st.table(checklist_df)

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