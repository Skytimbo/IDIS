import streamlit as st
import pandas as pd
import os
import logging
from datetime import datetime
from context_store import ContextStore
from unified_ingestion_agent import UnifiedIngestionAgent
from modules.shared.confidence_meter import extract_confidence_from_document, render_confidence_meter


def load_application_checklist_with_status_for_case(case_id: str,
                                                    entity_id: int):
    """
    Load the application checklist with current status for a specific case.
    Checks case_documents table for submitted documents.

    Args:
        case_id: The case ID to check status for.
        entity_id: The entity ID associated with the case.

    Returns:
        pd.DataFrame: Formatted checklist with current status.
    """
    try:
        db_path = st.session_state.get('database_path', 'production_idis.db')
        context_store = ContextStore(db_path)

        cursor = context_store.conn.cursor()
        cursor.execute(
            """
            SELECT ac.id, ac.required_doc_name, ac.description,
                   CASE 
                       WHEN cd.status = 'Submitted' AND cd.is_override = 1 THEN '🟡 Overridden'
                       WHEN cd.status = 'Submitted' THEN '🔵 Submitted'
                       ELSE '🔴 Missing'
                   END as status
            FROM application_checklists ac
            LEFT JOIN case_documents cd ON ac.id = cd.checklist_item_id 
                AND cd.case_id = ? AND cd.entity_id = ?
            WHERE ac.checklist_name = 'SOA Medicaid - Adult'
            ORDER BY ac.id
        """, (case_id, entity_id))

        requirements = cursor.fetchall()

        if not requirements:
            return pd.DataFrame()

        checklist_data = {
            "Document Required": [req[1] for req in requirements],
            "Status": [req[3] for req in requirements],
            "Examples": [req[2] for req in requirements]
        }

        return pd.DataFrame(checklist_data)

    except Exception as e:
        logging.error(
            f"Error loading application checklist for case {case_id}: {e}")
        return pd.DataFrame()


def validate_document_assignment(ai_detected_type: str,
                                 selected_requirement: str) -> dict:
    """
    Validate if a document assignment is appropriate based on AI classification.

    Args:
        ai_detected_type: The document type detected by AI
        selected_requirement: The requirement selected by the user

    Returns:
        dict: {'is_valid': bool, 'warning_message': str}
    """
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

    valid_types = valid_mappings.get(selected_requirement, [])

    if ai_detected_type in ['None', 'Unknown', '']:
        return {
            'is_valid':
            False,
            'warning_message':
            f"The AI could not determine the document type. Please verify this document is appropriate for '{selected_requirement}'. Expected types: {', '.join(valid_types)}"
        }
    elif ai_detected_type in valid_types:
        return {'is_valid': True, 'warning_message': ''}
    else:
        return {
            'is_valid':
            False,
            'warning_message':
            f"A '{ai_detected_type}' document may not be appropriate for '{selected_requirement}'. Expected types: {', '.join(valid_types)}"
        }


