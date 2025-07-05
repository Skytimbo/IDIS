import streamlit as st
import pandas as pd
import os

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
    uploaded_files = st.file_uploader(
        "Drag and drop your PDFs or images here.",
        type=['pdf', 'png', 'jpg', 'jpeg'],
        accept_multiple_files=True
    )

    if uploaded_files:
        st.success(f"{len(uploaded_files)} file(s) uploaded successfully. They are ready for processing.")
        for uploaded_file in uploaded_files:
            st.write(f"- {uploaded_file.name}")

    # --- 3. Processing ---
    st.header("3. Process and Prepare Packet")
    if st.button("✨ Analyze My Documents", type="primary", disabled=(not uploaded_files)):
        with st.spinner("Submitting documents to the processing pipeline..."):
            # Define the path to the main watch folder
            watch_folder = os.path.join("data", "scanner_output")
            os.makedirs(watch_folder, exist_ok=True)
            
            # Save each uploaded file to the watch folder
            for uploaded_file in uploaded_files or []:
                dest_path = os.path.join(watch_folder, uploaded_file.name)
                with open(dest_path, "wb") as f:
                    f.write(uploaded_file.getvalue())
                st.write(f"✅ Submitted {uploaded_file.name} for processing.")
                
            st.success("All documents submitted! The checklist will update as each document is analyzed.")
            st.balloons()