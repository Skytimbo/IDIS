import streamlit as st
import pandas as pd
import os
import logging
from context_store import ContextStore
from unified_ingestion_agent import UnifiedIngestionAgent

def load_application_checklist_with_status():
    """
    Load the application checklist with current status from database.
    Checks case_documents table for submitted documents.
    
    Returns:
        pd.DataFrame: Formatted checklist with current status
    """
    try:
        # Get database path from session state or use default
        db_path = st.session_state.get('database_path', 'production_idis.db')
        context_store = ContextStore(db_path)
        
        # Query checklist requirements with status
        cursor = context_store.conn.cursor()
        cursor.execute("""
            SELECT ac.id, ac.required_doc_name, ac.description,
                   CASE 
                       WHEN cd.status = 'Submitted' THEN '🔵 Submitted'
                       ELSE '🔴 Missing'
                   END as status
            FROM application_checklists ac
            LEFT JOIN case_documents cd ON ac.id = cd.checklist_item_id 
                AND cd.patient_id = 1
            WHERE ac.checklist_name = 'SOA Medicaid - Adult'
            ORDER BY ac.id
        """)
        
        requirements = cursor.fetchall()
        
        if not requirements:
            return pd.DataFrame()
        
        # Format the data for display
        checklist_data = {
            "Document Required": [req[1] for req in requirements],
            "Status": [req[3] for req in requirements],
            "Examples": [req[2] for req in requirements]
        }
        
        return pd.DataFrame(checklist_data)
        
    except Exception as e:
        logging.error(f"Error loading application checklist with status: {e}")
        return pd.DataFrame()


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


def validate_document_assignment(ai_detected_type: str, selected_requirement: str) -> dict:
    """
    Validate if a document assignment is appropriate based on AI classification.
    
    Args:
        ai_detected_type: The document type detected by AI
        selected_requirement: The requirement selected by the user
        
    Returns:
        dict: {'is_valid': bool, 'warning_message': str}
    """
    # Define valid document types for each requirement
    valid_mappings = {
        'Proof of Identity': [
            'Driver License', 'State ID', 'Passport', 'Birth Certificate',
            'Business License', 'Identity Document'
        ],
        'Proof of Citizenship': [
            'Birth Certificate', 'Passport', 'Citizenship Document',
            'Naturalization Certificate'
        ],
        'Proof of Residency': [
            'Utility Bill', 'Bank Statement', 'Lease Agreement',
            'Mortgage Statement', 'Rent Receipt'
        ],
        'Proof of Income': [
            'Paystub', 'Employment Letter', 'Social Security Award',
            'Tax Return', 'Bank Statement', 'Payslip'
        ],
        'Proof of Resources/Assets': [
            'Bank Statement', 'Investment Statement', 'Asset Valuation',
            'Property Deed', 'Vehicle Title'
        ]
    }
    
    # Check if the assignment is valid
    valid_types = valid_mappings.get(selected_requirement, [])
    
    # Handle special cases
    if ai_detected_type in ['None', 'Unknown', '']:
        # If AI couldn't determine type, show warning but allow assignment
        return {
            'is_valid': False,
            'warning_message': f"The AI could not determine the document type. Please verify this document is appropriate for '{selected_requirement}'. Expected types: {', '.join(valid_types)}"
        }
    elif ai_detected_type in valid_types:
        return {
            'is_valid': True,
            'warning_message': ''
        }
    else:
        return {
            'is_valid': False,
            'warning_message': f"A '{ai_detected_type}' document may not be appropriate for '{selected_requirement}'. Expected types: {', '.join(valid_types)}"
        }


