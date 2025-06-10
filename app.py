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

# Database configuration
DB_PATH = "demo_idis.db"

# Page configuration
st.set_page_config(
    page_title="QuantaIQ Document Search",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

def get_database_connection():
    """Get a connection to the SQLite database."""
    if not os.path.exists(DB_PATH):
        st.error(f"Database file not found: {DB_PATH}")
        st.stop()
    return sqlite3.connect(DB_PATH)

def get_document_types() -> List[str]:
    """Get distinct document types from the database."""
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT document_type FROM documents WHERE document_type IS NOT NULL ORDER BY document_type")
        types = [row[0] for row in cursor.fetchall()]
        conn.close()
        return types
    except Exception as e:
        st.error(f"Error fetching document types: {str(e)}")
        return []

def build_search_query(
    search_term: str,
    doc_types: List[str],
    issuer_filter: str,
    tags_filter: str,
    after_date: Any,
    before_date: Any
) -> Tuple[str, List[Any]]:
    """Build the SQL query and parameters for searching documents."""
    
    # Base query
    query = """
    SELECT 
        d.document_id,
        d.file_name,
        d.document_type,
        d.upload_timestamp,
        d.issuer_source,
        d.filed_path,
        d.extracted_text,
        d.document_dates,
        d.tags_extracted
    FROM documents d
    WHERE 1=1
    """
    
    params = []
    
    # Full-text search on extracted_text
    if search_term.strip():
        query += " AND d.extracted_text LIKE ?"
        params.append(f"%{search_term.strip()}%")
    
    # Document type filter
    if doc_types:
        placeholders = ",".join(["?" for _ in doc_types])
        query += f" AND d.document_type IN ({placeholders})"
        params.extend(doc_types)
    
    # Issuer/Source filter
    if issuer_filter.strip():
        query += " AND d.issuer_source LIKE ?"
        params.append(f"%{issuer_filter.strip()}%")
    
    # Tags filter
    if tags_filter.strip():
        query += " AND d.tags_extracted LIKE ?"
        params.append(f"%{tags_filter.strip()}%")
    
    # Date range filters
    if after_date:
        if hasattr(after_date, 'strftime'):
            query += " AND date(d.upload_timestamp) >= ?"
            params.append(after_date.strftime("%Y-%m-%d"))
    
    if before_date:
        if hasattr(before_date, 'strftime'):
            query += " AND date(d.upload_timestamp) <= ?"
            params.append(before_date.strftime("%Y-%m-%d"))
    
    # Order by most recent first
    query += " ORDER BY d.upload_timestamp DESC"
    
    return query, params

def get_document_summary(document_id: str) -> Optional[str]:
    """Get the AI-generated summary for a document from agent_outputs."""
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT output_data 
            FROM outputs 
            WHERE document_id = ? AND output_type = 'per_document_summary'
            ORDER BY creation_timestamp DESC
            LIMIT 1
        """, (document_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else None
    except Exception as e:
        st.error(f"Error fetching summary: {str(e)}")
        return None

def format_document_dates(dates_json: Optional[str]) -> str:
    """Format document dates from JSON string."""
    if not dates_json:
        return "No dates available"
    
    try:
        dates = json.loads(dates_json)
        if isinstance(dates, dict):
            formatted_dates = []
            for key, value in dates.items():
                formatted_dates.append(f"{key.replace('_', ' ').title()}: {value}")
            return ", ".join(formatted_dates)
        return str(dates)
    except (json.JSONDecodeError, TypeError):
        return dates_json or "No dates available"

def format_tags(tags_json: Optional[str]) -> str:
    """Format tags from JSON string."""
    if not tags_json:
        return "No tags"
    
    try:
        tags = json.loads(tags_json)
        if isinstance(tags, list):
            return ", ".join(tags)
        return str(tags)
    except (json.JSONDecodeError, TypeError):
        return tags_json or "No tags"

def get_filename_from_path(filed_path: Optional[str], original_name: str) -> str:
    """Extract descriptive filename from filed_path or use original name."""
    if filed_path and os.path.basename(filed_path):
        return os.path.basename(filed_path)
    return original_name

def main():
    """Main Streamlit application."""
    
    # Title
    st.title("🔍 QuantaIQ Document Search")
    st.markdown("*Intelligent Document Insight System - Cognitive Interface*")
    
    # Sidebar filters
    st.sidebar.header("🔧 Search Filters")
    
    # Document type filter
    available_types = get_document_types()
    selected_types = st.sidebar.multiselect(
        "Document Type",
        options=available_types,
        help="Filter by document classification"
    )
    
    # Issuer/Source filter
    issuer_filter = st.sidebar.text_input(
        "Issuer/Source",
        placeholder="e.g., Medical Center, Company Name",
        help="Filter by document issuer or source"
    )
    
    # Tags filter
    tags_filter = st.sidebar.text_input(
        "Tags",
        placeholder="e.g., urgent, confidential",
        help="Filter by document tags"
    )
    
    # Date range filters
    st.sidebar.subheader("📅 Date Range")
    after_date = st.sidebar.date_input(
        "After Date",
        value=None,
        help="Show documents uploaded after this date"
    )
    
    before_date = st.sidebar.date_input(
        "Before Date",
        value=None,
        help="Show documents uploaded before this date"
    )
    
    # Main search interface
    st.header("🔍 Search Documents")
    
    # Search input
    search_term = st.text_input(
        "Enter search terms",
        placeholder="Search document content...",
        help="Search within document text content"
    )
    
    # Search button
    search_clicked = st.button("🔍 Search", type="primary", use_container_width=True)
    
    # Perform search when button is clicked or any filter changes
    if search_clicked or search_term or selected_types or issuer_filter or tags_filter or after_date or before_date:
        
        # Build and execute query
        query, params = build_search_query(
            search_term, selected_types, issuer_filter, 
            tags_filter, after_date, before_date
        )
        
        try:
            conn = get_database_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)
            results = cursor.fetchall()
            conn.close()
            
            # Display results
            if not results:
                st.info("📭 No matching documents found.")
                st.markdown("Try adjusting your search criteria or filters.")
            else:
                st.success(f"📊 Found {len(results)} matching document(s)")
                
                # Display each result
                for row in results:
                    (document_id, file_name, document_type, upload_timestamp, 
                     issuer_source, filed_path, extracted_text, document_dates, tags_extracted) = row
                    
                    # Create container for each document
                    with st.container():
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            # Document header
                            display_filename = get_filename_from_path(filed_path, file_name)
                            st.subheader(f"📄 {display_filename}")
                            
                            # Document metadata
                            col_meta1, col_meta2, col_meta3 = st.columns(3)
                            
                            with col_meta1:
                                st.write(f"**Type:** {document_type or 'Unknown'}")
                                
                            with col_meta2:
                                st.write(f"**Uploaded:** {upload_timestamp}")
                                
                            with col_meta3:
                                st.write(f"**Source:** {issuer_source or 'Unknown'}")
                        
                        with col2:
                            # Document dates and tags
                            formatted_dates = format_document_dates(document_dates)
                            st.write(f"**Dates:** {formatted_dates}")
                            
                            formatted_tags = format_tags(tags_extracted)
                            st.write(f"**Tags:** {formatted_tags}")
                        
                        # View Details expander
                        with st.expander(f"🔍 View Details - {display_filename}"):
                            
                            # Get and display summary
                            summary = get_document_summary(document_id)
                            if summary:
                                st.subheader("📋 AI Summary")
                                st.write(summary)
                                st.divider()
                            
                            # Display extracted text
                            st.subheader("📝 Extracted Text")
                            if extracted_text:
                                st.text_area(
                                    "Document Content",
                                    value=extracted_text,
                                    height=200,
                                    key=f"text_{document_id}",
                                    disabled=True
                                )
                            else:
                                st.write("*No extracted text available*")
                            
                            # File path information
                            if filed_path:
                                st.subheader("📁 File Location")
                                st.code(filed_path)
                                if os.path.exists(filed_path):
                                    st.success("✅ File exists at this location")
                                else:
                                    st.warning("⚠️ File not found at this location")
                        
                        st.divider()
                        
        except Exception as e:
            st.error(f"Error executing search: {str(e)}")
    
    else:
        # Initial state - show instructions
        st.info("👆 Enter search terms or use the filters in the sidebar to search documents.")
        
        # Show database statistics
        try:
            conn = get_database_connection()
            cursor = conn.cursor()
            
            # Total documents
            cursor.execute("SELECT COUNT(*) FROM documents")
            total_docs = cursor.fetchone()[0]
            
            # Documents by type
            cursor.execute("SELECT document_type, COUNT(*) FROM documents GROUP BY document_type ORDER BY COUNT(*) DESC")
            type_counts = cursor.fetchall()
            
            conn.close()
            
            # Display stats
            st.subheader("📊 Database Statistics")
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Total Documents", total_docs)
            
            with col2:
                if type_counts:
                    st.write("**Documents by Type:**")
                    for doc_type, count in type_counts:
                        st.write(f"• {doc_type or 'Unclassified'}: {count}")
                        
        except Exception as e:
            st.error(f"Error loading database statistics: {str(e)}")

if __name__ == "__main__":
    main()