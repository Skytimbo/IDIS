import streamlit as st
import pandas as pd

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
        with st.spinner("Analyzing documents... This may take a few minutes."):
            # Placeholder for calling the backend processing pipeline
            st.success("Analysis Complete!")
            st.balloons()
            # In the future, this will update the checklist above