import streamlit as st
import pandas as pd
import os
import logging
from datetime import datetime
from context_store import ContextStore
from unified_ingestion_agent import UnifiedIngestionAgent
from modules.shared.confidence_meter import extract_confidence_from_document, render_confidence_meter

<<<<<<< HEAD



def load_application_checklist_with_status_for_entity(entity_id):
=======
def load_application_checklist_with_status(patient_id=None, case_id=None):
>>>>>>> 78c181f1711a5706d2e1e656e094ce786c836d37
    """
    Load the application checklist with current status for a specific entity.
    Checks case_documents table for submitted documents.
    
    Args:
<<<<<<< HEAD
        entity_id: The entity ID to check status for
=======
        patient_id: ID of the selected patient
        case_id: ID of the specific case
>>>>>>> 78c181f1711a5706d2e1e656e094ce786c836d37
    
    Returns:
        pd.DataFrame: Formatted checklist with current status
    """
    try:
        # Get database path from session state or use default
        db_path = st.session_state.get('database_path', 'production_idis.db')
        context_store = ContextStore(db_path)
        
<<<<<<< HEAD
        # Query checklist requirements with status for specific entity
=======
        # Use session state patient_id if not provided
        if patient_id is None:
            patient_id = st.session_state.get('selected_patient_id', 1)
        
        # Query checklist requirements with status
>>>>>>> 78c181f1711a5706d2e1e656e094ce786c836d37
        cursor = context_store.conn.cursor()
        cursor.execute("""
            SELECT ac.id, ac.required_doc_name, ac.description,
                   CASE 
                       WHEN cd.status = 'Submitted' AND cd.is_override = 1 THEN '🟡 Overridden'
                       WHEN cd.status = 'Submitted' THEN '🔵 Submitted'
                       ELSE '🔴 Missing'
                   END as status
            FROM application_checklists ac
            LEFT JOIN case_documents cd ON ac.id = cd.checklist_item_id 
                AND cd.entity_id = ?
            WHERE ac.checklist_name = 'SOA Medicaid - Adult'
            ORDER BY ac.id
<<<<<<< HEAD
        """, (entity_id,))
=======
        """, (patient_id,))
>>>>>>> 78c181f1711a5706d2e1e656e094ce786c836d37
        
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
        logging.error(f"Error loading application checklist with status for entity {entity_id}: {e}")
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
        'Proof of Alaska Residency': [
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


<<<<<<< HEAD
def assign_document_to_requirement(document_id: int, requirement_id: int, entity_id: int = None, override: bool = False, override_reason: str = ""):
=======
def assign_document_to_requirement(document_id: int, requirement_id: int, patient_id: int = None, case_id: str = None, override: bool = False, override_reason: str = ""):
>>>>>>> 78c181f1711a5706d2e1e656e094ce786c836d37
    """
    Assign a document to a specific checklist requirement.
    
    Args:
        document_id: ID of the document to assign
        requirement_id: ID of the checklist requirement
<<<<<<< HEAD
        entity_id: Entity ID (gets from session state if not provided)
=======
        patient_id: Patient ID (uses session state if not provided)
        case_id: Case ID (uses session state if not provided)
>>>>>>> 78c181f1711a5706d2e1e656e094ce786c836d37
        override: Whether this assignment is an override of validation warnings
        override_reason: Reason for the override (logged for audit trail)
    
    Returns:
        bool: True if assignment was successful
    """
    try:
        logging.info("DEBUG: Entered assign_document_to_requirement function.")
        
        # Log override actions for audit trail
        if override and override_reason:
            logging.info(f"AUDIT: Document assignment override - {override_reason}")
        
<<<<<<< HEAD
        # Get entity_id from session state if not provided
        if entity_id is None:
            entity_id = st.session_state.get('current_entity_id', 1)
        
        # Get or create case_id for this entity
        case_id = st.session_state.get('current_case_id', f"CASE-{entity_id}-DEFAULT")
=======
        # Use session state values if not provided
        if patient_id is None:
            patient_id = st.session_state.get('selected_patient_id', 1)
        if case_id is None:
            case_id = st.session_state.get('current_case_id', 'CASE-1-DEFAULT')
>>>>>>> 78c181f1711a5706d2e1e656e094ce786c836d37
        
        db_path = st.session_state.get('database_path', 'production_idis.db')
        context_store = ContextStore(db_path)
        cursor = context_store.conn.cursor()
        
        # Check if a record already exists for this requirement
        cursor.execute("""
            SELECT id FROM case_documents 
