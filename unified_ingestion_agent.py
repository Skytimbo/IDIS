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
    
    def process_documents_from_folder(self, patient_id: int = 1, session_id: int = 1) -> Tuple[int, List[str]]:
        """
        Process all documents found in the watch folder.
        
        Args:
            patient_id: ID of the patient to associate documents with
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
                success = self._process_single_file(file_path, filename, patient_id, session_id)
                
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
    
    def _process_single_file(self, file_path: str, filename: str, patient_id: int, session_id: int) -> bool:
        """
        Process a single document file through the complete unified pipeline.
        
        Args:
            file_path: Full path to the file
            filename: Name of the file
            patient_id: Patient ID for database association
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
            
            # Step 3: ADAPTER LOGIC - Prepare document data for Context Store
            # This is the "adapter" logic that bridges LLM output to database storage
            db_record = {
                'document_id': str(uuid.uuid4()),
                'patient_id': patient_id,
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
        """Extract text from PDF files using PyMuPDF with OCR fallback for image-based PDFs."""
        try:
            import fitz  # PyMuPDF
            import io
            
            # Try direct text extraction with PyMuPDF
            doc = fitz.open(file_path)
            text = ""
            for page in doc:
                text += page.get_text("text")
            
            # If we got substantial text, return it
            if len(text.strip()) > 50:  # Threshold for "substantial" text
                doc.close()
                self.logger.info(f"Successfully extracted text from PDF using direct method: {file_path}")
                return text
            
            # If little/no text was extracted, try OCR on each page
            self.logger.info(f"PDF appears to be image-based, attempting OCR fallback: {file_path}")
            try:
                import pytesseract
                from PIL import Image
                
                full_text = ""
                for page_num in range(len(doc)):
                    self.logger.debug(f"Processing page {page_num + 1} of {len(doc)} with OCR...")
                    page = doc.load_page(page_num)
                    pix = page.get_pixmap()
                    
                    # Convert pixmap to PIL Image
                    img = Image.open(io.BytesIO(pix.tobytes("png")))
                    
                    # Perform OCR on the image
                    page_text = pytesseract.image_to_string(img, lang='eng')
                    full_text += page_text + "\n\n"
                
                doc.close()
                
                if full_text.strip():
                    self.logger.info(f"Successfully extracted text from PDF using OCR fallback: {file_path}")
                    self.logger.info(f"OCR extracted text length: {len(full_text)} characters")
                    return full_text
                else:
                    self.logger.warning(f"OCR extraction failed to produce text for PDF: {file_path}")
                    return None
                    
            except ImportError:
                self.logger.error("pytesseract not installed. Cannot perform OCR fallback for image-based PDFs.")
                doc.close()
                return None
                
        except ImportError:
            self.logger.error("PyMuPDF not installed. Cannot process PDF files.")
            return None
        except Exception as e:
            self.logger.error(f"Error extracting text from PDF {file_path}: {e}")
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