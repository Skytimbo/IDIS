"""
QuantaIQ Document Search Interface
A Streamlit application for searching and viewing documents stored in the IDIS ContextStore database.
"""

import streamlit as st
import sqlite3
import pandas as pd
import json
from datetime import datetime, date
from typing import List, Tuple, Optional, Dict, Any
import os
import sys

# --- Dynamic Application Configuration ---

def initialize_app_config():
    """
    Parses command-line arguments to get the database and archive paths.
    This allows Docker to configure the running application.
    """
    db_path_arg = None
    archive_path_arg = None
    
    # Manually parse sys.argv to find our custom flags, which is more reliable inside Streamlit
    try:
        db_index = sys.argv.index('--database-path')
        db_path_arg = sys.argv[db_index + 1]
    except (ValueError, IndexError):
        pass  # Argument not found

    try:
        archive_index = sys.argv.index('--archive-path')
        archive_path_arg = sys.argv[archive_index + 1]
    except (ValueError, IndexError):
        pass # Argument not found
        
    # Provide default paths for local development (when not run via docker-compose)
    # This makes the app runnable with just `streamlit run app.py`
    if not db_path_arg:
        project_root = os.getcwd()
        default_db_path = os.path.join(project_root, 'data', 'idis_db_storage', 'idis.db')
        st.warning(f"Using default database path: {default_db_path}")
        db_path_arg = default_db_path

    if not archive_path_arg:
        project_root = os.getcwd()
        default_archive_path = os.path.join(project_root, 'data', 'idis_archive')
        st.warning(f"Using default archive path: {default_archive_path}")
        archive_path_arg = default_archive_path

    return db_path_arg, archive_path_arg

# Initialize configuration when the script is loaded
DB_PATH, ARCHIVE_PATH = initialize_app_config()


