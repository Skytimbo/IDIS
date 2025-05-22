"""
Unit tests for the TaggerAgent module.

These tests validate the functionality of the TaggerAgent class,
ensuring metadata extraction and document filing works correctly.
"""

import unittest
from unittest.mock import MagicMock, patch, mock_open
import os
import sys
import json
import shutil
from datetime import datetime

# Import from parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tagger_agent import TaggerAgent
from context_store import ContextStore


class TestTaggerAgent(unittest.TestCase):
    """Test suite for the TaggerAgent class."""
    
    def setUp(self):
        """Set up test environment before each test."""
        # Create mock ContextStore
        self.mock_context_store = MagicMock(spec=ContextStore)
        
        # Define test tag definitions
        self.tag_definitions = {
            "urgent": ["urgent", "immediate attention", "asap"],
            "confidential": ["confidential", "private", "sensitive"],
            "important": ["important", "critical", "essential"]
        }
        
        # Set up base filed folder
        self.base_filed_folder = "/tmp/idis_test_archive"
        
        # Create TaggerAgent with mock ContextStore
        self.agent = TaggerAgent(
            self.mock_context_store,
            self.base_filed_folder,
            self.tag_definitions
        )
        
        # Configure mock ContextStore behavior
        self.mock_context_store.update_document_fields.return_value = True
        self.mock_context_store.add_audit_log_entry.return_value = 1
    
    @patch('os.path.isfile')
    @patch('os.makedirs')
    @patch('shutil.move')
    def test_date_extraction(self, mock_move, mock_makedirs, mock_isfile):
        """Test extraction of various date formats."""
        # Text with different date formats
        text_with_dates = """
        Invoice Date: January 15, 2023
        Due Date: 02/28/2023
        Service Period: 2023-01-01 to 2023-01-31
        Letter sent on March 5, 2023
        Report completed: 04-10-2023
        """
        
        # Mock a document with this text
        mock_isfile.return_value = True
        mock_document = {
            "document_id": "test_doc_id",
            "extracted_text": text_with_dates,
            "file_name": "test_document.pdf",
            "original_watchfolder_path": "/tmp/test_document.pdf"
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
    
    @patch('os.path.isfile')
    @patch('os.makedirs')
    @patch('shutil.move')
    def test_issuer_extraction(self, mock_move, mock_makedirs, mock_isfile):
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
        mock_isfile.return_value = True
        mock_document = {
            "document_id": "test_doc_id",
            "extracted_text": text_with_issuer,
            "file_name": "test_document.pdf",
            "original_watchfolder_path": "/tmp/test_document.pdf"
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
    
    @patch('os.path.isfile')
    @patch('os.makedirs')
    @patch('shutil.move')
    def test_recipient_extraction(self, mock_move, mock_makedirs, mock_isfile):
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
        mock_isfile.return_value = True
        mock_document = {
            "document_id": "test_doc_id",
            "extracted_text": text_with_recipient,
            "file_name": "test_document.pdf",
            "original_watchfolder_path": "/tmp/test_document.pdf"
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
    
    @patch('os.path.isfile')
    @patch('os.makedirs')
    @patch('shutil.move')
    def test_tag_extraction(self, mock_move, mock_makedirs, mock_isfile):
        """Test extraction of predefined tags."""
        # Text with tag keywords
        text_with_tags = """
        CONFIDENTIAL - For Internal Use Only
        
        URGENT: Response Required by April 15, 2023
        
        This document contains important information about your account.
        """
        
        # Mock a document with this text
        mock_isfile.return_value = True
        mock_document = {
            "document_id": "test_doc_id",
            "extracted_text": text_with_tags,
            "file_name": "test_document.pdf",
            "original_watchfolder_path": "/tmp/test_document.pdf"
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
        
        self.assertIn("urgent", tags)
        self.assertIn("confidential", tags)
        self.assertIn("important", tags)
    
    @patch('os.path.isfile')
    @patch('os.makedirs')
    @patch('shutil.move')
    def test_filing_with_patient_id(self, mock_move, mock_makedirs, mock_isfile):
        """Test filing documents with patient ID."""
        # Mock document with patient ID
        mock_isfile.return_value = True
        mock_document = {
            "document_id": "test_doc_id",
            "extracted_text": "Test document with date January 15, 2023",
            "file_name": "test_document.pdf",
            "original_watchfolder_path": "/tmp/test_document.pdf",
            "patient_id": "patient_123"
        }
        self.mock_context_store.get_documents_by_processing_status.return_value = [mock_document]
        
        # Run tagging and filing
        result = self.agent.process_documents_for_tagging_and_filing()
        
        # Check results
        self.assertEqual(result[0], 1)  # One document successfully processed
        
        # Verify filing path was constructed correctly
        update_calls = self.mock_context_store.update_document_fields.call_args_list
        update_data = update_calls[0][0][1]
        
        self.assertIn("filed_path", update_data)
        filed_path = update_data["filed_path"]
        
        # Check that patient ID is in the path
        self.assertIn("patient_123", filed_path)
        
        # Verify move was called with correct paths
        mock_move.assert_called_once()
        source_path = mock_move.call_args[0][0]
        dest_path = mock_move.call_args[0][1]
        
        self.assertEqual(source_path, "/tmp/test_document.pdf")
        self.assertEqual(dest_path, filed_path)
        
        # Verify makedirs was called to create directory structure
        mock_makedirs.assert_called()
    
    @patch('os.path.isfile')
    @patch('os.makedirs')
    @patch('shutil.move')
    def test_filing_without_patient_id(self, mock_move, mock_makedirs, mock_isfile):
        """Test filing documents without patient ID."""
        # Mock document without patient ID but with document type
        mock_isfile.return_value = True
        mock_document = {
            "document_id": "test_doc_id",
            "extracted_text": "Test document with date January 15, 2023",
            "file_name": "test_document.pdf",
            "original_watchfolder_path": "/tmp/test_document.pdf",
            "document_type": "Invoice"
        }
        self.mock_context_store.get_documents_by_processing_status.return_value = [mock_document]
        
        # Run tagging and filing
        result = self.agent.process_documents_for_tagging_and_filing()
        
        # Check results
        self.assertEqual(result[0], 1)  # One document successfully processed
        
        # Verify filing path was constructed correctly
        update_calls = self.mock_context_store.update_document_fields.call_args_list
        update_data = update_calls[0][0][1]
        
        self.assertIn("filed_path", update_data)
        filed_path = update_data["filed_path"]
        
        # Check that general_documents and document type are in the path
        self.assertIn("general_documents", filed_path)
        self.assertIn("Invoice", filed_path)
        
        # Verify move was called with correct paths
        mock_move.assert_called_once()
    
    @patch('os.path.isfile')
    @patch('os.makedirs')
    @patch('shutil.move')
    def test_filing_error_handling(self, mock_move, mock_makedirs, mock_isfile):
        """Test handling of filing errors."""
        # Set up mock to simulate file not found
        mock_isfile.return_value = False
        
        # Mock document
        mock_document = {
            "document_id": "test_doc_id",
            "extracted_text": "Test document with date January 15, 2023",
            "file_name": "test_document.pdf",
            "original_watchfolder_path": "/tmp/nonexistent_file.pdf"
        }
        self.mock_context_store.get_documents_by_processing_status.return_value = [mock_document]
        
        # Run tagging and filing
        result = self.agent.process_documents_for_tagging_and_filing()
        
        # Check results
        self.assertEqual(result[0], 0)  # No documents successfully processed
        self.assertEqual(result[1], 1)  # One failed
        
        # Verify document status was updated correctly
        update_calls = self.mock_context_store.update_document_fields.call_args_list
        update_data = update_calls[0][0][1]
        
        self.assertIn("processing_status", update_data)
        self.assertEqual(update_data["processing_status"], "filing_error")
        
        # Verify move was not called
        mock_move.assert_not_called()
    
    @patch('os.path.isfile')
    @patch('os.makedirs')
    @patch('shutil.move')
    def test_move_error_handling(self, mock_move, mock_makedirs, mock_isfile):
        """Test handling of errors during file move operations."""
        # Set up mocks
        mock_isfile.return_value = True
        mock_move.side_effect = Exception("File move error")
        
        # Mock document
        mock_document = {
            "document_id": "test_doc_id",
            "extracted_text": "Test document with date January 15, 2023",
            "file_name": "test_document.pdf",
            "original_watchfolder_path": "/tmp/test_document.pdf"
        }
        self.mock_context_store.get_documents_by_processing_status.return_value = [mock_document]
        
        # Run tagging and filing
        result = self.agent.process_documents_for_tagging_and_filing()
        
        # Check results
        self.assertEqual(result[0], 0)  # No documents successfully processed
        self.assertEqual(result[1], 1)  # One failed
        
        # Verify document status was updated correctly
        update_calls = self.mock_context_store.update_document_fields.call_args_list
        update_data = update_calls[0][0][1]
        
        self.assertIn("processing_status", update_data)
        self.assertEqual(update_data["processing_status"], "filing_error")
    
    @patch('os.path.isfile')
    @patch('os.makedirs')
    @patch('shutil.move')
    def test_empty_text_handling(self, mock_move, mock_makedirs, mock_isfile):
        """Test handling of documents with empty or None text."""
        # Mock documents with empty and None text
        mock_documents = [
            {
                "document_id": "test_empty_id",
                "extracted_text": "",
                "file_name": "empty.pdf",
                "original_watchfolder_path": "/tmp/empty.pdf"
            },
            {
                "document_id": "test_none_id",
                "extracted_text": None,
                "file_name": "none.pdf",
                "original_watchfolder_path": "/tmp/none.pdf"
            }
        ]
        self.mock_context_store.get_documents_by_processing_status.return_value = mock_documents
        
        # Run tagging and filing
        result = self.agent.process_documents_for_tagging_and_filing()
        
        # Check results
        self.assertEqual(result[0], 0)  # No documents successfully processed
        self.assertEqual(result[1], 2)  # Two failed
        
        # Verify documents were marked as skipped
        self.assertEqual(self.mock_context_store.update_document_fields.call_count, 2)
        
        # Check first document update
        first_call_args = self.mock_context_store.update_document_fields.call_args_list[0][0]
        self.assertEqual(first_call_args[0], "test_empty_id")
        self.assertEqual(first_call_args[1]["processing_status"], "tagging_skipped_no_text")
        
        # Check second document update
        second_call_args = self.mock_context_store.update_document_fields.call_args_list[1][0]
        self.assertEqual(second_call_args[0], "test_none_id")
        self.assertEqual(second_call_args[1]["processing_status"], "tagging_skipped_no_text")


if __name__ == '__main__':
    unittest.main()