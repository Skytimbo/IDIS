#!/usr/bin/env python3
"""
Demo script to showcase the enhanced TaggerAgent filing and naming schema.

This script creates mock documents with various scenarios to demonstrate:
1. Patient-specific filing with human-readable folder names
2. General archive filing for non-patient documents
3. Enhanced filename generation with descriptive naming
4. Priority date selection logic
"""

import os
import sys
import tempfile
import shutil
from datetime import datetime

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from context_store import ContextStore
from ingestion_agent import IngestionAgent
from classifier_agent import ClassifierAgent
from summarizer_agent import SummarizerAgent
from tagger_agent import TaggerAgent

def create_demo_documents(watch_folder):
    """Create demo documents with different scenarios."""
    documents = [
        {
            "filename": "patient_scan.pdf",
            "content": "Medical Record\nPatient: John Doe\nDoctor: Dr. Smith\nVisit Date: January 15, 2023\nThis is a confidential medical record for patient treatment.",
            "patient_id": "patient_12345678",
            "doc_type": "Medical Record"
        },
        {
            "filename": "invoice_acme.pdf", 
            "content": "INVOICE\nFrom: ACME Corporation\nTo: Business Client\nInvoice Date: February 20, 2023\nAmount: $1,500.00\nThis is an urgent payment request.",
            "patient_id": None,
            "doc_type": "Invoice"
        },
        {
            "filename": "letter_insurance.pdf",
            "content": "Insurance Letter\nFrom: Health Insurance Co\nTo: Jane Smith\nLetter Date: March 10, 2023\nRegarding: Coverage Update\nThis letter contains important information about your coverage.",
            "patient_id": "patient_87654321",
            "doc_type": "Letter"
        }
    ]
    
    created_files = []
    for doc in documents:
        file_path = os.path.join(watch_folder, doc["filename"])
        with open(file_path, 'w') as f:
            f.write(doc["content"])
        created_files.append((file_path, doc))
    
    return created_files

def setup_demo_environment():
    """Set up temporary directories for the demo."""
    base_dir = tempfile.mkdtemp(prefix="tagger_demo_")
    
    directories = {
        "watch_folder": os.path.join(base_dir, "watch"),
        "holding_folder": os.path.join(base_dir, "holding"),
        "archive_folder": os.path.join(base_dir, "archive"),
        "db_path": os.path.join(base_dir, "demo.db")
    }
    
    # Create directories
    for dir_path in [directories["watch_folder"], directories["holding_folder"], directories["archive_folder"]]:
        os.makedirs(dir_path, exist_ok=True)
    
    return base_dir, directories

def add_demo_patients(context_store):
    """Add demo patients to the Context Store."""
    patients = [
        {"patient_id": "patient_12345678", "patient_name": "John Doe"},
        {"patient_id": "patient_87654321", "patient_name": "Jane Smith"}
    ]
    
    for patient in patients:
        context_store.add_patient(
            patient_id=patient["patient_id"],
            patient_name=patient["patient_name"],
            metadata={"demo": True}
        )
    
    print(f"Added {len(patients)} demo patients to Context Store")

def print_filing_results(archive_folder):
    """Print the resulting file structure to show the enhanced schema."""
    print("\n" + "="*60)
    print("ENHANCED FILING STRUCTURE RESULTS")
    print("="*60)
    
    if not os.path.exists(archive_folder):
        print("No archive folder found")
        return
    
    for root, dirs, files in os.walk(archive_folder):
        level = root.replace(archive_folder, '').count(os.sep)
        indent = ' ' * 2 * level
        rel_path = os.path.relpath(root, archive_folder)
        if rel_path == '.':
            print(f"{indent}📁 archive/")
        else:
            print(f"{indent}📁 {os.path.basename(root)}/")
        
        sub_indent = ' ' * 2 * (level + 1)
        for file in files:
            print(f"{sub_indent}📄 {file}")
    
    print("\n" + "="*60)
    print("SCHEMA EXPLANATION:")
    print("="*60)
    print("Patient Documents: /patients/<PatientName_ID6chars>/<YYYY>/<MM>/")
    print("General Documents: /general_archive/<YYYY>/<MM>/")
    print("Filenames: YYYY-MM-DD_<Info>_<TypeAbbrev>-<DocID8>.<ext>")
    print("="*60)

