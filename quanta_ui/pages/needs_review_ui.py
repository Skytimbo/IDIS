# quanta_ui/pages/needs_review_ui.py

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

# --- Helper Functions ---
def parse_extracted_data(extracted_data_str):
    """Parse extracted data JSON string and return structured information."""
    try:
        if not extracted_data_str:
            return {}
        data = json.loads(extracted_data_str)
        return data
    except json.JSONDecodeError:
        return {}

def format_ai_document_type(doc_type_data):
    """Format AI document type for display."""
    if isinstance(doc_type_data, dict):
        predicted_class = doc_type_data.get('predicted_class', 'Unknown')
        confidence = doc_type_data.get('confidence_score', 0)
        return f"{predicted_class} ({confidence:.1%} confidence)"
    return str(doc_type_data) if doc_type_data else 'Unknown'

def format_ai_issuer(issuer_data):
    """Format AI issuer for display."""
    if isinstance(issuer_data, dict):
        name = issuer_data.get('name', 'Unknown')
        address = issuer_data.get('address', '')
        if address:
            return f"{name} ({address})"
        return name
    return str(issuer_data) if issuer_data else 'Unknown'

def get_categorization_options():
    """Get available categorization options for documents."""
    return {
        "General Document": {
            "entity_type": "general",
            "description": "General purpose document for search and reference",
            "color": "#5c85ad"
        },
        "Medicaid/Healthcare": {
            "entity_type": "medicaid",
            "description": "Healthcare or Medicaid-related document",
            "color": "#28a745"
        },
        "Financial": {
            "entity_type": "financial",
            "description": "Financial document (invoice, receipt, statement)",
            "color": "#ffc107"
        },
        "Legal": {
            "entity_type": "legal",
            "description": "Legal document (contract, agreement, notice)",
            "color": "#dc3545"
        },
        "Administrative": {
            "entity_type": "administrative",
            "description": "Administrative or operational document",
            "color": "#6c757d"
        },
        "Personal": {
            "entity_type": "personal",
            "description": "Personal document or correspondence",
            "color": "#17a2b8"
        }
    }

