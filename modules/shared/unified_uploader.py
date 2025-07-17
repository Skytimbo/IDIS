"""
Unified Document Uploader Component

This module provides a consistent file upload interface that can be used
across different modules in the IDIS application. It supports context-aware
processing while maintaining consistent behavior and user experience.
"""

import streamlit as st
import os
import logging
from typing import List, Optional
from context_store import ContextStore
from unified_ingestion_agent import UnifiedIngestionAgent
from tagger_agent import TaggerAgent


def render_unified_uploader(
    context: str = "general",
    title: str = "Upload Documents",
    description: str = "Upload new files to add them to the system.",
    button_text: str = "Process Documents",
    file_types: List[str] = None,
    accept_multiple: bool = True
) -> None:
    """
    Renders a unified file uploader component with consistent behavior.
    
    Args:
        context: Processing context ('medicaid', 'general', etc.)
        title: Display title for the upload section
        description: Help text for the uploader
        button_text: Text for the process button
        file_types: Allowed file extensions (defaults to all supported types)
        accept_multiple: Whether to accept multiple files
    """
    
    # Set default file types if not provided
    if file_types is None:
        file_types = ['pdf', 'png', 'jpg', 'jpeg', 'txt', 'docx']
    
    # Render the upload interface - EXPANDED BY DEFAULT
    st.markdown("---")
    st.subheader(f"➕ {title}")
    uploaded_files = st.file_uploader(
        description,
        accept_multiple_files=accept_multiple,
        type=file_types
    )
    
    if uploaded_files:
        # Show uploaded files
        if accept_multiple:
            st.success(f"{len(uploaded_files)} file(s) uploaded successfully. Ready for processing.")
            for uploaded_file in uploaded_files:
                st.write(f"- {uploaded_file.name}")
        else:
            st.success(f"File '{uploaded_files.name}' uploaded successfully. Ready for processing.")
        
        # Process button
        if st.button(f"✨ {button_text}", type="primary"):
            _process_uploaded_files(uploaded_files, context, accept_multiple)


def _process_uploaded_files(uploaded_files, context: str, accept_multiple: bool) -> None:
    """
    Internal function to process uploaded files through the unified pipeline.
    
    Args:
        uploaded_files: Streamlit uploaded file objects
        context: Processing context for business logic
        accept_multiple: Whether multiple files were uploaded
    """
    
    logging.info(f"--- UNIFIED UPLOADER PROCESSING: {context.upper()} CONTEXT ---")
    
    # Initialize components
    context_store = ContextStore("production_idis.db")
    temp_folder = os.path.join("data", f"temp_{context}_upload")
    holding_folder = os.path.join("data", "holding")
    
    # Create necessary directories
    os.makedirs(temp_folder, exist_ok=True)
    os.makedirs(holding_folder, exist_ok=True)
    
    # Initialize the unified ingestion agent
    ingestion_agent = UnifiedIngestionAgent(
        context_store=context_store,
        watch_folder=temp_folder,
        holding_folder=holding_folder
    )
    
    # Initialize the tagger agent for archiving
    tagger_agent = TaggerAgent(
        context_store=context_store,
        base_filed_folder=os.path.join("data", "archive")
    )
    
    with st.spinner("Processing documents through AI pipeline..."):
        processed_count = 0
        failed_count = 0
        
        # Handle single file vs multiple files
        files_to_process = uploaded_files if accept_multiple else [uploaded_files]
        
        # Process each uploaded file directly through the AI pipeline
        for uploaded_file in files_to_process:
            try:
                # Save file temporarily
                temp_path = os.path.join(temp_folder, uploaded_file.name)
                logging.info(f"Processing '{uploaded_file.name}' through AI pipeline (context: {context})")
                
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getvalue())
                
                # Context-aware processing parameters
                entity_id, session_id = _get_context_parameters(context)
                
                # Process directly through UnifiedIngestionAgent
                success = ingestion_agent._process_single_file(
                    temp_path, 
                    uploaded_file.name, 
                    entity_id=entity_id, 
                    session_id=session_id
                )
                
                if success:
                    st.write(f"✅ Successfully processed {uploaded_file.name}")
                    processed_count += 1
                    
                    # Complete the archiving pipeline by running TaggerAgent
                    archiving_success = False
                    try:
                        # Process documents that are ready for tagging and filing
                        filed_count, failed_count = tagger_agent.process_documents_for_tagging_and_filing(
                            status_to_process="processing_complete",
                            new_status_after_filing="filed_and_tagged"
                        )
                        
                        if filed_count > 0:
                            st.write(f"📁 Successfully archived {filed_count} document(s)")
                            archiving_success = True
                        elif failed_count > 0:
                            st.write(f"⚠️  Document processed but archiving failed for {failed_count} document(s)")
                    
                    except Exception as e:
                        logging.error(f"Error during archiving: {e}")
                        st.write(f"⚠️  Document processed but archiving failed: {str(e)}")

                    # Store processed document info in session state for assignment
                    if context == "medicaid":
                        _store_processed_document(uploaded_file.name, context_store)
                        # Create case-document association for Medicaid uploads
                        _create_case_document_association(uploaded_file.name, context_store)
                    
                    # Context-specific success actions
                    _handle_success_context(context, uploaded_file.name)
                    
                    # Clean up temporary file ONLY after successful archiving
                    if archiving_success and os.path.exists(temp_path):
                        os.remove(temp_path)
                        logging.info(f"Cleaned up temp file: {temp_path}")
                    elif os.path.exists(temp_path):
                        logging.warning(f"Keeping temp file due to archiving failure: {temp_path}")
                else:
                    st.write(f"❌ Failed to process {uploaded_file.name}")
                    failed_count += 1
                    
                    # Clean up temporary file on processing failure
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    
            except Exception as e:
                st.write(f"❌ Error processing {uploaded_file.name}: {str(e)}")
                failed_count += 1
                logging.error(f"Error processing {uploaded_file.name}: {e}")
        
        # Show final results
        _display_processing_results(processed_count, failed_count, context)
    
    # Clean up temp directory
    try:
        if os.path.exists(temp_folder):
            os.rmdir(temp_folder)
    except OSError:
        pass  # Directory not empty, leave it for manual cleanup