def main():
    """Main demo function."""
    print("Enhanced TaggerAgent Filing and Naming Schema Demo")
    print("="*50)
    
    # Set up demo environment
    base_dir, dirs = setup_demo_environment()
    
    try:
        # Initialize Context Store
        context_store = ContextStore(dirs["db_path"])
        print(f"✓ Initialized Context Store: {dirs['db_path']}")
        
        # Add demo patients
        add_demo_patients(context_store)
        
        # Create demo session
        session_id = context_store.create_session(
            user_id="demo_user",
            metadata={"demo_type": "enhanced_filing"}
        )
        print(f"✓ Created demo session: {session_id}")
        
        # Create demo documents
        created_files = create_demo_documents(dirs["watch_folder"])
        print(f"✓ Created {len(created_files)} demo documents")
        
        # Initialize agents
        ingestion_agent = IngestionAgent(
            context_store=context_store,
            watch_folder=dirs["watch_folder"],
            holding_folder=dirs["holding_folder"]
        )
        
        classification_rules = {
            "Invoice": ["invoice", "bill", "payment", "amount"],
            "Medical Record": ["medical", "patient", "doctor", "treatment"],
            "Letter": ["letter", "correspondence", "regarding"]
        }
        
        classifier_agent = ClassifierAgent(
            context_store=context_store,
            classification_rules=classification_rules
        )
        
        summarizer_agent = SummarizerAgent(
            context_store=context_store,
            openai_api_key=None  # Use local summarization for demo
        )
        
        tagger_agent = TaggerAgent(
            context_store=context_store,
            base_filed_folder=dirs["archive_folder"]
        )
        
        print("\n" + "="*50)
        print("PROCESSING PIPELINE")
        print("="*50)
        
        # Step 1: Ingestion
        print("1. Processing documents with IngestionAgent...")
        for file_path, doc_info in created_files:
            try:
                document_id = ingestion_agent.process_specific_files(
                    [file_path],
                    patient_id=doc_info["patient_id"],
                    session_id=session_id
                )
                if document_id:
                    print(f"   ✓ Ingested: {doc_info['filename']}")
            except Exception as e:
                print(f"   ✗ Failed to ingest {doc_info['filename']}: {e}")
        
        # Step 2: Classification
        print("\n2. Classifying documents...")
        classified_count, _ = classifier_agent.process_documents_for_classification()
        print(f"   ✓ Classified {classified_count} documents")
        
        # Step 3: Summarization (local)
        print("\n3. Summarizing documents...")
        summarized_count, _ = summarizer_agent.process_documents_for_summarization()
        print(f"   ✓ Summarized {summarized_count} documents")
        
        # Step 4: Enhanced Tagging and Filing
        print("\n4. Filing documents with enhanced schema...")
        filed_count, failed_count = tagger_agent.process_documents_for_tagging_and_filing()
        print(f"   ✓ Filed {filed_count} documents")
        if failed_count > 0:
            print(f"   ⚠ {failed_count} documents failed to file")
        
        # Display results
        print_filing_results(dirs["archive_folder"])
        
        # Show database content
        print("\nDATABASE CONTENT:")
        print("-" * 30)
        documents = context_store.get_all_documents()
        for doc in documents:
            print(f"File: {doc['file_name']}")
            print(f"  Type: {doc.get('document_type', 'Unknown')}")
            print(f"  Patient: {doc.get('patient_id', 'None')}")
            print(f"  Status: {doc.get('processing_status', 'Unknown')}")
            print(f"  Filed Path: {doc.get('filed_path', 'Not filed')}")
            print()
        
        print(f"\nDemo completed successfully!")
        print(f"Demo environment: {base_dir}")
        print("You can explore the generated file structure and database.")
        
    except Exception as e:
        print(f"Demo failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Note: We don't clean up the temp directory so you can examine results
        print(f"\nDemo files preserved at: {base_dir}")

if __name__ == "__main__":
    main()