"""
Classifier Agent Module for Intelligent Document Insight System (IDIS)

This module provides the ClassifierAgent class which classifies documents
based on their extracted text using keyword-based rules.
"""

import re
import logging
from typing import Dict, List, Tuple, Any, Optional

from context_store import ContextStore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class ClassifierAgent:
    """
    Agent responsible for classifying documents based on their extracted text.
    
    The ClassifierAgent retrieves documents that need classification from the Context Store,
    applies keyword-based rules to determine the document type and classification confidence,
    and updates the document record in the Context Store accordingly.
    """
    
    def __init__(self, context_store: ContextStore, classification_rules: Dict[str, List[str]]):
        """
        Initialize the Classifier Agent with required parameters.
        
        Args:
            context_store: An initialized instance of the ContextStore
            classification_rules: A dictionary defining the classification logic
                Keys are document_type strings (e.g., "Invoice", "Medical Record")
                Values are lists of keywords or regex patterns as strings
        """
        self.context_store = context_store
        self.classification_rules = classification_rules
        self.logger = logging.getLogger('ClassifierAgent')
        self.agent_id = "classifier_agent_v1.0"
        
        # Pre-compile regex patterns for efficiency
        self.compiled_rules = {}
        for doc_type, keywords in self.classification_rules.items():
            self.compiled_rules[doc_type] = [
                re.compile(keyword, re.IGNORECASE) for keyword in keywords
            ]
        
        self.logger.info("ClassifierAgent initialized with rules for document types: %s", 
                         list(classification_rules.keys()))
    
    def process_documents_for_classification(
        self,
        user_id: str = "classifier_agent_mvp_user",
        status_to_classify: str = "ingested",
        new_status_after_classification: str = "classified"
    ) -> Tuple[int, int]:
        """
        Process documents needing classification and update their status in the Context Store.
        
        Fetches documents with the specified processing status, applies classification rules,
        and updates their document_type, classification_confidence, and processing_status.
        
        Args:
            user_id: User ID for audit trail purposes
            status_to_classify: Processing status of documents to retrieve for classification
            new_status_after_classification: New processing status to set after classification
            
        Returns:
            Tuple containing (successfully_classified_count, failed_to_classify_count)
        """
        self.logger.info(f"Starting classification batch run for documents with status: {status_to_classify}")
        
        # Fetch documents that need classification
        documents = self.context_store.get_documents_by_processing_status(
            processing_status=status_to_classify
        )
        
        self.logger.info(f"Found {len(documents)} documents to classify")
        
        successfully_classified_count = 0
        failed_to_classify_count = 0
        
        # Process each document
        for document in documents:
            document_id = document["document_id"]
            extracted_text = document.get("extracted_text")
            file_name = document.get("file_name", "Unknown")
            
            # Skip documents with no extracted text
            if not extracted_text:
                self.logger.warning(f"Document {document_id} ({file_name}) has no extracted text")
                classified_type = "Unclassified"
                assigned_confidence = None
                failed_to_classify_count += 1
            else:
                # Apply classification rules
                classified_type, assigned_confidence = self._classify_document(extracted_text)
                
                if classified_type == "Unclassified":
                    failed_to_classify_count += 1
                else:
                    successfully_classified_count += 1
            
            # Update document in Context Store
            self.logger.info(f"Classifying document {document_id} ({file_name}) as {classified_type} with confidence {assigned_confidence}")
            
            update_data = {
                "document_type": classified_type,
                "classification_confidence": assigned_confidence,
                "processing_status": new_status_after_classification
            }
            
            update_success = self.context_store.update_document_fields(document_id, update_data)
            
            if update_success:
                # Add audit log entry
                self.context_store.add_audit_log_entry(
                    user_id=user_id,
                    event_type="AGENT_ACTIVITY",
                    event_name="DOCUMENT_CLASSIFIED",
                    status="SUCCESS",
                    resource_type="document",
                    resource_id=document_id,
                    details=f"Classified as {classified_type} with confidence {assigned_confidence}"
                )
            else:
                self.logger.error(f"Failed to update document {document_id} in Context Store")
        
        self.logger.info(f"Classification batch run complete. "
                         f"Successful: {successfully_classified_count}, "
                         f"Failed: {failed_to_classify_count}")
        
        return (successfully_classified_count, failed_to_classify_count)
    
    def _classify_document(self, text: str) -> Tuple[str, Optional[str]]:
        """
        Classify a document based on its extracted text.
        
        Args:
            text: The extracted text from the document
            
        Returns:
            Tuple containing (document_type, confidence)
            document_type will be "Unclassified" if no rules match
            confidence will be "Medium" for matched rules, None for unclassified
        """
        # Apply each rule set
        for doc_type, patterns in self.compiled_rules.items():
            for pattern in patterns:
                if pattern.search(text):
                    # First match wins for simplicity in MVP
                    return doc_type, "Medium"
        
        # If no rules matched
        return "Unclassified", None