"""
QuantaIQ Document Search Interface
A Streamlit application for searching and viewing documents stored in the IDIS ContextStore database.
"""

import streamlit as st
import sqlite3
import pandas as pd
import json
import re
from datetime import datetime, date
from typing import List, Tuple, Optional, Dict, Any
import os
import sys
from modules.shared.confidence_meter import extract_confidence_from_document, render_confidence_meter, render_confidence_badge, render_processing_confidence_summary

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
        default_db_path = os.path.join(project_root, 'production_idis.db')
        # Don't show warning at module import time - this breaks the UI
        db_path_arg = default_db_path

    if not archive_path_arg:
        project_root = os.getcwd()
        default_archive_path = os.path.join(project_root, 'data', 'idis_archive')
        # Don't show warning at module import time - this breaks the UI
        archive_path_arg = default_archive_path

    return db_path_arg, archive_path_arg

# Initialize configuration when the script is loaded
DB_PATH, ARCHIVE_PATH = initialize_app_config()


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

def parse_boolean_search(search_term: str) -> Tuple[str, List[str]]:
    """Parse boolean search terms and convert to SQL WHERE clause."""
    if not search_term or not search_term.strip():
        return "", []
    
    search_term = search_term.strip()
    import re
    
    # Handle quoted strings first - strip quotes and treat as exact phrase
    if search_term.startswith('"') and search_term.endswith('"'):
        cleaned_term = search_term[1:-1].strip()
        return "full_text LIKE ? COLLATE NOCASE", [f"%{cleaned_term}%"]
    
    # Handle OR operator (case-insensitive)
    if re.search(r'\s+or\s+', search_term, re.IGNORECASE):
        terms = [term.strip() for term in re.split(r'\s+or\s+', search_term, flags=re.IGNORECASE) if term.strip()]
        if len(terms) > 1:
            conditions = []
            params = []
            for term in terms:
                # Handle quoted terms within OR
                if term.startswith('"') and term.endswith('"'):
                    term = term[1:-1].strip()
                conditions.append("full_text LIKE ? COLLATE NOCASE")
                params.append(f"%{term}%")
            return f"({' OR '.join(conditions)})", params
    
    # Handle AND operator (case-insensitive)
    elif re.search(r'\s+and\s+', search_term, re.IGNORECASE):
        terms = [term.strip() for term in re.split(r'\s+and\s+', search_term, flags=re.IGNORECASE) if term.strip()]
        if len(terms) > 1:
            conditions = []
            params = []
            for term in terms:
                # Handle quoted terms within AND
                if term.startswith('"') and term.endswith('"'):
                    term = term[1:-1].strip()
                conditions.append("full_text LIKE ? COLLATE NOCASE")
                params.append(f"%{term}%")
            return f"({' AND '.join(conditions)})", params
    
    # Handle NOT operator (case-insensitive)
    elif re.search(r'\s+not\s+', search_term, re.IGNORECASE):
        parts = [part.strip() for part in re.split(r'\s+not\s+', search_term, flags=re.IGNORECASE) if part.strip()]
        if len(parts) == 2:
            include_term = parts[0]
            exclude_term = parts[1]
            # Handle quoted terms in NOT
            if include_term.startswith('"') and include_term.endswith('"'):
                include_term = include_term[1:-1].strip()
            if exclude_term.startswith('"') and exclude_term.endswith('"'):
                exclude_term = exclude_term[1:-1].strip()
            return "(full_text LIKE ? COLLATE NOCASE AND full_text NOT LIKE ? COLLATE NOCASE)", [f"%{include_term}%", f"%{exclude_term}%"]
    
    # Default single term search - this should always work for simple terms
    return "full_text LIKE ? COLLATE NOCASE", [f"%{search_term}%"]