def render_needs_review_page():
    """Main render function for the Needs Review page."""
    st.title("📋 Documents Awaiting Review (HITL)")
    st.markdown("Review and categorize documents that the AI system has flagged for human attention.")

    # --- Database Connection ---
    @st.cache_resource
    def get_db_connection():
        """Create and cache the database connection."""
        try:
            # Use the environment variable for the DB path, with a fallback for local development
            db_path = os.getenv("REVIEW_PAGE_DB_PATH", "production_idis.db")
            
            # Ensure the directory exists (only if there's a directory path)
            db_dir = os.path.dirname(db_path)
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)
            
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

    # --- Queue Status ---
    if queue_count == 0:
        st.success("🎉 The review queue is empty! All documents have been categorized.", icon="✅")
        st.info("Documents will appear here when the AI system flags them for human review.")
        st.stop()

    # Show queue status
    st.info(f"📊 **{queue_count}** document(s) awaiting your review")

    # --- Process Each Document ---
    for doc_index, doc in enumerate(docs_in_queue):
        doc_id = doc.get('document_id')
        file_name = doc.get('file_name', 'Unknown File')
        extracted_data = parse_extracted_data(doc.get('extracted_data', ''))
        full_text = doc.get('full_text', '')
        
        # Create expandable section for each document
        with st.expander(f"📄 **{file_name}** (Document {doc_index + 1} of {queue_count})", expanded=(doc_index == 0)):
            
            # --- Document Overview ---
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.subheader("📋 Document Information")
                
                # AI Analysis Results
                if extracted_data:
                    ai_doc_type = format_ai_document_type(extracted_data.get('document_type', {}))
                    ai_issuer = format_ai_issuer(extracted_data.get('issuer', {}))
                    ai_summary = extracted_data.get('content', {}).get('summary', 'No summary available')
                    ai_tags = extracted_data.get('filing', {}).get('suggested_tags', [])
                    
                    st.markdown(f"**AI Classification:** {ai_doc_type}")
                    st.markdown(f"**AI Detected Issuer:** {ai_issuer}")
                    
                    # Tags
                    if ai_tags:
                        tags_str = " • ".join([f"`{tag}`" for tag in ai_tags])
                        st.markdown(f"**AI Suggested Tags:** {tags_str}")
                    
                    # Summary
                    st.markdown("**AI Summary:**")
                    st.info(ai_summary)
                    
                    # Financial information if available
                    financials = extracted_data.get('financials', {})
                    if financials and financials.get('total_amount'):
                        st.markdown(f"**Total Amount:** ${financials.get('total_amount', 'N/A')}")
                    
                    # Key dates
                    key_dates = extracted_data.get('key_dates', {})
                    if key_dates and key_dates.get('primary_date'):
                        st.markdown(f"**Primary Date:** {key_dates.get('primary_date', 'N/A')}")
                
                else:
                    st.warning("No AI analysis data available for this document.")
            
            with col2:
                st.subheader("📊 Document Stats")
                st.metric("Document ID", doc_id or "N/A")
                st.metric("Text Length", f"{len(full_text)} chars")
                st.metric("Status", "Pending Review")
            
            # --- Document Text Preview ---
            st.subheader("📖 Document Content")
            if full_text:
                with st.expander("View Full Document Text", expanded=False):
                    st.text_area("Document Text", full_text, height=300, disabled=True, key=f"text_{doc_id}")
            else:
                st.warning("No text content available for this document.")
            
            # --- Categorization Section ---
            st.subheader("🎯 Categorize This Document")
            st.markdown("Select the appropriate category for this document:")
            
            # Get categorization options
            categories = get_categorization_options()
            
            # Create categorization buttons
            col_count = 3
            button_cols = st.columns(col_count)
            
            category_items = list(categories.items())
            for i, (category_name, category_data) in enumerate(category_items):
                col_idx = i % col_count
                with button_cols[col_idx]:
                    if st.button(
                        f"📂 {category_name}",
                        key=f"cat_{doc_id}_{category_name.replace(' ', '_')}",
                        help=category_data["description"],
                        use_container_width=True
                    ):
                        # Process the categorization
                        success = categorize_document(context_store, doc_id, category_name, category_data)
                        if success:
                            st.success(f"✅ Document categorized as: {category_name}")
                            st.rerun()
                        else:
                            st.error("❌ Failed to categorize document. Please try again.")
            
            # --- Additional Actions ---
            st.subheader("🔧 Additional Actions")
            action_col1, action_col2 = st.columns(2)
            
            with action_col1:
                if st.button(f"🗑️ Skip This Document", key=f"skip_{doc_id}", help="Skip this document for now"):
                    # Move to a different status to remove from queue
                    skip_success = skip_document(context_store, doc_id)
                    if skip_success:
                        st.info("Document skipped and moved to later review.")
                        st.rerun()
                    else:
                        st.error("Failed to skip document.")
            
            with action_col2:
                if st.button(f"🔄 Re-analyze", key=f"reanalyze_{doc_id}", help="Re-run AI analysis on this document"):
                    st.info("Re-analysis feature not yet implemented.")
            
            st.divider()

def categorize_document(context_store, doc_id, category_name, category_data):
    """Categorize a document and update its status in the database."""
    try:
        # Create entity data for the categorization
        entity_data = {
            "entity_name": category_name,
            "entity_type": category_data["entity_type"],
            "entity_id": f"{category_data['entity_type']}_{doc_id}",
            "categorization_timestamp": datetime.now().isoformat(),
            "categorized_by": "human_reviewer",
            "category_description": category_data["description"]
        }
        
        # Update the document categorization
        entity_json = json.dumps(entity_data)
        success = context_store.update_document_categorization(doc_id, entity_json)
        
        if success:
            # Clear the cache to force a re-fetch of the document list
            st.cache_data.clear()
            return True
        else:
            return False
            
    except Exception as e:
        st.error(f"Error categorizing document: {e}")
        return False

def skip_document(context_store, doc_id):
    """Skip a document by changing its status."""
    try:
        # Update the document status to 'skipped_review'
        success = context_store.update_document_fields(doc_id, {
            'processing_status': 'skipped_review',
            'review_timestamp': datetime.now().isoformat(),
            'reviewed_by': 'human_reviewer'
        })
        
        if success:
            # Clear the cache to force a re-fetch of the document list
            st.cache_data.clear()
            return True
        else:
            return False
            
    except Exception as e:
        st.error(f"Error skipping document: {e}")
        return False