def _get_context_parameters(context: str) -> tuple:
    """
    Get context-specific entity_id and session_id parameters.
    
    Args:
        context: Processing context ('medicaid', 'general', etc.)
    
    Returns:
        Tuple of (entity_id, session_id)
    """
    
    if context == "medicaid":
        # Medicaid Navigator uses active case's entity ID
        entity_id = st.session_state.get('current_entity_id', 1)
        session_id = 1  # Default session ID
        logging.info(f"Medicaid context: Using entity_id={entity_id}, session_id={session_id}")
        return (entity_id, session_id)
    elif context == "general":
        # General document search uses default IDs
        return (1, 1)
    else:
        # Default fallback
        return (1, 1)


def _handle_success_context(context: str, filename: str) -> None:
    """
    Handle context-specific actions after successful processing.
    
    Args:
        context: Processing context
        filename: Name of the processed file
    """
    
    if context == "medicaid":
        # Future: Update Medicaid checklist, trigger compliance checks
        logging.info(f"Medicaid document processed: {filename}")
    elif context == "general":
        # Future: Update general document index, trigger search indexing
        logging.info(f"General document processed: {filename}")

def _create_case_document_association(filename: str, context_store: ContextStore) -> None:
    """
    Create a case-document association for Medicaid uploads.
    
    Args:
        filename: Name of the processed file
        context_store: Database connection
    """
    try:
        # Get the current case and entity IDs from session state
        case_id = st.session_state.get('current_case_id')
        entity_id = st.session_state.get('current_entity_id')
        
        if not case_id or not entity_id:
            logging.warning(f"No current case or entity ID found for document {filename}")
            return
        
        # Get the document ID for the uploaded file
        cursor = context_store.conn.cursor()
        cursor.execute("""
            SELECT id FROM documents 
            WHERE file_name = ? AND entity_id = ?
            ORDER BY upload_timestamp DESC 
            LIMIT 1
        """, (filename, entity_id))
        
        result = cursor.fetchone()
        if not result:
            logging.error(f"Could not find document ID for {filename} with entity {entity_id}")
            return
        
        document_id = result[0]
        
        # Check if association already exists
        cursor.execute("""
            SELECT id FROM case_documents 
            WHERE case_id = ? AND document_id = ?
        """, (case_id, document_id))
        
        if cursor.fetchone():
            logging.info(f"Case-document association already exists for {filename}")
            return
        
        # Create the case-document association
        cursor.execute("""
            INSERT INTO case_documents (case_id, entity_id, document_id, status, user_id, created_at, updated_at)
            VALUES (?, ?, ?, 'Pending', ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (case_id, entity_id, document_id, st.session_state.get('current_user_id', 'user_a')))
        
        context_store.conn.commit()
        logging.info(f"Created case-document association: Case={case_id}, Document={document_id} ({filename})")
        
    except Exception as e:
        logging.error(f"Error creating case-document association for {filename}: {e}")

def _store_processed_document(filename: str, context_store: ContextStore) -> None:
    """
    Store processed document information in session state for assignment.
    
    Args:
        filename: Name of the processed file
        context_store: Database connection to query document information
    """
    try:
        # Query for the most recently added document with this filename
        cursor = context_store.conn.cursor()
        cursor.execute("""
            SELECT id, file_name, document_type, extracted_data
            FROM documents 
            WHERE file_name = ? 
            ORDER BY upload_timestamp DESC 
            LIMIT 1
        """, (filename,))
        
        result = cursor.fetchone()
        
        if result:
            document_id, file_name, document_type, extracted_data = result
            
            # Initialize session state for processed documents if it doesn't exist
            if 'processed_documents' not in st.session_state:
                st.session_state.processed_documents = []
            
            # Check for duplicate entries before adding
            existing_filenames = [doc['filename'] for doc in st.session_state.processed_documents]
            if file_name not in existing_filenames:
                # Add to processed documents list
                document_info = {
                    'document_id': document_id,  # Using the 'id' column instead of 'document_id'
                    'filename': file_name,
                    'document_type': document_type,
                    'extracted_data': extracted_data
                }
                
                st.session_state.processed_documents.append(document_info)
            logging.info(f"Stored processed document: {filename} (ID: {document_id})")
        
    except Exception as e:
        logging.error(f"Error storing processed document {filename}: {e}")

def _display_processing_results(processed_count: int, failed_count: int, context: str) -> None:
    """
    Display context-appropriate processing results.
    
    Args:
        processed_count: Number of successfully processed files
        failed_count: Number of failed files
        context: Processing context
    """
    
    if processed_count > 0:
        if context == "medicaid":
            st.success(f"Successfully processed {processed_count} Medicaid documents! Your documents are now searchable and ready for compliance checking.")
        else:
            st.success(f"Successfully processed {processed_count} documents! Your documents are now searchable by content.")
            
        if failed_count > 0:
            st.warning(f"Failed to process {failed_count} documents. Please check the logs.")
        
        # Show celebration for successful processing
        st.balloons()
    else:
        st.error("No documents were processed successfully. Please try again or check the file formats.")