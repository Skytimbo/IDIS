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
        Due Date: 02/28/2023
        Service Period: 2023-01-01 to 2023-01-31
        Letter sent on March 5, 2023
        Report completed: 04-10-2023
        """
        
        # Configure mock to simulate safe file move behavior with state tracking
        copied_files = set()
        
        def mock_exists_side_effect(path):
            # Source files exist
            if '/tmp/' in path and any(ext in path for ext in ['.pdf', '.txt', '.doc']):
                return True
            # Destination files exist after copy operation
            if path in copied_files:
                return True
            # All other paths (destination archive paths) don't exist initially
            return False
        
        def mock_copy2_side_effect(src, dst):
            # Simulate successful copy by adding dst to copied_files
            copied_files.add(dst)
            return None
        
        mock_exists.side_effect = mock_exists_side_effect
        mock_copy2.side_effect = mock_copy2_side_effect
        mock_isfile.return_value = True
        
        # Mock a document with this text
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
    
    @patch('tagger_agent.os.remove')
    @patch('tagger_agent.shutil.copy2')
    @patch('tagger_agent.os.path.getsize', return_value=1024)
    @patch('tagger_agent.os.path.exists')
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
        
        # Configure mock to simulate safe file move behavior
        def mock_exists_side_effect(path):
            if '/tmp/' in path and any(ext in path for ext in ['.pdf', '.txt', '.doc']):
                return True  # Source files exist
            return False  # Destination archive paths don't exist initially
        
        mock_exists.side_effect = mock_exists_side_effect
        mock_isfile.return_value = True
        mock_getsize.return_value = 1024  # Mock file size
        
        # Mock a document with this text
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
    
    @patch('tagger_agent.os.remove')
    @patch('tagger_agent.shutil.copy2')
    @patch('tagger_agent.os.path.getsize', return_value=1024)
    @patch('tagger_agent.os.path.exists')
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
        
        # Configure mock to simulate safe file move behavior
        def mock_exists_side_effect(path):
            if '/tmp/' in path and any(ext in path for ext in ['.pdf', '.txt', '.doc']):
                return True  # Source files exist
            return False  # Destination archive paths don't exist initially
        
        mock_exists.side_effect = mock_exists_side_effect
        mock_isfile.return_value = True
        mock_getsize.return_value = 1024  # Mock file size
        
        # Mock a document with this text
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
    
    @patch('tagger_agent.os.remove')
    @patch('tagger_agent.shutil.copy2')
    @patch('tagger_agent.os.path.getsize', return_value=1024)
    @patch('tagger_agent.os.path.exists')
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
        
        # Configure mock to simulate safe file move behavior
        def mock_exists_side_effect(path):
            if '/tmp/' in path and any(ext in path for ext in ['.pdf', '.txt', '.doc']):
                return True  # Source files exist
            return False  # Destination archive paths don't exist initially
        
        mock_exists.side_effect = mock_exists_side_effect
        mock_isfile.return_value = True
        mock_getsize.return_value = 1024  # Mock file size
        
        # Mock a document with this text
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
    
    @patch('tagger_agent.os.remove')
    @patch('tagger_agent.shutil.copy2')
    @patch('tagger_agent.os.path.getsize', return_value=1024)
    @patch('tagger_agent.os.path.exists')
    @patch('tagger_agent.os.path.isfile', return_value=True)
    @patch('tagger_agent.os.makedirs')
    def test_filing_with_patient_id(self, mock_makedirs, mock_isfile, mock_exists, mock_getsize, mock_copy2, mock_remove):
        """Test filing documents with patient ID using enhanced schema."""
        # Configure mock to simulate safe file move behavior
        def mock_exists_side_effect(path):
            if '/tmp/' in path and any(ext in path for ext in ['.pdf', '.txt', '.doc']):
                return True  # Source files exist
            return False  # Destination archive paths don't exist initially
        
        mock_exists.side_effect = mock_exists_side_effect
        mock_isfile.return_value = True
        mock_getsize.return_value = 1024  # Mock file size
        
        # Mock document with patient ID
        mock_document = {
            "document_id": "test_doc_12345678",
            "extracted_text": "Test document with invoice_date January 15, 2023",
            "file_name": "scan001.pdf",
            "original_watchfolder_path": "/tmp/scan001.pdf",
            "patient_id": "patient_123456",
            "document_type": "Medical Record",
            "upload_timestamp": "2023-01-15T10:30:00Z"
        }
        self.mock_context_store.get_documents_by_processing_status.return_value = [mock_document]
        
        # Mock patient lookup to return patient name
        self.mock_context_store.get_patient.return_value = {
            "patient_id": "patient_123456",
            "patient_name": "John Doe"
        }
        
        # Run tagging and filing
        result = self.agent.process_documents_for_tagging_and_filing()
        
        # Check results
        self.assertEqual(result[0], 1)  # One document successfully processed
        
        # Verify filing path was constructed correctly with enhanced schema
        update_calls = self.mock_context_store.update_document_fields.call_args_list
        update_data = update_calls[0][0][1]
        
        self.assertIn("filed_path", update_data)
        filed_path = update_data["filed_path"]
        
        # Check enhanced filing structure: /patients/John_Doe_patien/2023/01/
        self.assertIn("patients", filed_path)
        self.assertIn("John_Doe_patien", filed_path)  # Sanitized name + first 6 chars of ID
        self.assertIn("2023", filed_path)
        self.assertIn("01", filed_path)
        
        # Check enhanced filename: 2023-01-15_scan001_MEDREC-test_doc.pdf
        self.assertIn("2023-01-15_scan001_MEDREC-test_doc", filed_path)
        
        # Verify copy2 was called with correct paths (safe file movement)
        mock_copy2.assert_called_once()
        source_path = mock_copy2.call_args[0][0]
        dest_path = mock_copy2.call_args[0][1]
        
        self.assertEqual(source_path, "/tmp/scan001.pdf")
        self.assertEqual(dest_path, filed_path)
        
        # Verify makedirs was called to create directory structure
        mock_makedirs.assert_called()
    
    @patch('tagger_agent.os.remove')
    @patch('tagger_agent.shutil.copy2')
    @patch('tagger_agent.os.path.getsize', return_value=1024)
    @patch('tagger_agent.os.path.exists')
    @patch('tagger_agent.os.path.isfile', return_value=True)
    @patch('tagger_agent.os.makedirs')
    def test_filing_without_patient_id(self, mock_makedirs, mock_isfile, mock_exists, mock_getsize, mock_copy2, mock_remove):
        """Test filing documents without patient ID using enhanced general archive schema."""
        # Configure mock to simulate safe file move behavior
        def mock_exists_side_effect(path):
            if '/tmp/' in path and any(ext in path for ext in ['.pdf', '.txt', '.doc']):
                return True  # Source files exist
            return False  # Destination archive paths don't exist initially
        
        mock_exists.side_effect = mock_exists_side_effect
        mock_isfile.return_value = True
        
        # Mock document without patient ID but with document type and issuer
        mock_document = {
            "document_id": "test_doc_87654321",
            "extracted_text": "Test invoice from ABC Company dated January 15, 2023",
            "file_name": "invoice_001.pdf",
            "original_watchfolder_path": "/tmp/invoice_001.pdf",
            "document_type": "Invoice",
            "upload_timestamp": "2023-01-15T14:20:00Z"
        }
        self.mock_context_store.get_documents_by_processing_status.return_value = [mock_document]
        
        # Run tagging and filing
        result = self.agent.process_documents_for_tagging_and_filing()
        
        # Check results
        self.assertEqual(result[0], 1)  # One document successfully processed
        
        # Verify filing path was constructed correctly with enhanced schema
        update_calls = self.mock_context_store.update_document_fields.call_args_list
        update_data = update_calls[0][0][1]
        
        self.assertIn("filed_path", update_data)
        filed_path = update_data["filed_path"]
        
        # Check enhanced filing structure: /general_archive/2023/01/
        self.assertIn("general_archive", filed_path)
        self.assertIn("2023", filed_path)
        self.assertIn("01", filed_path)
        
        # Check enhanced filename includes document type abbreviation and issuer
        self.assertIn("2023-01-15", filed_path)
        self.assertIn("INV-test_doc", filed_path)  # INV abbreviation for Invoice
        
        # Verify copy was called with correct paths for safe file move
        mock_copy2.assert_called_once()
    
    @patch('tagger_agent.os.remove')
    @patch('tagger_agent.shutil.copy2')
    @patch('tagger_agent.os.path.getsize', return_value=1024)
    @patch('tagger_agent.os.path.exists', return_value=True)
    @patch('tagger_agent.os.path.isfile', return_value=False)  # Simulate file not found
    @patch('tagger_agent.os.makedirs')
    def test_filing_error_handling(self, mock_makedirs, mock_isfile, mock_exists, mock_getsize, mock_copy2, mock_remove):
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
        
        # Verify copy was not called due to file not existing
        mock_copy2.assert_not_called()
    
    def test_sanitize_for_filename(self):
        """Test filename sanitization helper method."""
        # Test normal text
        result = self.agent._sanitize_for_filename("John Doe")
        self.assertEqual(result, "John_Doe")
        
        # Test text with special characters
        result = self.agent._sanitize_for_filename("Patient@#123!")
        self.assertEqual(result, "Patient123")
        
        # Test empty string
        result = self.agent._sanitize_for_filename("")
        self.assertEqual(result, "Unknown")
        
        # Test None case by passing empty string (simulating None input handling)
        result = self.agent._sanitize_for_filename("")
        self.assertEqual(result, "Unknown")
    
    def test_get_primary_date(self):
        """Test primary date determination logic."""
        # Test with priority date keys
        document_dates = {
            "invoice_date": "2023-01-15",
            "visit_date": "2023-01-20"
        }
        result = self.agent._get_primary_date(document_dates, "2023-01-10T10:00:00Z")
        self.assertEqual(result.strftime('%Y-%m-%d'), "2023-01-15")  # Should pick invoice_date
        
        # Test with earliest date when no priority keys
        document_dates = {
            "some_date": "2023-01-20",
            "another_date": "2023-01-15"
        }
        result = self.agent._get_primary_date(document_dates, "2023-01-10T10:00:00Z")
        self.assertEqual(result.strftime('%Y-%m-%d'), "2023-01-15")  # Should pick earliest
        
        # Test fallback to upload timestamp
        result = self.agent._get_primary_date({}, "2023-01-10T10:00:00Z")
        self.assertEqual(result.strftime('%Y-%m-%d'), "2023-01-10")
    
    def test_get_patient_folder_name(self):
        """Test patient folder name generation."""
        # Mock patient lookup to return patient name
        self.mock_context_store.get_patient.return_value = {
            "patient_id": "patient_123456",
            "patient_name": "John Doe"
        }
        
        result = self.agent._get_patient_folder_name("patient_123456")
        self.assertEqual(result, "John_Doe_patien")
        
        # Test fallback when patient not found
        self.mock_context_store.get_patient.return_value = None
        result = self.agent._get_patient_folder_name("unknown_patient")
        self.assertEqual(result, "unknown_patient")
    
    def test_generate_new_filename(self):
        """Test enhanced filename generation."""
        from datetime import datetime
        
        # Test patient document filename
        primary_date = datetime(2023, 1, 15)
        result = self.agent._generate_new_filename(
            "test_doc_12345678", "scan001.pdf", "Medical Record", 
            primary_date, "patient_123", None
        )
        self.assertEqual(result, "2023-01-15_scan001_MEDREC-test_doc.pdf")
        
        # Test general document filename with issuer
        result = self.agent._generate_new_filename(
            "test_doc_87654321", "invoice.pdf", "Invoice", 
            primary_date, None, "ABC Company"
        )
        self.assertEqual(result, "2023-01-15_ABC_Company_INV-test_doc.pdf")
        
        # Test general document filename without issuer
        result = self.agent._generate_new_filename(
            "test_doc_11111111", "document.pdf", "Unclassified", 
            primary_date, None, None
        )
        self.assertEqual(result, "2023-01-15_UnknownSource_UNC-test_doc.pdf")
    
    def test_extract_dates_month_year_format(self):
        """Test extraction of Month YYYY format dates."""
        # Test various Month YYYY formats
        test_cases = [
            ("This letter is dated February 2025", {"letter_date": "2025-02-01"}),
            ("Invoice date: Feb 2025", {"invoice_date": "2025-02-01"}),
            ("Report from March 2024", {"report_date": "2024-03-01"}),
            ("Due date: Dec. 2023", {"due_date": "2023-12-01"}),
            ("Service date JANUARY 2025", {"service_date": "2025-01-01"}),
            ("Letter dated September 2024", {"letter_date": "2024-09-01"}),
            ("Exam scheduled for Nov 2025", {"exam_date": "2025-11-01"}),
        ]
        
        for text, expected_dates in test_cases:
            with self.subTest(text=text):
                result = self.agent._extract_dates(text)
                for context, expected_date in expected_dates.items():
                    self.assertIn(context, result, f"Context '{context}' not found in extracted dates")
                    self.assertEqual(result[context], expected_date, 
                                   f"Expected {expected_date}, got {result[context]} for text: {text}")
    
    def test_normalize_date_month_year_format(self):
        """Test normalization of Month YYYY format dates."""
        test_cases = [
            ("February 2025", "2025-02-01"),
            ("Feb 2025", "2025-02-01"),
            ("Feb. 2025", "2025-02-01"),
            ("FEBRUARY 2025", "2025-02-01"),
            ("March 2024", "2024-03-01"),
            ("Dec 2023", "2023-12-01"),
            ("December 2023", "2023-12-01"),
            ("Jan 2026", "2026-01-01"),
            ("January 2026", "2026-01-01"),
            ("Sep 2025", "2025-09-01"),
            ("September 2025", "2025-09-01"),
        ]
        
        for date_str, expected in test_cases:
            with self.subTest(date_str=date_str):
                result = self.agent._normalize_date(date_str)
                self.assertEqual(result, expected, 
                               f"Failed to normalize '{date_str}' to '{expected}', got '{result}'")
    
    def test_normalize_date_mixed_formats(self):
        """Test that existing date formats still work alongside Month YYYY format."""
        test_cases = [
            # Existing formats should still work
            ("January 15, 2023", "2023-01-15"),
            ("12/25/2023", "2023-12-25"),
            ("2024-03-10", "2024-03-10"),
            # New Month YYYY format
            ("April 2025", "2025-04-01"),
            ("May 2024", "2024-05-01"),
        ]
        
        for date_str, expected in test_cases:
            with self.subTest(date_str=date_str):
                result = self.agent._normalize_date(date_str)
                self.assertEqual(result, expected, 
                               f"Failed to normalize '{date_str}' to '{expected}', got '{result}'")
    
    def test_extract_dates_contextual_month_year(self):
        """Test that Month YYYY dates are properly extracted with context labels."""
        text = """
        This invoice is dated February 2025.
        The payment is due March 2025.
        Service was provided in January 2025.
        This letter was written April 2025.
        """
        
        result = self.agent._extract_dates(text)
        
        # Should extract contextual dates
        expected_contexts = {
            "invoice_date": "2025-02-01",
            "due_date": "2025-03-01", 
            "service_date": "2025-01-01",
            "letter_date": "2025-04-01"
        }
        
        for context, expected_date in expected_contexts.items():
            self.assertIn(context, result, f"Context '{context}' not found")
            self.assertEqual(result[context], expected_date, 
                           f"Expected {expected_date} for {context}, got {result[context]}")
    
    @patch('tagger_agent.os.remove')
    @patch('tagger_agent.shutil.copy2')
    @patch('tagger_agent.os.path.getsize', return_value=1024)
    @patch('tagger_agent.os.path.exists', return_value=True)
    @patch('tagger_agent.os.path.isfile', return_value=True)
    @patch('tagger_agent.os.makedirs')
    def test_move_error_handling(self, mock_makedirs, mock_isfile, mock_exists, mock_getsize, mock_copy2, mock_remove):
        """Test handling of errors during file move operations."""
        # Set up mocks
        mock_isfile.return_value = True
        mock_copy2.side_effect = Exception("File copy error")
        
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
    
    @patch('tagger_agent.os.remove')
    @patch('tagger_agent.shutil.copy2')
    @patch('tagger_agent.os.path.getsize', return_value=1024)
    @patch('tagger_agent.os.path.exists', return_value=True)
    @patch('tagger_agent.os.path.isfile', return_value=True)
    @patch('tagger_agent.os.makedirs')
    def test_empty_text_handling(self, mock_makedirs, mock_isfile, mock_exists, mock_getsize, mock_copy2, mock_remove):
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