def build_search_query(search_term, doc_types, issuer_filter, tags_filter, after_date, before_date) -> Tuple[str, List[Any]]:
    """Build the SQL query and parameters for searching documents."""
    query_parts = ["SELECT document_id, file_name, document_type, upload_timestamp, issuer_source, filed_path, full_text, document_dates, tags_extracted, extracted_data FROM documents WHERE 1=1"]
    params = []

    if search_term:
        search_condition, search_params = parse_boolean_search(search_term)
        query_parts.append(f"AND {search_condition}")
        params.extend(search_params)
    if doc_types:
        placeholders = ",".join(["?" for _ in doc_types])
        query_parts.append(f"AND document_type IN ({placeholders})")
        params.extend(doc_types)
    if issuer_filter:
        query_parts.append("AND issuer_source LIKE ? COLLATE NOCASE")
        params.append(f"%{issuer_filter}%")
    if tags_filter:
        query_parts.append("AND tags_extracted LIKE ? COLLATE NOCASE")
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
def get_document_summary(document_id: str, extracted_data: str) -> str:
    """Get the AI-generated summary from extracted_data JSON or agent_outputs."""
    # First try to get summary from extracted_data JSON (cognitive agent)
    if extracted_data:
        try:
            data = json.loads(extracted_data)
            if data.get('content', {}).get('summary'):
                return data['content']['summary']
        except (json.JSONDecodeError, TypeError):
            pass
    
    # Fallback to agent_outputs table (summarizer agent)
    try:
        conn = get_database_connection()
        query = """
            SELECT output_data 
            FROM agent_outputs 
            WHERE document_id = ? AND output_type = 'per_document_summary'
            ORDER BY creation_timestamp DESC
            LIMIT 1
        """
        summary_df = pd.read_sql_query(query, conn, params=[document_id])
        if not summary_df.empty:
            return summary_df['output_data'].iloc[0]
    except Exception as e:
        st.warning(f"Could not fetch summary: {str(e)}")
    
    return "No summary available."

def get_extracted_data_field(extracted_data: Optional[str], field_path: str, fallback: str = "N/A") -> str:
    """Extract a specific field from the extracted_data JSON using dot notation."""
    if not extracted_data:
        return fallback
    
    try:
        data = json.loads(extracted_data)
        fields = field_path.split('.')
        current = data
        
        for field in fields:
            if isinstance(current, dict) and field in current:
                current = current[field]
            else:
                return fallback
        
        if current is None:
            return fallback
        
        # Handle different data types
        if isinstance(current, list):
            return ", ".join(str(item) for item in current) if current else fallback
        elif isinstance(current, dict):
            return json.dumps(current, indent=2)
        else:
            return str(current)
            
    except (json.JSONDecodeError, TypeError, KeyError):
        return fallback

def format_extracted_dates(extracted_data: Optional[str], document_dates: Optional[str]) -> str:
    """Format dates from extracted_data JSON or document_dates column."""
    # First try extracted_data
    if extracted_data:
        try:
            data = json.loads(extracted_data)
            key_dates = data.get('key_dates', {})
            if key_dates and any(v for v in key_dates.values() if v):
                formatted_dates = []
                for key, value in key_dates.items():
                    if value:
                        formatted_dates.append(f"{key.replace('_', ' ').title()}: {value}")
                return "\n".join(formatted_dates) if formatted_dates else "None"
        except (json.JSONDecodeError, TypeError):
            pass
    
    # Fallback to document_dates column
    return format_json_display(document_dates, 'None')

def get_enhanced_issuer(extracted_data: Optional[str], issuer_source: Optional[str]) -> str:
    """Get issuer information from extracted_data or fallback to issuer_source."""
    if extracted_data:
        try:
            data = json.loads(extracted_data)
            issuer = data.get('issuer', {})
            if issuer and issuer.get('name'):
                name = issuer.get('name', '')
                contact = issuer.get('contact_info', '')
                if contact:
                    return f"{name} ({contact})"
                return name
        except (json.JSONDecodeError, TypeError):
            pass
    
    return issuer_source or "N/A"

def get_enhanced_tags(extracted_data: Optional[str], tags_extracted: Optional[str]) -> str:
    """Get tags from extracted_data or fallback to tags_extracted."""
    if extracted_data:
        try:
            data = json.loads(extracted_data)
            suggested_tags = data.get('filing', {}).get('suggested_tags', [])
            if suggested_tags:
                return ", ".join(suggested_tags)
        except (json.JSONDecodeError, TypeError):
            pass
    
    return format_json_display(tags_extracted, 'None')

