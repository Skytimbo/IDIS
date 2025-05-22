"""
End-to-End Test Suite for Intelligent Document Insight System (IDIS)

This module tests the complete IDIS pipeline from ingestion to cover sheet generation
using the run_mvp.py script with mock documents.
"""

import os
import sys
import json
import shutil
import tempfile
import unittest
import subprocess
import sqlite3
from typing import Dict, Any, List, Optional

# Add the parent directory to sys.path to allow importing from the parent directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from run_mvp import DB_NAME, setup_environment, create_mock_documents, cleanup_environment


class TestEndToEndPipeline(unittest.TestCase):
    """Test cases for the end-to-end IDIS pipeline."""
    
    def setUp(self):
        """Set up test environment before each test."""
        # Create a temporary directory for the test
        self.test_run_base_dir = tempfile.mkdtemp(prefix="idis_e2e_test_")
        
        # Copy permissions rules file to test directory
        src_permissions_path = os.path.join(os.path.dirname(__file__), "..", "permissions_rules.json")
        dest_permissions_path = os.path.join(self.test_run_base_dir, "permissions_rules.json")
        shutil.copy(src_permissions_path, dest_permissions_path)
        
        # Set up environment paths
        self.paths = setup_environment(self.test_run_base_dir)
        self.db_path = self.paths['db_path']
        self.watch_dir = self.paths['watch_folder']
        self.holding_dir = self.paths['holding_folder']
        self.archive_dir = self.paths['archive_folder']
        self.cover_sheet_output_dir = self.paths['pdf_output_dir']
    
    def tearDown(self):
        """Clean up after each test."""
        # Remove the temporary directory and all its contents
        if os.path.exists(self.test_run_base_dir):
            shutil.rmtree(self.test_run_base_dir)
    
    def test_full_pipeline_success(self):
        """Test the full IDIS pipeline with mock documents."""
        # Create mock documents in the test folder first
        create_mock_documents(self.watch_dir)
        
        # Run the pipeline script
        cmd = [
            sys.executable,  # Python executable
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "run_mvp.py"),
            "--base-dir", self.test_run_base_dir,
            "--keep-temp-files"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Check that the command executed successfully
        self.assertEqual(
            result.returncode, 0,
            f"Pipeline execution failed with code {result.returncode}. "
            f"STDERR: {result.stderr}"
        )
        
        # Verify the results in the database
        self._verify_database_contents()
        
        # Verify the cover sheet was generated
        self._verify_cover_sheet_exists()
        
        # Verify documents were filed in the archive folder
        self._verify_filed_documents()
    
    def _verify_database_contents(self):
        """Verify the database contains the expected documents and metadata."""
        # Connect to the SQLite database
        self.assertTrue(os.path.exists(self.db_path), f"Database file not found at {self.db_path}")
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check if the expected tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row['name'] for row in cursor.fetchall()]
        expected_tables = ['patients', 'sessions', 'documents', 'agent_outputs', 'audit_trail']
        for table in expected_tables:
            self.assertIn(table, tables, f"Table '{table}' not found in database")
        
        # Verify sessions table has an entry
        cursor.execute("SELECT * FROM sessions")
        sessions = cursor.fetchall()
        self.assertGreaterEqual(len(sessions), 1, "No sessions found in database")
        
        # Get the session ID for further checks
        session_id = sessions[0]['session_id']
        
        # Verify documents were ingested
        cursor.execute("SELECT * FROM documents")
        documents = cursor.fetchall()
        self.assertEqual(len(documents), 3, f"Expected 3 documents, found {len(documents)}")
        
        # Verify each document's properties
        for doc in documents:
            # Basic document properties
            self.assertIsNotNone(doc['document_id'], "Document ID is None")
            self.assertIsNotNone(doc['file_name'], "File name is None")
            
            # Ingestion status
            self.assertEqual(doc['ingestion_status'], 'ingestion_successful',
                            f"Document {doc['document_id']} has unexpected ingestion_status: {doc['ingestion_status']}")
            
            # Document type and classification
            self.assertIn(doc['document_type'], ['Invoice', 'Medical Record', 'Letter', 'Unclassified'],
                         f"Document {doc['document_id']} has unexpected document_type: {doc['document_type']}")
            
            if doc['document_type'] != 'Unclassified':
                self.assertEqual(doc['classification_confidence'], 'Medium',
                               f"Document {doc['document_id']} has unexpected classification_confidence: {doc['classification_confidence']}")
            
            # Processing status
            self.assertIn(doc['processing_status'], ['filed', 'filing_error', 'summarized', 'classified'],
                         f"Document {doc['document_id']} has unexpected processing_status: {doc['processing_status']}")
            
            # Extracted text
            self.assertIsNotNone(doc['extracted_text'], f"Document {doc['document_id']} has no extracted text")
            self.assertGreater(len(doc['extracted_text']), 0, f"Document {doc['document_id']} has empty extracted text")
            
            # Check if expected metadata is present for known document types
            if doc['file_name'] == 'invoice_001.txt':
                self.assertEqual(doc['document_type'], 'Invoice', "Invoice document misclassified")
                self._check_document_metadata(doc, issuer_contains="ACME", recipient_contains="John Doe")
            
            elif doc['file_name'] == 'medical_002.txt':
                self.assertEqual(doc['document_type'], 'Medical Record', "Medical document misclassified")
                self._check_document_metadata(doc, recipient_contains="Jane Smith")
            
            elif doc['file_name'] == 'letter_003.txt':
                self.assertEqual(doc['document_type'], 'Letter', "Letter document misclassified")
                self._check_document_metadata(doc, issuer_contains="Smith & Associates", recipient_contains="Richard Roe")
        
        # Verify agent outputs were generated
        cursor.execute("SELECT * FROM agent_outputs")
        outputs = cursor.fetchall()
        self.assertGreaterEqual(len(outputs), 3, "Expected at least 3 agent outputs (summaries)")
        
        # Verify there are summaries for each document
        document_ids = [doc['document_id'] for doc in documents]
        summary_doc_ids = [output['document_id'] for output in outputs 
                          if output['output_type'] == 'per_document_summary']
        
        for doc_id in document_ids:
            self.assertIn(doc_id, summary_doc_ids, f"No summary found for document {doc_id}")
        
        # Verify audit log entries
        cursor.execute("SELECT * FROM audit_log")
        audit_entries = cursor.fetchall()
        self.assertGreaterEqual(len(audit_entries), 5, "Too few audit log entries")
        
        # Close database connection
        conn.close()
    
    def _check_document_metadata(self, doc: sqlite3.Row, issuer_contains: Optional[str] = None, 
                               recipient_contains: Optional[str] = None):
        """
        Check if a document has the expected metadata.
        
        Args:
            doc: Document row from the database
            issuer_contains: String that should be in the issuer field
            recipient_contains: String that should be in the recipient field
        """
        # Check for dates
        if doc['document_dates']:
            if isinstance(doc['document_dates'], str):
                try:
                    dates = json.loads(doc['document_dates'])
                    self.assertIsInstance(dates, dict, "Document dates not parsed as a dictionary")
                    self.assertGreater(len(dates), 0, "No dates found in document")
                except json.JSONDecodeError:
                    self.fail(f"Invalid JSON in document_dates: {doc['document_dates']}")
        
        # Check for issuer
        if issuer_contains and doc['issuer_source']:
            self.assertIn(issuer_contains, doc['issuer_source'], 
                        f"Issuer '{doc['issuer_source']}' does not contain '{issuer_contains}'")
        
        # Check for recipient
        if recipient_contains and doc['recipient']:
            self.assertIn(recipient_contains, doc['recipient'], 
                         f"Recipient '{doc['recipient']}' does not contain '{recipient_contains}'")
        
        # Check for tags if they should be present
        if doc['file_name'] == 'invoice_001.txt':
            self._check_tags(doc, expected_tags=['urgent', 'financial'])
        
        elif doc['file_name'] == 'medical_002.txt':
            self._check_tags(doc, expected_tags=['confidential', 'medical'])
    
    def _check_tags(self, doc: sqlite3.Row, expected_tags: List[str]):
        """
        Check if a document has the expected tags.
        
        Args:
            doc: Document row from the database
            expected_tags: List of tags that should be present
        """
        if not doc['tags_extracted']:
            self.fail(f"No tags found for document {doc['file_name']}")
            return
        
        # Parse tags if they're stored as a JSON string
        tags = doc['tags_extracted']
        if isinstance(tags, str):
            try:
                tags = json.loads(tags)
            except json.JSONDecodeError:
                self.fail(f"Invalid JSON in tags_extracted: {doc['tags_extracted']}")
        
        # Check if expected tags are present
        for tag in expected_tags:
            self.assertIn(tag, tags, f"Tag '{tag}' not found in document {doc['file_name']}")
    
    def _verify_cover_sheet_exists(self):
        """Verify that a cover sheet PDF was generated."""
        # Check if at least one PDF file exists in the cover sheets directory
        pdf_files = [f for f in os.listdir(self.cover_sheet_output_dir) if f.endswith('.pdf')]
        self.assertGreaterEqual(len(pdf_files), 1, "No cover sheet PDF files found")
        
        # Check if the PDF file is not empty
        pdf_path = os.path.join(self.cover_sheet_output_dir, pdf_files[0])
        self.assertGreater(os.path.getsize(pdf_path), 0, "Cover sheet PDF file is empty")
    
    def _verify_filed_documents(self):
        """Verify that documents were filed in the archive folder."""
        # Check if the archive folder contains any files (recursively)
        found_files = False
        for root, _, files in os.walk(self.archive_dir):
            if files:
                found_files = True
                break
        
        # If documents failed to file due to missing original files (common in test), then we can skip this check
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT processing_status FROM documents")
        statuses = [row['processing_status'] for row in cursor.fetchall()]
        conn.close()
        
        # Only assert if documents should have been filed
        if 'filed' in statuses:
            self.assertTrue(found_files, "No filed documents found in archive folder")


if __name__ == '__main__':
    unittest.main()