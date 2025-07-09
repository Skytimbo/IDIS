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
        logging.info("--- ANALYZE BUTTON CLICKED ---")
        
        # Initialize the UnifiedIngestionAgent for direct processing
        context_store = ContextStore("production_idis.db")
        temp_folder = os.path.join("data", "temp_medicaid_upload")
        holding_folder = os.path.join("data", "holding")
        
        # Create necessary directories
        os.makedirs(temp_folder, exist_ok=True)
        os.makedirs(holding_folder, exist_ok=True)
        
        # Initialize the agent
        ingestion_agent = UnifiedIngestionAgent(
            context_store=context_store,
            watch_folder=temp_folder,
            holding_folder=holding_folder
        )
        
        with st.spinner("Processing documents through AI pipeline..."):
            processed_count = 0
            failed_count = 0
            
            # Process each uploaded file directly through the AI pipeline
            for uploaded_file in uploaded_files or []:
                try:
                    # Save file temporarily
                    temp_path = os.path.join(temp_folder, uploaded_file.name)
                    logging.info(f"Processing '{uploaded_file.name}' through AI pipeline")
                    
                    with open(temp_path, "wb") as f:
                        f.write(uploaded_file.getvalue())
                    
                    # Process directly through UnifiedIngestionAgent
                    success = ingestion_agent._process_single_file(
                        temp_path, 
                        uploaded_file.name, 
                        patient_id=1, 
                        session_id=1
                    )
                    
                    if success:
                        st.write(f"✅ Successfully processed {uploaded_file.name}")
                        processed_count += 1
                    else:
                        st.write(f"❌ Failed to process {uploaded_file.name}")
                        failed_count += 1
                    
                    # Clean up temporary file
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                        
                except Exception as e:
                    st.write(f"❌ Error processing {uploaded_file.name}: {str(e)}")
                    failed_count += 1
                    logging.error(f"Error processing {uploaded_file.name}: {e}")
            
            # Show results
            if processed_count > 0:
                st.success(f"Successfully processed {processed_count} documents! Your documents are now searchable by content.")
                if failed_count > 0:
                    st.warning(f"Failed to process {failed_count} documents. Please check the logs.")
                st.balloons()
            else:
                st.error("No documents were processed successfully. Please try again or check the file formats.")
        
        # Clean up temp directory
        try:
            if os.path.exists(temp_folder):
                import shutil
                shutil.rmtree(temp_folder)
        except Exception as e:
            logging.warning(f"Could not clean up temp folder: {e}")