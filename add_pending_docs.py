#!/usr/bin/env python3
"""
Script to add sample documents with pending_categorization status
for testing the HITL workflow in the QuantaIQ UI.
"""

import os
import json
from context_store import ContextStore

def add_pending_documents():
    """Add sample documents that need manual categorization."""
    
    # Build a reliable, absolute path to the database
    # REPL_HOME is a Replit environment variable pointing to the project root
    project_root = os.environ.get('REPL_HOME', os.getcwd())
    db_dir = os.path.join(project_root, 'data', 'idis_db_storage')
    os.makedirs(db_dir, exist_ok=True)
    db_path = os.path.join(db_dir, 'idis_live_test.db')
    
    context_store = ContextStore(db_path)
    print(f"Connected to database at: {db_path}")
    
    # Sample documents requiring HITL review
    pending_docs = [
        {
            'file_name': 'grocery_receipt_safeway.pdf',
            'original_file_type': 'pdf',
            'ingestion_status': 'ingestion_successful',
            'processing_status': 'pending_categorization',
            'patient_id': 1,
            'session_id': 1,
            'extracted_data': json.dumps({
                "schema_version": "1.3",
                "document_type": {"predicted_class": "Receipt", "confidence_score": 0.75},
                "issuer": {"name": "Safeway Store #1234", "address": "123 Main St, Anchorage, AK"},
                "key_dates": {"primary_date": "2025-06-22", "date_type": "transaction_date"},
                "financials": {"total_amount": 58.75, "currency": "USD"},
                "content": {"summary": "Grocery receipt from Safeway on June 22, 2025 for $58.75. Items included milk, bread, apples, and chicken."},
                "filing": {"suggested_tags": ["grocery", "receipt", "safeway", "food"]}
            }),
            'full_text': 'SAFEWAY STORE #1234 123 Main St, Anchorage, AK Transaction Date: 06/22/2025 MILK 2% 1GAL $3.99 BREAD WHITE $2.49 APPLES RED 3LB $4.99 CHICKEN BREAST 2LB $8.99 SUBTOTAL $20.46 TAX $1.84 TOTAL $58.75'
        },
        {
            'file_name': 'home_depot_receipt.pdf',
            'original_file_type': 'pdf',
            'ingestion_status': 'ingestion_successful',
            'processing_status': 'pending_categorization',
            'patient_id': 1,
            'session_id': 1,
            'extracted_data': json.dumps({
                "schema_version": "1.3",
                "document_type": {"predicted_class": "Receipt", "confidence_score": 0.82},
                "issuer": {"name": "The Home Depot #0825", "address": "456 Hardware Ave, Anchorage, AK"},
                "key_dates": {"primary_date": "2025-06-21", "date_type": "transaction_date"},
                "financials": {"total_amount": 127.43, "currency": "USD"},
                "content": {"summary": "Hardware store receipt from Home Depot for plumbing supplies including PVC pipe, fittings, and tools."},
                "filing": {"suggested_tags": ["hardware", "receipt", "home_depot", "plumbing", "supplies"]}
            }),
            'full_text': 'THE HOME DEPOT #0825 456 Hardware Ave, Anchorage, AK Transaction Date: 06/21/2025 PVC PIPE 1/2" 10FT $12.99 PIPE FITTINGS ASSORTED $24.50 PLUMBER WRENCH SET $45.99 TEFLON TAPE $3.99 SUBTOTAL $87.47 TAX $7.87 TOTAL $127.43'
        },
        {
            'file_name': 'restaurant_invoice.pdf',
            'original_file_type': 'pdf',
            'ingestion_status': 'ingestion_successful',
            'processing_status': 'pending_categorization',
            'patient_id': 1,
            'session_id': 1,
            'extracted_data': json.dumps({
                "schema_version": "1.3",
                "document_type": {"predicted_class": "Invoice", "confidence_score": 0.88},
                "issuer": {"name": "Arctic Roadrunner Restaurant", "address": "789 Food Court Dr, Anchorage, AK"},
                "key_dates": {"primary_date": "2025-06-20", "date_type": "invoice_date"},
                "financials": {"total_amount": 234.56, "currency": "USD"},
                "content": {"summary": "Restaurant invoice for catering services provided for office meeting on June 20, 2025."},
                "filing": {"suggested_tags": ["restaurant", "invoice", "catering", "business", "meeting"]}
            }),
            'full_text': 'ARCTIC ROADRUNNER RESTAURANT 789 Food Court Dr, Anchorage, AK INVOICE #AR-2025-0620 Date: June 20, 2025 CATERING SERVICES Office Meeting Catering Package for 15 people Sandwich Platters $125.00 Beverage Service $45.00 Dessert Tray $35.00 Service Fee $19.56 TAX $10.00 TOTAL $234.56'
        }
    ]
    
    for doc_data in pending_docs:
        doc_id = context_store.add_document(doc_data)
        print(f"Added document: {doc_data['file_name']} (ID: {doc_id})")
    
    print(f"\nAdded {len(pending_docs)} documents with pending_categorization status")
    print("These documents are now available for HITL review in the QuantaIQ UI")

if __name__ == '__main__':
    add_pending_documents()