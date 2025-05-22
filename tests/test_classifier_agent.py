"""
Unit tests for the ClassifierAgent module.

These tests validate the functionality of the ClassifierAgent class,
ensuring document classification and context store updates work correctly.
"""

import unittest
from unittest.mock import MagicMock, patch
import os
import sys

# Import from parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from classifier_agent import ClassifierAgent
from context_store import ContextStore


class TestClassifierAgent(unittest.TestCase):
    """Test suite for the ClassifierAgent class."""
    
    def setUp(self):
        """Set up test environment before each test."""
        # Create mock ContextStore
        self.mock_context_store = MagicMock(spec=ContextStore)
        
        # Define sample classification rules
        self.classification_rules = {
            "Invoice": ["invoice #", "bill to:", "total due"],
            "Medical Record": ["patient name:", "diagnosis:", "treatment plan"],
            "Letter": ["dear sir", "dear madam", "sincerely,"],
            "Receipt": ["receipt #", "payment method", "amount paid"],
            "Insurance Document": ["policy number", "coverage", "premium"],
            "Legal Document": ["legal notice", "court", "attorney"],
            "Report": ["findings", "analysis", "conclusion"]
        }
        
        # Create ClassifierAgent with mock ContextStore
        self.agent = ClassifierAgent(
            self.mock_context_store,
            self.classification_rules
        )
        
        # Configure mock ContextStore behavior
        self.mock_context_store.update_document_fields.return_value = True
        self.mock_context_store.add_audit_log_entry.return_value = 1
    
    def test_classify_invoice_document(self):
        """Test classification of a document matching 'Invoice' rules."""
        # Prepare mock document data
        invoice_text = "Invoice #12345\nBill to: ACME Corp\nDate: 2025-05-21\nTotal Due: $1,234.56"
        mock_documents = [{
            "document_id": "test_invoice_id",
            "extracted_text": invoice_text,
            "file_name": "invoice.pdf"
        }]
        self.mock_context_store.get_documents_by_processing_status.return_value = mock_documents
        
        # Run classification
        success_count, fail_count = self.agent.process_documents_for_classification(
            status_to_classify="ingested",
            new_status_after_classification="classified"
        )
        
        # Check results
        self.assertEqual(success_count, 1)
        self.assertEqual(fail_count, 0)
        
        # Verify ContextStore methods were called correctly
        self.mock_context_store.get_documents_by_processing_status.assert_called_with(
            processing_status="ingested"
        )
        self.mock_context_store.update_document_fields.assert_called_with(
            "test_invoice_id",
            {
                "document_type": "Invoice",
                "classification_confidence": "Medium",
                "processing_status": "classified"
            }
        )
        self.mock_context_store.add_audit_log_entry.assert_called()
    
    def test_classify_medical_record_document(self):
        """Test classification of a document matching 'Medical Record' rules."""
        # Prepare mock document data
        medical_text = "Patient Name: John Doe\nDiagnosis: Hypertension\nTreatment Plan: Diet and exercise"
        mock_documents = [{
            "document_id": "test_medical_id",
            "extracted_text": medical_text,
            "file_name": "medical_record.pdf"
        }]
        self.mock_context_store.get_documents_by_processing_status.return_value = mock_documents
        
        # Run classification
        success_count, fail_count = self.agent.process_documents_for_classification()
        
        # Check results
        self.assertEqual(success_count, 1)
        self.assertEqual(fail_count, 0)
        
        # Verify ContextStore methods were called correctly
        self.mock_context_store.update_document_fields.assert_called_with(
            "test_medical_id",
            {
                "document_type": "Medical Record",
                "classification_confidence": "Medium",
                "processing_status": "classified"
            }
        )
    
    def test_classify_unmatched_document(self):
        """Test classification of a document that doesn't match any rules."""
        # Prepare mock document data
        unknown_text = "This text doesn't match any of the defined rules."
        mock_documents = [{
            "document_id": "test_unknown_id",
            "extracted_text": unknown_text,
            "file_name": "unknown.pdf"
        }]
        self.mock_context_store.get_documents_by_processing_status.return_value = mock_documents
        
        # Run classification
        success_count, fail_count = self.agent.process_documents_for_classification()
        
        # Check results
        self.assertEqual(success_count, 0)
        self.assertEqual(fail_count, 1)
        
        # Verify ContextStore methods were called correctly
        self.mock_context_store.update_document_fields.assert_called_with(
            "test_unknown_id",
            {
                "document_type": "Unclassified",
                "classification_confidence": None,
                "processing_status": "classified"
            }
        )
    
    def test_classify_empty_text_document(self):
        """Test classification of a document with empty or None text."""
        # Prepare mock document data - one with empty text, one with None
        mock_documents = [
            {
                "document_id": "test_empty_id",
                "extracted_text": "",
                "file_name": "empty.pdf"
            },
            {
                "document_id": "test_none_id",
                "extracted_text": None,
                "file_name": "none.pdf"
            }
        ]
        self.mock_context_store.get_documents_by_processing_status.return_value = mock_documents
        
        # Run classification
        success_count, fail_count = self.agent.process_documents_for_classification()
        
        # Check results
        self.assertEqual(success_count, 0)
        self.assertEqual(fail_count, 2)
        
        # Verify ContextStore methods were called correctly - should be called twice
        self.assertEqual(self.mock_context_store.update_document_fields.call_count, 2)
        self.mock_context_store.update_document_fields.assert_any_call(
            "test_empty_id",
            {
                "document_type": "Unclassified",
                "classification_confidence": None,
                "processing_status": "classified"
            }
        )
    
    def test_process_multiple_documents(self):
        """Test processing multiple documents with different classifications."""
        # Prepare mock document data with various types
        mock_documents = [
            {
                "document_id": "test_invoice_id",
                "extracted_text": "Invoice #12345\nBill to: ACME Corp\nTotal Due: $1,234.56",
                "file_name": "invoice.pdf"
            },
            {
                "document_id": "test_letter_id",
                "extracted_text": "Dear Sir,\nI am writing to inform you...\nSincerely,\nJohn Doe",
                "file_name": "letter.pdf"
            },
            {
                "document_id": "test_unknown_id",
                "extracted_text": "Random text that doesn't match any rules",
                "file_name": "unknown.pdf"
            }
        ]
        self.mock_context_store.get_documents_by_processing_status.return_value = mock_documents
        
        # Run classification
        success_count, fail_count = self.agent.process_documents_for_classification()
        
        # Check results
        self.assertEqual(success_count, 2)  # Invoice and Letter
        self.assertEqual(fail_count, 1)     # Unknown
        
        # Verify ContextStore methods were called the right number of times
        self.assertEqual(self.mock_context_store.update_document_fields.call_count, 3)
        self.assertEqual(self.mock_context_store.add_audit_log_entry.call_count, 3)
    
    def test_no_documents_to_classify(self):
        """Test behavior when no documents need classification."""
        # Return empty list from get_documents_by_processing_status
        self.mock_context_store.get_documents_by_processing_status.return_value = []
        
        # Run classification
        success_count, fail_count = self.agent.process_documents_for_classification()
        
        # Check results
        self.assertEqual(success_count, 0)
        self.assertEqual(fail_count, 0)
        
        # Verify ContextStore methods were called correctly
        self.mock_context_store.get_documents_by_processing_status.assert_called_once()
        self.mock_context_store.update_document_fields.assert_not_called()
        self.mock_context_store.add_audit_log_entry.assert_not_called()


if __name__ == '__main__':
    unittest.main()