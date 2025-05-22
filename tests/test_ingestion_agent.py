"""
Unit tests for the IngestionAgent module.

These tests validate the functionality of the IngestionAgent class,
ensuring all document processing and text extraction operations work correctly.
"""

import unittest
import os
import tempfile
import shutil
from unittest.mock import MagicMock, patch
import sys
import io
from PIL import Image

# Import from parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingestion_agent import IngestionAgent
from context_store import ContextStore


class TestIngestionAgent(unittest.TestCase):
    """Test suite for the IngestionAgent class."""
    
    def setUp(self):
        """Set up test environment before each test."""
        # Create temporary directories for testing
        self.test_watch_folder = tempfile.mkdtemp()
        self.test_holding_folder = tempfile.mkdtemp()
        
        # Create a mock ContextStore
        self.mock_context_store = MagicMock(spec=ContextStore)
        
        # Configure mock behavior
        self.mock_context_store.add_document.return_value = "test_document_id"
        self.mock_context_store.update_document_fields.return_value = True
        self.mock_context_store.add_audit_log_entry.return_value = 1
        
        # Create IngestionAgent with mock ContextStore
        self.agent = IngestionAgent(
            self.mock_context_store,
            self.test_watch_folder,
            self.test_holding_folder
        )
        
        # Create test files
        self._create_test_files()
    
    def tearDown(self):
        """Clean up after each test."""
        # Remove temporary directories
        shutil.rmtree(self.test_watch_folder, ignore_errors=True)
        shutil.rmtree(self.test_holding_folder, ignore_errors=True)
    
    def _create_test_files(self):
        """Create test files of various types in the watch folder."""
        # Create a simple text file
        with open(os.path.join(self.test_watch_folder, 'test.txt'), 'w') as f:
            f.write("This is a test text file for ingestion.")
        
        # Create an empty file that will simulate an error during processing
        open(os.path.join(self.test_watch_folder, 'empty.txt'), 'w').close()
        
        # Create a file with an unsupported extension
        with open(os.path.join(self.test_watch_folder, 'unsupported.xyz'), 'w') as f:
            f.write("This file has an unsupported extension.")
    
    @patch('ingestion_agent.IngestionAgent._extract_text_from_file')
    def test_process_pending_documents_success(self, mock_extract):
        """Test successful processing of documents in the watch folder."""
        # Configure mock to return successful text extraction for test.txt
        mock_extract.return_value = ("Extracted text content", 100.0)
        
        # Create a single test file to process
        # First, clear the existing files
        for file in os.listdir(self.test_watch_folder):
            os.remove(os.path.join(self.test_watch_folder, file))
            
        # Create just one test file
        with open(os.path.join(self.test_watch_folder, 'test.txt'), 'w') as f:
            f.write("This is a test text file for ingestion.")
        
        # Process documents
        result = self.agent.process_pending_documents(
            session_id="test_session",
            patient_id="test_patient",
            user_id="test_user"
        )
        
        # Check that the document was processed
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], "test_document_id")
        
        # Check that ContextStore methods were called correctly
        self.mock_context_store.add_document.assert_called()
        self.mock_context_store.update_document_fields.assert_called_with(
            "test_document_id",
            {
                'extracted_text': "Extracted text content",
                'ocr_confidence_percent': 100.0,
                'ingestion_status': 'ingestion_successful',
                'processing_status': 'ingested'
            }
        )
        self.mock_context_store.add_audit_log_entry.assert_called()
    
    @patch('ingestion_agent.IngestionAgent._extract_text_from_file')
    def test_process_pending_documents_extraction_failure(self, mock_extract):
        """Test handling of text extraction failure."""
        # Configure mock to return failed text extraction
        mock_extract.return_value = (None, None)
        
        # Process documents
        result = self.agent.process_pending_documents(
            session_id="test_session",
            patient_id="test_patient",
            user_id="test_user"
        )
        
        # Check that no documents were successfully processed
        self.assertEqual(len(result), 0)
        
        # Check that ContextStore methods were called correctly
        self.mock_context_store.add_document.assert_called()
        self.mock_context_store.update_document_fields.assert_called_with(
            "test_document_id",
            {'ingestion_status': 'ingestion_failed'}
        )
        
        # Check that the file was moved to the holding folder
        holding_files = os.listdir(self.test_holding_folder)
        self.assertTrue(len(holding_files) > 0)
    
    @patch('ingestion_agent.IngestionAgent._extract_text_from_file')
    def test_process_pending_documents_exception(self, mock_extract):
        """Test handling of exceptions during document processing."""
        # Configure mock to raise an exception
        mock_extract.side_effect = Exception("Test exception")
        
        # Process documents
        result = self.agent.process_pending_documents(
            session_id="test_session",
            patient_id="test_patient",
            user_id="test_user"
        )
        
        # Check that no documents were successfully processed
        self.assertEqual(len(result), 0)
        
        # Check that error handling occurred
        self.mock_context_store.update_document_fields.assert_called_with(
            "test_document_id",
            {'ingestion_status': 'ingestion_failed'}
        )
        
        # Check that files were moved to the holding folder
        holding_files = os.listdir(self.test_holding_folder)
        self.assertTrue(len(holding_files) > 0)
    
    def test_extract_text_from_txt(self):
        """Test text extraction from a TXT file."""
        file_path = os.path.join(self.test_watch_folder, 'test.txt')
        
        # Call the method directly
        text, confidence = self.agent._extract_text_from_file(file_path, 'txt')
        
        # Check the results
        self.assertIsNotNone(text)
        self.assertEqual(text, "This is a test text file for ingestion.")
        self.assertEqual(confidence, 100.0)
    
    @patch('docx.Document')
    def test_extract_text_from_docx(self, mock_document):
        """Test text extraction from a DOCX file."""
        # Configure mock document
        mock_doc = MagicMock()
        mock_doc.paragraphs = [MagicMock(text="Paragraph 1"), MagicMock(text="Paragraph 2")]
        mock_document.return_value = mock_doc
        
        # Create a fake docx file path
        file_path = os.path.join(self.test_watch_folder, 'test.docx')
        open(file_path, 'w').close()  # Create empty file
        
        # We need to create a module-like structure since we're patching at the sys.modules level
        mock_docx_module = MagicMock()
        mock_docx_module.Document = mock_document
        
        # Call the method with mocking inside the testing context
        with patch.dict('sys.modules', {'docx': mock_docx_module}):
            # Call the method
            text, confidence = self.agent._extract_text_from_file(file_path, 'docx')
            
            # Check the results
            self.assertIsNotNone(text)
            self.assertEqual(text, "Paragraph 1\nParagraph 2\n")
            self.assertEqual(confidence, 100.0)
    
    @patch('pytesseract.image_to_data')
    @patch('pytesseract.image_to_string')
    def test_extract_text_from_image(self, mock_image_to_string, mock_image_to_data):
        """Test text extraction from an image file."""
        # Configure mocks
        mock_image_to_string.return_value = "OCR extracted text"
        mock_image_to_data.return_value = {
            'conf': ['90', '85', '95']
        }
        
        # Create a small test image
        image_path = os.path.join(self.test_watch_folder, 'test.png')
        img = Image.new('RGB', (100, 30), color=(73, 109, 137))
        img.save(image_path)
        
        # Create a mock pytesseract module
        mock_pytesseract = MagicMock()
        mock_pytesseract.image_to_data.return_value = {'conf': ['90', '85', '95']}
        mock_pytesseract.image_to_string.return_value = "OCR extracted text"
        mock_pytesseract.Output = MagicMock()
        mock_pytesseract.Output.DICT = "DICT"
        
        # Call the method
        with patch.dict('sys.modules', {'pytesseract': mock_pytesseract}):
            text, confidence = self.agent._extract_text_from_file(image_path, 'image')
            
            # Check the results
            self.assertEqual(text, "OCR extracted text")
            self.assertEqual(confidence, 90.0)  # Average of [90, 85, 95]
    
    def test_extract_text_from_pdf_direct(self):
        """Test direct text extraction from a PDF file."""
        # Create a mock fitz module
        mock_fitz = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = "PDF extracted text content that is substantial enough to skip OCR"
        mock_doc = MagicMock()
        mock_doc.__iter__.return_value = [mock_page]
        mock_fitz.open.return_value = mock_doc
        
        file_path = os.path.join(self.test_watch_folder, 'test.pdf')
        open(file_path, 'w').close()  # Create empty file
        
        # Call the method with mocked modules
        with patch.dict('sys.modules', {'fitz': mock_fitz}):
            # Call the method
            text, confidence = self.agent._extract_text_from_pdf(file_path)
            
            # Check that direct extraction was successful
            self.assertIsNotNone(text)
            if text:  # Add a check to avoid the "in None" warning
                self.assertTrue("PDF extracted text content" in text)
            self.assertEqual(confidence, 100.0)
    
    def test_extract_text_from_pdf_ocr(self):
        """Test OCR text extraction from an image-based PDF file."""
        # Create a mock fitz module for image-based PDF
        mock_fitz = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = ""  # No text extracted directly
        mock_pixmap = MagicMock()
        mock_pixmap.tobytes.return_value = b"fake_image_data"
        mock_page.get_pixmap.return_value = mock_pixmap
        
        mock_doc = MagicMock()
        mock_doc.__iter__.return_value = [mock_page]
        mock_doc.__len__.return_value = 1
        mock_doc.load_page.return_value = mock_page
        
        mock_fitz.open.return_value = mock_doc
        
        # Create a mock pytesseract module
        mock_pytesseract = MagicMock()
        mock_pytesseract.image_to_string.return_value = "OCR extracted PDF text"
        mock_pytesseract.image_to_data.return_value = {'conf': ['88', '92', '90']}
        mock_pytesseract.Output = MagicMock()
        mock_pytesseract.Output.DICT = "DICT"
        
        file_path = os.path.join(self.test_watch_folder, 'test.pdf')
        open(file_path, 'w').close()  # Create empty file
        
        # Mock PIL.Image.open
        mock_pil_image = MagicMock()
        
        # Call the method with mocked modules
        with patch.dict('sys.modules', {'fitz': mock_fitz, 'pytesseract': mock_pytesseract}), \
             patch('PIL.Image.open', return_value=mock_pil_image):
            
            # Call the method
            text, confidence = self.agent._extract_text_from_pdf(file_path)
            
            # Check that OCR extraction was successful
            self.assertIsNotNone(text)
            if text:  # Add a check to avoid the "in None" warning
                self.assertTrue("OCR extracted PDF text" in text)
            self.assertEqual(confidence, 90.0)  # Average of [88, 92, 90]


if __name__ == '__main__':
    unittest.main()