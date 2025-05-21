"""
Demo script for testing the Context Store functionality.

This script demonstrates basic operations with the ContextStore class
including creating patients, sessions, documents, and querying data.
"""

from context_store import ContextStore
import json
from datetime import datetime

# Create a new Context Store with a file-based SQLite database
context_store = ContextStore("demo_idis.db")
print("Context Store initialized with demo_idis.db")

# Add a patient
patient_data = {
    "patient_name": "Jane Doe"
}
patient_id = context_store.add_patient(patient_data)
print(f"Added patient with ID: {patient_id}")

# Create a session
session_metadata = {
    "source": "demo_script",
    "purpose": "demonstration"
}
session_id = context_store.create_session("demo_user", session_metadata)
print(f"Created session with ID: {session_id}")

# Add a document linked to both patient and session
document_data = {
    "patient_id": patient_id,
    "session_id": session_id,
    "file_name": "medical_record.pdf",
    "original_file_type": "pdf",
    "ingestion_status": "ingestion_successful",
    "extracted_text": "Patient: Jane Doe\nDiagnosis: Healthy\nDate: 2025-05-21",
    "document_type": "Medical Record",
    "classification_confidence": "High",
    "processing_status": "classified",
    "document_dates": {
        "record_date": "2025-05-21"
    },
    "issuer_source": "Demo Medical Center",
    "recipient": "Jane Doe",
    "tags_extracted": ["medical", "record", "checkup"]
}
document_id = context_store.add_document(document_data)
print(f"Added document with ID: {document_id}")

# Save agent output
output_id = context_store.save_agent_output(
    document_id,
    "summarizer_agent_v1.0",
    "per_document_summary",
    "This is a routine checkup record for Jane Doe dated May 21, 2025. The diagnosis is healthy with no concerns.",
    0.95
)
print(f"Saved agent output with ID: {output_id}")

# Add audit log entry
log_id = context_store.add_audit_log_entry(
    user_id="demo_user",
    event_type="DATA_ACCESS",
    event_name="VIEW_DOCUMENT",
    status="SUCCESS",
    resource_type="document",
    resource_id=document_id,
    details="Viewed document as part of demonstration"
)
print(f"Added audit log entry with ID: {log_id}")

# Retrieve and display patient data
patient = context_store.get_patient(patient_id)
print("\nPatient Data:")
print(json.dumps(patient, indent=2, default=str))

# Retrieve and display document
document = context_store.get_document(document_id)
print("\nDocument Data:")
print(json.dumps(document, indent=2, default=str))

# Get agent outputs for document
outputs = context_store.get_agent_outputs_for_document(document_id)
print("\nAgent Outputs:")
for output in outputs:
    print(json.dumps(output, indent=2, default=str))

# Query patient history
history = context_store.query_patient_history(patient_id)
print("\nPatient History:")
print(json.dumps(history, indent=2, default=str))

print("\nDemo completed successfully. Database file 'demo_idis.db' contains all created records.")