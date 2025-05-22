#!/usr/bin/env python3
"""
MVP Pipeline Runner for Intelligent Document Insight System (IDIS)

This script orchestrates the complete IDIS pipeline, from document ingestion through
classification, summarization, tagging/filing, to cover sheet generation.
It creates mock documents, processes them through all IDIS agents, and outputs
a cover sheet summarizing the results.
"""

import os
import shutil
import tempfile
import uuid
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

# Default configurations
DB_NAME = "mvp_e2e_test_idis.db"
PERMISSIONS_RULES_FILE = os.path.join(os.path.dirname(__file__), "permissions_rules.json")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Classification rules for the Classifier Agent
CLASSIFICATION_RULES = {
    "Invoice": ["invoice #", "total due", "bill to"],
    "Medical Record": ["patient name:", "diagnosis", "chief complaint"],
    "Letter": ["dear sir", "sincerely", "yours truly"],
    "Report": ["executive summary", "findings", "analysis section"]
}

# Tag definitions for the Tagger Agent
TAG_DEFINITIONS = {
    "urgent": ["urgent", "immediate action required", "priority!"],
    "confidential": ["confidential", "private and confidential"],
    "financial": ["payment", "invoice", "total due"],
    "medical": ["patient", "diagnosis", "treatment"]
}


def setup_environment(base_dir: str) -> Dict[str, str]:
    """
    Set up the directory structure for the MVP pipeline.
    
    Args:
        base_dir: Base directory for all pipeline components
        
    Returns:
        Dictionary containing paths for all required directories
    """
    # Create subdirectories
    watch_folder = os.path.join(base_dir, "watch_folder")
    holding_folder = os.path.join(base_dir, "holding_folder")
    archive_folder = os.path.join(base_dir, "archive_folder")
    pdf_output_dir = os.path.join(base_dir, "cover_sheets")
    
    # Ensure directories exist
    for folder in [watch_folder, holding_folder, archive_folder, pdf_output_dir]:
        os.makedirs(folder, exist_ok=True)
        
    # Database path
    db_path = os.path.join(base_dir, DB_NAME)
    
    return {
        'base_dir': base_dir,
        'watch_folder': watch_folder,
        'holding_folder': holding_folder,
        'archive_folder': archive_folder,
        'pdf_output_dir': pdf_output_dir,
        'db_path': db_path
    }