def assign_document_to_requirement(document_id: int,
                                   requirement_id: int,
                                   override: bool = False,
                                   override_reason: str = ""):
    """
    Assign a document to a specific checklist requirement for the current case.

    Args:
        document_id: ID of the document to assign
        requirement_id: ID of the checklist requirement
        override: Whether this assignment is an override of validation warnings
        override_reason: Reason for the override (logged for audit trail)

    Returns:
        bool: True if assignment was successful
    """
    try:
        logging.info("DEBUG: Entered assign_document_to_requirement function.")

        if override and override_reason:
            logging.info(
                f"AUDIT: Document assignment override - {override_reason}")

        entity_id = st.session_state.get('current_entity_id')
        case_id = st.session_state.get('current_case_id')

        if not entity_id or not case_id:
            logging.error("No active entity or case in session.")
            return False

        db_path = st.session_state.get('database_path', 'production_idis.db')
        context_store = ContextStore(db_path)
        cursor = context_store.conn.cursor()

        cursor.execute(
            """
            SELECT id FROM case_documents 
            WHERE checklist_item_id = ? AND entity_id = ? AND case_id = ?
        """, (requirement_id, entity_id, case_id))

        existing_record = cursor.fetchone()

        if existing_record:
            cursor.execute(
                """
                UPDATE case_documents 
                SET document_id = ?, status = 'Submitted', is_override = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (document_id, 1 if override else 0, existing_record[0]))
        else:
            # This path is less likely with the new "create_new_case" logic, but is good for robustness.
            cursor.execute(
                """
                INSERT INTO case_documents (case_id, entity_id, checklist_item_id, document_id, status, is_override, user_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'Submitted', ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (case_id, entity_id, requirement_id, document_id,
                  1 if override else 0,
                  st.session_state.get('current_user_id', 'user_a')))

        context_store.conn.commit()
        logging.info("DEBUG: Database update successful, returning True.")
        return True

    except Exception as e:
        logging.error(
            f"Error assigning document {document_id} to requirement {requirement_id}: {e}"
        )
        return False


def render_document_assignment_interface():
    """
    Render the document assignment interface for processed documents.
    """
    if 'processed_documents' not in st.session_state or not st.session_state.processed_documents:
        return

    st.header("📎 Assign Documents to Requirements")

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

    documents_to_process = list(st.session_state.processed_documents)
    documents_to_remove = []
    rerun_needed = False

    for i, doc_info in enumerate(documents_to_process):
        with st.expander(f"📄 New document '{doc_info['filename']}' processed",
                         expanded=True):
            col1, col2 = st.columns([2, 1])

            with col1:
                st.write(f"**Filename:** {doc_info['filename']}")
                st.write(
                    f"**AI-detected type:** {doc_info.get('document_type', 'Unknown')}"
                )

                if doc_info.get('extracted_data'):
                    confidence, document_type, has_heuristic_override = extract_confidence_from_document(
                        {'extracted_data': doc_info['extracted_data']})
                    st.markdown("**AI Classification Confidence:**")
                    render_confidence_meter(confidence,
                                            document_type,
                                            compact=True)

                options_with_placeholder = ["Select a requirement..."] + list(
                    requirement_options.keys())
                selected_requirement = st.selectbox(
                    "Assign to requirement:",
                    options=options_with_placeholder,
                    key=f"req_select_{i}",
                    index=0)

                if selected_requirement == "Select a requirement...":
                    selected_requirement = None

            with col2:
                if st.button("✅ Assign Document",
                              key=f"assign_btn_{i}",
                              type="primary"):
                    if selected_requirement:
                        requirement_id = requirement_options[
                            selected_requirement]

                        validation_result = validate_document_assignment(
                            doc_info.get('document_type', 'Unknown'),
                            selected_requirement)

                        is_override = not validation_result['is_valid']
                        override_reason = ""

                        if is_override:
                            override_reason = f"User override: {doc_info.get('document_type', 'Unknown')} → {selected_requirement}"
                            st.warning(
                                f"⚠️ {validation_result['warning_message']}")

                        success = assign_document_to_requirement(
                            doc_info['document_id'],
                            requirement_id,
                            override=is_override,
                            override_reason=override_reason)

                        if success:
                            st.success(
                                f"✅ Document assigned to '{selected_requirement}'"
                                + (" (Override)" if is_override else ""))
                            documents_to_remove.append(doc_info)
                            rerun_needed = True
                        else:
                            st.error("❌ Failed to assign document")
                    else:
                        st.warning("Please select a requirement first")

    if documents_to_remove:
        for doc_to_remove in documents_to_remove:
            if doc_to_remove in st.session_state.processed_documents:
                st.session_state.processed_documents.remove(doc_to_remove)

    if rerun_needed:
        st.rerun()

def get_current_user_id():
    """
    Get the current user ID (simulated for demo purposes).
    In a real application, this would come from an authentication system.
    """
    return st.session_state.get('current_user_id', 'user_a')


def get_user_entities(user_id, search_term: str = None):
    """
    Get all entities belonging to a specific user, with optional search.
    """
    try:
        db_path = st.session_state.get('database_path', 'production_idis.db')
        context_store = ContextStore(db_path)
        cursor = context_store.conn.cursor()

        if search_term:
            query = """
                SELECT id, entity_name, creation_timestamp
                FROM entities 
                WHERE user_id = ? AND entity_name LIKE ?
                ORDER BY entity_name
            """
            params = (user_id, f"%{search_term}%")
        else:
            # Return empty list if no search term, to avoid showing all entities by default
            return []

        cursor.execute(query, params)
        entities = cursor.fetchall()
        return [{
            'id': row[0],
            'name': row[1],
            'created': row[2]
        } for row in entities]

    except Exception as e:
        logging.error(f"Error loading user entities: {e}")
        return []


def create_new_entity(entity_name, user_id):
    """
    Create a new entity for the specified user.
    """
    try:
        db_path = st.session_state.get('database_path', 'production_idis.db')
        context_store = ContextStore(db_path)
        cursor = context_store.conn.cursor()

        cursor.execute(
            """
            INSERT INTO entities (entity_name, user_id, creation_timestamp, last_modified_timestamp)
            VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (entity_name, user_id))

        entity_id = cursor.lastrowid
        context_store.conn.commit()

        logging.info(
            f"Created new entity '{entity_name}' (ID: {entity_id}) for user {user_id}"
        )
        return entity_id

    except Exception as e:
        logging.error(f"Error creating new entity: {e}")
        return None


def create_new_case(entity_id, user_id):
    """
    Create a new case for the specified entity and user.
    """
    try:
        db_path = st.session_state.get('database_path', 'production_idis.db')
        context_store = ContextStore(db_path)
        cursor = context_store.conn.cursor()

        cursor.execute("SELECT entity_name FROM entities WHERE id = ?",
                       (entity_id, ))
        entity_result = cursor.fetchone()
        if not entity_result:
            return None
        entity_name = entity_result[0]

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        case_id = f"CASE-{entity_name.replace(' ', '')}-{timestamp}"

        cursor.execute("""
            SELECT id FROM application_checklists 
            WHERE checklist_name = 'SOA Medicaid - Adult'
        """)
        checklist_items = cursor.fetchall()

        for item in checklist_items:
            cursor.execute(
                """
                INSERT INTO case_documents (case_id, entity_id, checklist_item_id, status, user_id, created_at, updated_at)
                VALUES (?, ?, ?, 'Pending', ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (case_id, entity_id, item[0], user_id))

        context_store.conn.commit()
        logging.info(
            f"Created new case '{case_id}' for entity {entity_id} (user {user_id})"
        )
        return case_id

    except Exception as e:
        logging.error(f"Error creating new case: {e}")
        return None


def get_case_dashboard_data():
    """
    Retrieve all active cases with their progress metrics for the current user.
    """
    try:
        current_user = get_current_user_id()
        db_path = st.session_state.get('database_path', 'production_idis.db')
        context_store = ContextStore(db_path)
        cursor = context_store.conn.cursor()

        cursor.execute(
            """
            SELECT DISTINCT cd.case_id, cd.entity_id, e.entity_name
            FROM case_documents cd
            JOIN entities e ON cd.entity_id = e.id
            WHERE cd.user_id = ?
            ORDER BY cd.case_id
        """, (current_user, ))

        cases_raw = cursor.fetchall()
        cases_data = []

        for case_id, entity_id, entity_name in cases_raw:
            cursor.execute("""
                SELECT COUNT(*) 
                FROM application_checklists 
                WHERE checklist_name = 'SOA Medicaid - Adult'
            """)
            total_requirements = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT COUNT(*) 
                FROM case_documents 
                WHERE case_id = ? AND status = 'Submitted'
            """, (case_id, ))
            submitted_count = cursor.fetchone()[0]

            progress_percentage = (submitted_count / total_requirements
                                   ) * 100 if total_requirements > 0 else 0

            cases_data.append({
                'case_id':
                case_id,
                'entity_id':
                entity_id,
                'entity_name':
                entity_name,
                'total_requirements':
                total_requirements,
                'submitted_count':
                submitted_count,
                'progress_percentage':
                progress_percentage,
                'status':
                'Complete'
                if submitted_count == total_requirements else 'In Progress'
            })

        return cases_data

    except Exception as e:
        logging.error(f"Error loading case dashboard data: {e}")
        return []


def render_home_page():
    """
    Render the Case Manager Home Dashboard with KPIs and navigation.
    """
    # This function would fetch real data in a production setting
    # For now, we use dummy data as planned
    current_user = get_current_user_id()

    st.title("🏠 Case Manager Home Dashboard")
    st.markdown("---")
    st.markdown(
        f"**Welcome, {current_user}** - Your comprehensive case management overview"
    )

    # KPIs Section
    st.subheader("📊 Key Performance Indicators")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Active Cases", "42", "2 New")
    with col2:
        st.metric("Clients Managed", "65")
    with col3:
        st.metric("Deadlines This Week", "3", "-1 vs last week")

    st.markdown("---")

    # Status Chart Section
    st.subheader("📈 Case Status Overview")
    status_data = pd.DataFrame({
        'Status': ['In Progress', 'Awaiting SOA', 'Client Action', 'Complete'],
        'Count': [25, 10, 5, 57]
    })
    st.bar_chart(status_data.set_index('Status'))

    st.markdown("---")

    # Action Buttons Section
    st.subheader("🚀 Quick Actions")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("📋 View All Active Cases",
                      type="primary",
                      use_container_width=True):
            st.session_state.medicaid_view = 'active_cases'
            st.rerun()

    with col2:
        if st.button("➕ Start New Application",
                      type="secondary",
                      use_container_width=True):
            st.session_state.medicaid_view = 'new_application'
            st.rerun()


def render_active_cases_view():
    """
    Render the detailed view showing all active cases.
    """
    current_user = get_current_user_id()

    st.title("🏥 Active Cases")
    st.markdown("---")

    cases = get_case_dashboard_data()

    if not cases:
        st.info("No active cases found for this user.")
        return

    # Using st.columns for a responsive card layout
    cols = st.columns(2)
    for i, case in enumerate(cases):
        with cols[i % 2]:
            with st.container():
                st.markdown(f"**👤 {case['entity_name']}**")
                st.caption(f"Case ID: {case['case_id']}")
                st.markdown(f"**Status:** {case['status']}")
                st.markdown(
                    f"**Documents Submitted:** {case['submitted_count']} / {case['total_requirements']}"
                )
                st.progress(case['progress_percentage'] / 100)

                if st.button(f"📝 View Case Details",
                             key=f"view_case_{case['case_id']}",
                             use_container_width=True):
                    st.session_state.current_case_id = case['case_id']
                    st.session_state.current_entity_id = case['entity_id']
                    st.session_state.medicaid_view = 'case_detail'
                    st.rerun()
                st.markdown("---")

def get_documents_for_case(case_id: str):
    """
    Helper function to retrieve all documents associated with a specific case.
    """
    try:
        db_path = st.session_state.get('database_path', 'production_idis.db')
        context_store = ContextStore(db_path)
        cursor = context_store.conn.cursor()
        query = """
            SELECT d.id, d.filename
            FROM documents d
            JOIN case_documents cd ON d.id = cd.document_id
            WHERE cd.case_id = ?
        """
        cursor.execute(query, (case_id, ))
        docs = cursor.fetchall()
        return [{"id": row[0], "filename": row[1]} for row in docs]
    except Exception as e:
        logging.error(f"Error retrieving documents for case {case_id}: {e}")
        return []


def render_case_detail_view():
    """
    Render the detailed view for a specific case.
    """
    case_id = st.session_state.get('current_case_id')
    entity_id = st.session_state.get('current_entity_id')

    if not case_id or not entity_id:
        st.error("No case selected. Please return to the dashboard.")
        return

    try:
        db_path = st.session_state.get('database_path', 'production_idis.db')
        context_store = ContextStore(db_path)
        cursor = context_store.conn.cursor()
        cursor.execute("SELECT entity_name FROM entities WHERE id = ?",
                       (entity_id, ))
        entity_result = cursor.fetchone()
        entity_name = entity_result[0] if entity_result else "Unknown Entity"
    except Exception as e:
        logging.error(f"Error getting entity name: {e}")
        entity_name = "Unknown Entity"

    st.title(f"🩺 Case Details: {entity_name}")
    st.markdown("---")
    st.markdown(f"**Case ID:** {case_id}")

    st.header("1. Application Checklist")
    checklist_df = load_application_checklist_with_status_for_case(
        case_id, entity_id)

    if not checklist_df.empty:
        st.table(checklist_df)
    else:
        st.warning("Unable to load application checklist.")

    st.subheader("📄 Case Documents")
    case_documents = get_documents_for_case(case_id)

    if not case_documents:
        st.info("No documents have been assigned to this case yet.")
    else:
        for doc in case_documents:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(doc['filename'])
            with col2:
                if st.button("View Document", key=f"view_doc_{doc['id']}"):
                    st.session_state.document_to_view = doc['id']

    if 'document_to_view' in st.session_state and st.session_state.document_to_view:
        doc_id = st.session_state.document_to_view
        user_id = get_current_user_id()
        db_path = st.session_state.get('database_path', 'production_idis.db')
        context_store = ContextStore(db_path)

        with st.expander("Document Viewer", expanded=True):
            # TODO: Add OAuth-based user validation here when authentication is implemented
            # For MVP demo: bypassing user access checks
            retrieved_doc = context_store.get_document_details_by_id(doc_id, user_id=None)

            if retrieved_doc:
                st.write(f"**Viewing:** {retrieved_doc['filename']}")
                content_type = retrieved_doc['content_type']

                if 'image' in content_type:
                    st.image(retrieved_doc['content'])
                elif 'text' in content_type:
                    st.text(retrieved_doc['content'].decode('utf-8',
                                                          errors='ignore'))
                else:
                    st.download_button(
                        label=f"Download {retrieved_doc['filename']}",
                        data=retrieved_doc['content'],
                        file_name=retrieved_doc['filename'],
                        mime=content_type)

                if st.button("Close Viewer"):
                    st.session_state.document_to_view = None
                    st.rerun()
            else:
                st.error(
                    "Could not retrieve document or you do not have permission."
                )

    st.header("3. Upload & Assign Documents")

    # Make the file uploader clearly visible by default
    with st.container(border=True):
        from modules.shared.unified_uploader import render_unified_uploader
        render_unified_uploader(
            context="medicaid",
            title="Upload New Documents for this Case",
            description="Drag files here or click to browse.",
            button_text="Analyze Documents",
            file_types=['pdf', 'png', 'jpg', 'jpeg', 'txt', 'docx'],
            accept_multiple=True)

    render_document_assignment_interface()


def render_start_new_application():
    """
    Render the workflow to start a new application.
    """
    current_user = get_current_user_id()

    st.title("🏢 Start New Application")
    st.markdown("---")

    st.markdown("### Choose an option to proceed:")

    col1, col2 = st.columns(2)

    with col1:
        with st.form("create_entity_form"):
            st.markdown("#### Option 1: Create New Entity")
            entity_name = st.text_input(
                "New Entity Name",
                help="Enter the full name of the person applying.")
            if st.form_submit_button("Create Entity & Start Case",
                                     type="primary"):
                if entity_name.strip():
                    entity_id = create_new_entity(entity_name.strip(),
                                                  current_user)
                    if entity_id:
                        case_id = create_new_case(entity_id, current_user)
                        if case_id:
                            st.success(f"✅ Created new case '{case_id}'")
                            st.session_state.current_case_id = case_id
                            st.session_state.current_entity_id = entity_id
                            st.session_state.medicaid_view = 'case_detail'
                            st.rerun()
                        else:
                            st.error("Failed to create a case.")
                    else:
                        st.error("Failed to create an entity.")
                else:
                    st.error("Please enter a valid entity name.")

    with col2:
        with st.form("select_entity_form"):
            st.markdown("#### Option 2: Use Existing Entity")

            search_term = st.text_input("Search for Existing Entity by Name:",
                                        key="entity_search_term")

            if st.form_submit_button("Search Entities"):
                if search_term.strip():
                    st.session_state.entity_search_results = get_user_entities(
                        current_user, search_term.strip())
                else:
                    st.session_state.entity_search_results = []

            if 'entity_search_results' in st.session_state and st.session_state.entity_search_results:
                results = st.session_state.entity_search_results
                entity_options = {
                    f"{entity['name']} (ID: {entity['id']})": entity['id']
                    for entity in results
                }

                selected_entity_display = st.radio(
                    "Select an entity from search results:",
                    options=list(entity_options.keys()))

                if st.form_submit_button("Start New Case for Selected Entity",
                                         type="primary"):
                    selected_entity_id = entity_options[
                        selected_entity_display]
                    case_id = create_new_case(selected_entity_id, current_user)
                    if case_id:
                        st.success(f"✅ Created new case '{case_id}'")
                        st.session_state.current_case_id = case_id
                        st.session_state.current_entity_id = selected_entity_id
                        st.session_state.medicaid_view = 'case_detail'
                        st.session_state.entity_search_results = [
                        ]  # Clear results after use
                        st.rerun()
                    else:
                        st.error("Failed to create a case.")
            elif 'entity_search_results' in st.session_state:  # Searched but no results
                st.info("No matching entities found.")


    st.markdown("---")
    st.markdown(
        "**Privacy Notice:** You can only see and create cases for your own entities."
    )


def render_navigator_ui():
    """Main router for the Medicaid Navigator module."""
    if 'medicaid_view' not in st.session_state:
        st.session_state.medicaid_view = 'home'

    # Add a "Back to Home" button on all pages except the home page
    if st.session_state.medicaid_view != 'home':
        if st.sidebar.button("🏠 Back to Home Dashboard"):
            st.session_state.medicaid_view = 'home'
            st.rerun()
        st.sidebar.markdown("---")

    if st.session_state.medicaid_view == 'home':
        render_home_page()
    elif st.session_state.medicaid_view ==