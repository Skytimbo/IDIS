"""
Unit tests for the ContextStore module.

These tests validate the functionality of the ContextStore class,
ensuring all database operations work correctly.
"""

import unittest
import os
import json
import sqlite3
from datetime import datetime, timedelta
import tempfile

# Import the ContextStore class from the parent directory
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from context_store import ContextStore


class TestContextStore(unittest.TestCase):
    """Test suite for the ContextStore class."""

    def setUp(self):
        """Set up a new in-memory database for each test."""
        self.db_path = ":memory:"
        self.context_store = ContextStore(self.db_path)
    
    def tearDown(self):
        """Clean up after each test."""
        if hasattr(self, 'context_store') and self.context_store:
            del self.context_store
    
    # Helper methods
    
    def create_test_patient(self):
        """Create a test patient and return the patient_id."""
        patient_data = {
            "patient_name": "Test Patient"
        }
        return self.context_store.add_patient(patient_data)
    
    def create_test_session(self):
        """Create a test session and return the session_id."""
        session_metadata = {
            "source": "test_suite",
            "purpose": "unit_testing"
        }
        return self.context_store.create_session("test_user", session_metadata)
    
    def create_test_document(self, patient_id=None, session_id=None):
        """Create a test document and return the document_id."""
        document_data = {
            "file_name": "test_document.pdf",
            "original_file_type": "pdf",
            "ingestion_status": "ingestion_successful",
            "extracted_text": "This is a test document for unit testing.",
            "document_type": "Test Document",
            "classification_confidence": "High",
            "processing_status": "new",
            "document_dates": {
                "document_date": datetime.now().strftime("%Y-%m-%d"),
                "received_date": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            },
            "issuer_source": "Test Issuer",
            "recipient": "Test Recipient",
            "tags_extracted": ["test", "document", "unit_testing"],
            "patient_id": patient_id,
            "session_id": session_id
        }
        return self.context_store.add_document(document_data)
    
    # Patient Tests
    
    def test_add_patient(self):
        """Test adding a patient."""
        patient_data = {
            "patient_name": "John Doe"
        }
        patient_id = self.context_store.add_patient(patient_data)
        
        self.assertIsNotNone(patient_id)
        self.assertTrue(len(patient_id) > 0)
    
    def test_get_patient(self):
        """Test retrieving a patient."""
        # Create a patient
        patient_data = {
            "patient_name": "Jane Smith"
        }
        patient_id = self.context_store.add_patient(patient_data)
        
        # Retrieve the patient
        patient = self.context_store.get_patient(patient_id)
        
        self.assertIsNotNone(patient)
        self.assertEqual(patient["patient_id"], patient_id)
        self.assertEqual(patient["patient_name"], "Jane Smith")
    
    def test_get_nonexistent_patient(self):
        """Test retrieving a patient that doesn't exist."""
        patient = self.context_store.get_patient("nonexistent_id")
        self.assertIsNone(patient)
    
    def test_update_patient(self):
        """Test updating a patient."""
        # Create a patient
        patient_data = {
            "patient_name": "Original Name"
        }
        patient_id = self.context_store.add_patient(patient_data)
        
        # Update the patient
        update_data = {
            "patient_name": "Updated Name"
        }
        result = self.context_store.update_patient(patient_id, update_data)
        
        # Verify update was successful
        self.assertTrue(result)
        
        # Retrieve the patient to verify the update
        patient = self.context_store.get_patient(patient_id)
        self.assertEqual(patient["patient_name"], "Updated Name")
    
    # Session Tests
    
    def test_create_session(self):
        """Test creating a session."""
        session_metadata = {
            "source": "unit_test",
            "purpose": "testing"
        }
        session_id = self.context_store.create_session("test_user", session_metadata)
        
        self.assertIsNotNone(session_id)
        self.assertTrue(len(session_id) > 0)
    
    def test_get_session(self):
        """Test retrieving a session."""
        # Create a session
        session_metadata = {
            "source": "unit_test",
            "purpose": "testing"
        }
        session_id = self.context_store.create_session("test_user", session_metadata)
        
        # Retrieve the session
        session = self.context_store.get_session(session_id)
        
        self.assertIsNotNone(session)
        self.assertEqual(session["session_id"], session_id)
        self.assertEqual(session["user_id"], "test_user")
        self.assertEqual(session["status"], "active")
        self.assertEqual(session["session_metadata"]["source"], "unit_test")
        self.assertEqual(session["session_metadata"]["purpose"], "testing")
    
    def test_update_session_status(self):
        """Test updating a session's status."""
        # Create a session
        session_id = self.context_store.create_session("test_user")
        
        # Update the session status
        result = self.context_store.update_session_status(session_id, "completed")
        
        # Verify update was successful
        self.assertTrue(result)
        
        # Retrieve the session to verify the update
        session = self.context_store.get_session(session_id)
        self.assertEqual(session["status"], "completed")
        
    def test_update_session_metadata(self):
        """Test updating a session's metadata."""
        # Create a session
        session_id = self.create_test_session()
        
        # Test adding new metadata to a session with existing metadata
        metadata_update = {'batch_summary': 'This is a test batch summary'}
        result = self.context_store.update_session_metadata(session_id, metadata_update)
        self.assertTrue(result)
        
        # Verify the update
        session = self.context_store.get_session(session_id)
        self.assertIn('batch_summary', session['session_metadata'])
        self.assertEqual(session['session_metadata']['batch_summary'], 'This is a test batch summary')
        
        # Test updating existing keys in session metadata
        metadata_update = {'batch_summary': 'Updated batch summary'}
        result = self.context_store.update_session_metadata(session_id, metadata_update)
        self.assertTrue(result)
        
        # Verify the update
        session = self.context_store.get_session(session_id)
        self.assertEqual(session['session_metadata']['batch_summary'], 'Updated batch summary')
        
        # Test adding new keys to existing session metadata
        metadata_update = {'processed_by': 'summarizer_agent_v1.0'}
        result = self.context_store.update_session_metadata(session_id, metadata_update)
        self.assertTrue(result)
        
        # Verify the update
        session = self.context_store.get_session(session_id)
        self.assertIn('batch_summary', session['session_metadata'])
        self.assertIn('processed_by', session['session_metadata'])
        self.assertEqual(session['session_metadata']['processed_by'], 'summarizer_agent_v1.0')
        
        # Test handling a non-existent session_id
        result = self.context_store.update_session_metadata('nonexistent_session', metadata_update)
        self.assertFalse(result)
    
    # Document Tests
    
    def test_add_document(self):
        """Test adding a document."""
        document_data = {
            "file_name": "test.pdf",
            "original_file_type": "pdf",
            "ingestion_status": "ingestion_successful",
            "extracted_text": "This is a test document.",
            "document_type": "Test",
            "classification_confidence": "High",
            "processing_status": "new",
            "document_dates": {
                "document_date": "2025-05-21"
            },
            "issuer_source": "Test Source",
            "recipient": "Test Recipient",
            "tags_extracted": ["test", "document"]
        }
        
        document_id = self.context_store.add_document(document_data)
        
        self.assertIsNotNone(document_id)
        self.assertTrue(len(document_id) > 0)
    
    def test_get_document(self):
        """Test retrieving a document."""
        # Create a document
        document_data = {
            "file_name": "test.pdf",
            "original_file_type": "pdf",
            "ingestion_status": "ingestion_successful",
            "document_type": "Test"
        }
        document_id = self.context_store.add_document(document_data)
        
        # Retrieve the document
        document = self.context_store.get_document(document_id)
        
        self.assertIsNotNone(document)
        self.assertEqual(document["document_id"], document_id)
        self.assertEqual(document["file_name"], "test.pdf")
        self.assertEqual(document["original_file_type"], "pdf")
        self.assertEqual(document["document_type"], "Test")
    
    def test_update_document_fields(self):
        """Test updating document fields."""
        # Create a document
        document_id = self.create_test_document()
        
        # Update document fields
        fields_to_update = {
            "document_type": "Updated Type",
            "classification_confidence": "Medium",
            "processing_status": "classified",
            "tags_extracted": ["updated", "tags"]
        }
        
        result = self.context_store.update_document_fields(document_id, fields_to_update)
        
        # Verify update was successful
        self.assertTrue(result)
        
        # Retrieve the document to verify the update
        document = self.context_store.get_document(document_id)
        self.assertEqual(document["document_type"], "Updated Type")
        self.assertEqual(document["classification_confidence"], "Medium")
        self.assertEqual(document["processing_status"], "classified")
        self.assertEqual(document["tags_extracted"], ["updated", "tags"])
    
    def test_link_document_to_session(self):
        """Test linking a document to a session."""
        # Create a document without a session
        document_id = self.create_test_document()
        
        # Create a session
        session_id = self.create_test_session()
        
        # Link the document to the session
        result = self.context_store.link_document_to_session(document_id, session_id)
        
        # Verify the link was successful
        self.assertTrue(result)
        
        # Retrieve the document to verify the link
        document = self.context_store.get_document(document_id)
        self.assertEqual(document["session_id"], session_id)
    
    def test_get_documents_for_session(self):
        """Test retrieving documents for a session."""
        # Create a session
        session_id = self.create_test_session()
        
        # Create multiple documents linked to the session
        document_id1 = self.create_test_document(session_id=session_id)
        document_id2 = self.create_test_document(session_id=session_id)
        document_id3 = self.create_test_document(session_id=session_id)
        
        # Retrieve documents for the session
        documents = self.context_store.get_documents_for_session(session_id)
        
        # Verify we got all documents
        self.assertEqual(len(documents), 3)
        document_ids = [doc["document_id"] for doc in documents]
        self.assertIn(document_id1, document_ids)
        self.assertIn(document_id2, document_ids)
        self.assertIn(document_id3, document_ids)
    
    # Agent Output Tests
    
    def test_save_agent_output(self):
        """Test saving agent output."""
        # Create a document
        document_id = self.create_test_document()
        
        # Save agent output
        agent_id = "summarizer_agent_v1.0"
        output_type = "per_document_summary"
        output_data = "This is a summary of the test document."
        confidence = 0.95
        
        output_id = self.context_store.save_agent_output(
            document_id, agent_id, output_type, output_data, confidence
        )
        
        self.assertIsNotNone(output_id)
        self.assertTrue(len(output_id) > 0)
    
    def test_get_agent_outputs_for_document(self):
        """Test retrieving agent outputs for a document."""
        # Create a document
        document_id = self.create_test_document()
        
        # Save multiple agent outputs
        self.context_store.save_agent_output(
            document_id, "summarizer_agent_v1.0", "per_document_summary", 
            "Summary 1", 0.9
        )
        self.context_store.save_agent_output(
            document_id, "summarizer_agent_v1.0", "batch_summary", 
            "Batch Summary", 0.85
        )
        self.context_store.save_agent_output(
            document_id, "classifier_agent_v1.0", "classification", 
            "Test Document", 0.8
        )
        
        # Test retrieval of all outputs for the document
        all_outputs = self.context_store.get_agent_outputs_for_document(document_id)
        self.assertEqual(len(all_outputs), 3)
        
        # Test filtering by agent_id
        summarizer_outputs = self.context_store.get_agent_outputs_for_document(
            document_id, agent_id="summarizer_agent_v1.0"
        )
        self.assertEqual(len(summarizer_outputs), 2)
        
        # Test filtering by output_type
        per_doc_summaries = self.context_store.get_agent_outputs_for_document(
            document_id, output_type="per_document_summary"
        )
        self.assertEqual(len(per_doc_summaries), 1)
        
        # Test filtering by both agent_id and output_type
        specific_outputs = self.context_store.get_agent_outputs_for_document(
            document_id, agent_id="summarizer_agent_v1.0", output_type="batch_summary"
        )
        self.assertEqual(len(specific_outputs), 1)
        self.assertEqual(specific_outputs[0]["output_data"], "Batch Summary")
    
    # Audit Log Tests
    
    def test_add_audit_log_entry(self):
        """Test adding an audit log entry."""
        # Add an audit log entry
        log_id = self.context_store.add_audit_log_entry(
            user_id="test_user",
            event_type="DATA_ACCESS",
            event_name="VIEW_DOCUMENT_TEXT",
            status="SUCCESS",
            resource_type="document",
            resource_id="test_doc_id",
            details="Viewed document text during unit test"
        )
        
        self.assertIsNotNone(log_id)
        self.assertGreater(log_id, 0)
    
    # Query Methods Tests
    
    def test_get_documents_by_processing_status(self):
        """Test retrieving documents by processing status."""
        # Create documents with different processing statuses
        patient_id = self.create_test_patient()
        session_id = self.create_test_session()
        
        # Create documents with "new" status
        doc1 = self.create_test_document(patient_id, session_id)
        self.context_store.update_document_fields(doc1, {"processing_status": "new"})
        
        doc2 = self.create_test_document(patient_id, session_id)
        self.context_store.update_document_fields(doc2, {"processing_status": "new"})
        
        # Create a document with "classified" status
        doc3 = self.create_test_document(patient_id, session_id)
        self.context_store.update_document_fields(doc3, {"processing_status": "classified"})
        
        # Get documents with "new" status
        new_docs = self.context_store.get_documents_by_processing_status("new")
        
        # Check that we got the right documents
        self.assertEqual(len(new_docs), 2)
        doc_ids = [doc["document_id"] for doc in new_docs]
        self.assertIn(doc1, doc_ids)
        self.assertIn(doc2, doc_ids)
        
        # Check that the documents have the required fields
        for doc in new_docs:
            self.assertIn("document_id", doc)
            self.assertIn("extracted_text", doc)
            self.assertIn("file_name", doc)
            self.assertIn("patient_id", doc)
            self.assertIn("session_id", doc)
        
        # Get documents with "classified" status
        classified_docs = self.context_store.get_documents_by_processing_status("classified")
        self.assertEqual(len(classified_docs), 1)
        self.assertEqual(classified_docs[0]["document_id"], doc3)
        
        # Test the limit parameter
        limited_docs = self.context_store.get_documents_by_processing_status("new", limit=1)
        self.assertEqual(len(limited_docs), 1)
        
        # Test status with no documents
        no_docs = self.context_store.get_documents_by_processing_status("nonexistent_status")
        self.assertEqual(len(no_docs), 0)
    
    def test_query_patient_history(self):
        """Test querying patient history."""
        # Create a patient
        patient_id = self.create_test_patient()
        
        # Create multiple documents for the patient
        self.create_test_document(patient_id=patient_id)
        self.create_test_document(patient_id=patient_id)
        self.create_test_document(patient_id=patient_id)
        
        # Query patient history
        history = self.context_store.query_patient_history(patient_id)
        
        # Verify history
        self.assertEqual(len(history), 3)
        for doc in history:
            self.assertIn("document_id", doc)
            self.assertIn("file_name", doc)
            self.assertIn("document_type", doc)
            self.assertIn("processing_status", doc)
            self.assertIn("upload_timestamp", doc)
    
    # Edge Cases and Error Handling Tests
    
    def test_get_nonexistent_document(self):
        """Test retrieving a document that doesn't exist."""
        document = self.context_store.get_document("nonexistent_id")
        self.assertIsNone(document)
    
    def test_update_nonexistent_document(self):
        """Test updating a document that doesn't exist."""
        result = self.context_store.update_document_fields(
            "nonexistent_id", 
            {"document_type": "Updated Type"}
        )
        self.assertFalse(result)
    
    def test_persistence_with_file_db(self):
        """Test database persistence using a temporary file."""
        # Create a temporary file
        temp_db = tempfile.NamedTemporaryFile(delete=False)
        temp_db_path = temp_db.name
        temp_db.close()
        
        try:
            # Create a context store with the temp file
            file_context_store = ContextStore(temp_db_path)
            
            # Add a patient
            patient_data = {"patient_name": "Persistence Test"}
            patient_id = file_context_store.add_patient(patient_data)
            
            # Close the context store
            del file_context_store
            
            # Create a new context store with the same file
            new_context_store = ContextStore(temp_db_path)
            
            # Retrieve the patient
            patient = new_context_store.get_patient(patient_id)
            
            # Verify the patient still exists
            self.assertIsNotNone(patient)
            self.assertEqual(patient["patient_name"], "Persistence Test")
            
            # Clean up
            del new_context_store
        finally:
            # Remove the temporary file
            if os.path.exists(temp_db_path):
                os.unlink(temp_db_path)
    
    def test_json_serialization_deserialization(self):
        """Test JSON serialization and deserialization."""
        # Create a document with complex JSON fields
        complex_data = {
            "file_name": "complex.pdf",
            "original_file_type": "pdf",
            "ingestion_status": "ingestion_successful",
            "document_dates": {
                "invoice_date": "2025-05-21",
                "due_date": "2025-06-21",
                "service_dates": ["2025-04-01", "2025-04-15", "2025-04-30"]
            },
            "tags_extracted": ["important", "finance", "needs_review", "urgent"]
        }
        
        # Add the document
        document_id = self.context_store.add_document(complex_data)
        
        # Retrieve the document
        document = self.context_store.get_document(document_id)
        
        # Verify JSON fields were properly serialized and deserialized
        self.assertEqual(document["document_dates"]["invoice_date"], "2025-05-21")
        self.assertEqual(document["document_dates"]["due_date"], "2025-06-21")
        self.assertEqual(len(document["document_dates"]["service_dates"]), 3)
        self.assertEqual(document["tags_extracted"], ["important", "finance", "needs_review", "urgent"])


if __name__ == "__main__":
    unittest.main()
