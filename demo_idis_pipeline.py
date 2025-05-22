#!/usr/bin/env python3
"""
IDIS Full Pipeline Demo

This script demonstrates the complete Intelligent Document Insight System pipeline:
1. Document ingestion
2. Document classification
3. Document summarization
4. Document tagging and filing
5. Cover sheet generation

This provides an end-to-end showcase of IDIS capabilities.
"""

import os
import argparse
import logging
import json
import shutil
import tempfile
from pathlib import Path

from context_store import ContextStore
from ingestion_agent import IngestionAgent
from classifier_agent import ClassifierAgent
from summarizer_agent import SummarizerAgent
from tagger_agent import TaggerAgent
from cover_sheet import SmartCoverSheetRenderer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("IDIS_Demo")

def create_demo_folders(base_path):
    """Create folders for the IDIS demo."""
    folders = {
        "watch_folder": os.path.join(base_path, "watch_folder"),
        "problem_files": os.path.join(base_path, "problem_files"),
        "archived_files": os.path.join(base_path, "archived_files")
    }
    
    for folder in folders.values():
        os.makedirs(folder, exist_ok=True)
    
    return folders

def create_demo_documents(watch_folder):
    """Create sample documents in the watch folder."""
    demo_documents = [
        {
            "name": "invoice_12345.txt",
            "content": """INVOICE #12345
Date: January 15, 2025
From: ABC Supplies Co.
To: IDIS Healthcare

Items:
1. Medical equipment - $1,500.00
2. Office supplies - $350.00
3. Software license - $2,000.00

Total: $3,850.00

Payment due within 30 days.
"""
        },
        {
            "name": "medical_record_jane_doe.txt",
            "content": """MEDICAL RECORD
Patient: Jane Doe
DOB: 03/12/1980
Date of Service: May 10, 2025

Chief Complaint: Persistent headaches and fatigue for 2 weeks

Assessment:
- Tension headaches
- Possible iron-deficiency anemia

Plan:
1. Blood tests ordered
2. Prescribed pain reliever for headaches
3. Follow-up in 2 weeks

Dr. Smith, MD
"""
        },
        {
            "name": "legal_notification_roe.txt",
            "content": """LEGAL NOTIFICATION
Case: Roe vs. Healthcare Systems
Date: April 30, 2025

This notice is to inform all parties that the scheduled deposition
for the above-referenced case has been postponed until June 15, 2025.

All other deadlines remain unchanged. Please contact our office
with any questions.

Sincerely,
Legal Department
"""
        }
    ]
    
    created_files = []
    for doc in demo_documents:
        file_path = os.path.join(watch_folder, doc["name"])
        with open(file_path, "w") as f:
            f.write(doc["content"])
        created_files.append(file_path)
        logger.info(f"Created demo document: {file_path}")
    
    return created_files

