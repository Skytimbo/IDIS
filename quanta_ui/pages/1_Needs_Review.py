# quanta_ui/pages/1_Needs_Review.py

import streamlit as st
import os
import sys
import json
from datetime import datetime

# --- Path Setup ---
# This is a robust way to ensure the script can find the context_store module
# It adds the project's root directory to the Python path.
def get_project_root():
    """Traverse up to find the project root marked by '.git' or 'pyproject.toml'."""
    current_path = os.path.abspath(os.path.dirname(__file__))
    while current_path != os.path.dirname(current_path): # Stop at filesystem root
        if os.path.isdir(os.path.join(current_path, '.git')) or os.path.isfile(os.path.join(current_path, 'pyproject.toml')):
            return current_path
        current_path = os.path.dirname(current_path)
    return os.path.abspath(os.path.dirname(__file__)) # Fallback

# Add project root to path
project_root = get_project_root()
if project_root not in sys.path:
    sys.path.append(project_root)

from context_store import ContextStore

# --- Page Configuration ---
st.set_page_config(
    page_title="Documents Awaiting Review",
    page_icon="🧐",
    layout="wide"
)

st.title("Documents Awaiting Review (HITL) 🧐")
st.markdown("Assign a context to documents that the system could not categorize automatically.")

# --- Database Connection ---
@st.cache_resource
def get_db_connection():
    """Create and cache the database connection."""
    try:
        db_path = os.path.expanduser('~/IDIS_Dell_Scan_Test/idis_db_storage/idis_live_test.db')
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        if not os.path.exists(db_path):
            st.error(f"Database not found at {db_path}. Please run the initialization script.")
            return None
        return ContextStore(db_path)
    except Exception as e:
        st.error(f"Failed to connect to database: {e}")
        return None

context_store = get_db_connection()

# --- Data Fetching ---
@st.cache_data(ttl=10) # Cache data for 10 seconds to allow for quick refreshes
def get_docs_to_review():
    """Fetch documents with 'pending_categorization' status."""
    if not context_store:
        return []
    try:
        docs = context_store.get_documents_by_processing_status('pending_categorization')
        return docs
    except Exception as e:
        st.error(f"Error fetching documents: {e}")
        return []

# --- Main Application Logic ---
if not context_store:
    st.stop()

# Fetch the documents that need review
docs_in_queue = get_docs_to_review()
queue_count = len(docs_in_queue)

st.info(f"You have **{queue_count}** document(s) awaiting your review.", icon="ℹ️")

if not docs_in_queue:
    st.success("The review queue is empty! Great job.", icon="✅")
    st.stop()

# Get the current document to display (always the first in the list)
current_doc = docs_in_queue[0]
doc_id = current_doc['document_id']
extracted_data = json.loads(current_doc.get('extracted_data', '{}'))

# --- UI Layout ---
st.divider()
st.header(f"Reviewing: `{current_doc.get('file_name', 'Unknown File')}`")

col1, col2 = st.columns([1, 2])

with col1:
    # Display key information from the extracted JSON
    st.subheader("Extracted Details")
    st.text(f"Document ID: {doc_id}")
    st.info(f"**Issuer:** {extracted_data.get('issuer', {}).get('name', 'N/A')}")
    st.text(f"**Primary Date:** {extracted_data.get('key_dates', {}).get('primary_date', 'N/A')}")
    st.text(f"**Total Amount:** {extracted_data.get('financials', {}).get('total_amount', 'N/A')}")
    
    summary = extracted_data.get('content', {}).get('summary', 'No summary available.')
    st.text_area("AI Summary", summary, height=200, disabled=True)

with col2:
    st.subheader("Document Preview")
    st.warning("Document image preview is not yet implemented.", icon="🖼️")
    st.image("https://i.imgur.com/n4s4z4V.png", caption="Placeholder for Scanned Document Image")

st.divider()

# --- Action Panel ---
st.subheader("Which entity should this be associated with?")

# MOCK ENTITIES - In a real app, this would be fetched from the user's settings
MOCK_ENTITIES = {
    "Primary Residence": {"entity_id": "prop-uuid-001", "entity_type": "Property"},
    "Rental on Pioneer Ave": {"entity_id": "prop-uuid-002", "entity_type": "Property"},
    "General Business Expense": {"entity_id": "biz-uuid-001", "entity_type": "Business"}
}

def categorize_document(document_id_to_update, entity_data):
    """Callback function to update the database when a button is clicked."""
    if context_store:
        entity_json = json.dumps(entity_data)
        success = context_store.update_document_categorization(document_id_to_update, entity_json)
        if success:
            # Clear the cache to force a re-fetch of the document list on the next run
            st.cache_data.clear()
        else:
            st.error("Failed to update document categorization in the database.")

# Create a button for each entity
button_cols = st.columns(len(MOCK_ENTITIES))
for i, (entity_name, entity_data) in enumerate(MOCK_ENTITIES.items()):
    with button_cols[i]:
        st.button(
            entity_name, 
            key=f"entity_{entity_name}", 
            on_click=categorize_document,
            args=(doc_id, entity_data),
            use_container_width=True,
            type="primary" if i == 0 else "secondary"
        )