def create_mock_documents(watch_folder: str) -> List[Dict[str, Any]]:
    """
    Create mock documents in the watch folder for processing.
    
    Args:
        watch_folder: Directory where documents should be created
        
    Returns:
        List of dictionaries with metadata about the created documents
    """
    mock_docs = []
    
    # Mock Invoice
    invoice_path = os.path.join(watch_folder, "invoice_001.txt")
    invoice_content = """
    ACME CORPORATION
    123 Business Blvd.
    Corpville, CA 90001
    
    Invoice #123 for Project Alpha
    Date: 2023-10-01
    
    Bill to:
    John Doe
    456 Customer Lane
    Buyerville, CA 90002
    
    Item         Description                 Quantity    Price       Total
    ---------------------------------------------------------------------
    Consulting   Technical Consultation      10 hours    $100.00     $1,000.00
    Hardware     Server Components           2 units     $500.00     $1,000.00
    Software     License Fees                5 licenses  $200.00     $1,000.00
    
    Subtotal:                                                       $3,000.00
    Tax (8%):                                                         $240.00
    Total Due:                                                      $3,240.00
    
    Payment Terms: Net 30
    Please process this invoice as soon as possible. This is urgent!
    """
    
    with open(invoice_path, 'w') as f:
        f.write(invoice_content)
    
    mock_docs.append({
        'filename': 'invoice_001.txt',
        'expected_type': 'Invoice',
        'contains_tags': ['urgent', 'financial'],
        'expected_dates': {'invoice_date': '2023-10-01'},
        'expected_issuer': 'ACME CORPORATION',
        'expected_recipient': 'John Doe'
    })
    
    # Mock Medical Record
    medical_path = os.path.join(watch_folder, "medical_002.txt")
    medical_content = """
    CONFIDENTIAL MEDICAL RECORD
    
    Patient Name: Jane Smith
    Date of Birth: 1980-05-15
    Date of Visit: 2023-10-02
    
    Chief Complaint:
    Patient reports recurring headaches and mild dizziness for the past two weeks.
    
    Vital Signs:
    BP: 120/80, Pulse: 72, Temp: 98.6°F
    
    Assessment:
    Diagnosis: Tension headaches, possibly exacerbated by seasonal allergies.
    No indications of more serious conditions based on examination.
    
    Treatment Plan:
    1. Prescribed Amitriptyline 10mg nightly for headache prevention
    2. Recommended OTC Zyrtec for allergies
    3. Discussed stress reduction techniques
    4. Follow-up in 3 weeks if symptoms persist
    
    Seen by: Dr. Emily White
    
    This record is confidential and contains private patient information.
    """
    
    with open(medical_path, 'w') as f:
        f.write(medical_content)
    
    mock_docs.append({
        'filename': 'medical_002.txt',
        'expected_type': 'Medical Record',
        'contains_tags': ['confidential', 'medical'],
        'expected_dates': {'visit_date': '2023-10-02', 'birth_date': '1980-05-15'},
        'expected_issuer': 'Dr. Emily White',
        'expected_recipient': 'Jane Smith'
    })
    
    # Mock Letter
    letter_path = os.path.join(watch_folder, "letter_003.txt")
    letter_content = """
    Law Offices of Smith & Associates
    789 Legal Avenue
    Lawtown, CA 90003
    
    October 3, 2023
    
    Mr. Richard Roe
    123 Recipient Street
    Client Town, CA 90005
    
    Dear Mr. Roe,
    
    This letter serves as formal notification that your case #LA-7890 (Property Dispute)
    has been scheduled for hearing on October 15, 2023 at 9:00 AM at the Central County Courthouse.
    
    Please bring the following documents with you:
    1. Property deed
    2. Survey reports
    3. Correspondence with the opposing party
    4. Photos of the property line
    
    Please confirm receipt of this letter by October 10, 2023.
    
    Sincerely,
    
    James Smith, Esq.
    Smith & Associates
    """
    
    with open(letter_path, 'w') as f:
        f.write(letter_content)
    
    mock_docs.append({
        'filename': 'letter_003.txt',
        'expected_type': 'Letter',
        'contains_tags': [],
        'expected_dates': {'letter_date': '2023-10-03', 'hearing_date': '2023-10-15', 'confirmation_date': '2023-10-10'},
        'expected_issuer': 'Law Offices of Smith & Associates',
        'expected_recipient': 'Mr. Richard Roe'
    })
    
    return mock_docs


def cleanup_environment(paths: Dict[str, str], base_dir: Optional[str] = None):
    """
    Clean up the environment by removing temporary files and directories.
    
    Args:
        paths: Dictionary of paths created by setup_environment
        base_dir: Base directory to remove (if different from paths['base_dir'])
    """
    if base_dir:
        if os.path.exists(base_dir) and os.path.isdir(base_dir):
            shutil.rmtree(base_dir)
    else:
        for key, path in paths.items():
            if key != 'db_path' and os.path.exists(path) and os.path.isdir(path):
                shutil.rmtree(path)
        if 'db_path' in paths and os.path.exists(paths['db_path']):
            os.remove(paths['db_path'])


