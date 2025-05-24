#!/usr/bin/env python3
"""
Docker-aware version of the Context Store demo script.

This script demonstrates basic operations with the ContextStore class
in a Docker environment, using the appropriate paths and configurations.
"""

import os
import sys
import json
import argparse
from datetime import datetime
import logging

from context_store import ContextStore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("IDIS_Docker_Demo")

def run_context_store_demo(db_path):
    """Run the Context Store demo with the specified database path."""
    
    logger.info(f"Initializing Context Store with database: {db_path}")
    context_store = ContextStore(db_path)
    
    # Add a patient
    patient_data = {
        "patient_name": "Jane Doe",
        "date_of_birth": "1980-05-15",
        "medical_record_number": "MRN-DOCKER-123"
    }
    patient_id = context_store.add_patient(patient_data)
    logger.info(f"Added patient with ID: {patient_id}")
    
    # Create a session
    session_metadata = {
        "source": "docker_demo_script",
        "purpose": "docker_environment_testing",
        "timestamp": datetime.now().isoformat()
    }
    session_id = context_store.create_session("docker_demo_user", session_metadata)
    logger.info(f"Created session with ID: {session_id}")
    
    # Add a document linked to both patient and session
    document_data = {
        "patient_id": patient_id,
        "session_id": session_id,
        "file_name": "docker_test_medical_record.pdf",
        "original_file_type": "pdf",
        "ingestion_status": "ingestion_successful",
        "extracted_text": "Patient: Jane Doe\nDiagnosis: Healthy\nDate: 2025-05-21\nDocker Environment Test",
        "document_type": "Medical Record",
        "classification_confidence": "High",
        "processing_status": "classified",
        "document_dates": json.dumps({
            "record_date": "2025-05-21"
        }),
        "issuer_source": "Docker Test Medical Center",
        "recipient": "Jane Doe",
        "tags_extracted": json.dumps(["medical", "record", "docker_test"])
    }
    document_id = context_store.add_document(document_data)
    logger.info(f"Added document with ID: {document_id}")
    
    # Save agent output
    output_id = context_store.save_agent_output(
        document_id,
        "summarizer_agent_v1.0",
        "per_document_summary",
        "This is a routine checkup record for Jane Doe dated May 21, 2025. The diagnosis is healthy. This record was created during Docker environment testing.",
        0.95
    )
    logger.info(f"Saved agent output with ID: {output_id}")
    
    # Add audit log entry
    log_id = context_store.add_audit_log_entry(
        user_id="docker_demo_user",
        event_type="DOCKER_TEST",
        event_name="RUN_DOCKER_DEMO",
        status="SUCCESS",
        resource_type="document",
        resource_id=document_id,
        details="Created test document as part of Docker environment verification"
    )
    logger.info(f"Added audit log entry with ID: {log_id}")
    
    # Retrieve and display patient data
    patient = context_store.get_patient(patient_id)
    logger.info("\nPatient Data:")
    logger.info(json.dumps(patient, indent=2, default=str))
    
    # Retrieve and display document
    document = context_store.get_document(document_id)
    logger.info("\nDocument Data:")
    logger.info(json.dumps(document, indent=2, default=str))
    
    # Get agent outputs for document
    outputs = context_store.get_agent_outputs_for_document(document_id)
    logger.info("\nAgent Outputs:")
    for output in outputs:
        logger.info(json.dumps(output, indent=2, default=str))
    
    # Query patient history
    history = context_store.query_patient_history(patient_id)
    logger.info("\nPatient History:")
    logger.info(json.dumps(history, indent=2, default=str))
    
    logger.info(f"\nDocker demo completed successfully. Database at {db_path} contains all test records.")
    return True

def main():
    """Main function to parse arguments and run the demo."""
    parser = argparse.ArgumentParser(description="Run Context Store demo in Docker environment")
    parser.add_argument("--db-path", default="/app/db/docker_demo_idis.db", 
                        help="Path to the SQLite database file (default: /app/db/docker_demo_idis.db)")
    args = parser.parse_args()
    
    # Run the demo
    success = run_context_store_demo(args.db_path)
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())