def run_idis_pipeline(db_path, folders, openai_key=None, output_pdf=None):
    """Run the complete IDIS pipeline on the demo documents."""
    # Initialize the Context Store
    context_store = ContextStore(db_path)
    logger.info(f"Initialized Context Store with database: {db_path}")
    
    # Create a session for this demo run
    session_id = context_store.create_session(
        user_id="idis_demo_user",
        session_metadata={"purpose": "full_pipeline_demo"}
    )
    logger.info(f"Created session with ID: {session_id}")
    
    # Initialize the Ingestion Agent
    ingestion_agent = IngestionAgent(
        context_store=context_store,
        watch_folder=folders["watch_folder"],
        holding_folder=folders["problem_files"]
    )
    logger.info("Initialized Ingestion Agent")
    
    # Initialize the Classifier Agent with rules
    classification_rules = {
        "Invoice": ["invoice", "payment", "due", "total", "amount", "paid", "balance"],
        "Medical Record": ["patient", "diagnosis", "treatment", "doctor", "hospital", "medical", "health"],
        "Letter": ["dear", "sincerely", "regards", "letter", "notification", "inform"],
        "Receipt": ["receipt", "purchased", "transaction", "store", "bought", "customer"],
        "Insurance Document": ["insurance", "coverage", "policy", "claim", "premium", "deductible"],
        "Legal Document": ["legal", "law", "contract", "agreement", "terms", "conditions", "lawsuit"],
        "Report": ["report", "analysis", "findings", "conclusion", "investigation", "results"]
    }
    
    classifier_agent = ClassifierAgent(
        context_store=context_store,
        classification_rules=classification_rules
    )
    logger.info("Initialized Classifier Agent")
    
    # Initialize the Summarizer Agent
    summarizer_agent = SummarizerAgent(
        context_store=context_store,
        openai_api_key=openai_key
    )
    logger.info("Initialized Summarizer Agent")
    
    # Initialize the Tagger Agent
    tag_definitions = {
        "urgent": ["urgent", "immediate", "asap", "priority", "expedite"],
        "confidential": ["confidential", "private", "sensitive", "restricted"],
        "action_required": ["action required", "please respond", "attention required", "needs approval"],
        "important": ["important", "critical", "vital", "essential", "key", "significant"]
    }
    
    tagger_agent = TaggerAgent(
        context_store=context_store,
        base_filed_folder=folders["archived_files"],
        tag_definitions=tag_definitions
    )
    logger.info("Initialized Tagger Agent")
    
    # Process the pipeline
    
    # Step 1: Document Ingestion
    logger.info("Starting document ingestion...")
    successful_document_ids = ingestion_agent.process_pending_documents(session_id=session_id)
    logger.info(f"Ingested {len(successful_document_ids)} documents")
    
    # Step 2: Document Classification
    logger.info("Starting document classification...")
    classification_results = classifier_agent.process_documents_for_classification()
    logger.info(f"Classification complete: {classification_results[0]} succeeded, {classification_results[1]} failed")
    
    # Step 3: Document Summarization
    logger.info("Starting document summarization...")
    if openai_key:
        summarization_results = summarizer_agent.summarize_classified_documents(session_id=session_id)
        logger.info(f"Summarization complete: {summarization_results[0]} succeeded, batch summary: {summarization_results[1]}")
    else:
        logger.warning("No OpenAI API key provided, skipping summarization")
        # Update document status to allow pipeline to continue
        documents = context_store.get_documents_for_session(session_id)
        for doc in documents:
            context_store.update_document_fields(
                doc['document_id'], 
                {'processing_status': 'summarized'}
            )
    
    # Step 4: Document Tagging and Filing
    logger.info("Starting document tagging and filing...")
    tagging_results = tagger_agent.process_documents_for_tagging_and_filing()
    logger.info(f"Tagging and filing complete: {tagging_results[0]} succeeded, {tagging_results[1]} failed")
    
    # Step 5: Generate Cover Sheet
    if output_pdf:
        logger.info("Generating cover sheet...")
        documents = context_store.get_documents_for_session(session_id)
        document_ids = [doc["document_id"] for doc in documents]
        
        if document_ids:
            renderer = SmartCoverSheetRenderer(context_store)
            success = renderer.generate_cover_sheet(
                document_ids=document_ids,
                output_pdf_filename=output_pdf,
                session_id=session_id
            )
            
            if success:
                logger.info(f"Successfully generated cover sheet: {output_pdf}")
            else:
                logger.error("Failed to generate cover sheet")
        else:
            logger.error("No documents found to include in cover sheet")
    
    return context_store, session_id

def main():
    parser = argparse.ArgumentParser(description="Run the complete IDIS pipeline demo")
    parser.add_argument("--db-path", default="./idis_demo.db", help="Path to the SQLite database file")
    parser.add_argument("--demo-dir", default="./idis_demo", help="Base directory for demo files")
    parser.add_argument("--output-pdf", default="./idis_demo_cover_sheet.pdf", help="Path to save the output cover sheet PDF")
    parser.add_argument("--openai", action="store_true", help="Use OpenAI API for summarization (requires API key)")
    parser.add_argument("--clean", action="store_true", help="Clean existing demo folders before starting")
    
    args = parser.parse_args()
    
    # Check for OpenAI API key if --openai is specified
    openai_key = None
    if args.openai:
        openai_key = os.environ.get("OPENAI_API_KEY")
        if not openai_key:
            logger.warning("OpenAI API key not found in environment. Summarization will be skipped.")
    
    # Clean existing demo folders if requested
    if args.clean and os.path.exists(args.demo_dir):
        logger.info(f"Cleaning existing demo directory: {args.demo_dir}")
        shutil.rmtree(args.demo_dir)
    
    # Create demo folders
    folders = create_demo_folders(args.demo_dir)
    
    # Create demo documents
    create_demo_documents(folders["watch_folder"])
    
    # Run the pipeline
    run_idis_pipeline(
        db_path=args.db_path,
        folders=folders,
        openai_key=openai_key,
        output_pdf=args.output_pdf
    )
    
    logger.info("IDIS pipeline demo completed successfully!")

if __name__ == "__main__":
    main()