<<<<<<< HEAD
            WHERE checklist_item_id = ? AND entity_id = ?
        """, (requirement_id, entity_id))
=======
            WHERE checklist_item_id = ? AND entity_id = ? AND case_id = ?
        """, (requirement_id, patient_id, case_id))
>>>>>>> 78c181f1711a5706d2e1e656e094ce786c836d37
        
        existing_record = cursor.fetchone()
        
        if existing_record:
            # Update existing record
            cursor.execute("""
                UPDATE case_documents 
                SET document_id = ?, status = 'Submitted', is_override = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (document_id, 1 if override else 0, existing_record[0]))
        else:
            # Insert new record
            cursor.execute("""
<<<<<<< HEAD
                INSERT INTO case_documents (case_id, entity_id, checklist_item_id, document_id, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'Submitted', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (case_id, entity_id, requirement_id, document_id))
=======

                INSERT INTO case_documents (case_id, entity_id, checklist_item_id, document_id, status, is_override, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'Submitted', ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (case_id, patient_id, requirement_id, document_id, 1 if override else 0))

>>>>>>> 78c181f1711a5706d2e1e656e094ce786c836d37
        
        context_store.conn.commit()
        logging.info("DEBUG: Database update successful, returning True.")
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
    
    # Process each unassigned document - use a copy to avoid modification during iteration
    documents_to_process = list(st.session_state.processed_documents)
    documents_to_remove = []
    rerun_needed = False
    
    for i, doc_info in enumerate(documents_to_process):
        with st.expander(f"📄 New document '{doc_info['filename']}' processed", expanded=True):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.write(f"**Filename:** {doc_info['filename']}")
                st.write(f"**AI-detected type:** {doc_info.get('document_type', 'Unknown')}")
                
                # Display confidence meter if we have extracted data
                if doc_info.get('extracted_data'):
                    confidence, document_type, has_heuristic_override = extract_confidence_from_document(
                        {'extracted_data': doc_info['extracted_data']}
                    )
                    st.markdown("**AI Classification Confidence:**")
                    render_confidence_meter(confidence, document_type, compact=True)
                
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
                        
                        # Check validation but don't block assignment
                        validation_result = validate_document_assignment(
                            doc_info.get('document_type', 'Unknown'), 
                            selected_requirement
                        )
                        
                        # Always proceed with assignment regardless of validation
                        is_override = not validation_result['is_valid']
                        override_reason = ""
                        
                        if is_override:
                            override_reason = f"User override: {doc_info.get('document_type', 'Unknown')} → {selected_requirement}"
                            st.warning(f"⚠️ {validation_result['warning_message']}")
                        
                        success = assign_document_to_requirement(
                            doc_info['document_id'], 
                            requirement_id,
                            override=is_override,
                            override_reason=override_reason
                        )
                        
                        if success:
                            if is_override:
                                st.success(f"✅ Document assigned to '{selected_requirement}' (Override)")
                            else:
                                st.success(f"✅ Document assigned to '{selected_requirement}'")
                            # Mark document for removal
                            documents_to_remove.append(doc_info)
                            rerun_needed = True
                        else:
                            st.error("❌ Failed to assign document")
                    else:
                        st.warning("Please select a requirement first")
    
    # Remove assigned documents from the session state
    for doc_to_remove in documents_to_remove:
        if doc_to_remove in st.session_state.processed_documents:
            st.session_state.processed_documents.remove(doc_to_remove)
    
    # Rerun the app after all processing is complete
    if rerun_needed:
        st.experimental_rerun()


<<<<<<< HEAD
def get_current_user_id():
=======
def get_all_patients():
    """
    Get all patients from the database for patient selection.
    
    Returns:
        List of patient dictionaries
    """
    try:
        db_path = st.session_state.get('database_path', 'production_idis.db')
        context_store = ContextStore(db_path)
        cursor = context_store.conn.cursor()
        cursor.execute("""
            SELECT id, entity_name 
            FROM entities 
            ORDER BY entity_name
        """)
        
        patients = []
        for row in cursor.fetchall():
            patients.append({
                "patient_id": row[0],  # Keep legacy field name for UI compatibility
                "patient_name": row[1]  # Keep legacy field name for UI compatibility
            })
        
        return patients
        
    except Exception as e:
        logging.error(f"Error retrieving patients: {e}")
        return []

def generate_case_id(patient_name):
    """
    Generate a unique case ID for a patient.
    
    Args:
        patient_name: Name of the patient
        
    Returns:
        str: Unique case ID
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Clean patient name for use in case ID
    clean_name = patient_name.replace(" ", "").replace(".", "")[:20]
    return f"CASE-{clean_name}-{timestamp}"

def render_patient_selection():
    """
    Render the patient selection interface at the top of the Medicaid Navigator.
    """
    st.subheader("👤 Patient Selection")
    
    # Get all patients
    patients = get_all_patients()
    
    if not patients:
        st.warning("No patients found. Please go to the Patient Management page to add patients first.")
        return False
    
    # Create options for selectbox
    patient_options = {f"{p['patient_name']} (ID: {p['patient_id']})": p['patient_id'] for p in patients}
    
    # Patient selection
    selected_patient_display = st.selectbox(
        "Select a patient:",
        options=list(patient_options.keys()),
        key="patient_selector",
        help="Choose the patient for this Medicaid application case"
    )
    
    if selected_patient_display:
        selected_patient_id = patient_options[selected_patient_display]
        selected_patient_name = [p['patient_name'] for p in patients if p['patient_id'] == selected_patient_id][0]
        
        # Store in session state
        st.session_state.selected_patient_id = selected_patient_id
        st.session_state.selected_patient_name = selected_patient_name
        
        # Generate or retrieve case ID for this session
        if 'current_case_id' not in st.session_state or st.session_state.get('last_selected_patient_id') != selected_patient_id:
            st.session_state.current_case_id = generate_case_id(selected_patient_name)
            st.session_state.last_selected_patient_id = selected_patient_id
        
        # Display current selection
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"**Selected Patient:** {selected_patient_name}")
        with col2:
            st.info(f"**Case ID:** {st.session_state.current_case_id}")
        
        return True
    
    return False

def render_navigator_ui():
>>>>>>> 78c181f1711a5706d2e1e656e094ce786c836d37
    """
    Get the current user ID (simulated for demo purposes).
    In a real application, this would come from authentication system.
    """
    # For demonstration, we'll simulate different users
    # In production, this would come from your authentication system
    return st.session_state.get('current_user_id', 'user_a')

def get_user_entities(user_id):
    """
    Get all entities belonging to a specific user.
    
    Args:
        user_id: The user ID to filter entities for
        
    Returns:
        list: List of dictionaries containing entity information
    """
    try:
        db_path = st.session_state.get('database_path', 'production_idis.db')
        context_store = ContextStore(db_path)
        cursor = context_store.conn.cursor()
        
        cursor.execute("""
            SELECT id, entity_name, creation_timestamp
            FROM entities 
            WHERE user_id = ?
            ORDER BY entity_name
        """, (user_id,))
        
        entities = cursor.fetchall()
        return [{'id': row[0], 'name': row[1], 'created': row[2]} for row in entities]
        
    except Exception as e:
        logging.error(f"Error loading user entities: {e}")
        return []

def create_new_entity(entity_name, user_id):
    """
    Create a new entity for the specified user.
    
    Args:
        entity_name: Name of the new entity
        user_id: ID of the user creating the entity
        
    Returns:
        int: ID of the newly created entity, or None if failed
    """
    try:
        db_path = st.session_state.get('database_path', 'production_idis.db')
        context_store = ContextStore(db_path)
        cursor = context_store.conn.cursor()
        
        cursor.execute("""
            INSERT INTO entities (entity_name, user_id, creation_timestamp, last_modified_timestamp)
            VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (entity_name, user_id))
        
        entity_id = cursor.lastrowid
        context_store.conn.commit()
        
        logging.info(f"Created new entity '{entity_name}' (ID: {entity_id}) for user {user_id}")
        return entity_id
        
    except Exception as e:
        logging.error(f"Error creating new entity: {e}")
        return None

