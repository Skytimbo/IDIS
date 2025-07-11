"""
Unified Ingestion Agent Module for Intelligent Document Insight System (IDIS)

This module provides a unified approach that combines document ingestion with 
LLM-powered cognitive processing using the CognitiveAgent for complete document analysis.
"""

import os
import logging
import shutil
import json
import uuid
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any
from PIL import Image

# Import required components
from context_store import ContextStore
from agents.cognitive_agent import CognitiveAgent

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class UnifiedIngestionAgent:
    """
    Unified agent that combines document ingestion with cognitive processing.
    
    This agent processes documents through a complete pipeline:
    1. Text extraction from various formats (PDF, DOCX, TXT, images)
    2. LLM-powered structured data extraction using CognitiveAgent
    3. Storage of both raw text and structured JSON data in Context Store
    """
    
    def __init__(self, context_store: ContextStore, watch_folder: str, holding_folder: str):
        """
        Initialize the Unified Ingestion Agent.
        
        Args:
            context_store: An initialized instance of the ContextStore
            watch_folder: Path to the directory to monitor for new files
            holding_folder: Path to the directory where unprocessable files will be moved
        """
        self.context_store = context_store
        self.watch_folder = watch_folder
        self.holding_folder = holding_folder
        self.logger = logging.getLogger('UnifiedIngestionAgent')
        self.agent_id = "unified_ingestion_agent_v1.0"
        
        # Strategy pattern for text extraction
        self.extractors = {
            'txt': self._extract_text_from_txt,
            'pdf': self._extract_text_from_pdf,
            'docx': self._extract_text_from_docx,
            'jpg': self._extract_text_from_image,
            'jpeg': self._extract_text_from_image,
            'png': self._extract_text_from_image,
            'tiff': self._extract_text_from_image,
            'bmp': self._extract_text_from_image,
        }
        
        # Initialize the CognitiveAgent
        self.cognitive_agent = CognitiveAgent()
        
        # Ensure directories exist
        os.makedirs(self.watch_folder, exist_ok=True)
        os.makedirs(self.holding_folder, exist_ok=True)
        
        self.logger.info(f"UnifiedIngestionAgent initialized with watch folder: {self.watch_folder}")
    
    def apply_heuristic_rules(self, extracted_data: Dict[str, Any], full_text: str) -> Dict[str, Any]:
        """
        Apply rule-based heuristics to improve document classification accuracy.
        
        This function applies keyword-based rules to override AI classifications when the AI
        produces generic document types like "Correspondence" or "Unknown". It provides a
        scalable way to improve classification accuracy through targeted rule matching.
        
        Args:
            extracted_data: The structured data extracted by the CognitiveAgent
            full_text: The full text content of the document
            
        Returns:
            Updated extracted_data with potentially corrected document classification
        """
        # Rule definitions - easily expandable for new document types
        heuristic_rules = [
            {
                "keywords": ["payslip", "paystub", "pay period", "gross pay", "net pay", "salary", "wages", "employee", "employer", "deductions"],
                "document_type": "Payslip",
                "confidence": 0.9
            },
            {
                "keywords": ["electric", "electricity", "power", "kwh", "utility", "gci", "homer electric", "alaska electric", "aml&p", "chugach"],
                "document_type": "Utility Bill",
                "confidence": 0.85
            },
            {
                "keywords": ["bank statement", "checking account", "savings account", "balance", "deposit", "withdrawal", "account number"],
                "document_type": "Bank Statement",
                "confidence": 0.85
            },
            {
                "keywords": ["receipt", "purchase", "total", "tax", "store", "retail", "transaction"],
                "document_type": "Receipt",
                "confidence": 0.8
            },
            {
                "keywords": ["invoice", "bill", "amount due", "payment terms", "invoice number", "due date"],
                "document_type": "Invoice",
                "confidence": 0.8
            }
        ]
        
        # Get current AI classification
        current_classification = extracted_data.get('document_type', {})
        if not isinstance(current_classification, dict):
            current_classification = {}
            
        current_type = current_classification.get('predicted_class', '').lower()
        
        # Generic types that should be overridden by heuristics
        generic_types = ['correspondence', 'unknown', 'document', 'text', 'file']
        
        # Only apply heuristics if the AI classification is generic or has low confidence
        current_confidence = current_classification.get('confidence_score', 0.0)
        should_apply_heuristics = (
            current_type in generic_types or 
            current_confidence < 0.7 or 
            not current_type
        )
        
        if should_apply_heuristics:
            full_text_lower = full_text.lower()
            
            # Check each rule for keyword matches
            for rule in heuristic_rules:
                keywords_found = [keyword for keyword in rule['keywords'] if keyword in full_text_lower]
                
                # If we found keywords for this rule, apply it
                if keywords_found:
                    self.logger.info(f"Heuristic Rules Engine: Matched keywords {keywords_found} for {rule['document_type']}")
                    self.logger.info(f"Overriding AI classification '{current_type}' with '{rule['document_type']}'")
                    
                    # Update the document type classification
                    extracted_data['document_type'] = {
                        'predicted_class': rule['document_type'],
                        'confidence_score': rule['confidence']
                    }
                    
                    # Add heuristic metadata to track rule application
                    if 'heuristic_metadata' not in extracted_data:
                        extracted_data['heuristic_metadata'] = {}
                    
                    extracted_data['heuristic_metadata']['rule_applied'] = True
                    extracted_data['heuristic_metadata']['matched_keywords'] = keywords_found
                    extracted_data['heuristic_metadata']['original_classification'] = current_type
                    extracted_data['heuristic_metadata']['rule_type'] = rule['document_type']
                    
                    break  # Apply the first matching rule
        
        return extracted_data
    
    def process_documents_from_folder(self, entity_id: int = 1, session_id: int = 1) -> Tuple[int, List[str]]:
        """
        Process all documents found in the watch folder.
        
        Args:
            entity_id: ID of the entity to associate documents with
            session_id: ID of the session to associate documents with
            
        Returns:
            Tuple of (successfully_processed_count, list_of_error_messages)
        """
        processed_count = 0
        error_messages = []
        
        try:
            files = [f for f in os.listdir(self.watch_folder) 
                    if os.path.isfile(os.path.join(self.watch_folder, f)) and not f.startswith('.')]
        except Exception as e:
            error_msg = f"Error listing files in watch folder: {e}"
            self.logger.error(error_msg)
            return 0, [error_msg]
        
        self.logger.info(f"Found {len(files)} files to process")
        
        for filename in files:
            try:
                file_path = os.path.join(self.watch_folder, filename)
                success = self._process_single_file(file_path, filename, entity_id, session_id)
                
                if success:
                    processed_count += 1
                    self.logger.info(f"Successfully processed: {filename}")
                    # Remove processed file
                    os.remove(file_path)
                else:
                    error_msg = f"Failed to process file: {filename}"
                    error_messages.append(error_msg)
                    self.logger.error(error_msg)
                    # Move problematic file to holding folder
                    self._move_to_holding(file_path, filename)
                    
            except Exception as e:
                error_msg = f"Unexpected error processing {filename}: {e}"
                error_messages.append(error_msg)
                self.logger.error(error_msg)
                try:
                    self._move_to_holding(file_path, filename)
                except:
                    pass  # Don't let move errors break the main loop
        
        self.logger.info(f"Document processing complete. Successfully processed: {processed_count}")
        return processed_count, error_messages
    
    def _process_single_file(self, file_path: str, filename: str, entity_id: int, session_id: int) -> bool:
        """
        Process a single document file through the complete unified pipeline.
        
        Args:
            file_path: Full path to the file
            filename: Name of the file
            entity_id: Entity ID for database association
            session_id: Session ID for database association
            
        Returns:
            True if processing was successful, False otherwise
        """
        try:
            # V1 list of document types that require manual categorization by a human
            HITL_TRIGGER_TYPES = ["Receipt", "Invoice", "Correspondence", "Bank Deposit Slip"]
            
            # Step 1: Extract text from the document
            file_extension = os.path.splitext(filename)[1].lower()
            extracted_text = self._extract_text_from_file(file_path, file_extension)
            
            if not extracted_text or not extracted_text.strip():
                self.logger.warning(f"No text extracted from {filename}")
                return False
            
            self.logger.info(f"Extracted {len(extracted_text)} characters from {filename}")
            
            # Step 2: Use CognitiveAgent to extract structured data
            structured_data = self.cognitive_agent.extract_structured_data(extracted_text)
            
            if not structured_data or "error" in structured_data:
                self.logger.warning(f"CognitiveAgent failed to extract structured data from {filename}")
                return False
            
            # Step 2.5: Apply Heuristic Rules Engine to improve classification accuracy
            structured_data = self.apply_heuristic_rules(structured_data, extracted_text)
            
            # Step 3: ADAPTER LOGIC - Prepare document data for Context Store
            # This is the "adapter" logic that bridges LLM output to database storage
            db_record = {
                'document_id': str(uuid.uuid4()),
                'entity_id': entity_id,
                'session_id': session_id,
                'file_name': os.path.basename(file_path),
                'original_file_type': file_extension.lstrip('.'),
                'original_watchfolder_path': file_path,
                'ingestion_status': 'ingestion_successful',
                'processing_status': 'processing_complete',
                'upload_timestamp': datetime.now().isoformat(),
                
                # --- Populating legacy fields for UI compatibility ---
                'document_type': structured_data.get('document_type', {}).get('predicted_class'),
                'issuer_source': structured_data.get('issuer', {}).get('name'),
                'tags_extracted': None,  # Will be populated below
                
                # --- Storing the new rich data ---
                'extracted_data': json.dumps(structured_data),  # Convert the full dict to a JSON string
                'full_text': extracted_text  # The full text is the single source of truth
            }
            
            # Enhanced legacy field extraction with error handling
            if isinstance(structured_data, dict):
                # Extract tags from filing information
                filing_info = structured_data.get('filing', {})
                if isinstance(filing_info, dict) and 'suggested_tags' in filing_info:
                    tags = filing_info['suggested_tags']
                    if isinstance(tags, list) and tags:
                        db_record['tags_extracted'] = ', '.join(str(tag) for tag in tags)
                
                # Extract recipient information if available
                recipient_info = structured_data.get('recipient', {})
                if isinstance(recipient_info, dict) and 'name' in recipient_info:
                    db_record['recipient'] = recipient_info['name']
                
                # Extract key dates if available
                dates_info = structured_data.get('key_dates', {})
                if isinstance(dates_info, dict) and 'primary_date' in dates_info:
                    db_record['document_dates'] = dates_info['primary_date']
            
            # Set status based on whether the doc type is in our HITL trigger list
            if db_record.get('document_type') in HITL_TRIGGER_TYPES:
                db_record['processing_status'] = 'pending_categorization'
            
            # Use the prepared record instead of document_data
            document_data = db_record
            
            # Step 4: Add document to Context Store with enhanced logging
            self.logger.info(f"Adapter processed structured data for {filename}:")
            self.logger.info(f"  Document type: {db_record.get('document_type', 'Unknown')}")
            self.logger.info(f"  Issuer: {db_record.get('issuer_source', 'Unknown')}")
            self.logger.info(f"  Tags: {db_record.get('tags_extracted', 'None')}")
            
            document_id = self.context_store.add_document(document_data)
            
            if document_id:
                self.logger.info(f"Successfully processed and saved document. DB ID: {document_id}")
                self.logger.info(f"Rich JSON data stored in extracted_data field for enhanced search capabilities")
                return True
            else:
                self.logger.error(f"Failed to add document to context store: {filename}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error processing file {filename}: {e}")
            return False
    
    def _extract_text_from_file(self, file_path: str, file_extension: str) -> Optional[str]:
        """
        Extract text content from various file formats using a strategy pattern.
        """
        file_extension = file_extension.lower().lstrip('.')
        
        extractor_func = self.extractors.get(file_extension)
        
        if extractor_func:
            try:
                return extractor_func(file_path)
            except Exception as e:
                self.logger.error(f"Error extracting text from {file_path} using {extractor_func.__name__}: {e}")
                return None
        else:
            self.logger.warning(f"Unsupported file type: {file_extension}")
            return None
    
    def _extract_text_from_txt(self, file_path: str) -> Optional[str]:
        """Extract text from TXT files."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                return file.read()
        except Exception as e:
            self.logger.error(f"Error reading TXT file {file_path}: {e}")
            return None
    
    def _extract_text_from_pdf(self, file_path: str) -> Optional[str]:
        """
        Extract text from a PDF using a competitive strategy: try both direct
        extraction and OCR, then return the result with the most text.
        """
        import os
        direct_text = ""
        ocr_text = ""
        
        try:
            import fitz  # PyMuPDF
            
            with fitz.open(file_path) as doc:
                # Method 1: Direct Text Extraction
                try:
                    for page in doc:
                        direct_text += page.get_text("text")
                    self.logger.debug(f"Direct text extraction yielded {len(direct_text.strip())} chars.")
                except Exception as e:
                    self.logger.warning(f"Direct text extraction failed for {file_path}: {e}")

                # Method 2: OCR Extraction
                try:
                    import pytesseract
                    import io
                    from PIL import Image

                    for page_num in range(len(doc)):
                        page = doc.load_page(page_num)
                        pix = page.get_pixmap()
                        img = Image.open(io.BytesIO(pix.tobytes("png")))
                        ocr_text += pytesseract.image_to_string(img, lang='eng') + "\n\n"
                    self.logger.debug(f"OCR extraction yielded {len(ocr_text.strip())} chars.")
                except Exception as e:
                    self.logger.warning(f"OCR extraction failed for {file_path}: {e}")

        except Exception as e:
            self.logger.exception(f"A critical error occurred opening or processing PDF {file_path}")
            return None

        # Compare results and return the best one
        if len(direct_text.strip()) > len(ocr_text.strip()):
            self.logger.info(f"Using direct extraction result for {os.path.basename(file_path)}")
            return direct_text
        elif len(ocr_text.strip()) > 0:
            self.logger.info(f"Using OCR extraction result for {os.path.basename(file_path)}")
            return ocr_text
        else:
            self.logger.error(f"Both direct and OCR text extraction failed for {file_path}")
            return None
    
    def _extract_text_from_docx(self, file_path: str) -> Optional[str]:
        """Extract text from DOCX files using python-docx."""
        try:
            from docx import Document
            doc = Document(file_path)
            text = []
            for paragraph in doc.paragraphs:
                text.append(paragraph.text)
            return '\n'.join(text)
        except ImportError:
            self.logger.error("python-docx not installed. Cannot process DOCX files.")
            return None
        except Exception as e:
            self.logger.error(f"Error extracting text from DOCX {file_path}: {e}")
            return None
    
    def _extract_text_from_image(self, file_path: str) -> Optional[str]:
        """Extract text from image files using pytesseract OCR."""
        try:
            import pytesseract
            from PIL import Image
            
            image = Image.open(file_path)
            text = pytesseract.image_to_string(image)
            return text
        except ImportError:
            self.logger.error("pytesseract not installed. Cannot process image files.")
            return None
        except Exception as e:
            self.logger.error(f"Error extracting text from image {file_path}: {e}")
            return None
    
    def _move_to_holding(self, file_path: str, filename: str):
        """Move a problematic file to the holding folder."""
        try:
            holding_path = os.path.join(self.holding_folder, filename)
            shutil.move(file_path, holding_path)
            self.logger.info(f"Moved problematic file to holding folder: {holding_path}")
        except Exception as e:
            self.logger.error(f"Error moving file to holding folder: {e}")