def run_pipeline(config: Dict[str, Any], keep_temp_files: bool = False) -> Dict[str, Any]:
    """
    Run the complete IDIS pipeline from ingestion to cover sheet generation.
    
    Args:
        config: Dictionary containing configuration paths
        keep_temp_files: Whether to keep temporary files after completion
        
    Returns:
        Dictionary with pipeline results and statistics
    """
    logger = logging.getLogger("MVP_Pipeline")
    logger.info("Starting IDIS MVP Pipeline")
    
    # Initialize the context store
    context_store = ContextStore(db_path=config['db_path'])
    logger.info(f"Initialized Context Store with database: {config['db_path']}")
    
    # Initialize permissions manager
    permissions_manager = PermissionsManager(rules_file_path=PERMISSIONS_RULES_FILE)
    logger.info("Initialized Permissions Manager")
    
    # Define default user and create patient record
    default_user = "mvp_pipeline_user"
    mock_patient_id = context_store.add_patient({
        "patient_name": "Test Patient",
        "date_of_birth": "1980-01-01",
        "medical_record_number": "MRN-TEST-123"
    })
    
    # Create session linked to the patient
    mock_session_id = context_store.create_session(
        user_id=default_user,
        session_metadata={"description": "MVP E2E Test Batch", "patient_id": mock_patient_id}
    )
    logger.info(f"Created session with ID: {mock_session_id}")
    
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
    
    # Create mock documents
    mock_doc_details = create_mock_documents(config['watch_folder'])
    logger.info(f"Created {len(mock_doc_details)} mock documents in {config['watch_folder']}")
    
    # Process documents through the pipeline
    
    # Step 1: Ingestion
    logger.info("Starting document ingestion...")
    ingestion_results = ingestion_agent.process_pending_documents(
        session_id=mock_session_id,
        patient_id=mock_patient_id,
        user_id=default_user
    )
    logger.info(f"Ingested {ingestion_results} documents")
    
    # Step 2: Classification
    logger.info("Starting document classification...")
    classification_results = classifier_agent.process_documents_for_classification(
        user_id=default_user,
        status_to_classify="ingestion_successful",
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
        session_id=mock_session_id,
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
    documents = context_store.get_documents_for_session(mock_session_id)
    document_ids = [doc["document_id"] for doc in documents]
    
    # Initialize cover sheet path
    cover_sheet_pdf_path = None
    
    if document_ids:
        cover_sheet_pdf_path = os.path.join(
            config['pdf_output_dir'],
            f"MVP_Cover_Sheet_{mock_session_id}.pdf"
        )
        
        success = cover_sheet_renderer.generate_cover_sheet(
            document_ids=document_ids,
            output_pdf_filename=cover_sheet_pdf_path,
            session_id=mock_session_id,
            user_id=default_user
        )
        
        if success:
            logger.info(f"Successfully generated cover sheet: {cover_sheet_pdf_path}")
        else:
            logger.error("Failed to generate cover sheet")
    else:
        logger.warning("No documents found to include in cover sheet")
    
    # Print document summary for verification
    logger.info("\n" + "="*80)
    logger.info("IDIS PIPELINE RESULTS")
    logger.info("="*80)
    
    # Get session metadata for batch summary
    session_data = context_store.get_session(mock_session_id)
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
    
    logger.info(f"Session ID: {mock_session_id}")
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
    
    logger.info("="*80)
    logger.info("END OF RESULTS")
    logger.info("="*80)
    
    # Return results for the test suite
    return {
        'session_id': mock_session_id,
        'patient_id': mock_patient_id,
        'documents': documents,
        'cover_sheet_path': cover_sheet_pdf_path if document_ids else None,
        'stats': {
            'ingested': ingestion_results,
            'classified': classification_results,
            'summarized': summarization_results,
            'tagged': tagging_results
        }
    }


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run the IDIS MVP Pipeline")
    parser.add_argument('--keep-temp-files', action='store_true', 
                        help='Keep temporary files after completion')
    parser.add_argument('--base-dir', type=str, 
                        help='Base directory for temporary files (defaults to a new temp directory)')
    args = parser.parse_args()
    
    # Create base directory if not provided
    if args.base_dir:
        base_dir = args.base_dir
        os.makedirs(base_dir, exist_ok=True)
    else:
        base_dir = tempfile.mkdtemp(prefix="idis_mvp_run_")
    
    # Default to None in case setup fails
    config_paths = None
    
    try:
        # Setup environment and run pipeline
        config_paths = setup_environment(base_dir)
        run_pipeline(config_paths, args.keep_temp_files)
        print(f"Pipeline completed successfully. Results stored in {base_dir}")
        if args.keep_temp_files:
            print(f"Temporary files preserved in {base_dir}")
    except Exception as e:
        print(f"Error running IDIS MVP Pipeline: {e}")
        raise
    finally:
        # Clean up if not keeping temp files
        if not args.keep_temp_files and not args.base_dir and config_paths is not None:
            cleanup_environment(config_paths, base_dir)