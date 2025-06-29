"""
Summarizer Agent Module for Intelligent Document Insight System (IDIS)

This module provides the SummarizerAgent class which generates concise summaries
for documents using OpenAI's GPT-4o model.
"""

import os
import logging
from typing import Dict, List, Tuple, Any, Optional
import json
import tiktoken

from openai import OpenAI
from context_store import ContextStore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class SummarizerAgent:
    """
    Agent responsible for generating summaries of documents using OpenAI's GPT-4o.
    
    The SummarizerAgent retrieves classified documents from the Context Store,
    sends their text to OpenAI for summarization, and saves both per-document
    summaries and batch-level summaries back to the Context Store.
    """
    
    def __init__(self, context_store: ContextStore, openai_api_key: Optional[str] = None):
        """
        Initialize the Summarizer Agent with required parameters.
        
        Args:
            context_store: An initialized instance of the ContextStore
            openai_api_key: The OpenAI API key. If not provided, will attempt to read from
                           OPENAI_API_KEY environment variable.
                           
        Raises:
            ValueError: If no API key is available
        """
        self.context_store = context_store
        self.logger = logging.getLogger('SummarizerAgent')
        self.agent_id = "summarizer_agent_v1.0"
        
        # Get API key from parameter or environment variable
        self.api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            error_msg = "No OpenAI API key provided. Please provide as parameter or set OPENAI_API_KEY environment variable."
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Initialize OpenAI client
        self.openai_client = OpenAI(api_key=self.api_key)
        self.logger.info("SummarizerAgent initialized")
    
    def summarize_classified_documents(
        self,
        session_id: Optional[str] = None,
        user_id: str = "summarizer_agent_mvp_user",
        status_to_summarize: str = "classified",
        new_status_after_summarization: str = "summarized"
    ) -> Tuple[int, int]:
        """
        Process documents needing summarization and update their status in the Context Store.
        
        Fetches documents with the specified processing status, generates summaries using OpenAI,
        and saves the summaries back to the Context Store.
        
        Args:
            session_id: Optional session ID for batch-level summary
            user_id: User ID for audit trail purposes
            status_to_summarize: Processing status of documents to retrieve for summarization
            new_status_after_summarization: New processing status to set after summarization
            
        Returns:
            Tuple containing (successfully_summarized_doc_count, batch_summary_generated_bool_as_int)
        """
        self.logger.info(f"Starting summarization batch run for documents with status: {status_to_summarize}")
        
        # Fetch documents that need summarization
        documents = self.context_store.get_documents_by_processing_status(
            processing_status=status_to_summarize
        )
        
        self.logger.info(f"Found {len(documents)} documents to summarize")
        
        successfully_summarized_doc_count = 0
        per_doc_summaries_for_batch = []
        doc_types_for_batch = []
        
        # Process each document
        for document in documents:
            document_id = document["document_id"]
            extracted_text = document.get("extracted_text")
            file_name = document.get("file_name", "Unknown")
            document_type = document.get("document_type", "Unknown")
            
            # Skip documents with no extracted text
            if not extracted_text:
                self.logger.warning(f"Document {document_id} ({file_name}) has no extracted text")
                
                # Update document status to indicate it was skipped
                self.context_store.update_document_fields(
                    document_id, 
                    {"processing_status": "summarization_skipped_no_text"}
                )
                
                # Add audit log entry
                self.context_store.add_audit_log_entry(
                    user_id=user_id,
                    event_type="AGENT_ACTIVITY",
                    event_name="DOCUMENT_SUMMARIZATION_SKIPPED",
                    status="SKIPPED",
                    resource_type="document",
                    resource_id=document_id,
                    details="Document skipped due to no extracted text"
                )
                
                continue
            
            # Add document type to batch context
            if document_type != "Unknown" and document_type != "Unclassified":
                doc_types_for_batch.append(document_type)
            
            # Generate per-document summary
            summary_text, api_call_confidence = self._generate_summary(extracted_text)
            
            # Save the summary output
            output_id = self.context_store.save_agent_output(
                document_id=document_id,
                agent_id=self.agent_id,
                output_type="per_document_summary",
                output_data=summary_text,
                confidence=api_call_confidence
            )
            
            # Update document status if summary was successful
            if api_call_confidence > 0:
                self.context_store.update_document_fields(
                    document_id,
                    {"processing_status": new_status_after_summarization}
                )
                
                # Add successful summary to batch collection
                per_doc_summaries_for_batch.append(summary_text)
                successfully_summarized_doc_count += 1
            
            # Add audit log entry
            status = "SUCCESS" if api_call_confidence > 0 else "FAILURE"
            self.context_store.add_audit_log_entry(
                user_id=user_id,
                event_type="AGENT_ACTIVITY",
                event_name="DOCUMENT_SUMMARIZED",
                status=status,
                resource_type="document",
                resource_id=document_id,
                details=f"Document summarized with confidence {api_call_confidence}"
            )
        
        # Generate batch-level summary if session_id and per-document summaries are available
        batch_summary_generated_bool_as_int = 0
        if session_id and per_doc_summaries_for_batch:
            # Get most common document types
            doc_type_counts = {}
            for doc_type in doc_types_for_batch:
                doc_type_counts[doc_type] = doc_type_counts.get(doc_type, 0) + 1
            
            # Sort by count and take top 3
            dominant_types = sorted(doc_type_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            dominant_types_str = ", ".join([doc_type for doc_type, _ in dominant_types])
            
            # Create batch summary
            batch_summary_text, batch_api_confidence = self._generate_batch_summary(
                per_doc_summaries_for_batch, 
                dominant_types_str
            )
            
            if batch_api_confidence > 0:
                # Update session metadata with batch summary
                self.context_store.update_session_metadata(
                    session_id,
                    {
                        "batch_summary": batch_summary_text,
                        "batch_summary_agent_id": self.agent_id,
                        "summarized_document_count": successfully_summarized_doc_count
                    }
                )
                
                # Add audit log entry
                self.context_store.add_audit_log_entry(
                    user_id=user_id,
                    event_type="AGENT_ACTIVITY",
                    event_name="BATCH_SUMMARIZED",
                    status="SUCCESS",
                    resource_type="session",
                    resource_id=session_id,
                    details=f"Batch summary generated for {successfully_summarized_doc_count} documents"
                )
                
                batch_summary_generated_bool_as_int = 1
                self.logger.info(f"Batch summary generated for session {session_id}")
        
        self.logger.info(f"Summarization batch run complete. "
                        f"Successfully summarized: {successfully_summarized_doc_count}, "
                        f"Batch summary generated: {batch_summary_generated_bool_as_int}")
        
        return (successfully_summarized_doc_count, batch_summary_generated_bool_as_int)
    
    def _generate_summary(self, text: str, style: str = "neutral", length: str = "2-3 sentences") -> Tuple[str, float]:
        """
        Generate a summary for a document using OpenAI's GPT-4o.
        
        Args:
            text: The document text to summarize
            style: Summary style (default: "neutral")
            length: Summary length specification (default: "2-3 sentences")
            
        Returns:
            Tuple containing (summary_text, confidence)
            confidence will be 1.0 for successful API calls, 0.0 for failed calls
        """
        # Token-based truncation using tiktoken
        try:
            encoding = tiktoken.encoding_for_model("gpt-4o")
            tokens = encoding.encode(text)
            if len(tokens) > 3500:  # Leave room for prompt and response
                truncated_text = encoding.decode(tokens[:3500])
            else:
                truncated_text = text
        except Exception as e:
            self.logger.warning(f"tiktoken encoding failed, falling back to character limit: {e}")
            truncated_text = text[:4000] if len(text) > 4000 else text
        
        # Create prompt for summarization with customizable parameters
        prompt_text = f"Summarize the following document text in {length} {style}, fact-based sentences:\n\n---\n{truncated_text}\n---"
        
        # Select model based on text complexity and length
        if len(truncated_text) < 1000:
            model = "gpt-3.5-turbo"  # Cheaper for short documents
            max_tokens = 150
        else:
            model = "gpt-4o"  # Better for complex/long documents
            max_tokens = 200
        
        # Add logging for model selection
        self.logger.debug(f"Using model {model} for document of length {len(truncated_text)}")
        
        try:
            # Call OpenAI API
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = self.openai_client.chat.completions.create(
                model=model,  # Now dynamic
                messages=[{"role": "user", "content": prompt_text}],
                temperature=0.3,
                max_tokens=max_tokens
            )
            
            # Extract summary from response
            summary_text = response.choices[0].message.content.strip()
            
            self.logger.info(f"Summary generated successfully, length: {len(summary_text)} chars")
            return summary_text, 1.0
            
        except Exception as e:
            self.logger.error(f"Error generating summary with OpenAI: {str(e)}")
            return f"Error generating summary: {str(e)[:100]}...", 0.0
    
    def _generate_batch_summary(self, per_doc_summaries: List[str], dominant_types: str, style: str = "neutral", length: str = "1-2 sentence") -> Tuple[str, float]:
        """
        Generate a batch-level summary for a set of documents.
        
        Args:
            per_doc_summaries: List of per-document summaries
            dominant_types: String containing the dominant document types
            style: Summary style (default: "neutral")
            length: Summary length specification (default: "1-2 sentence")
            
        Returns:
            Tuple containing (batch_summary_text, confidence)
            confidence will be 1.0 for successful API calls, 0.0 for failed calls
        """
        # Combine per-document summaries with token-based truncation
        combined_summaries = "; ".join(per_doc_summaries)
        
        # Token-based truncation for combined summaries
        try:
            encoding = tiktoken.encoding_for_model("gpt-4o")
            tokens = encoding.encode(combined_summaries)
            if len(tokens) > 800:  # Leave more room for batch context
                truncated_summaries = encoding.decode(tokens[:800])
            else:
                truncated_summaries = combined_summaries
        except Exception as e:
            self.logger.warning(f"tiktoken encoding failed for batch summary, falling back to character limit: {e}")
            truncated_summaries = combined_summaries[:1000] if len(combined_summaries) > 1000 else combined_summaries
        
        # Create prompt for batch summarization with customizable parameters
        prompt_text = (
            f"Provide a brief ({length}) {style}, fact-based overview of a batch of documents. "
            f"The batch includes: {len(per_doc_summaries)} documents, with types like {dominant_types}. "
            f"The content is generally about: {truncated_summaries}"
        )
        
        # Select model based on complexity (batch summaries are typically simpler)
        if len(truncated_summaries) < 500:
            model = "gpt-3.5-turbo"  # Cheaper for simple batch summaries
            max_tokens = 80
        else:
            model = "gpt-4o"  # Better for complex batch analysis
            max_tokens = 100
        
        # Add logging for model selection
        self.logger.debug(f"Using model {model} for batch summary of length {len(truncated_summaries)}")
        
        try:
            # Call OpenAI API
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = self.openai_client.chat.completions.create(
                model=model,  # Now dynamic
                messages=[{"role": "user", "content": prompt_text}],
                temperature=0.3,
                max_tokens=max_tokens
            )
            
            # Extract batch summary from response
            batch_summary_text = response.choices[0].message.content.strip()
            
            self.logger.info(f"Batch summary generated successfully, length: {len(batch_summary_text)} chars")
            return batch_summary_text, 1.0
            
        except Exception as e:
            self.logger.error(f"Error generating batch summary with OpenAI: {str(e)}")
            return f"Error generating batch summary: {str(e)[:100]}...", 0.0