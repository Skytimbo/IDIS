#!/usr/bin/env python3
"""
Demo script for testing the Smart Cover Sheet Renderer functionality.

This script demonstrates how to use the SmartCoverSheetRenderer to create a PDF
cover sheet from documents processed by the IDIS system.
"""

import os
import argparse
import logging
import sqlite3
from typing import List, Optional

from context_store import ContextStore
from cover_sheet import SmartCoverSheetRenderer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("IDIS_CoverSheet_Demo")

def find_session_with_documents(db_path: str) -> Optional[str]:
    """
    Find a session in the database that has documents associated with it.
    
    Args:
        db_path: Path to the SQLite database
        
    Returns:
        Session ID if found, None otherwise
    """
    try:
        # Connect directly to the database to find a suitable session
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Find sessions that have documents
        cursor.execute("""
            SELECT DISTINCT s.session_id
            FROM sessions s
            JOIN documents d ON s.session_id = d.session_id
            LIMIT 1
        """)
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return result[0]
        return None
    except Exception as e:
        logger.warning(f"Error finding session with documents: {e}")
        return None

def create_demo_document(context_store: ContextStore, session_id: str) -> str:
    """
    Create a demo document if no documents exist.
    
    Args:
        context_store: ContextStore instance
        session_id: Session ID to associate the document with
        
    Returns:
        Document ID of the created document
    """
    import json
    
    # Create a demo document - make sure to follow the context_store's API
    doc_id = context_store.add_document(
        patient_id=None,
        session_id=session_id,
        file_name="demo_document.txt",
        original_file_type="txt",
        ingestion_status="ingestion_successful",
        extracted_text="This is a demo document for testing the cover sheet functionality.",
        document_type="Demo Document",
        classification_confidence="High",
        document_dates=json.dumps({"creation_date": "2025-05-22"}),
        issuer_source="IDIS Demo System",
        recipient="IDIS User",
        tags_extracted=json.dumps(["demo", "test", "cover_sheet"]),
        processing_status="classified",
        user_id="cover_sheet_demo_user"
    )
    
    # Add a summary for the document
    # Use the add_agent_output method from the context store
    agent_output_id = context_store.add_agent_output(
        document_id=doc_id,
        agent_id="summarizer_agent_v1.0",
        output_type="per_document_summary",
        output_data="This is a demonstration document created to showcase the Smart Cover Sheet Renderer's capabilities in generating professional PDF reports.",
        confidence=0.95,
        user_id="cover_sheet_demo_user"
    )
    
    logger.info(f"Created agent output with ID: {agent_output_id}")
    return doc_id

def main():
    """
    Demo function to generate a cover sheet for processed documents.
    """
    parser = argparse.ArgumentParser(description="Generate a cover sheet PDF for IDIS processed documents")
    parser.add_argument("--db-path", default="./idis_demo.db", help="Path to the SQLite database file")
    parser.add_argument("--session-id", help="Session ID to generate cover sheet for (uses the most recent if not specified)")
    parser.add_argument("--output-pdf", default="./idis_cover_sheet.pdf", help="Path to save the output PDF")
    parser.add_argument("--create-demo", action="store_true", help="Create a demo document if none exist")
    
    args = parser.parse_args()
    
    # Initialize the Context Store
    context_store = ContextStore(args.db_path)
    logger.info(f"Initialized Context Store with database: {args.db_path}")
    
    # Get the session ID (use the provided one or find the most recent)
    session_id = args.session_id
    
    if not session_id:
        # Try to find a session with documents
        session_id = find_session_with_documents(args.db_path)
        
        if session_id:
            logger.info(f"Found session with documents, ID: {session_id}")
        else:
            # Create a new session if none found
            logger.info("No session with documents found, creating a new session")
            session_id = context_store.create_session(
                user_id="cover_sheet_demo_user",
                session_metadata={"purpose": "cover_sheet_demo", "batch_summary": "Demo batch for IDIS Cover Sheet generation."}
            )
    
    if not session_id:
        logger.error("Failed to get or create a session")
        return
    
    logger.info(f"Using session ID: {session_id}")
    
    # Get documents from this session
    documents = context_store.get_documents_for_session(session_id)
    
    # Create a demo document if requested and no documents exist
    if not documents and args.create_demo:
        logger.info("No documents found, creating a demo document")
        doc_id = create_demo_document(context_store, session_id)
        documents = context_store.get_documents_for_session(session_id)
        logger.info(f"Created demo document with ID: {doc_id}")
    
    if not documents:
        logger.error(f"No documents found for session ID: {session_id}")
        return
    
    document_ids = [doc["document_id"] for doc in documents]
    logger.info(f"Found {len(document_ids)} documents for session ID: {session_id}")
    
    # Initialize the Smart Cover Sheet Renderer
    renderer = SmartCoverSheetRenderer(context_store)
    
    # Generate the cover sheet
    output_dir = os.path.dirname(args.output_pdf)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    success = renderer.generate_cover_sheet(
        document_ids=document_ids,
        output_pdf_filename=args.output_pdf,
        session_id=session_id
    )
    
    if success:
        logger.info(f"Successfully generated cover sheet: {args.output_pdf}")
        logger.info(f"You can view the PDF at: {os.path.abspath(args.output_pdf)}")
    else:
        logger.error("Failed to generate cover sheet")

if __name__ == "__main__":
    main()