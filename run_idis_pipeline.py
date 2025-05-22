#!/usr/bin/env python3
"""
IDIS Pipeline Demo Script

This script demonstrates the complete Intelligent Document Insight System pipeline:
1. Set up a watch folder for document ingestion
2. Ingest documents using the Ingestion Agent
3. Classify documents using the Classifier Agent
4. Generate summaries using the Summarizer Agent
5. Extract metadata and file documents using the Tagger Agent

The pipeline processes all documents in the watch folder and outputs results to the console.
"""

import os
import sys
import time
import shutil
import argparse
import logging
import json
from typing import Dict, List

from context_store import ContextStore
from ingestion_agent import IngestionAgent
from classifier_agent import ClassifierAgent
from summarizer_agent import SummarizerAgent
from tagger_agent import TaggerAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("IDIS_Pipeline")

# Classification rules for document types
CLASSIFICATION_RULES = {
    "Invoice": ["invoice", "bill to", "total due", "payment terms", "subtotal"],
    "Medical Record": ["patient name", "diagnosis", "treatment plan", "medical history", "health record"],
    "Letter": ["dear", "sincerely", "regards", "to whom it may concern"],
    "Receipt": ["receipt", "payment received", "amount paid", "thank you for your purchase"],
    "Insurance Document": ["policy", "coverage", "premium", "insurance claim", "insured"],
    "Legal Document": ["legal", "agreement", "contract", "terms and conditions", "hereby"],
    "Report": ["findings", "analysis", "conclusion", "recommendation", "executive summary"]
}

# Tag definitions for documents
TAG_DEFINITIONS = {
    "urgent": ["urgent", "immediate attention", "asap", "emergency"],
    "confidential": ["confidential", "private", "sensitive", "do not distribute"],
    "important": ["important", "critical", "essential", "priority"],
    "follow_up": ["follow up", "follow-up", "requires response", "get back to", "respond by"]
}


def setup_folders(base_path: str) -> Dict[str, str]:
    """
    Set up the necessary folders for the IDIS pipeline.
    
    Args:
        base_path: The base directory for all IDIS folders
        
    Returns:
        Dictionary with paths to all created folders
    """
    # Create base path if it doesn't exist
    os.makedirs(base_path, exist_ok=True)
    
    # Define and create all required folders
    folders = {
        "watch_folder": os.path.join(base_path, "watch_folder"),
        "problem_files": os.path.join(base_path, "problem_files"),
        "archived_files": os.path.join(base_path, "archived_files")
    }
    
    for folder in folders.values():
        os.makedirs(folder, exist_ok=True)
        
    logger.info(f"Created IDIS folders in {base_path}")
    return folders


def create_test_document(watch_folder: str, content: str, filename: str) -> str:
    """
    Create a test document in the watch folder.
    
    Args:
        watch_folder: Path to the watch folder
        content: Content to write to the document
        filename: Name of the file to create
        
    Returns:
        Path to the created document
    """
    file_path = os.path.join(watch_folder, filename)
    with open(file_path, 'w') as f:
        f.write(content)
    logger.info(f"Created test document: {file_path}")
    return file_path


