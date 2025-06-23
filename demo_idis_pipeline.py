#!/usr/bin/env python3
"""
IDIS Pipeline Demo with V1 HITL Workflow
Demonstrates the complete Intelligent Document Insight System pipeline including
Human-in-the-Loop functionality for ambiguous document categorization.
"""

import os
import sys
import argparse
import tempfile
import shutil
import json
import logging
from typing import List, Dict, Any
from pathlib import Path

# Import IDIS components
from context_store import ContextStore
from unified_ingestion_agent import UnifiedIngestionAgent
from cover_sheet import SmartCoverSheetRenderer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_demo_documents(demo_folder: str) -> List[str]:
    """Create sample documents for testing the IDIS pipeline with HITL scenarios."""
    watch_folder = os.path.join(demo_folder, "watch")
    os.makedirs(watch_folder, exist_ok=True)
    
    # Document 1: Clear medical record (should auto-categorize)
    medical_doc = """PATIENT MEDICAL RECORD
    
Patient Name: John Smith
Date of Birth: 1985-03-15
Patient ID: MR-12345
Date of Visit: 2025-06-23

CHIEF COMPLAINT:
Patient presents with persistent cough and fatigue lasting 2 weeks.

VITAL SIGNS:
Temperature: 98.6°F
Blood Pressure: 120/80 mmHg
Heart Rate: 72 bpm
Respiratory Rate: 16/min

ASSESSMENT:
Upper respiratory infection, likely viral etiology.

PLAN:
1. Rest and increased fluid intake
2. Over-the-counter cough suppressant
3. Follow-up in 1 week if symptoms persist

Provider: Dr. Sarah Johnson, MD
Date: 2025-06-23
"""
    
    # Document 2: Clear invoice (should auto-categorize)
    invoice_doc = """INVOICE

Invoice Number: INV-2025-001
Date: 2025-06-23
Due Date: 2025-07-23

Bill To:
ABC Medical Supplies
123 Healthcare Blvd
Medical City, MC 12345

From:
XYZ Equipment Corp
456 Supply Street
Equipment Town, ET 67890

ITEMS:
- Medical Examination Table x2 @ $1,200.00 each: $2,400.00
- Digital Thermometer x10 @ $45.00 each: $450.00
- Disposable Gloves (100 boxes) @ $12.00 each: $1,200.00

Subtotal: $4,050.00
Tax (8.5%): $344.25
Total: $4,394.25

Payment Terms: Net 30 days
"""
    
    # Document 3: Ambiguous document (should trigger HITL)
    ambiguous_doc = """COMMUNICATION RECORD

Date: 2025-06-23
Reference: CR-2025-001

SUBJECT: Equipment Maintenance Schedule

Dear Facilities Team,

Please be advised that the following equipment requires scheduled maintenance:

1. MRI Scanner Unit A - Due for quarterly calibration
2. X-Ray Machine Room 3 - Annual safety inspection required
3. Ultrasound Equipment - Software update pending

The maintenance window has been scheduled for next weekend.
Please coordinate with the IT department for system downtime.

Contact: maintenance@hospital.com
Priority: Standard

Best regards,
Equipment Management Team
"""
    
    documents = [
        ("medical_record_001.txt", medical_doc),
        ("invoice_001.txt", invoice_doc),
        ("maintenance_notice_001.txt", ambiguous_doc)
    ]
    
    created_files = []
    for filename, content in documents:
        file_path = os.path.join(watch_folder, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        created_files.append(file_path)
        logger.info(f"Created demo document: {filename}")
    
    return created_files

def demonstrate_hitl_workflow(context_store: ContextStore) -> List[Dict[str, Any]]:
    """Demonstrate the Human-in-the-Loop workflow for documents requiring manual review."""
    logger.info("Checking for documents requiring HITL review...")
    
    # Get documents with pending categorization status
    pending_docs = context_store.get_documents_by_processing_status('pending_categorization')
    
    if not pending_docs:
        logger.info("No documents require HITL review at this time.")
        return []
    
    hitl_results = []
    for doc in pending_docs:
        logger.info(f"Processing HITL review for document: {doc.get('file_name', 'Unknown')}")
        
        # Simulate human review decision
        # In a real implementation, this would be done through the UI
        document_id = doc.get('id') or doc.get('document_id')
        
        # For demo purposes, categorize the maintenance notice as "Administrative"
        if 'maintenance' in doc.get('file_name', '').lower():
            entity_data = {
                "entity_type": "administrative_document",
                "entity_name": "Equipment Maintenance Notice",
                "confidence_score": 0.95,
                "review_notes": "Categorized as administrative document via HITL review",
                "reviewer": "demo_user",
                "review_timestamp": "2025-06-23T00:00:00Z"
            }
            
            # Update document categorization
            if document_id:
                success = context_store.update_document_categorization(
                    int(document_id), 
                    json.dumps(entity_data)
                )
            
            if success:
                logger.info(f"Successfully completed HITL review for document {document_id}")
                hitl_results.append({
                    'document_id': document_id,
                    'filename': doc.get('file_name', 'Unknown'),
                    'categorization': entity_data,
                    'status': 'completed'
                })
            else:
                logger.error(f"Failed to complete HITL review for document {document_id}")
                hitl_results.append({
                    'document_id': document_id,
                    'filename': doc.get('file_name', 'Unknown'),
                    'status': 'failed'
                })
    
    return hitl_results

def generate_demo_report(context_store: ContextStore, output_pdf: str = None) -> str:
    """Generate a comprehensive report of the demo results."""
    logger.info("Generating demo report...")
    
    # Get all processed documents
    all_docs = []
    for status in ['processed', 'complete', 'pending_categorization']:
        docs = context_store.get_documents_by_processing_status(status)
        if docs:
            all_docs.extend(docs)
    
    if not all_docs:
        logger.warning("No documents found for report generation")
        return "No documents processed during demo."
    
    # Use SmartCoverSheetRenderer to generate PDF report
    if output_pdf and all_docs:
        try:
            renderer = SmartCoverSheetRenderer(context_store)
            document_ids = [str(doc['id']) for doc in all_docs]
            
            success = renderer.generate_cover_sheet(
                document_ids=document_ids,
                output_pdf=output_pdf,
                title="IDIS Pipeline Demo Report",
                subtitle="V1 HITL Workflow Demonstration"
            )
            
            if success:
                logger.info(f"Demo report generated: {output_pdf}")
                return f"Demo report successfully generated: {output_pdf}"
            else:
                logger.error("Failed to generate PDF report")
                return "PDF generation failed, but demo completed successfully."
        except Exception as e:
            logger.error(f"Error generating PDF report: {e}")
            return f"PDF generation error: {e}, but demo completed successfully."
    
    return "Demo completed successfully. Use --output-pdf to generate a PDF report."

def main():
    """Main demo function demonstrating the complete IDIS pipeline with HITL workflow."""
    parser = argparse.ArgumentParser(description='IDIS Pipeline Demo with V1 HITL Workflow')
    parser.add_argument('--clean', action='store_true', help='Clean up temporary files after demo')
    parser.add_argument('--openai', action='store_true', help='Use OpenAI API for cognitive processing')
    parser.add_argument('--output-pdf', type=str, help='Generate PDF report at specified path')
    parser.add_argument('--db-path', type=str, default='./demo_idis_pipeline.db', 
                       help='Database path for demo')
    
    args = parser.parse_args()
    
    if args.openai and not os.getenv('OPENAI_API_KEY'):
        logger.error("OpenAI API key not found. Please set OPENAI_API_KEY environment variable.")
        sys.exit(1)
    
    # Create temporary demo environment
    demo_folder = tempfile.mkdtemp(prefix='idis_pipeline_demo_')
    logger.info(f"Created demo environment: {demo_folder}")
    
    try:
        # Initialize Context Store
        logger.info("Initializing Context Store...")
        context_store = ContextStore(args.db_path)
        
        # Create patient and session for demo
        patient_id = context_store.add_patient({
            'patient_name': 'Demo Patient',
            'patient_metadata': json.dumps({
                'demo': True,
                'created_for': 'IDIS Pipeline Demo with HITL'
            })
        })
        
        session_id = context_store.create_session(
            user_id='demo_user',
            session_metadata={
                'demo_type': 'IDIS Pipeline with HITL',
                'openai_enabled': args.openai
            }
        )
        
        logger.info(f"Created demo patient (ID: {patient_id}) and session (ID: {session_id})")
        
        # Create demo documents
        logger.info("Creating demo documents...")
        demo_files = create_demo_documents(demo_folder)
        
        # Initialize UnifiedIngestionAgent
        watch_folder = os.path.join(demo_folder, "watch")
        holding_folder = os.path.join(demo_folder, "holding")
        os.makedirs(holding_folder, exist_ok=True)
        
        logger.info("Initializing Unified Ingestion Agent...")
        ingestion_agent = UnifiedIngestionAgent(
            context_store=context_store,
            watch_folder=watch_folder,
            holding_folder=holding_folder
        )
        
        # Process documents through unified pipeline
        logger.info("Processing documents through unified cognitive pipeline...")
        processed_count, errors = ingestion_agent.process_documents_from_folder(
            patient_id=patient_id,
            session_id=session_id
        )
        
        logger.info(f"Processed {processed_count} documents successfully")
        if errors:
            logger.warning(f"Encountered {len(errors)} errors during processing")
            for error in errors:
                logger.warning(f"  - {error}")
        
        # Demonstrate HITL workflow
        logger.info("Demonstrating Human-in-the-Loop workflow...")
        hitl_results = demonstrate_hitl_workflow(context_store)
        
        if hitl_results:
            logger.info(f"Completed HITL review for {len(hitl_results)} documents")
            for result in hitl_results:
                logger.info(f"  - {result['filename']}: {result['status']}")
        
        # Generate report
        report_result = generate_demo_report(context_store, args.output_pdf)
        logger.info(report_result)
        
        # Demo summary
        print("\n" + "="*60)
        print("IDIS PIPELINE DEMO WITH V1 HITL WORKFLOW - SUMMARY")
        print("="*60)
        print(f"Demo Environment: {demo_folder}")
        print(f"Database Path: {args.db_path}")
        print(f"Documents Processed: {processed_count}")
        print(f"HITL Reviews Completed: {len(hitl_results)}")
        print(f"OpenAI API Used: {'Yes' if args.openai else 'No'}")
        if args.output_pdf:
            print(f"PDF Report: {args.output_pdf}")
        print("="*60)
        print("Demo completed successfully!")
        
        return True
        
    except Exception as e:
        logger.error(f"Demo failed with error: {e}")
        return False
        
    finally:
        # Cleanup
        if args.clean:
            try:
                shutil.rmtree(demo_folder)
                logger.info(f"Cleaned up demo environment: {demo_folder}")
            except Exception as e:
                logger.warning(f"Failed to clean up demo environment: {e}")

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)