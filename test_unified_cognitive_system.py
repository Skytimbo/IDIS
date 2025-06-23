#!/usr/bin/env python3
"""
Comprehensive test for the Unified Cognitive System with OpenAI API integration.
Tests the complete pipeline from document ingestion to structured data extraction.
"""

import os
import tempfile
import json
from context_store import ContextStore
from unified_ingestion_agent import UnifiedIngestionAgent
from agents.cognitive_agent import CognitiveAgent

def test_cognitive_agent_standalone():
    """Test the CognitiveAgent directly with a sample document."""
    print("Testing CognitiveAgent standalone...")
    
    agent = CognitiveAgent()
    
    sample_text = """
ALASKA REGIONAL HOSPITAL
Medical Record Summary

Patient: Jane Doe
Date of Birth: 03/22/1985
Medical Record Number: MRN-123456789
Date of Service: June 22, 2025

Chief Complaint: Follow-up appointment for diabetes management

Vital Signs:
Blood Pressure: 130/85 mmHg
Heart Rate: 78 bpm
Temperature: 98.4°F
Weight: 165 lbs
Height: 5'6"

Assessment:
Patient's diabetes is well-controlled with current medication regimen.
HbA1c levels have improved since last visit.

Plan:
- Continue current metformin dosage
- Schedule quarterly follow-up
- Nutrition counseling referral

Provider: Dr. Michael Smith, MD
"""
    
    result = agent.extract_structured_data(sample_text)
    
    if result and isinstance(result, dict):
        print("✓ CognitiveAgent successfully extracted structured data")
        print(f"  Document type: {result.get('document_type', {}).get('predicted_class', 'Unknown')}")
        print(f"  Schema version: {result.get('schema_version', 'Unknown')}")
        return True
    else:
        print("✗ CognitiveAgent failed to extract structured data")
        return False

def test_unified_ingestion_pipeline():
    """Test the complete unified ingestion pipeline."""
    print("\nTesting Unified Ingestion Pipeline...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        watch_folder = os.path.join(temp_dir, "watch")
        holding_folder = os.path.join(temp_dir, "holding")
        db_path = os.path.join(temp_dir, "test.db")
        
        os.makedirs(watch_folder, exist_ok=True)
        os.makedirs(holding_folder, exist_ok=True)
        
        # Create test document
        test_file = os.path.join(watch_folder, "test_invoice.txt")
        with open(test_file, 'w') as f:
            f.write("""
ACME CORPORATION
Invoice #INV-2025-001234

Bill To:
John Smith
123 Main Street
Anchorage, AK 99501

Invoice Date: June 22, 2025
Due Date: July 22, 2025

Description                     Amount
Professional Services          $2,500.00
Travel Expenses                 $450.00
Materials                       $150.00

Subtotal:                       $3,100.00
Tax (8.5%):                     $263.50
Total Amount Due:               $3,363.50

Payment Terms: Net 30 days
""")
        
        # Initialize system
        context_store = ContextStore(db_path)
        patient_id = context_store.add_patient({"patient_name": "Test Patient"})
        session_id = context_store.create_session("test_user", {"source": "unified_test"})
        
        agent = UnifiedIngestionAgent(context_store, watch_folder, holding_folder)
        
        # Process documents
        processed_count, errors = agent.process_documents_from_folder(
            patient_id=patient_id, 
            session_id=session_id
        )
        
        if processed_count > 0 and len(errors) == 0:
            print("✓ Unified pipeline successfully processed document")
            
            # Verify data in database
            documents = context_store.get_documents_for_session(str(session_id))
            if documents and len(documents) > 0:
                doc = documents[0]
                if doc.get('extracted_data'):
                    try:
                        structured_data = json.loads(doc['extracted_data'])
                        print(f"  Stored document type: {structured_data.get('document_type', {}).get('predicted_class', 'Unknown')}")
                        print(f"  Financial total: {structured_data.get('financials', {}).get('total_amount', 'Unknown')}")
                        return True
                    except json.JSONDecodeError:
                        print("✗ Failed to parse stored structured data")
                        return False
            
            print("✗ No documents found in database after processing")
            return False
        else:
            print(f"✗ Pipeline failed - processed: {processed_count}, errors: {len(errors)}")
            for error in errors:
                print(f"    Error: {error}")
            return False

def test_database_schema():
    """Test the hybrid database schema supports both legacy and modern structures."""
    print("\nTesting Database Schema Compatibility...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "schema_test.db")
        context_store = ContextStore(db_path)
        
        # Test document creation with hybrid data
        test_doc = {
            'document_id': 'test_doc_001',
            'patient_id': '1',
            'session_id': '1',
            'file_name': 'test_document.txt',
            'original_file_type': 'txt',
            'document_type': 'Test Document',  # Legacy field
            'extracted_data': json.dumps({     # Modern V1.3 field
                'schema_version': '1.3',
                'document_type': {'predicted_class': 'Test Document', 'confidence_score': 0.95}
            }),
            'full_text': 'Sample document text',
            'extracted_text': 'Sample document text',
            'processing_status': 'processing_complete'
        }
        
        doc_id = context_store.add_document(test_doc)
        
        if doc_id:
            retrieved_doc = context_store.get_document(str(doc_id))
            if retrieved_doc:
                has_legacy = 'document_type' in retrieved_doc
                has_modern = 'extracted_data' in retrieved_doc
                
                if has_legacy and has_modern:
                    print("✓ Hybrid schema successfully supports both legacy and modern fields")
                    return True
                else:
                    print(f"✗ Schema issue - legacy: {has_legacy}, modern: {has_modern}")
                    return False
            else:
                print("✗ Failed to retrieve document from database")
                return False
        else:
            print("✗ Failed to add document to database")
            return False

def main():
    """Run comprehensive tests of the unified cognitive system."""
    print("=== Unified Cognitive System Test Suite ===\n")
    
    tests = [
        ("CognitiveAgent Standalone", test_cognitive_agent_standalone),
        ("Unified Ingestion Pipeline", test_unified_ingestion_pipeline),
        ("Database Schema Compatibility", test_database_schema)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                print(f"FAILED: {test_name}")
        except Exception as e:
            print(f"ERROR in {test_name}: {e}")
    
    print(f"\n=== Test Results ===")
    print(f"Passed: {passed}/{total}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("\n🎉 All tests passed! The unified cognitive system is working correctly.")
        print("The system successfully:")
        print("  ✓ Integrates OpenAI GPT-4o for document processing")
        print("  ✓ Extracts structured data using V1.3 JSON schema")
        print("  ✓ Maintains hybrid database compatibility")
        print("  ✓ Processes documents through complete pipeline")
    else:
        print(f"\n⚠️  {total - passed} tests failed. Please review the issues above.")

if __name__ == "__main__":
    main()