def run_pipeline(folders: Dict[str, str], db_path: str, use_openai: bool = False) -> None:
    """
    Run the complete IDIS pipeline on documents in the watch folder.
    
    Args:
        folders: Dictionary with paths to IDIS folders
        db_path: Path to the SQLite database file
        use_openai: Whether to use OpenAI for summarization
    """
    # Initialize the Context Store
    context_store = ContextStore(db_path)
    logger.info(f"Initialized Context Store with database: {db_path}")
    
    # Step 1: Create a session for this pipeline run
    session_id = context_store.create_session(
        user_id="pipeline_demo_user",
        session_metadata={"purpose": "demo", "pipeline_version": "1.0"}
    )
    logger.info(f"Created session with ID: {session_id}")
    
    # Step 2: Initialize the Ingestion Agent
    ingestion_agent = IngestionAgent(
        context_store=context_store,
        watch_folder=folders["watch_folder"],
        holding_folder=folders["problem_files"]
    )
    logger.info("Initialized Ingestion Agent")
    
    # Step 3: Initialize the Classifier Agent
    classifier_agent = ClassifierAgent(
        context_store=context_store,
        classification_rules=CLASSIFICATION_RULES
    )
    logger.info("Initialized Classifier Agent")
    
    # Step 4: Initialize the Summarizer Agent
    summarizer_agent = SummarizerAgent(
        context_store=context_store,
        openai_api_key=None  # Will use environment variable if use_openai is True
    )
    logger.info("Initialized Summarizer Agent")
    
    # Step 5: Initialize the Tagger Agent
    tagger_agent = TaggerAgent(
        context_store=context_store,
        base_filed_folder=folders["archived_files"],
        tag_definitions=TAG_DEFINITIONS
    )
    logger.info("Initialized Tagger Agent")
    
    # Step 6: Run the Ingestion Agent to process documents
    logger.info("Starting document ingestion...")
    ingested_document_ids = ingestion_agent.process_pending_documents(session_id=session_id)
    ingested_count = len(ingested_document_ids)
    logger.info(f"Ingested {ingested_count} documents")
    
    if ingested_count == 0:
        logger.warning("No documents were ingested, pipeline cannot proceed")
        return
    
    # Step 7: Run the Classifier Agent to categorize documents
    logger.info("Starting document classification...")
    
    # First, make sure we set the processing_status to "ingested" for all documents
    docs = context_store.get_documents_for_session(session_id)
    for doc in docs:
        if doc['processing_status'] == 'new':
            context_store.update_document_fields(
                doc['document_id'],
                {"processing_status": "ingested"}
            )
    
    classified_success, classified_failed = classifier_agent.process_documents_for_classification(
        user_id="pipeline_demo_user"
    )
    logger.info(f"Classification complete: {classified_success} succeeded, {classified_failed} failed")
    
    # Step 8: Run the Summarizer Agent to generate summaries
    if use_openai:
        logger.info("Starting document summarization with OpenAI...")
        try:
            summarized_success, batch_summary = summarizer_agent.summarize_classified_documents(
                session_id=session_id,
                user_id="pipeline_demo_user"
            )
            logger.info(f"Summarization complete: {summarized_success} succeeded, batch summary: {batch_summary}")
        except Exception as e:
            logger.error(f"Summarization failed: {str(e)}")
            # Continue with the pipeline even if summarization fails
            logger.info("Updating document status to allow tagging...")
            # Get documents that are classified but not summarized
            classified_docs = context_store.get_documents_by_processing_status("classified")
            for doc in classified_docs:
                context_store.update_document_fields(
                    doc["document_id"],
                    {"processing_status": "summarization_skipped"}
                )
    else:
        logger.info("Skipping OpenAI summarization (use --openai to enable)")
        # Update document status to allow tagging
        classified_docs = context_store.get_documents_by_processing_status("classified")
        for doc in classified_docs:
            context_store.update_document_fields(
                doc["document_id"],
                {"processing_status": "summarization_skipped"}
            )
    
    # Step 9: Run the Tagger Agent to extract metadata and file documents
    logger.info("Starting document tagging and filing...")
    tagged_success, tagged_failed = tagger_agent.process_documents_for_tagging_and_filing(
        user_id="pipeline_demo_user",
        status_to_process="summarized" if use_openai else "summarization_skipped"
    )
    logger.info(f"Tagging and filing complete: {tagged_success} succeeded, {tagged_failed} failed")
    
    # Step 10: Display summary of processed documents
    display_pipeline_results(context_store, session_id)


def display_pipeline_results(context_store: ContextStore, session_id: str) -> None:
    """
    Display results of the pipeline processing.
    
    Args:
        context_store: The initialized Context Store
        session_id: ID of the current session
    """
    print("\n" + "="*80)
    print(" "*30 + "IDIS PIPELINE RESULTS")
    print("="*80)
    
    # Get session information
    session = context_store.get_session(session_id)
    print(f"\nSession ID: {session_id}")
    
    if session and 'session_metadata' in session:
        session_metadata = session['session_metadata']
        if isinstance(session_metadata, str):
            import json
            try:
                session_metadata = json.loads(session_metadata)
            except:
                session_metadata = {}
                
        if 'batch_summary' in session_metadata:
            print(f"\nBatch Summary: {session_metadata['batch_summary']}")
    
    # Get all documents processed in this session
    documents = context_store.get_documents_for_session(session_id)
    print(f"\nProcessed {len(documents)} documents:")
    
    for i, doc in enumerate(documents, 1):
        print(f"\n{i}. Document: {doc['file_name']}")
        print(f"   - ID: {doc['document_id']}")
        print(f"   - Type: {doc.get('document_type', 'Unknown')}")
        print(f"   - Status: {doc.get('processing_status', 'Unknown')}")
        
        # Get agent outputs for this document
        outputs = context_store.get_agent_outputs_for_document(doc['document_id'])
        summaries = [o for o in outputs if o['output_type'] == 'per_document_summary']
        
        if summaries:
            print(f"   - Summary: {summaries[0]['output_data']}")
        
        # Display metadata if available
        if doc.get('document_dates'):
            try:
                dates = json.loads(doc['document_dates']) if isinstance(doc['document_dates'], str) else doc['document_dates']
                if dates:
                    print(f"   - Dates: {', '.join([f'{k}: {v}' for k, v in dates.items()])}")
            except:
                pass
        
        if doc.get('issuer_source'):
            print(f"   - Issuer: {doc['issuer_source']}")
            
        if doc.get('recipient'):
            print(f"   - Recipient: {doc['recipient']}")
            
        if doc.get('tags_extracted'):
            try:
                tags = json.loads(doc['tags_extracted']) if isinstance(doc['tags_extracted'], str) else doc['tags_extracted']
                if tags:
                    print(f"   - Tags: {', '.join(tags)}")
            except:
                pass
        
        if doc.get('filed_path'):
            print(f"   - Filed at: {doc['filed_path']}")
    
    print("\n" + "="*80)
    print(" "*30 + "END OF RESULTS")
    print("="*80 + "\n")