def create_new_case(entity_id, user_id):
    """
    Create a new case for the specified entity and user.
    
    Args:
        entity_id: ID of the entity the case belongs to
        user_id: ID of the user creating the case
        
    Returns:
        str: Case ID of the newly created case, or None if failed
    """
    try:
        db_path = st.session_state.get('database_path', 'production_idis.db')
        context_store = ContextStore(db_path)
        cursor = context_store.conn.cursor()
        
        # Get entity name for case ID generation
        cursor.execute("SELECT entity_name FROM entities WHERE id = ?", (entity_id,))
        entity_result = cursor.fetchone()
        if not entity_result:
            return None
            
        entity_name = entity_result[0]
        
        # Generate case ID with timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        case_id = f"CASE-{entity_name.replace(' ', '')}-{timestamp}"
        
        # Create initial case document entries for all checklist items
        cursor.execute("""
            SELECT id FROM application_checklists 
            WHERE checklist_name = 'SOA Medicaid - Adult'
        """)
        
        checklist_items = cursor.fetchall()
        
        for item in checklist_items:
            cursor.execute("""
                INSERT INTO case_documents (case_id, entity_id, checklist_item_id, status, user_id, created_at, updated_at)
                VALUES (?, ?, ?, 'Pending', ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (case_id, entity_id, item[0], user_id))
        
        context_store.conn.commit()
        
        logging.info(f"Created new case '{case_id}' for entity {entity_id} (user {user_id})")
        return case_id
        
    except Exception as e:
        logging.error(f"Error creating new case: {e}")
        return None

def get_case_dashboard_data():
    """
    Retrieve all active cases with their progress metrics for the current user.
    
    Returns:
        list: List of dictionaries containing case information
    """
    try:
        current_user = get_current_user_id()
        db_path = st.session_state.get('database_path', 'production_idis.db')
        context_store = ContextStore(db_path)
        cursor = context_store.conn.cursor()
        
        # Get all distinct cases with entity information filtered by user
        cursor.execute("""
            SELECT DISTINCT cd.case_id, cd.entity_id, e.entity_name
            FROM case_documents cd
            JOIN entities e ON cd.entity_id = e.id
            WHERE cd.user_id = ?
            ORDER BY cd.case_id
        """, (current_user,))
        
        cases_raw = cursor.fetchall()
        cases_data = []
        
        # For each case, calculate progress metrics
        for case_id, entity_id, entity_name in cases_raw:
            # Get total checklist items (always 5 for SOA Medicaid - Adult)
            cursor.execute("""
                SELECT COUNT(*) 
                FROM application_checklists 
                WHERE checklist_name = 'SOA Medicaid - Adult'
            """)
            total_requirements = cursor.fetchone()[0]
            
            # Get submitted documents count for this case
            cursor.execute("""
                SELECT COUNT(*) 
                FROM case_documents 
                WHERE case_id = ? AND status = 'Submitted'
            """, (case_id,))
            submitted_count = cursor.fetchone()[0]
            
            # Calculate progress percentage
            progress_percentage = (submitted_count / total_requirements) * 100 if total_requirements > 0 else 0
            
            cases_data.append({
                'case_id': case_id,
                'entity_id': entity_id,
                'entity_name': entity_name,
                'total_requirements': total_requirements,
                'submitted_count': submitted_count,
                'progress_percentage': progress_percentage,
                'status': 'Complete' if submitted_count == total_requirements else 'In Progress'
            })
        
        return cases_data
        
    except Exception as e:
        logging.error(f"Error loading case dashboard data: {e}")
        return []


def render_case_dashboard():
    """
    Render the main Case Management Dashboard showing all active cases.
    """
    current_user = get_current_user_id()
    
    # Add user switcher for demo purposes
    st.sidebar.subheader("🔐 User Simulation")
    user_options = ['user_a', 'user_b']
    current_user_display = st.sidebar.selectbox(
        "Current User:", 
        options=user_options, 
        index=user_options.index(current_user),
        help="For demo purposes - simulates different users"
    )
    
    if current_user_display != current_user:
        st.session_state.current_user_id = current_user_display
        st.experimental_rerun()
    
    st.title("🏥 Active Case Dashboard")
    st.markdown("---")
    st.markdown(f"**Caseworker Portal** - View and manage all active Medicaid application cases (User: {current_user})")
    
    # Add "Start New Application" button
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("➕ Start New Application", type="primary", use_container_width=True):
            st.session_state.show_case_detail = False
            st.session_state.current_case_id = None
            st.session_state.show_entity_management = True
            st.experimental_rerun()
    
    st.markdown("---")
    
    # Load case data
    cases = get_case_dashboard_data()
    
    if not cases:
        st.info("No active cases found. Click 'Start New Application' to begin.")
        return
    
    # Display case cards
    st.subheader(f"📋 Active Cases ({len(cases)})")
    
    # Create columns for responsive layout
    cols = st.columns(2)
    
    for i, case in enumerate(cases):
        with cols[i % 2]:
            # Create case card using container
            with st.container():
                st.markdown(f"""
                <div style="
                    border: 1px solid #e1e5f2;
                    border-radius: 8px;
                    padding: 20px;
                    margin: 10px 0;
                    background-color: #f8f9fa;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                ">
                    <h4 style="margin-top: 0; color: #1f2041;">
                        👤 {case['entity_name']}
                    </h4>
                    <p style="margin: 5px 0; color: #6c757d;">
                        <strong>Case ID:</strong> {case['case_id']}
                    </p>
                    <p style="margin: 5px 0; color: #1f2041;">
                        <strong>Status:</strong> {case['status']}
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                # Progress metrics
                st.markdown(f"**Documents Submitted:** {case['submitted_count']} / {case['total_requirements']}")
                
                # Progress bar
                progress_value = case['progress_percentage'] / 100
                st.progress(progress_value)
                
                # Action button
                if st.button(f"📝 View Case Details", key=f"view_case_{case['case_id']}", use_container_width=True):
                    st.session_state.show_case_detail = True
                    st.session_state.current_case_id = case['case_id']
                    st.session_state.current_entity_id = case['entity_id']
                    st.session_state.show_entity_management = False
                    st.experimental_rerun()
                
                st.markdown("---")


def render_case_detail_view():
    """
    Render the detailed view for a specific case (the existing checklist interface).
    """
    case_id = st.session_state.get('current_case_id')
    entity_id = st.session_state.get('current_entity_id')
    
    if not case_id or not entity_id:
        st.error("No case selected. Please return to the dashboard.")
        return
    
    # Get entity name
    try:
        db_path = st.session_state.get('database_path', 'production_idis.db')
        context_store = ContextStore(db_path)
        cursor = context_store.conn.cursor()
        cursor.execute("SELECT entity_name FROM entities WHERE id = ?", (entity_id,))
        entity_result = cursor.fetchone()
        entity_name = entity_result[0] if entity_result else "Unknown Entity"
    except Exception as e:
        logging.error(f"Error getting entity name: {e}")
        entity_name = "Unknown Entity"
    
    # Header with back button
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("← Back to Dashboard", key="back_to_dashboard"):
            st.session_state.show_case_detail = False
            st.session_state.current_case_id = None
            st.session_state.current_entity_id = None
            st.experimental_rerun()
    
    with col2:
        st.title(f"🩺 Case Details: {entity_name}")
    
    st.markdown("---")
    st.markdown(f"**Case ID:** {case_id}")
    st.markdown("This tool helps you gather, check, and prepare documents for an Alaska Medicaid application.")

    # --- 0. Patient Selection ---
    if not render_patient_selection():
        return  # Stop here if no patient is selected
    
    st.markdown("---")

    # --- 1. Application Checklist ---
    st.header("1. Application Checklist")
    st.info("Upload documents below. The system will automatically check them off the list.")

<<<<<<< HEAD
    # Load checklist with current status from database (modified to use current entity)
    checklist_df = load_application_checklist_with_status_for_entity(entity_id)
=======
    # Load checklist with current status from database for selected patient
    checklist_df = load_application_checklist_with_status(
        patient_id=st.session_state.get('selected_patient_id'),
        case_id=st.session_state.get('current_case_id')
    )
>>>>>>> 78c181f1711a5706d2e1e656e094ce786c836d37
    
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


def render_start_new_application():
    """
    Render the secure multi-user "Start New Application" workflow.
    """
    current_user = get_current_user_id()
    
    st.title("🏢 Start New Application")
    st.markdown("---")
    st.markdown(f"**User:** {current_user}")
    
    # Back to dashboard button
    if st.button("← Back to Dashboard"):
        st.session_state.show_entity_management = False
        st.experimental_rerun()
    
    st.markdown("---")
    
    # Two-option workflow
    st.markdown("### Choose how to proceed:")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Option 1: Create New Entity")
        st.markdown("Create a new person/entity for this application")
        
        with st.form("create_entity_form"):
            entity_name = st.text_input("Entity Name", help="Enter the full name of the person applying")
            create_entity_submit = st.form_submit_button("Create Entity & Start Case", type="primary")
            
            if create_entity_submit:
                if entity_name.strip():
                    # Create new entity
                    entity_id = create_new_entity(entity_name.strip(), current_user)
                    if entity_id:
                        # Create new case
                        case_id = create_new_case(entity_id, current_user)
                        if case_id:
                            st.success(f"✅ Created new entity '{entity_name}' and case '{case_id}'")
                            st.session_state.show_entity_management = False
                            st.session_state.show_case_detail = True
                            st.session_state.current_case_id = case_id
                            st.session_state.current_entity_id = entity_id
                            st.experimental_rerun()
                        else:
                            st.error("Failed to create case. Please try again.")
                    else:
                        st.error("Failed to create entity. Please try again.")
                else:
                    st.error("Please enter a valid entity name.")
    
    with col2:
        st.markdown("#### Option 2: Select Existing Entity")
        st.markdown("Choose from your existing entities")
        
        # Get user's entities
        user_entities = get_user_entities(current_user)
        
        if user_entities:
            with st.form("select_entity_form"):
                entity_options = {f"{entity['name']} (Created: {entity['created'][:10]})": entity['id'] for entity in user_entities}
                selected_entity_display = st.selectbox(
                    "Select Entity:",
                    options=list(entity_options.keys()),
                    help="Choose an existing entity to create a new case for"
                )
                select_entity_submit = st.form_submit_button("Start New Case", type="primary")
                
                if select_entity_submit:
                    selected_entity_id = entity_options[selected_entity_display]
                    
                    # Create new case for selected entity
                    case_id = create_new_case(selected_entity_id, current_user)
                    if case_id:
                        st.success(f"✅ Created new case '{case_id}' for existing entity")
                        st.session_state.show_entity_management = False
                        st.session_state.show_case_detail = True
                        st.session_state.current_case_id = case_id
                        st.session_state.current_entity_id = selected_entity_id
                        st.experimental_rerun()
                    else:
                        st.error("Failed to create case. Please try again.")
        else:
            st.info("No existing entities found. Use Option 1 to create a new entity.")
    
    st.markdown("---")
    st.markdown("**Privacy Notice:** You can only see and create cases for your own entities. This ensures data security in multi-user environments.")


def render_navigator_ui():
    """
    Main router for the Medicaid Navigator - shows dashboard or case detail view.
    """
    # Initialize session state for navigation
    if 'show_case_detail' not in st.session_state:
        st.session_state.show_case_detail = False
    if 'current_case_id' not in st.session_state:
        st.session_state.current_case_id = None
    if 'current_entity_id' not in st.session_state:
        st.session_state.current_entity_id = None
    if 'show_entity_management' not in st.session_state:
        st.session_state.show_entity_management = False
    
    # Route to appropriate view
    if st.session_state.show_entity_management:
        render_start_new_application()
    elif st.session_state.show_case_detail:
        render_case_detail_view()
    else:
        render_case_dashboard()
