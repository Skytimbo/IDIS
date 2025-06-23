#!/usr/bin/env python3
"""
Initialize V1 Demo Database for QuantaIQ UI
Creates a clean V1 schema database with sample V1.3 JSON data.
"""

import os
import json
import sqlite3

def create_v1_database():
    """Create a clean V1 database with V1.3 sample data."""
    print("Creating V1 database...")
    
    # Create the database path
    db_path = os.path.expanduser('~/IDIS_Dell_Scan_Test/idis_db_storage/idis_live_test.db')
    
    # Remove existing database
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"Removed existing database at {db_path}")
    
    # Create database connection
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create clean V1 schema tables
    cursor.execute('''
        CREATE TABLE patients (
            id INTEGER PRIMARY KEY,
            patient_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE sessions (
            id INTEGER PRIMARY KEY,
            user_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'active',
            session_metadata TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE documents (
            document_id TEXT PRIMARY KEY,
            patient_id TEXT,
            session_id TEXT,
            file_name TEXT,
            original_file_type TEXT,
            original_watchfolder_path TEXT,
            upload_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            ingestion_status TEXT,
            extracted_text TEXT,
            ocr_confidence_percent REAL,
            document_type TEXT,
            classification_confidence TEXT,
            processing_status TEXT,
            document_dates TEXT,
            issuer_source TEXT,
            recipient TEXT,
            tags_extracted TEXT,
            filed_path TEXT,
            last_modified_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            extracted_data TEXT,
            full_text TEXT
        )
    ''')
    
    print("V1 tables created successfully.")
    
    # Insert sample patient
    cursor.execute('INSERT INTO patients (patient_name) VALUES (?)', ('Demo Patient',))
    patient_id = '1'
    print(f"Created patient with ID: {patient_id}")
    
    # Insert sample session
    session_metadata = json.dumps({'source': 'v1_demo_initialization'})
    cursor.execute('INSERT INTO sessions (user_id, session_metadata) VALUES (?, ?)', 
                   ('demo_user', session_metadata))
    session_id = '1'
    print(f"Created session with ID: {session_id}")
    
    # Sample V1.3 document data
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
    
    cursor.execute('''
        INSERT INTO documents (document_id, file_name, original_file_type, ingestion_status, processing_status, 
                              patient_id, session_id, document_type, extracted_data, full_text, extracted_text)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        'doc_1',
        'sample_credit_card_statement.pdf',
        'pdf',
        'ingestion_successful',
        'processing_complete',
        patient_id,
        session_id,
        'Financial Statement',
        json.dumps(fidelity_data),
        'Fidelity Rewards Visa Signature New Balance: $1,234.56 Minimum Payment Due: $25.00 Closing Date: 2025-06-15',
        'Fidelity Rewards Visa Signature New Balance: $1,234.56 Minimum Payment Due: $25.00 Closing Date: 2025-06-15'
    ))
    print("Added Fidelity statement to database.")
    
    gci_data = {
        "schema_version": "1.3",
        "document_type": {"predicted_class": "Utility Bill", "confidence_score": 0.98},
        "issuer": {"name": "GCI", "address": None, "contact_info": "gci.com"},
        "recipient": {"name": "Demo Patient", "account_number": "123456789"},
        "key_dates": {"primary_date": "2025-06-01", "date_type": "invoice_date", "due_date": "2025-06-25"},
        "financials": {"total_amount": 89.99, "currency": "USD", "amount_due": 89.99},
        "content": {"summary": "Monthly internet service bill from GCI for the May service period."},
        "filing": {"suggested_tags": ["utility", "internet", "bill", "gci"]}
    }
    
    cursor.execute('''
        INSERT INTO documents (document_id, file_name, original_file_type, ingestion_status, processing_status, 
                              patient_id, session_id, document_type, extracted_data, full_text, extracted_text)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        'doc_2',
        'sample_utility_bill.pdf',
        'pdf',
        'ingestion_successful',
        'processing_complete',
        patient_id,
        session_id,
        'Utility Bill',
        json.dumps(gci_data),
        'GCI Internet Service Bill Account: 123456789 Service Period: May 1-31, 2025 Amount Due: $89.99',
        'GCI Internet Service Bill Account: 123456789 Service Period: May 1-31, 2025 Amount Due: $89.99'
    ))
    print("Added GCI bill to database.")
    
    conn.commit()
    conn.close()
    
    print(f"\nV1 database initialization complete at: {db_path}")

if __name__ == '__main__':
    create_v1_database()