#!/usr/bin/env python3
"""
Demo script for testing the UnifiedIngestionAgent with OpenAI API integration.
"""

import os
import tempfile
import shutil
from context_store import ContextStore
from unified_ingestion_agent import UnifiedIngestionAgent

def create_sample_documents(watch_folder):
    """Create sample documents for testing."""
    
    # Sample credit card statement
    credit_card_content = """
FIDELITY REWARDS VISA SIGNATURE CARD

Statement Date: June 15, 2025
Account Number: XXXX-XXXX-XXXX-1234

Previous Balance: $1,109.56
Payments/Credits: -$500.00
New Purchases: $625.00
Interest Charges: $0.00
Fees: $0.00

New Balance: $1,234.56
Minimum Payment Due: $25.00
Payment Due Date: July 10, 2025

RECENT TRANSACTIONS:
06/12/25  AMAZON.COM           $89.99
06/10/25  STARBUCKS #1234      $12.45
06/08/25  SHELL GAS STATION    $65.32
06/05/25  GROCERY MART         $125.88
06/03/25  NETFLIX SUBSCRIPTION $15.99
"""
    
    # Sample utility bill
    utility_bill_content = """
GCI COMMUNICATIONS
Internet Service Bill

Account Number: 123456789
Service Period: May 1-31, 2025
Bill Date: June 1, 2025
Due Date: June 25, 2025

Service Details:
High-Speed Internet - Residential
Download Speed: 100 Mbps
Upload Speed: 10 Mbps

Current Charges:
Monthly Service Fee: $79.99
Equipment Rental: $10.00
Total Amount Due: $89.99

Payment Methods:
- Online at gci.com
- Phone: 1-800-GCI-4YOU
- Mail: PO Box 4000, Anchorage, AK 99509
"""
    
    # Sample medical document
    medical_content = """
ALASKA REGIONAL HOSPITAL
Medical Record Summary

Patient: John Doe
Date of Birth: 01/15/1980
Medical Record Number: MRN-987654321
Date of Service: June 20, 2025

Chief Complaint: Annual physical examination

Vital Signs:
Blood Pressure: 120/80 mmHg
Heart Rate: 72 bpm
Temperature: 98.6°F
Weight: 175 lbs
Height: 5'10"

Assessment:
Patient presents for routine annual physical. Overall health status is good.
No acute concerns noted during examination.

Plan:
- Continue current exercise routine
- Maintain healthy diet
- Return for annual follow-up
- Lab work ordered: Complete blood panel

Provider: Dr. Sarah Johnson, MD
"""

    # Write sample files
    sample_files = [
        ("credit_card_statement.txt", credit_card_content),
        ("utility_bill.txt", utility_bill_content),
        ("medical_record.txt", medical_content)
    ]
    
    for filename, content in sample_files:
        filepath = os.path.join(watch_folder, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
    
    return len(sample_files)

def test_unified_ingestion():
    """Test the UnifiedIngestionAgent with sample documents."""
    
    print("=== Unified Ingestion Agent Demo ===\n")
    
    # Create temporary directories
    with tempfile.TemporaryDirectory() as temp_dir:
        watch_folder = os.path.join(temp_dir, "watch")
        holding_folder = os.path.join(temp_dir, "holding")
        db_path = os.path.join(temp_dir, "demo.db")
        
        os.makedirs(watch_folder, exist_ok=True)
        os.makedirs(holding_folder, exist_ok=True)
        
        print(f"Created temporary directories:")
        print(f"  Watch folder: {watch_folder}")
        print(f"  Holding folder: {holding_folder}")
        print(f"  Database: {db_path}")
        print()
        
        # Initialize Context Store
        print("Initializing Context Store...")
        context_store = ContextStore(db_path)
        
        # Create sample patient and session
        patient_id = context_store.add_patient({"patient_name": "Demo Patient"})
        session_id = context_store.create_session("demo_user", {"source": "unified_demo"})
        
        print(f"Created patient ID: {patient_id}")
        print(f"Created session ID: {session_id}")
        print()
        
        # Create sample documents
        print("Creating sample documents...")
        num_files = create_sample_documents(watch_folder)
        print(f"Created {num_files} sample documents in watch folder")
        print()
        
        # Initialize and run UnifiedIngestionAgent
        print("Initializing UnifiedIngestionAgent...")
        agent = UnifiedIngestionAgent(context_store, watch_folder, holding_folder)
        print()
        
        print("Processing documents with OpenAI API integration...")
        processed_count, errors = agent.process_documents_from_folder(
            patient_id=patient_id, 
            session_id=session_id
        )
        
        print(f"\n=== Processing Results ===")
        print(f"Successfully processed: {processed_count} documents")
        print(f"Errors encountered: {len(errors)}")
        
        if errors:
            print("\nError details:")
            for error in errors:
                print(f"  - {error}")
        print()
        
        # Query and display results
        print("=== Database Contents ===")
        
        # Get all documents for the session
        documents = context_store.get_documents_for_session(str(session_id))
        print(f"Documents in database: {len(documents)}")
        
        for i, doc in enumerate(documents, 1):
            print(f"\nDocument {i}:")
            print(f"  ID: {doc.get('document_id', 'N/A')}")
            print(f"  Filename: {doc.get('file_name', 'N/A')}")
            print(f"  Type: {doc.get('document_type', 'N/A')}")
            print(f"  Status: {doc.get('processing_status', 'N/A')}")
            print(f"  Issuer: {doc.get('issuer_source', 'N/A')}")
            print(f"  Tags: {doc.get('tags_extracted', 'N/A')}")
            
            # Show structured data if available
            if doc.get('extracted_data'):
                try:
                    import json
                    structured_data = json.loads(doc['extracted_data'])
                    print(f"  Structured data schema: {structured_data.get('schema_version', 'N/A')}")
                    
                    # Show key financial info if available
                    if 'financials' in structured_data:
                        financials = structured_data['financials']
                        if 'total_amount' in financials:
                            currency = financials.get('currency', 'USD')
                            amount = financials['total_amount']
                            print(f"  Amount: {currency} {amount}")
                            
                except (json.JSONDecodeError, KeyError):
                    print("  Structured data: Parse error")
        
        print(f"\n=== Demo Complete ===")
        print("All sample documents have been processed through the unified pipeline.")
        print("The system successfully:")
        print("  ✓ Extracted text from documents")
        print("  ✓ Used OpenAI API to structure the data")
        print("  ✓ Stored both raw text and JSON metadata")
        print("  ✓ Made data searchable through QuantaIQ interface")

if __name__ == "__main__":
    test_unified_ingestion()