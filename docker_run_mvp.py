#!/usr/bin/env python3
"""
Docker-optimized MVP Pipeline Runner for IDIS

This script orchestrates the complete IDIS pipeline in a Docker environment,
processing documents from the watch folder through the entire pipeline:
ingestion, classification, summarization, tagging, and cover sheet generation.
"""

import os
import sys
import shutil
import logging
import json
import datetime
import argparse
from typing import Dict, List, Any, Optional

from context_store import ContextStore
from permissions import PermissionsManager
from ingestion_agent import IngestionAgent
from classifier_agent import ClassifierAgent
from summarizer_agent import SummarizerAgent
from tagger_agent import TaggerAgent
from cover_sheet import SmartCoverSheetRenderer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Default Docker environment paths
DEFAULT_DB_PATH = "/app/db/idis.db"
DEFAULT_WATCH_FOLDER = "/app/watch_folder"
DEFAULT_HOLDING_FOLDER = "/app/holding_folder"
DEFAULT_ARCHIVE_FOLDER = "/app/archive_folder"
DEFAULT_COVER_SHEETS_FOLDER = "/app/cover_sheets"

# Default configurations
PERMISSIONS_RULES_FILE = os.path.join(os.path.dirname(__file__), "permissions_rules.json")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Classification rules for the Classifier Agent
CLASSIFICATION_RULES = {
    "Invoice": ["invoice #", "total due", "bill to", "payment", "amount"],
    "Medical Record": ["patient name:", "diagnosis", "chief complaint", "medical record", "treatment"],
    "Letter": ["dear sir", "sincerely", "yours truly", "regards", "recipient"],
    "Report": ["executive summary", "findings", "analysis section", "conclusion", "recommendations"],
    "Credit Card Statement": ["visa signature", "new balance", "minimum payment due", "account summary", "closing date", "reward points"]
}

# Tag definitions for the Tagger Agent
TAG_DEFINITIONS = {
    "urgent": ["urgent", "immediate action required", "priority!", "asap"],
    "confidential": ["confidential", "private and confidential", "sensitive"],
    "financial": ["payment", "invoice", "total due", "amount", "cost"],
    "medical": ["patient", "diagnosis", "treatment", "medical", "doctor"]
}

def setup_environment(base_dir: str, db_path: str) -> Dict[str, str]:
    """
    Set up the directory structure for the MVP pipeline in Docker.
    
    Args:
        base_dir: Base directory for all pipeline components
        db_path: Path to the database file
        
    Returns:
        Dictionary containing paths for all required directories
    """
    # Ensure base directory exists
    os.makedirs(base_dir, exist_ok=True)
    
    # Create subdirectories
    watch_folder = os.path.join(base_dir, "watch_folder")
    holding_folder = os.path.join(base_dir, "holding_folder")
    archive_folder = os.path.join(base_dir, "archive_folder")
    pdf_output_dir = os.path.join(base_dir, "cover_sheets")
    
    # Ensure directories exist
    for folder in [watch_folder, holding_folder, archive_folder, pdf_output_dir]:
        os.makedirs(folder, exist_ok=True)
    
    # Ensure database directory exists
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    
    return {
        'base_dir': base_dir,
        'watch_folder': watch_folder,
        'holding_folder': holding_folder,
        'archive_folder': archive_folder,
        'pdf_output_dir': pdf_output_dir,
        'db_path': db_path
    }

