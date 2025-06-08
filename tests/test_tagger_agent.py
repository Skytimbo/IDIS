"""
Unit tests for the TaggerAgent module.

Tests the functionality of document tagging, filing, and metadata extraction.
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import json
import tempfile
import os
import shutil

import sys
sys.path.append('..')

from tagger_agent import TaggerAgent
from context_store import ContextStore


class TestTaggerAgent(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a mock ContextStore
        self.mock_context_store = Mock(spec=ContextStore)
        
        # Mock base filed folder path - use unique path per test to avoid conflicts
        import time
        self.test_base_filed_folder = f"/tmp/test_archive_{int(time.time() * 1000000)}"
        
        # Initialize TaggerAgent with mocked dependencies
        self.agent = TaggerAgent(
            context_store=self.mock_context_store,
            base_filed_folder=self.test_base_filed_folder
        )
        
        # Configure mock ContextStore behavior
        self.mock_context_store.update_document_fields.return_value = True
        self.mock_context_store.add_audit_log_entry.return_value = 1
    
    @patch('tagger_agent.os.remove')
    @patch('tagger_agent.shutil.copy2')
    @patch('tagger_agent.os.path.getsize', return_value=1024)
    @patch('tagger_agent.os.path.exists')
    @patch('tagger_agent.os.path.isfile', return_value=True)
    @patch('tagger_agent.os.makedirs')
    def test_date_extraction(self, mock_makedirs, mock_isfile, mock_exists, mock_getsize, mock_copy2, mock_remove):
        """Test extraction of various date formats."""
        # Text with different date formats
        text_with_dates = """
        Invoice Date: January 15, 2023
        Due Date: February 28, 2023
        Letter sent on March 5, 2023
        Report completed: 04-10-2023
        """
        
        # Mock a document with this text
        mock_document = {
            "document_id": "test_doc_id",
            "extracted_text": text_with_dates,
            "file_name": "test_document.pdf",
            "original_watchfolder_path": "/tmp/test_document.pdf",
            "processing_status": "summarized"
        }
        self.mock_context_store.get_documents_by_processing_status.return_value = [mock_document]
        
        # Run tagging and filing
        result = self.agent.process_documents_for_tagging_and_filing()
        
        # Check results
        self.assertEqual(result[0], 1)  # One document successfully processed
        
        # Verify dates were extracted correctly
        update_calls = self.mock_context_store.update_document_fields.call_args_list
        self.assertEqual(len(update_calls), 1)
        
        # Check the dates in the update data
        update_data = update_calls[0][0][1]  # args[0][1] = second argument of first call
        document_dates = json.loads(update_data["document_dates"])
        
        # Verify specific dates were extracted
        self.assertIn("invoice_date", document_dates)
        self.assertEqual(document_dates["invoice_date"], "2023-01-15")
        
        # Check that at least one date was extracted from the text that contains "due date"
        date_keys = document_dates.keys()
        due_date_found = False
        for key in date_keys:
            if "due" in key.lower() and document_dates[key] in ["2023-02-28", "2023-03-05"]:
                due_date_found = True
                break
        
        self.assertTrue(due_date_found, "No due date was extracted from the text")
    
    @patch('tagger_agent.os.remove')
    @patch('tagger_agent.shutil.copy2')
    @patch('tagger_agent.os.path.getsize', return_value=1024)
    @patch('tagger_agent.os.path.exists', return_value=True)
    @patch('tagger_agent.os.path.isfile', return_value=True)
    @patch('tagger_agent.os.makedirs')
    def test_issuer_extraction(self, mock_makedirs, mock_isfile, mock_exists, mock_getsize, mock_copy2, mock_remove):
        """Test extraction of document issuer."""
        # Text with issuer information
        text_with_issuer = """
        ACME Corporation
        123 Main Street, Anytown, USA
        
        Invoice #12345
        
        From: ACME Billing Department
        To: XYZ Customer
        
        Invoice Date: January 15, 2023
        """
        
        # Mock a document with this text
        mock_document = {
            "document_id": "test_doc_id",
            "extracted_text": text_with_issuer,
            "file_name": "test_document.pdf",
            "original_watchfolder_path": "/tmp/test_document.pdf",
            "processing_status": "summarized"
        }
        self.mock_context_store.get_documents_by_processing_status.return_value = [mock_document]
        
        # Run tagging and filing
        result = self.agent.process_documents_for_tagging_and_filing()
        
        # Check results
        self.assertEqual(result[0], 1)  # One document successfully processed
        
        # Verify issuer was extracted correctly
        update_calls = self.mock_context_store.update_document_fields.call_args_list
        update_data = update_calls[0][0][1]
        
        self.assertIn("issuer_source", update_data)
        self.assertIn("ACME", update_data["issuer_source"])
    
    @patch('tagger_agent.os.remove')
    @patch('tagger_agent.shutil.copy2')
    @patch('tagger_agent.os.path.getsize', return_value=1024)
    @patch('tagger_agent.os.path.exists', return_value=True)
    @patch('tagger_agent.os.path.isfile', return_value=True)
    @patch('tagger_agent.os.makedirs')
    def test_recipient_extraction(self, mock_makedirs, mock_isfile, mock_exists, mock_getsize, mock_copy2, mock_remove):
        """Test extraction of document recipient."""
        # Text with recipient information
        text_with_recipient = """
        ACME Corporation
        123 Main Street, Anytown, USA
        
        To: John Doe
        123 Client Street
        Client City, CS 12345
        
        Dear Mr. Doe,
        
        This letter is to inform you...
        """
        
        # Mock a document with this text
        mock_document = {
            "document_id": "test_doc_id",
            "extracted_text": text_with_recipient,
            "file_name": "test_document.pdf",
            "original_watchfolder_path": "/tmp/test_document.pdf",
            "processing_status": "summarized"
        }
        self.mock_context_store.get_documents_by_processing_status.return_value = [mock_document]
        
        # Run tagging and filing
        result = self.agent.process_documents_for_tagging_and_filing()
        
        # Check results
        self.assertEqual(result[0], 1)  # One document successfully processed
        
        # Verify recipient was extracted correctly
        update_calls = self.mock_context_store.update_document_fields.call_args_list
        update_data = update_calls[0][0][1]
        
        self.assertIn("recipient", update_data)
        self.assertIn("John Doe", update_data["recipient"])
    
    @patch('tagger_agent.os.remove')
    @patch('tagger_agent.shutil.copy2')
    @patch('tagger_agent.os.path.getsize', return_value=1024)
    @patch('tagger_agent.os.path.exists', return_value=True)
    @patch('tagger_agent.os.path.isfile', return_value=True)
    @patch('tagger_agent.os.makedirs')
    def test_tag_extraction(self, mock_makedirs, mock_isfile, mock_exists, mock_getsize, mock_copy2, mock_remove):
        """Test extraction of predefined tags."""
        # Text with tag keywords
        text_with_tags = """
        CONFIDENTIAL - For Internal Use Only
        
        URGENT: Response Required by April 15, 2023
        
        This document contains important information about your account.
        """
        
        # Mock a document with this text
        mock_document = {
            "document_id": "test_doc_id",
            "extracted_text": text_with_tags,
            "file_name": "test_document.pdf",
            "original_watchfolder_path": "/tmp/test_document.pdf",
            "processing_status": "summarized"
        }
        self.mock_context_store.get_documents_by_processing_status.return_value = [mock_document]
        
        # Run tagging and filing
        result = self.agent.process_documents_for_tagging_and_filing()
        
        # Check results
        self.assertEqual(result[0], 1)  # One document successfully processed
        
        # Verify tags were extracted correctly
        update_calls = self.mock_context_store.update_document_fields.call_args_list
        update_data = update_calls[0][0][1]
        
        self.assertIn("tags_extracted", update_data)
        tags = json.loads(update_data["tags_extracted"])
        
        # Check for presence of expected tags
        self.assertIn("CONFIDENTIAL", tags)
        self.assertIn("URGENT", tags)
    
    @patch('tagger_agent.os.remove')
    @patch('tagger_agent.shutil.copy2')
    @patch('tagger_agent.os.path.getsize', return_value=1024)
    @patch('tagger_agent.os.path.exists', return_value=True)
    @patch('tagger_agent.os.path.isfile', return_value=True)
    @patch('tagger_agent.os.makedirs')
    def test_filing_with_patient_id(self, mock_makedirs, mock_isfile, mock_exists, mock_getsize, mock_copy2, mock_remove):
        """Test filing documents with patient ID using enhanced schema."""
        # Text with patient information
        text_with_patient = """
        Patient: Jane Smith
        DOB: 01/15/1985
        Patient ID: P123456
        
        Medical Record
        
        Date of Service: March 15, 2023
        Provider: Dr. Johnson
        """
        
        # Mock a document with this text and patient ID
        mock_document = {
            "document_id": "test_doc_id",
            "extracted_text": text_with_patient,
            "file_name": "medical_record.pdf",
            "original_watchfolder_path": "/tmp/medical_record.pdf",
            "patient_id": "patient_123",
            "document_type": "Medical Record",
            "processing_status": "summarized"
        }
        self.mock_context_store.get_documents_by_processing_status.return_value = [mock_document]
        
        # Run tagging and filing
        result = self.agent.process_documents_for_tagging_and_filing()
        
        # Check results
        self.assertEqual(result[0], 1)  # One document successfully processed
        
        # Verify filing occurred and document was updated
        update_calls = self.mock_context_store.update_document_fields.call_args_list
        self.assertEqual(len(update_calls), 1)
        
        # Check that filed_path was set
        update_data = update_calls[0][0][1]
        self.assertIn("filed_path", update_data)
        self.assertIn("patient_123", update_data["filed_path"])
        self.assertIn("Medical_Record", update_data["filed_path"])
    
    @patch('tagger_agent.os.remove')
    @patch('tagger_agent.shutil.copy2')
    @patch('tagger_agent.os.path.getsize', return_value=1024)
    @patch('tagger_agent.os.path.exists', return_value=True)
    @patch('tagger_agent.os.path.isfile', return_value=True)
    @patch('tagger_agent.os.makedirs')
    def test_filing_without_patient_id(self, mock_makedirs, mock_isfile, mock_exists, mock_getsize, mock_copy2, mock_remove):
        """Test filing documents without patient ID using enhanced general archive schema."""
        # Text without patient information
        text_without_patient = """
        Invoice #12345
        
        ACME Corporation
        123 Main Street, Anytown, USA
        
        Invoice Date: January 15, 2023
        Due Date: February 28, 2023
        
        Description: Professional services
        Amount: $1,250.00
        """
        
        # Mock a document without patient ID
        mock_document = {
            "document_id": "test_doc_id",
            "extracted_text": text_without_patient,
            "file_name": "invoice_12345.pdf",
            "original_watchfolder_path": "/tmp/invoice_12345.pdf",
            "patient_id": None,
            "document_type": "Invoice",
            "processing_status": "summarized"
        }
        self.mock_context_store.get_documents_by_processing_status.return_value = [mock_document]
        
        # Run tagging and filing
        result = self.agent.process_documents_for_tagging_and_filing()
        
        # Check results
        self.assertEqual(result[0], 1)  # One document successfully processed
        
        # Verify filing occurred and document was updated
        update_calls = self.mock_context_store.update_document_fields.call_args_list
        self.assertEqual(len(update_calls), 1)
        
        # Check that filed_path was set to general archive
        update_data = update_calls[0][0][1]
        self.assertIn("filed_path", update_data)
        self.assertIn("General_Archive", update_data["filed_path"])
        self.assertIn("Invoice", update_data["filed_path"])
    
    @patch('tagger_agent.os.remove')
    @patch('tagger_agent.shutil.copy2')
    @patch('tagger_agent.os.path.getsize', return_value=1024)
    @patch('tagger_agent.os.path.exists', return_value=True)
    @patch('tagger_agent.os.path.isfile', return_value=True)
    @patch('tagger_agent.os.makedirs')
    def test_filing_error_handling(self, mock_makedirs, mock_isfile, mock_exists, mock_getsize, mock_copy2, mock_remove):
        """Test handling of filing errors."""
        # Configure mock to simulate file operation failure
        mock_copy2.side_effect = Exception("File copy failed")
        
        # Mock a document
        mock_document = {
            "document_id": "test_doc_id",
            "extracted_text": "Test document content",
            "file_name": "test.pdf",
            "original_watchfolder_path": "/tmp/test.pdf",
            "patient_id": None,
            "document_type": "Letter",
            "processing_status": "summarized"
        }
        self.mock_context_store.get_documents_by_processing_status.return_value = [mock_document]
        
        # Run tagging and filing
        result = self.agent.process_documents_for_tagging_and_filing()
        
        # Check results - should handle error gracefully
        self.assertEqual(result[1], 1)  # One document failed to process
    
    def test_no_documents_to_process(self):
        """Test behavior when no documents need processing."""
        # Mock empty document list
        self.mock_context_store.get_documents_by_processing_status.return_value = []
        
        # Run tagging and filing
        result = self.agent.process_documents_for_tagging_and_filing()
        
        # Check results
        self.assertEqual(result[0], 0)  # No documents processed
        self.assertEqual(result[1], 0)  # No failures
    



if __name__ == '__main__':
    unittest.main()