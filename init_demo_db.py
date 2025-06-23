# init_demo_db.py

import os
import json
from context_store import ContextStore

def initialize_demo_database():
    """
    Initializes a demo database with a sample patient and documents
    that conform to the new V1.3 schema structure.
    """
    print("Initializing demo database...")
    
    # Create the database path
    db_path = os.path.expanduser('~/IDIS_Dell_Scan_Test/idis_db_storage/idis_live_test.db')
    
    # If DB exists, remove it for a clean start
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"Removed existing database at {db_path}")

    # Initialize ContextStore (this creates the database and tables)
    context_store = ContextStore(db_path)
    print("ContextStore initialized and tables created.")

    # Add a sample patient
    patient_id = context_store.add_patient({'patient_name': 'Demo Patient'})
    print(f"Created patient with ID: {patient_id}")

    # Create a session
    session_id = context_store.create_session(
        user_id='demo_user',
        session_metadata={'source': 'demo_initialization'}
    )
    print(f"Created session with ID: {session_id}")

    # --- Sample Document 1: Fidelity Statement ---
    fidelity_data = {
      "schema_version": "1.3",
      "document_type": {"predicted_class": "Financial Statement", "confidence_score": 0.99},
      "issuer": {"name": "Fidelity Rewards Visa Signature", "address": None, "contact_info": None},
      "recipient": {"name": "Demo Patient", "account_number": "XXXX-XXXX-XXXX-1234"},
      "key_dates": {"primary_date": "2025-06-15", "date_type": "statement_date", "due_date": "2025-07-10"},
      "financials": {"total_amount": 1234.56, "currency": "USD", "amount_due": 25.00},
      "content": {"summary": "Monthly credit card statement from Fidelity showing new balance and minimum payment due."},
      "filing": {"suggested_tags": ["financial", "credit_card", "statement", "fidelity"]}
    }
    
    context_store.add_document({
        'file_name': 'sample_credit_card_statement.pdf',
        'original_file_type': 'pdf',
        'ingestion_status': 'ingestion_successful',
        'processing_status': 'processing_complete',
        'patient_id': patient_id,
        'session_id': session_id,
        'extracted_data': json.dumps(fidelity_data), # Convert dict to JSON string
        'full_text': 'Fidelity Rewards Visa Signature New Balance: $1,234.56 Minimum Payment Due: $25.00 Closing Date: 2025-06-15'
    })
    print("Added Fidelity statement to database.")

    # --- Sample Document 2: GCI Bill ---
    gci_data = {
      "schema_version": "1.3",
      "document_type": {"predicted_class": "Utility Bill", "confidence_score": 0.98},
      "issuer": {"name": "GCI", "address": None, "contact_info": "gci.com"},
      "recipient": {"name": "Demo Patient", "account_number": "123456789"},
      "key_dates": {"primary_date": "2025-06-01", "date_type": "invoice_date", "due_date": "2025-06-25", "start_date": "2025-05-01", "end_date": "2025-05-31"},
      "financials": {"total_amount": 89.99, "currency": "USD", "amount_due": 89.99},
      "service_details": {"service_type": "Internet"},
      "content": {"summary": "Monthly internet service bill from GCI for the May service period."},
      "filing": {"suggested_tags": ["utility", "internet", "bill", "gci"]}
    }

    context_store.add_document({
        'file_name': 'sample_utility_bill.pdf',
        'original_file_type': 'pdf',
        'ingestion_status': 'ingestion_successful',
        'processing_status': 'processing_complete',
        'patient_id': patient_id,
        'session_id': session_id,
        'extracted_data': json.dumps(gci_data), # Convert dict to JSON string
        'full_text': 'GCI Internet Service Bill Account: 123456789 Service Period: May 1-31, 2025 Amount Due: $89.99'
    })
    print("Added GCI bill to database.")
    print("\nDatabase initialization complete.")

if __name__ == '__main__':
    initialize_demo_database()