# --- Page Configuration ---
st.set_page_config(
    page_title="QuantaIQ Document Search",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Database Functions ---
@st.cache_resource
def get_database_connection():
    """Get a connection to the SQLite database. Using Streamlit's cache to maintain connection."""
    if not os.path.exists(DB_PATH):
        st.error(f"Database file not found: {DB_PATH}. Please ensure the watcher service is running and has processed at least one document.")
        st.stop()
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def get_document_types() -> List[str]:
    """Get distinct document types from the database."""
    try:
        conn = get_database_connection()
        types = pd.read_sql_query("SELECT DISTINCT document_type FROM documents WHERE document_type IS NOT NULL ORDER BY document_type", conn)
        return types['document_type'].tolist()
    except Exception as e:
        st.error(f"Error fetching document types: {str(e)}")
        return []

def build_search_query(search_term, doc_types, issuer_filter, tags_filter, after_date, before_date) -> Tuple[str, List[Any]]:
    """Build the SQL query and parameters for searching documents."""
    query_parts = ["SELECT document_id, file_name, document_type, upload_timestamp, issuer_source, filed_path, full_text, document_dates, tags_extracted FROM documents WHERE 1=1"]
    params = []

    if search_term:
        query_parts.append("AND full_text LIKE ?")
        params.append(f"%{search_term}%")
    if doc_types:
        placeholders = ",".join(["?" for _ in doc_types])
        query_parts.append(f"AND document_type IN ({placeholders})")
        params.extend(doc_types)
    if issuer_filter:
        query_parts.append("AND issuer_source LIKE ?")
        params.append(f"%{issuer_filter}%")
    if tags_filter:
        query_parts.append("AND tags_extracted LIKE ?")
        params.append(f"%{tags_filter}%")
    if after_date:
        query_parts.append("AND date(upload_timestamp) >= ?")
        params.append(after_date)
    if before_date:
        query_parts.append("AND date(upload_timestamp) <= ?")
        params.append(before_date)

    query_parts.append("ORDER BY upload_timestamp DESC")
    return " ".join(query_parts), params

@st.cache_data
def get_document_summary(document_id: str) -> Optional[str]:
    """Get the AI-generated summary for a document from agent_outputs."""
    try:
        conn = get_database_connection()
        query = """
            SELECT output_data 
            FROM agent_outputs 
            WHERE document_id = ? AND output_type = 'per_document_summary'
            ORDER BY creation_timestamp DESC
            LIMIT 1
        """
        summary_df = pd.read_sql_query(query, conn, params=(document_id,))
        return summary_df['output_data'].iloc[0] if not summary_df.empty else "No summary available."
    except Exception as e:
        st.warning(f"Could not fetch summary: {str(e)}")
        return "Error fetching summary."

# --- UI Helper Functions ---
def format_json_display(json_string: Optional[str], default_text="Not available") -> str:
    if not json_string: return default_text
    try:
        data = json.loads(json_string)
        if isinstance(data, dict):
            return "; ".join([f"{k.replace('_', ' ').title()}: {v}" for k, v in data.items()])
        if isinstance(data, list):
            return ", ".join(data) if data else default_text
    except (json.JSONDecodeError, TypeError):
        return json_string
    return default_text

def get_display_filename(filed_path: Optional[str], original_name: str) -> str:
    return os.path.basename(filed_path) if filed_path and os.path.basename(filed_path) else original_name

# --- Main Application UI ---
def main():
    st.title("🔍 QuantaIQ Document Search")
    st.markdown("*Intelligent Document Insight System - Cognitive Interface*")

    st.sidebar.header("🔧 Search Filters")
    search_term = st.sidebar.text_input("Search Document Content")
    selected_types = st.sidebar.multiselect("Document Type", options=get_document_types())
    issuer_filter = st.sidebar.text_input("Issuer / Source")
    tags_filter = st.sidebar.text_input("Tags (comma-separated)")
    after_date = st.sidebar.date_input("Uploaded After", value=None)
    before_date = st.sidebar.date_input("Uploaded Before", value=None)
    
    run_search = st.sidebar.button("🔍 Search", type="primary")

    if 'results' not in st.session_state:
        st.session_state.results = None

    if run_search:
        conn = get_database_connection()
        query, params = build_search_query(search_term, selected_types, issuer_filter, tags_filter, after_date, before_date)
        st.session_state.results = pd.read_sql_query(query, conn, params=params)

    if st.session_state.results is not None:
        results_df = st.session_state.results
        st.success(f"📊 Found {len(results_df)} matching document(s)")
        
        for index, row in results_df.iterrows():
            display_filename = get_display_filename(row['filed_path'], row['file_name'])
            with st.container(border=True):
                st.subheader(f"📄 {display_filename}")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Type:** `{row['document_type'] or 'N/A'}`")
                    st.markdown(f"**Source:** `{row['issuer_source'] or 'N/A'}`")
                with col2:
                    processed_date_str = "N/A"
                    if pd.notna(row['upload_timestamp']):
                        upload_dt = pd.to_datetime(row['upload_timestamp'])
                        processed_date_str = upload_dt.strftime('%Y-%m-%d %H:%M')
                    st.markdown(f"**Processed:** `{processed_date_str}`")
                    st.markdown(f"**Tags:** `{format_json_display(row['tags_extracted'], 'None')}`")
                
                with st.expander("View Details"):
                    st.markdown("---")
                    st.subheader("📋 AI Summary")
                    st.info(get_document_summary(row['document_id']))
                    
                    st.subheader("📅 Extracted Dates")
                    st.code(format_json_display(row['document_dates'], 'None'))
                    
                    st.subheader("📝 Extracted Text")
                    st.text_area("Full Text", value=row['full_text'], height=250, key=f"text_{row['document_id']}_{index}")

                    if row['filed_path']:
                        st.subheader("📁 File Location")
                        st.code(row['filed_path'], language=None)
    else:
        st.info("👆 Use the filters in the sidebar and click Search to find documents.")

if __name__ == "__main__":
    main()