def get_enhanced_document_type(extracted_data: Optional[str], document_type: Optional[str]) -> str:
    """Get document type from CognitiveAgent data or fallback to legacy column."""
    if extracted_data:
        try:
            data = json.loads(extracted_data)
            cognitive_type = data.get('document_type')
            # Handle both string and dict types for document_type
            if isinstance(cognitive_type, dict):
                cognitive_type = cognitive_type.get('predicted_type') or cognitive_type.get('name')
            if cognitive_type and isinstance(cognitive_type, str) and cognitive_type.strip():
                return cognitive_type
        except (json.JSONDecodeError, TypeError):
            pass
    
    return document_type or "N/A"

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
def render_search_ui():
    st.title("🔍 QuantaIQ Document Search")
    st.markdown("*Intelligent Document Insight System - Cognitive Interface*")

    # Clear search results button with better explanation
    if st.button("🔄 Clear Search Results", help="Clear all previous search results and start fresh"):
        if 'results' in st.session_state:
            del st.session_state['results']
        if 'search_term' in st.session_state:
            del st.session_state['search_term']
        st.experimental_rerun()

    # Alternative approach - move everything to main area and use columns
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Search Parameters")
        
        # Use working text area method
        search_term = st.text_area("Search Document Content", height=100, placeholder="Enter search terms here (e.g., payslip, utility bill)...", help="Type your search terms and press Enter to search (the 'cmd+enter' popup is optional - regular Enter works fine)")
        
        # Boolean search help
        with st.expander("💡 Boolean Search Tips"):
            st.markdown("""
            **Boolean operators supported (case-insensitive):**
            - `payslip OR invoice` or `payslip or invoice` - Find documents with either term
            - `payslip AND medicaid` or `payslip and medicaid` - Find documents with both terms
            - `invoice NOT utility` or `invoice not utility` - Find documents with 'invoice' but not 'utility'
            - `payslip` - Simple single term search
            
            **Note:** Operators work in both uppercase and lowercase
            """)
        
        # Additional filters - expanded by default for better accessibility
        with st.expander("Advanced Filters", expanded=True):
            selected_types = st.multiselect("Document Type", options=get_document_types())
            issuer_filter = st.text_area("Issuer / Source", height=68, placeholder="Enter issuer or source organization...")
            tags_filter = st.text_area("Tags (comma-separated)", height=68, placeholder="Enter tags separated by commas...")
            
            col_date1, col_date2 = st.columns(2)
            with col_date1:
                after_date = st.date_input("Uploaded After", value=None)
            with col_date2:
                before_date = st.date_input("Uploaded Before", value=None)
            
            # Reset dates if they are equal to today (user likely didn't set them)
            from datetime import date
            today = date.today()
            if after_date == today:
                after_date = None
            if before_date == today:
                before_date = None
    
    with col2:
        st.subheader("Actions")
        run_search = st.button("🔍 Search Documents", type="primary")

    # --- File Upload Section ---
    from modules.shared.unified_uploader import render_unified_uploader
    
    render_unified_uploader(
        context="general",
        title="Upload New Documents",
        description="Upload new files to add them to the system.",
        button_text="Process Documents",
        file_types=['pdf', 'png', 'jpg', 'jpeg', 'txt', 'docx'],
        accept_multiple=True
    )

    # Initialize results if not present
    if 'results' not in st.session_state:
        st.session_state.results = None

    # Execute search when button is clicked
    if run_search:
        try:
            conn = get_database_connection()
            query, params = build_search_query(search_term, selected_types, issuer_filter, tags_filter, after_date, before_date)
            
            st.session_state.results = pd.read_sql_query(query, conn, params=params)
            # Store search term for highlighting
            st.session_state.search_term = search_term
            
            # Debug information (collapsed by default)
            with st.expander("Debug Information"):
                st.write(f"**Debug Info:**")
                st.write(f"Raw search term: '{search_term}'")
                st.write(f"Query: {query}")
                st.write(f"Parameters: {params}")
                st.write(f"**Results found:** {len(st.session_state.results)}")
        except Exception as e:
            st.error(f"Search error: {str(e)}")
            st.session_state.results = None

    if st.session_state.results is not None:
        results_df = st.session_state.results
        st.success(f"📊 Found {len(results_df)} matching document(s)")
        
        # Add confidence summary for multiple documents
        if len(results_df) > 1:
            documents_data = []
            for _, row in results_df.iterrows():
                documents_data.append({
                    'extracted_data': str(row['extracted_data']) if pd.notna(row['extracted_data']) and row['extracted_data'] != 'None' else None
                })
            render_processing_confidence_summary(documents_data)
            st.markdown("---")
        
        for index, row in results_df.iterrows():
            # Convert Series values to strings for proper handling
            filed_path = row['filed_path'] if pd.notna(row['filed_path']) else None
            file_name = str(row['file_name'])
            extracted_data = str(row['extracted_data']) if pd.notna(row['extracted_data']) and row['extracted_data'] != 'None' else None
            document_id = str(row['document_id'])
            
            # Get enhanced document type from CognitiveAgent data or fallback to legacy
            enhanced_document_type = get_enhanced_document_type(extracted_data, str(row['document_type']) if pd.notna(row['document_type']) else 'N/A')
            
            # Get processed date for display
            processed_date_str = "N/A"
            if pd.notna(row['upload_timestamp']):
                upload_dt = pd.to_datetime(row['upload_timestamp'])
                processed_date_str = upload_dt.strftime('%Y-%m-%d')
            
            # Get enhanced issuer
            enhanced_issuer = get_enhanced_issuer(extracted_data, str(row['issuer_source']) if pd.notna(row['issuer_source']) else None)
            
            # Create concise one-line summary for expander label
            display_filename = get_display_filename(filed_path, file_name)
            
            # Get confidence for badge display
            confidence, _, has_heuristic_override = extract_confidence_from_document(dict(extracted_data=extracted_data))
            confidence_badge = render_confidence_badge(confidence, has_heuristic_override)
            
            # Create a clean, scannable expander label with key information
            expander_label = f"📄 {display_filename} | {enhanced_document_type} | {enhanced_issuer} | {processed_date_str}"
            
            # Use expander for each document with the concise summary as label
            with st.expander(expander_label, expanded=False):
                # Show basic document details in header
                detail_col1, detail_col2 = st.columns(2)
                with detail_col1:
                    st.markdown(f"**Type:** `{enhanced_document_type}`")
                    st.markdown(f"**Source:** `{enhanced_issuer}`")
                with detail_col2:
                    st.markdown(f"**Processed:** `{processed_date_str}`")
                    enhanced_tags = get_enhanced_tags(extracted_data, str(row['tags_extracted']) if pd.notna(row['tags_extracted']) else None)
                    st.markdown(f"**Tags:** `{enhanced_tags}`")
                
                st.markdown("---")
                st.subheader("📋 AI Summary")
                summary = get_document_summary(document_id, extracted_data)
                st.info(summary)
                
                # Display CognitiveAgent structured data if available
                if extracted_data:
                    try:
                        data = json.loads(extracted_data)
                        
                        # Show confidence meter with enhanced UI
                        confidence, document_type, has_heuristic_override = extract_confidence_from_document(dict(extracted_data=extracted_data))
                        st.subheader("🎯 AI Classification Confidence")
                        render_confidence_meter(confidence, document_type, compact=False)
                        
                        # Show financial information if available
                        financials = data.get('financials', {})
                        if financials and any(v for v in financials.values() if v):
                            st.subheader("💰 Financial Details")
                            fin_col1, fin_col2 = st.columns(2)
                            with fin_col1:
                                if financials.get('gross_amount'):
                                    st.metric("Gross Amount", f"${financials['gross_amount']}")
                                if financials.get('net_amount'):
                                    st.metric("Net Amount", f"${financials['net_amount']}")
                            with fin_col2:
                                if financials.get('total_deductions'):
                                    st.metric("Total Deductions", f"${financials['total_deductions']}")
                                if financials.get('total_amount'):
                                    st.metric("Total Amount", f"${financials['total_amount']}")
                        
                        # Show entity information if available
                        entity = data.get('entity', {})
                        if entity and any(v for v in entity.values() if v):
                            st.subheader("👤 Entity Information")
                            if entity.get('name'):
                                st.text(f"Name: {entity['name']}")
                            if entity.get('role'):
                                st.text(f"Role: {entity['role']}")
                            if entity.get('id'):
                                st.text(f"ID: {entity['id']}")
                                
                    except (json.JSONDecodeError, TypeError):
                        pass
                
                st.subheader("📅 Extracted Dates")
                formatted_dates = format_extracted_dates(extracted_data, str(row['document_dates']) if pd.notna(row['document_dates']) else None)
                st.code(formatted_dates)
                
                st.subheader("📝 Extracted Text")
                full_text = str(row['full_text']) if pd.notna(row['full_text']) else ""
                
                # Get the search term for highlighting
                search_term = st.session_state.get('search_term', '')
                
                if search_term and search_term.strip():
                    # Extract the actual search term for highlighting (handle quoted strings)
                    highlight_term = search_term.strip()
                    if highlight_term.startswith('"') and highlight_term.endswith('"'):
                        highlight_term = highlight_term[1:-1].strip()
                    
                    # For OR searches, highlight all terms
                    if re.search(r'\s+or\s+', highlight_term, re.IGNORECASE):
                        terms = [term.strip() for term in re.split(r'\s+or\s+', highlight_term, flags=re.IGNORECASE) if term.strip()]
                        highlighted_text = full_text
                        for term in terms:
                            # Handle quoted terms within OR
                            if term.startswith('"') and term.endswith('"'):
                                term = term[1:-1].strip()
                            replacement_style = r"<span style='background-color: #FFFF00; color: black;'>\1</span>"
                            highlighted_text = re.sub(
                                f'({re.escape(term)})', 
                                replacement_style, 
                                highlighted_text, 
                                flags=re.IGNORECASE
                            )
                    else:
                        # Single term highlighting
                        replacement_style = r"<span style='background-color: #FFFF00; color: black;'>\1</span>"
                        highlighted_text = re.sub(
                            f'({re.escape(highlight_term)})', 
                            replacement_style, 
                            full_text, 
                            flags=re.IGNORECASE
                        )
                    
                    # Convert newlines to HTML <br> tags for proper rendering in markdown
                    html_text_with_breaks = highlighted_text.replace('\n', '<br>')
                    
                    # Use a simpler scrollable container
                    st.markdown(
                        f"<div style='height: 250px; overflow-y: scroll; border: 1px solid #444; padding: 5px; color: black; background-color: #f9f9f9;'>{html_text_with_breaks}</div>", 
                        unsafe_allow_html=True
                    )
                else:
                    # Fallback to a normal text area if no search term
                    st.text_area("Full Text", value=full_text, height=250, key=f"text_{document_id}_{index}")

                if filed_path:
                    st.subheader("📁 File Location")
                    st.code(filed_path, language=None)
                    
                    # Document Viewer Component
                    st.subheader("📄 Original Document")
                    
                    # Check if this is a test document placeholder
                    if filed_path.startswith("TEST_DOCUMENT_NO_ARCHIVE/"):
                        st.info("ℹ️ This is a test document added directly to the database. No archived file is available for display.")
                    elif os.path.exists(filed_path):
                        file_extension = os.path.splitext(filed_path)[1].lower()
                        
                        if file_extension == '.pdf':
                            # For PDF files, show a download button
                            with open(filed_path, 'rb') as file:
                                pdf_bytes = file.read()
                            st.download_button(
                                label="📥 Download PDF",
                                data=pdf_bytes,
                                file_name=os.path.basename(filed_path),
                                mime="application/pdf"
                            )
                            
                        elif file_extension in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
                            # For image files, display directly
                            st.image(filed_path, caption=f"Original Document: {os.path.basename(filed_path)}")
                            
                        elif file_extension in ['.txt', '.md']:
                            # For text files, show content
                            with open(filed_path, 'r', encoding='utf-8', errors='ignore') as file:
                                text_content = file.read()
                            st.text_area("File Content", value=text_content, height=200, disabled=True)
                            
                        else:
                            # For other file types, provide download option
                            with open(filed_path, 'rb') as file:
                                file_bytes = file.read()
                            st.download_button(
                                label=f"📥 Download {file_extension.upper()} File",
                                data=file_bytes,
                                file_name=os.path.basename(filed_path),
                                mime="application/octet-stream"
                            )
                    else:
                        st.error("⚠️ Original document file not found at the specified location.")
    else:
        st.info("👆 Use the filters in the sidebar and click Search to find documents.")