def assign_document_to_requirement(document_id: int, requirement_id: int, patient_id: int = 1, override: bool = False, override_reason: str = ""):
    """
    Assign a document to a specific checklist requirement.
    
    Args:
        document_id: ID of the document to assign
        requirement_id: ID of the checklist requirement
        patient_id: Patient ID (default: 1)
        override: Whether this assignment is an override of validation warnings
        override_reason: Reason for the override (logged for audit trail)
    
    Returns:
        bool: True if assignment was successful
    """
    try:
        # Log override actions for audit trail
        if override and override_reason:
            logging.info(f"AUDIT: Document assignment override - {override_reason}")
        
        db_path = st.session_state.get('database_path', 'production_idis.db')
        context_store = ContextStore(db_path)
        cursor = context_store.conn.cursor()
        
        # Check if a record already exists for this requirement
        cursor.execute("""
            SELECT id FROM case_documents 
            WHERE checklist_item_id = ? AND patient_id = ?
        """, (requirement_id, patient_id))
        
        existing_record = cursor.fetchone()
        
        if existing_record:
            # Update existing record
            cursor.execute("""
                UPDATE case_documents 
                SET document_id = ?, status = 'Submitted', updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (document_id, existing_record[0]))
        else:
            # Insert new record - case_id should be TEXT, so use string
            cursor.execute("""
                INSERT INTO case_documents (case_id, patient_id, checklist_item_id, document_id, status, created_at, updated_at)
                VALUES ('1', ?, ?, ?, 'Submitted', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (patient_id, requirement_id, document_id))
        
        context_store.conn.commit()
        return True
        
    except Exception as e:
        logging.error(f"Error assigning document {document_id} to requirement {requirement_id}: {e}")
        return False


def render_document_assignment_interface():
    """
    Render the document assignment interface for processed documents.
    """
    if 'processed_documents' not in st.session_state or not st.session_state.processed_documents:
        return
    
    st.header("📎 Assign Documents to Requirements")
    
    # Get checklist requirements for dropdown
    try:
        db_path = st.session_state.get('database_path', 'production_idis.db')
        context_store = ContextStore(db_path)
        cursor = context_store.conn.cursor()
        cursor.execute("""
            SELECT id, required_doc_name 
            FROM application_checklists 
            WHERE checklist_name = 'SOA Medicaid - Adult'
            ORDER BY id
        """)
        requirements = cursor.fetchall()
        requirement_options = {req[1]: req[0] for req in requirements}
        
    except Exception as e:
        st.error(f"Error loading requirements: {e}")
        return
    
    # Process each unassigned document
    for i, doc_info in enumerate(st.session_state.processed_documents):
        with st.expander(f"📄 New document '{doc_info['filename']}' processed", expanded=True):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.write(f"**Filename:** {doc_info['filename']}")
                st.write(f"**AI-detected type:** {doc_info.get('document_type', 'Unknown')}")
                
                # Dropdown for assignment
                options_with_placeholder = ["Select a requirement..."] + list(requirement_options.keys())
                selected_requirement = st.selectbox(
                    "Assign to requirement:",
                    options=options_with_placeholder,
                    key=f"req_select_{i}",
                    index=0
                )
                
                # Handle the placeholder selection
                if selected_requirement == "Select a requirement...":
                    selected_requirement = None
            
            with col2:
                if st.button("✅ Assign Document", key=f"assign_btn_{i}", type="primary"):
                    if selected_requirement:
                        requirement_id = requirement_options[selected_requirement]
                        
                        # Validate the assignment
                        validation_result = validate_document_assignment(
                            doc_info.get('document_type', 'Unknown'), 
                            selected_requirement
                        )
                        
                        if validation_result['is_valid']:
                            # Valid assignment - proceed normally
                            success = assign_document_to_requirement(
                                doc_info['document_id'], 
                                requirement_id
                            )
                            
                            if success:
                                st.success(f"✅ Document assigned to '{selected_requirement}'")
                                # Remove from processed documents list
                                st.session_state.processed_documents.pop(i)
                                st.experimental_rerun()
                            else:
                                st.error("❌ Failed to assign document")
                        else:
                            # Invalid assignment - show warning
                            st.warning(f"⚠️ {validation_result['warning_message']}")
                            
                            # Create override option outside of expander to avoid nesting issues
                            st.write("**Override Options:**")
                            st.write(f"• AI detected: {doc_info.get('document_type', 'Unknown')}")
                            st.write(f"• You're assigning to: {selected_requirement}")
                            st.write("• Risk: This may not meet Medicaid application requirements.")
                            
                            if st.button("⚠️ Override and Assign Anyway", key=f"override_{i}", type="secondary"):
                                # Proceed with override assignment
                                success = assign_document_to_requirement(
                                    doc_info['document_id'], 
                                    requirement_id,
                                    override=True,
                                    override_reason=f"User override: {doc_info.get('document_type', 'Unknown')} → {selected_requirement}"
                                )
                                
                                if success:
                                    st.success(f"✅ Document assigned to '{selected_requirement}' (Override)")
                                    # Remove from processed documents list
                                    st.session_state.processed_documents.pop(i)
                                    st.experimental_rerun()
                                else:
                                    st.error("❌ Failed to assign document")
                    else:
                        st.warning("Please select a requirement first")


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

    # Load checklist with current status from database
    checklist_df = load_application_checklist_with_status()
    
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


    # --- 2.5. Document Assignment Interface ---
    render_document_assignment_interface()
    
    # --- 3. Next Steps ---
    st.header("3. Next Steps")
    st.info("""
    **After uploading your documents:**
    1. Review the updated checklist above to see which documents have been processed
    2. Upload any remaining required documents
    3. Use the General Document Search to verify all documents are properly categorized
    4. Contact your caseworker when all requirements are complete
    """)
    
    st.markdown("---")
    st.markdown("**Need help?** Contact Alaska Medicaid Support at 1-800-XXX-XXXX")