def run_pipeline(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the complete IDIS pipeline in Docker environment.
    
    Args:
        config: Dictionary containing configuration paths
        
    Returns:
        Dictionary with pipeline results and statistics
    """
    logger = logging.getLogger("IDIS_Docker_Pipeline")
    logger.info("Starting IDIS Pipeline in Docker Environment")
    
    # Initialize the context store
    context_store = ContextStore(db_path=config['db_path'])
    logger.info(f"Initialized Context Store with database: {config['db_path']}")
    
    # Initialize permissions manager
    permissions_manager = PermissionsManager(rules_file_path=PERMISSIONS_RULES_FILE)
    logger.info("Initialized Permissions Manager")
    
    # Define default user and create patient record
    default_user = "docker_pipeline_user"
    mock_patient_id = context_store.add_patient({
        "patient_name": "Docker Test Patient",
        "date_of_birth": "1980-01-01",
        "medical_record_number": "MRN-DOCKER-123"
    })
    
    # Create session linked to the patient
    session_id = context_store.create_session(
        user_id=default_user,
        session_metadata={"description": "Docker Pipeline Batch", "patient_id": mock_patient_id}
    )
    logger.info(f"Created session with ID: {session_id}")
    
    # Initialize agents
    ingestion_agent = IngestionAgent(
        context_store=context_store,
        watch_folder=config['watch_folder'],
        holding_folder=config['holding_folder']
    )
    logger.info("Initialized Ingestion Agent")
    
    classifier_agent = ClassifierAgent(
        context_store=context_store,
        classification_rules=CLASSIFICATION_RULES
    )
    logger.info("Initialized Classifier Agent")
    
    summarizer_agent = SummarizerAgent(
        context_store=context_store,
        openai_api_key=OPENAI_API_KEY
    )
    logger.info("Initialized Summarizer Agent")
    
    tagger_agent = TaggerAgent(
        context_store=context_store,
        base_filed_folder=config['archive_folder'],
        tag_definitions=TAG_DEFINITIONS
    )
    logger.info("Initialized Tagger Agent")
    
    cover_sheet_renderer = SmartCoverSheetRenderer(context_store=context_store)
    logger.info("Initialized Cover Sheet Renderer")
    
    # Process documents through the pipeline
    
    # Step 1: Ingestion
    logger.info("Starting document ingestion...")
    ingestion_results = ingestion_agent.process_pending_documents(
        session_id=session_id,
        patient_id=mock_patient_id,
        user_id=default_user
    )
    logger.info(f"Ingested {ingestion_results} documents")
    
    # Step 2: Classification
    logger.info("Starting document classification...")
    classification_results = classifier_agent.process_documents_for_classification(
        user_id=default_user,
        status_to_classify="ingested",
        new_status_after_classification="classified"
    )
    logger.info(f"Classification complete: {classification_results[0]} succeeded, {classification_results[1]} failed")
    
    # Step 3: Summarization
    logger.info("Starting document summarization...")
    if OPENAI_API_KEY:
        logger.info("Using OpenAI for summarization")
    else:
        logger.info("No OpenAI API key provided, using mock summarization")
    
    summarization_results = summarizer_agent.summarize_classified_documents(
        session_id=session_id,
        user_id=default_user,
        status_to_summarize="classified"
    )
    logger.info(f"Summarization complete: {summarization_results[0]} succeeded, {summarization_results[1]} failed")
    
    # Step 4: Tagging and Filing
    logger.info("Starting document tagging and filing...")
    tagging_results = tagger_agent.process_documents_for_tagging_and_filing(
        user_id=default_user,
        status_to_process="summarized"
    )
    logger.info(f"Tagging and filing complete: {tagging_results[0]} succeeded, {tagging_results[1]} failed")
    
    # Step 5: Generate Cover Sheet
    logger.info("Generating cover sheet...")
    
    # Get all processed documents for the session
    documents = context_store.get_documents_for_session(session_id)
    document_ids = [doc["document_id"] for doc in documents]
    
    # Initialize cover sheet path
    cover_sheet_pdf_path = None
    
    if document_ids:
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        cover_sheet_pdf_path = os.path.join(
            config['pdf_output_dir'],
            f"IDIS_Cover_Sheet_{timestamp}.pdf"
        )
        
        success = cover_sheet_renderer.generate_cover_sheet(
            document_ids=document_ids,
            output_pdf_filename=cover_sheet_pdf_path,
            session_id=session_id,
            user_id=default_user
        )
        
        if success:
            logger.info(f"Successfully generated cover sheet: {cover_sheet_pdf_path}")
        else:
            logger.error("Failed to generate cover sheet PDF, but Markdown file should be available")
    else:
        logger.warning("No documents found to include in cover sheet")
    
    # Print document summary for verification
    logger.info("\n" + "="*80)
    logger.info("IDIS PIPELINE RESULTS")
    logger.info("="*80)
    
    # Get session metadata for batch summary
    session_data = context_store.get_session(session_id)
    batch_summary = None
    if session_data and 'metadata' in session_data and session_data['metadata']:
        if isinstance(session_data['metadata'], str):
            try:
                metadata = json.loads(session_data['metadata'])
                batch_summary = metadata.get('batch_summary')
            except json.JSONDecodeError:
                logger.warning("Failed to parse session metadata as JSON")
        elif isinstance(session_data['metadata'], dict):
            batch_summary = session_data['metadata'].get('batch_summary')
    
    logger.info(f"Session ID: {session_id}")
    logger.info(f"Batch Summary: {batch_summary}")
    
    # Print document details
    logger.info(f"Processed {len(documents)} documents:")
    for idx, doc in enumerate(documents, 1):
        logger.info(f"{idx}. Document: {doc.get('file_name', 'Unknown')}")
        logger.info(f"   - ID: {doc.get('document_id', 'Unknown')}")
        logger.info(f"   - Type: {doc.get('document_type', 'Unclassified')}")
        logger.info(f"   - Status: {doc.get('processing_status', 'Unknown')}")
        
        # Get summary if available
        doc_id = doc.get('document_id')
        if doc_id is not None:
            summaries = context_store.get_agent_outputs_for_document(
                document_id=doc_id,
                agent_id="summarizer_agent",
                output_type="per_document_summary"
            )
        else:
            summaries = []
        if summaries:
            logger.info(f"   - Summary: {summaries[0].get('output_data', 'No summary available')}")
        
        # Print metadata
        logger.info(f"   - Issuer: {doc.get('issuer_source', 'Unknown')}")
        logger.info(f"   - Recipient: {doc.get('recipient', 'Unknown')}")
        if doc.get('document_dates'):
            dates_str = doc.get('document_dates', {})
            if isinstance(dates_str, str):
                try:
                    dates = json.loads(dates_str)
                    logger.info(f"   - Dates: {dates}")
                except json.JSONDecodeError:
                    logger.info(f"   - Dates: {dates_str}")
            else:
                logger.info(f"   - Dates: {dates_str}")
                
        tags = doc.get('tags_extracted', [])
        if tags:
            if isinstance(tags, str):
                try:
                    tags_list = json.loads(tags)
                    logger.info(f"   - Tags: {', '.join(tags_list)}")
                except json.JSONDecodeError:
                    logger.info(f"   - Tags: {tags}")
            else:
                logger.info(f"   - Tags: {', '.join(tags)}")
    
    # Return results summary
    return {
        'session_id': session_id,
        'documents_processed': len(documents),
        'ingestion_count': ingestion_results,
        'classification_success': classification_results[0],
        'classification_failure': classification_results[1],
        'summarization_success': summarization_results[0],
        'tagging_success': tagging_results[0],
        'tagging_failure': tagging_results[1],
        'cover_sheet_path': cover_sheet_pdf_path
    }

def main():
    """
    Main function for running the IDIS pipeline in Docker.
    """
    parser = argparse.ArgumentParser(description="Run IDIS pipeline in Docker environment")
    parser.add_argument("--db-path", default=DEFAULT_DB_PATH, 
                        help=f"Path to the SQLite database file (default: {DEFAULT_DB_PATH})")
    parser.add_argument("--watch-folder", default=DEFAULT_WATCH_FOLDER,
                        help=f"Path to the folder to watch for documents (default: {DEFAULT_WATCH_FOLDER})")
    parser.add_argument("--holding-folder", default=DEFAULT_HOLDING_FOLDER,
                        help=f"Path to the folder for problematic documents (default: {DEFAULT_HOLDING_FOLDER})")
    parser.add_argument("--archive-folder", default=DEFAULT_ARCHIVE_FOLDER,
                        help=f"Path to the folder for archived documents (default: {DEFAULT_ARCHIVE_FOLDER})")
    parser.add_argument("--cover-sheets-folder", default=DEFAULT_COVER_SHEETS_FOLDER,
                        help=f"Path to the folder for generated cover sheets (default: {DEFAULT_COVER_SHEETS_FOLDER})")
    
    args = parser.parse_args()
    
    # Set up environment
    config = setup_environment(
        base_dir="/app",
        db_path=args.db_path
    )
    
    # Update config with command-line arguments
    config['watch_folder'] = args.watch_folder
    config['holding_folder'] = args.holding_folder
    config['archive_folder'] = args.archive_folder
    config['pdf_output_dir'] = args.cover_sheets_folder
    
    # Run the pipeline
    results = run_pipeline(config)
    
    # Log summary
    logger = logging.getLogger("IDIS_Docker_Pipeline")
    logger.info("\nPipeline execution summary:")
    logger.info(f"Session ID: {results['session_id']}")
    logger.info(f"Documents processed: {results['documents_processed']}")
    logger.info(f"Documents ingested: {results['ingestion_count']}")
    logger.info(f"Documents classified: {results['classification_success']}")
    logger.info(f"Documents summarized: {results['summarization_success']}")
    logger.info(f"Documents tagged and filed: {results['tagging_success']}")
    
    if results['cover_sheet_path']:
        logger.info(f"Cover sheet generated: {results['cover_sheet_path']}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())