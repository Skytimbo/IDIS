"""
Unit tests for the SummarizerAgent module.

These tests validate the functionality of the SummarizerAgent class,
ensuring document summarization and batch summary generation work correctly.
"""

import unittest
from unittest.mock import MagicMock, patch, Mock
import os
import sys
import json

# Import from parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from summarizer_agent import SummarizerAgent
from context_store import ContextStore


class TestSummarizerAgent(unittest.TestCase):
    """Test suite for the SummarizerAgent class."""
    
    def setUp(self):
        """Set up test environment before each test."""
        # Create mock ContextStore
        self.mock_context_store = MagicMock(spec=ContextStore)
        
        # Mock OpenAI API key
        self.api_key = "test_api_key"
        
        # Create SummarizerAgent with mock ContextStore
        with patch('openai.OpenAI'):
            self.agent = SummarizerAgent(
                self.mock_context_store,
                self.api_key
            )
        
        # Configure mock ContextStore behavior
        self.mock_context_store.update_document_fields.return_value = True
        self.mock_context_store.save_agent_output.return_value = "test_output_id"
        self.mock_context_store.add_audit_log_entry.return_value = 1
        self.mock_context_store.update_session_metadata.return_value = True
    
    @patch('openai.OpenAI')
    def test_api_key_handling(self, mock_openai):
        """Test API key handling from environment variable."""
        # Test with key provided directly
        agent = SummarizerAgent(self.mock_context_store, "direct_key")
        self.assertEqual(agent.api_key, "direct_key")
        
        # Test with environment variable
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'env_key'}):
            agent = SummarizerAgent(self.mock_context_store)
            self.assertEqual(agent.api_key, "env_key")
        
        # Test with no key
        with patch.dict('os.environ', {}, clear=True):
            with self.assertRaises(ValueError):
                SummarizerAgent(self.mock_context_store)
    
    def test_successful_document_summarization(self):
        """Test successful summarization of a document."""
        # Create a patched version of the agent with a controlled OpenAI client
        with patch.object(self.agent, '_generate_summary') as mock_generate_summary:
            # Mock the summary generation to return a successful result
            mock_generate_summary.return_value = ("This is a test summary.", 1.0)
            
            # Prepare mock document data
            mock_documents = [{
                "document_id": "test_doc_id",
                "extracted_text": "This is the document text to summarize.",
                "file_name": "test_doc.pdf",
                "document_type": "Medical Record"
            }]
            self.mock_context_store.get_documents_by_processing_status.return_value = mock_documents
            
            # Run summarization
            result = self.agent.summarize_classified_documents()
            
            # Check results
            self.assertEqual(result[0], 1)  # One document successfully summarized
            self.assertEqual(result[1], 0)  # No batch summary generated (no session_id)
            
            # Verify the summary generation was called with the document text
            mock_generate_summary.assert_called_once_with("This is the document text to summarize.")
            
            # Verify ContextStore methods were called correctly
            self.mock_context_store.save_agent_output.assert_called_with(
                document_id="test_doc_id",
                agent_id="summarizer_agent_v1.0",
                output_type="per_document_summary",
                output_data="This is a test summary.",
                confidence=1.0
            )
            self.mock_context_store.update_document_fields.assert_called_with(
                "test_doc_id",
                {"processing_status": "summarized"}
            )
            self.mock_context_store.add_audit_log_entry.assert_called()
    
    def test_successful_batch_summarization(self):
        """Test successful generation of a batch summary."""
        # Create a patched version of the agent with controlled summary generators
        with patch.object(self.agent, '_generate_summary') as mock_generate_summary, \
             patch.object(self.agent, '_generate_batch_summary') as mock_generate_batch_summary:
            
            # Set up the mocks to return successful results
            mock_generate_summary.side_effect = [
                ("Document summary 1", 1.0),
                ("Document summary 2", 1.0)
            ]
            mock_generate_batch_summary.return_value = ("This is a batch summary.", 1.0)
            
            # Prepare mock document data
            mock_documents = [
                {
                    "document_id": "test_doc_id1",
                    "extracted_text": "Document text 1",
                    "file_name": "doc1.pdf",
                    "document_type": "Medical Record"
                },
                {
                    "document_id": "test_doc_id2",
                    "extracted_text": "Document text 2",
                    "file_name": "doc2.pdf",
                    "document_type": "Invoice"
                }
            ]
            self.mock_context_store.get_documents_by_processing_status.return_value = mock_documents
            
            # Run summarization with session_id
            session_id = "test_session_id"
            result = self.agent.summarize_classified_documents(session_id=session_id)
            
            # Check results
            self.assertEqual(result[0], 2)  # Two documents successfully summarized
            self.assertEqual(result[1], 1)  # Batch summary generated
            
            # Verify the summary generators were called correctly
            self.assertEqual(mock_generate_summary.call_count, 2)
            mock_generate_summary.assert_any_call("Document text 1")
            mock_generate_summary.assert_any_call("Document text 2")
            
            # Verify the batch summary generator was called
            mock_generate_batch_summary.assert_called_once()
            # We don't check the exact parameters as they're complex, but we can verify it was called
            
            # Verify session metadata was updated with batch summary
            self.mock_context_store.update_session_metadata.assert_called_with(
                session_id,
                {
                    "batch_summary": "This is a batch summary.",
                    "batch_summary_agent_id": "summarizer_agent_v1.0",
                    "summarized_document_count": 2
                }
            )
    
    @patch('openai.OpenAI')
    def test_api_error_handling(self, mock_openai):
        """Test handling of OpenAI API errors."""
        # Mock OpenAI client to raise an exception
        mock_openai_instance = mock_openai.return_value
        mock_openai_instance.chat.completions.create.side_effect = Exception("API error")
        
        # Prepare mock document data
        mock_documents = [{
            "document_id": "test_doc_id",
            "extracted_text": "This is the document text to summarize.",
            "file_name": "test_doc.pdf",
            "document_type": "Medical Record"
        }]
        self.mock_context_store.get_documents_by_processing_status.return_value = mock_documents
        
        # Run summarization
        result = self.agent.summarize_classified_documents()
        
        # Check results
        self.assertEqual(result[0], 0)  # No documents successfully summarized
        
        # Verify ContextStore methods were called correctly - just check that save_agent_output was called for the right document
        self.mock_context_store.save_agent_output.assert_called_once()
        call_args = self.mock_context_store.save_agent_output.call_args[1]
        self.assertEqual(call_args["document_id"], "test_doc_id")
        self.assertEqual(call_args["agent_id"], "summarizer_agent_v1.0")
        self.assertEqual(call_args["output_type"], "per_document_summary")
        self.assertIn("Error generating summary:", call_args["output_data"])
        self.assertEqual(call_args["confidence"], 0.0)
        
        self.mock_context_store.update_document_fields.assert_not_called()
        self.mock_context_store.add_audit_log_entry.assert_called()
    
    @patch('openai.OpenAI')
    def test_empty_text_handling(self, mock_openai):
        """Test handling of documents with empty or None text."""
        # Mock OpenAI client (shouldn't be called)
        mock_openai_instance = mock_openai.return_value
        
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
        
        # Run summarization
        result = self.agent.summarize_classified_documents()
        
        # Check results
        self.assertEqual(result[0], 0)  # No documents successfully summarized
        
        # Verify OpenAI API was not called
        mock_openai_instance.chat.completions.create.assert_not_called()
        
        # Verify documents were marked as skipped
        self.mock_context_store.update_document_fields.assert_any_call(
            "test_empty_id",
            {"processing_status": "summarization_skipped_no_text"}
        )
        self.mock_context_store.update_document_fields.assert_any_call(
            "test_none_id",
            {"processing_status": "summarization_skipped_no_text"}
        )
    
    @patch('openai.OpenAI')
    def test_no_documents_to_summarize(self, mock_openai):
        """Test behavior when no documents need summarization."""
        # Mock OpenAI client (shouldn't be called)
        mock_openai_instance = mock_openai.return_value
        
        # Return empty list from get_documents_by_processing_status
        self.mock_context_store.get_documents_by_processing_status.return_value = []
        
        # Run summarization
        result = self.agent.summarize_classified_documents()
        
        # Check results
        self.assertEqual(result[0], 0)  # No documents successfully summarized
        self.assertEqual(result[1], 0)  # No batch summary generated
        
        # Verify OpenAI API was not called
        mock_openai_instance.chat.completions.create.assert_not_called()
        
        # Verify ContextStore methods were called correctly
        self.mock_context_store.get_documents_by_processing_status.assert_called_once()
        self.mock_context_store.save_agent_output.assert_not_called()
        self.mock_context_store.update_document_fields.assert_not_called()
        self.mock_context_store.add_audit_log_entry.assert_not_called()


if __name__ == '__main__':
    unittest.main()