def create_demo_documents(watch_folder: str) -> None:
    """
    Create a set of demo documents in the watch folder.
    
    Args:
        watch_folder: Path to the watch folder
    """
    # Invoice document
    invoice_text = """
    ACME CORPORATION
    123 Business Rd, Commerce City, CA 90001
    
    INVOICE #12345
    
    Date: May 15, 2023
    Due Date: June 15, 2023
    
    Bill To:
    John Smith
    XYZ Company
    456 Customer Lane
    Buyerville, CA 90002
    
    Item         Description                 Quantity    Price       Total
    -------------------------------------------------------------------------
    SVC-001      Consulting Services         40 hrs      $150.00     $6,000.00
    HW-002       Server Hardware             2           $1,200.00   $2,400.00
    SW-003       Software License            5           $300.00     $1,500.00
    
    Subtotal:                                                       $9,900.00
    Tax (8%):                                                         $792.00
    Total Due:                                                     $10,692.00
    
    Payment Terms: Net 30
    Please make checks payable to ACME Corporation
    
    URGENT: Please process this invoice as soon as possible.
    """
    
    # Medical record document
    medical_record_text = """
    CONFIDENTIAL MEDICAL RECORD
    
    Sunshine Medical Center
    789 Health Avenue
    Wellness City, CA 90003
    
    Patient Name: Jane Doe
    Date of Birth: 04/12/1985
    Patient ID: SMC-12345
    
    Date of Visit: May 10, 2023
    
    Chief Complaint:
    Patient presents with recurring headaches and mild dizziness for the past 2 weeks.
    
    Medical History:
    - Hypertension (diagnosed 2018)
    - Seasonal allergies
    
    Vital Signs:
    - BP: 138/85
    - Pulse: 76
    - Temp: 98.6°F
    
    Assessment:
    Patient likely experiencing tension headaches possibly exacerbated by seasonal allergies.
    No indication of more serious conditions at this time.
    
    Treatment Plan:
    1. Prescribed Amitriptyline 10mg daily for headache prevention
    2. Recommended OTC Zyrtec for allergies
    3. Stress reduction techniques discussed
    4. Follow up in 3 weeks if symptoms persist
    
    Dr. Robert Johnson, MD
    """
    
    # Letter document
    letter_text = """
    Law Offices of Smith & Associates
    555 Legal Boulevard
    Jurisdiction City, CA 90004
    
    May 18, 2023
    
    To: Mr. Richard Roe
    123 Recipient Street
    Client Town, CA 90005
    
    Dear Mr. Roe,
    
    This letter serves as formal notification that your case #LA-7890 regarding the property
    dispute at 789 Contested Lane has been scheduled for a hearing on June 20, 2023, at
    9:00 AM at the Central County Courthouse.
    
    Please ensure you bring all relevant documentation as previously discussed, including:
    
    1. Property deed
    2. Survey reports
    3. Correspondence with the opposing party
    4. Photos of the property line in question
    
    IMPORTANT: Your attendance is required. Please confirm receipt of this letter by May 25, 2023.
    
    If you have any questions or concerns, please do not hesitate to contact our office.
    
    Sincerely,
    
    Janet Smith, Esq.
    Senior Partner
    Smith & Associates
    """
    
    create_test_document(watch_folder, invoice_text, "invoice_12345.txt")
    create_test_document(watch_folder, medical_record_text, "medical_record_jane_doe.txt")
    create_test_document(watch_folder, letter_text, "legal_notification_roe.txt")
    
    logger.info(f"Created 3 demo documents in {watch_folder}")


if __name__ == "__main__":
    import json
    
    parser = argparse.ArgumentParser(description="Run the IDIS pipeline demo")
    parser.add_argument("--base-path", default="./idis_demo", help="Base path for IDIS folders")
    parser.add_argument("--db-path", default="./idis_demo.db", help="Path to the SQLite database file")
    parser.add_argument("--create-docs", action="store_true", help="Create demo documents")
    parser.add_argument("--openai", action="store_true", help="Use OpenAI for summarization")
    parser.add_argument("--clean", action="store_true", help="Clean existing files before running")
    
    args = parser.parse_args()
    
    # Clean existing files if requested
    if args.clean:
        if os.path.exists(args.base_path):
            shutil.rmtree(args.base_path)
        if os.path.exists(args.db_path):
            os.remove(args.db_path)
        logger.info("Cleaned existing files")
    
    # Setup folders
    folders = setup_folders(args.base_path)
    
    # Create demo documents if requested
    if args.create_docs:
        create_demo_documents(folders["watch_folder"])
    
    # Run the pipeline
    try:
        run_pipeline(folders, args.db_path, args.openai)
    except KeyboardInterrupt:
        logger.info("Pipeline interrupted by user")
    except Exception as e:
        logger.error(f"Pipeline error: {str(e)}")
        raise
    
    logger.info("Pipeline demo completed")