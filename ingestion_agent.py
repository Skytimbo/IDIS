"""
Ingestion Agent Module for Intelligent Document Insight System (IDIS)

This module provides the IngestionAgent class which monitors a watchfolder for new documents,
processes various file types (PDF, DOCX, TXT, images) to extract their text content,
and stores the extracted information in the Context Store.
"""

import os
import logging
import shutil
import io
from typing import Optional, Tuple, List, Set, Dict, Any
from PIL import Image

# Import the ContextStore class and CognitiveAgent
from context_store import ContextStore
from agents.cognitive_agent import CognitiveAgent

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Comprehensive suppression of noisy third-party PDF and font libraries
noisy_loggers = ['fontTools', 'fpdf2', 'reportlab']
for logger_name in noisy_loggers:
    logging.getLogger(logger_name).setLevel(logging.WARNING)


class IngestionAgent:
    """
    Agent responsible for monitoring and processing documents placed in a watchfolder.
    
    The IngestionAgent extracts text from various document formats (PDF, DOCX, TXT, images)
    and stores this information along with relevant metadata in the Context Store.
    It also handles problematic files by moving them to a holding folder.
    """
    
    def __init__(self, context_store: ContextStore, watch_folder: str, holding_folder: str):
        """
        Initialize the Ingestion Agent with required parameters.
        
        Args:
            context_store: An initialized instance of the ContextStore
            watch_folder: Path to the directory to monitor for new files
            holding_folder: Path to the directory where unprocessable files will be moved
        """
        self.context_store = context_store
        self.watch_folder = watch_folder
        self.holding_folder = holding_folder
        self.logger = logging.getLogger('IngestionAgent')
        self.agent_id = "ingestion_agent_v1.0"
        
        # Ensure directories exist
        os.makedirs(self.watch_folder, exist_ok=True)
        os.makedirs(self.holding_folder, exist_ok=True)
        
        self.logger.info(f"IngestionAgent initialized - watching folder: {watch_folder}")
    
    def process_pending_documents(self, session_id: Optional[str] = None, 
                                  entity_id: Optional[str] = None,
                                  user_id: str = "ingestion_agent_mvp_user") -> List[str]:
        """
        Scan the watchfolder and process all pending documents.
        
        For each document found, this method:
        1. Creates an initial record in the Context Store
        2. Attempts to extract text based on file type
        3. Updates the document record with extracted text and status
        4. Moves unprocessable files to the holding folder
        
        Args:
            session_id: Optional session ID to associate with processed documents
            entity_id: Optional entity ID to associate with processed documents
            user_id: User ID for audit trail purposes
            
        Returns:
            List of document IDs that were successfully processed
        """
        self.logger.info(f"Starting document processing scan of watch folder: {self.watch_folder}")
        
        # Track processed files to avoid duplication within this run
        processed_files: Set[str] = set()
        successful_document_ids: List[str] = []
        
        # Get all files in the watchfolder
        try:
            files = [f for f in os.listdir(self.watch_folder) 
                     if os.path.isfile(os.path.join(self.watch_folder, f))]
        except Exception as e:
            self.logger.error(f"Error accessing watchfolder {self.watch_folder}: {str(e)}")
            return []
        
        self.logger.info(f"Found files in watch folder: {files}")
        self.logger.info(f"Total file count: {len(files)}")
        
        for filename in files:
            if filename in processed_files:
                self.logger.info(f"Skipping already processed file: {filename}")
                continue
            
            file_path = os.path.join(self.watch_folder, filename)
            processed_files.add(filename)
            
            # Determine file type from extension using shared method
            file_type_category = self._determine_file_type(filename)
            file_type = os.path.splitext(filename)[1].lower()
            file_type = file_type[1:] if file_type.startswith('.') else file_type
            
            self.logger.info(f"Processing file: {filename} (Type: {file_type_category})")
            
            # Create initial document record
            document_data = {
                'file_name': filename,
                'original_file_type': file_type,
                'original_watchfolder_path': file_path,
                'ingestion_status': 'pending_ingestion',
                'processing_status': 'new',
                'entity_id': entity_id,
                'session_id': session_id
            }
            
            self.logger.info(f"About to add document to context store: {document_data}")
            
            document_id = None
            
            try:
                document_id = self.context_store.add_document(document_data)
                self.logger.info(f"Successfully added document to context store - ID: {document_id}, filename: {filename}")
                
                # Add audit log entry for processing start
                self.context_store.add_audit_log_entry(
                    user_id=user_id,
                    event_type="AGENT_ACTIVITY",
                    event_name="START_DOCUMENT_INGESTION",
                    status="INFO",
                    resource_type="document",
                    resource_id=document_id,
                    details=f"Started ingestion of {filename}"
                )
                
                # Extract text from file
                extracted_text, confidence = self._extract_text_from_file(file_path, file_type_category)
                
                if extracted_text:
                    # Update document with extracted text and successful status
                    update_data = {
                        'full_text': extracted_text,
                        'ingestion_status': 'ingestion_successful',
                        'processing_status': 'ingested'
                    }
                    
                    # Update the document in the database with error handling
                    try:
                        update_success = self.context_store.update_document_fields(document_id, update_data)
                        if not update_success:
                            self.logger.error(f"Failed to update document {document_id} in database - update returned False")
                            raise Exception("Database update returned False")
                        else:
                            self.logger.info(f"Successfully saved {len(extracted_text)} characters to full_text for document {document_id}")
                    except Exception as e:
                        self.logger.error(f"Critical error updating document {document_id} in database: {e}")
                        # Move file to holding folder since database update failed
                        holding_path = os.path.join(self.holding_folder, filename)
                        shutil.move(file_path, holding_path)
                        self.logger.error(f"Moved {filename} to holding folder due to database update failure")
                        continue
                    
                    # Add audit log entry for successful processing
                    self.context_store.add_audit_log_entry(
                        user_id=user_id,
                        event_type="AGENT_ACTIVITY",
                        event_name="COMPLETE_DOCUMENT_INGESTION",
                        status="SUCCESS",
                        resource_type="document",
                        resource_id=document_id,
                        details=f"Successfully ingested {filename} with confidence {confidence}%"
                    )
                    
                    self.logger.info(f"Successfully ingested document: {filename} (ID: {document_id})")
                    successful_document_ids.append(document_id)
                    
                else:
                    # Move file to holding folder and update status to failed
                    holding_path = os.path.join(self.holding_folder, filename)
                    shutil.move(file_path, holding_path)
                    
                    self.context_store.update_document_fields(
                        document_id, 
                        {'ingestion_status': 'ingestion_failed'}
                    )
                    
                    # Add audit log entry for failed processing
                    self.context_store.add_audit_log_entry(
                        user_id=user_id,
                        event_type="AGENT_ACTIVITY",
                        event_name="COMPLETE_DOCUMENT_INGESTION",
                        status="FAILURE",
                        resource_type="document",
                        resource_id=document_id,
                        details=f"Failed to extract text from {filename}"
                    )
                    
                    self.logger.warning(
                        f"Failed to extract text from document: {filename} (ID: {document_id}). "
                        f"Moved to holding folder: {holding_path}"
                    )
            
            except Exception as e:
                self.logger.error(f"Error processing file {filename}: {str(e)}")
                
                # If we already created a document record, update it to failed
                if document_id:
                    try:
                        self.context_store.update_document_fields(
                            document_id, 
                            {'ingestion_status': 'ingestion_failed'}
                        )
                        
                        self.context_store.add_audit_log_entry(
                            user_id=user_id,
                            event_type="AGENT_ACTIVITY",
                            event_name="COMPLETE_DOCUMENT_INGESTION",
                            status="ERROR",
                            resource_type="document",
                            resource_id=document_id,
                            details=f"Error processing {filename}: {str(e)}"
                        )
                    except Exception as inner_e:
                        self.logger.error(f"Error updating document status: {str(inner_e)}")
                
                # Try to move the file to holding folder if it exists
                try:
                    if os.path.exists(file_path):
                        holding_path = os.path.join(self.holding_folder, filename)
                        shutil.move(file_path, holding_path)
                        self.logger.info(f"Moved problematic file to holding folder: {holding_path}")
                except Exception as move_e:
                    self.logger.error(f"Error moving file to holding folder: {str(move_e)}")
        
        self.logger.info(f"Document processing scan complete. Successfully processed: {len(successful_document_ids)}")
        return successful_document_ids
    
    def process_specific_files(
        self, 
        file_paths: List[str], 
        session_id: str, 
        entity_id: Optional[str] = None, 
        user_id: str = "system_watcher"
    ) -> int:
        """
        Process a specific list of file paths through the ingestion pipeline.
        
        Args:
            file_paths: List of absolute paths to files to process
            session_id: Session ID to associate documents with
            entity_id: Optional entity ID to associate documents with
            user_id: User ID for audit trail purposes
            
        Returns:
            Number of successfully processed documents
        """
        self.logger.info(f"Starting processing of {len(file_paths)} specific files")
        
        successful_document_ids = []
        
        for file_path in file_paths:
            if not os.path.exists(file_path):
                self.logger.warning(f"File does not exist: {file_path}")
                continue
                
            if not os.path.isfile(file_path):
                self.logger.warning(f"Path is not a file: {file_path}")
                continue
            
            filename = os.path.basename(file_path)
            document_id = None
            
            try:
                # Determine file type
                file_type = self._determine_file_type(filename)
                
                # Add document to context store first
                document_data = {
                    'file_name': filename,
                    'original_file_type': file_type,
                    'ingestion_status': 'ingestion_pending',
                    'processing_status': 'new',
                    'entity_id': entity_id,
                    'session_id': session_id,
                    'original_watchfolder_path': file_path  # Store original path for reference
                }
                
                document_id = self.context_store.add_document(document_data)
                self.logger.info(f"Created document record with ID: {document_id} for file: {filename}")
                
                # Add audit log entry for document creation
                self.context_store.add_audit_log_entry(
                    user_id=user_id,
                    event_type="AGENT_ACTIVITY",
                    event_name="START_DOCUMENT_INGESTION",
                    status="SUCCESS",
                    resource_type="document",
                    resource_id=document_id,
                    details=f"Starting ingestion of {filename}"
                )
                
                # Extract text from the file
                extracted_text, confidence = self._extract_text_from_file(file_path, file_type)
                
                if extracted_text:
                    # Update document with extracted text and success status
                    update_data = {
                        'full_text': extracted_text,
                        'ocr_confidence_percent': confidence,
                        'ingestion_status': 'ingestion_successful',
                        'processing_status': 'ingested'
                    }
                    
                    self.context_store.update_document_fields(document_id, update_data)
                    
                    # Add audit log entry for successful processing
                    self.context_store.add_audit_log_entry(
                        user_id=user_id,
                        event_type="AGENT_ACTIVITY",
                        event_name="COMPLETE_DOCUMENT_INGESTION",
                        status="SUCCESS",
                        resource_type="document",
                        resource_id=document_id,
                        details=f"Successfully ingested {filename} with confidence {confidence}%"
                    )
                    
                    self.logger.info(f"Successfully ingested document: {filename} (ID: {document_id})")
                    successful_document_ids.append(document_id)
                    
                    # Leave successfully processed file at original location for TaggerAgent to find and archive properly
                    
                else:
                    # Move file to holding folder and update status to failed
                    holding_path = os.path.join(self.holding_folder, filename)
                    # Handle duplicate filenames
                    if os.path.exists(holding_path):
                        import time
                        timestamp = int(time.time())
                        name, ext = os.path.splitext(filename)
                        holding_path = os.path.join(self.holding_folder, f"{name}_{timestamp}{ext}")
                    
                    shutil.move(file_path, holding_path)
                    
                    self.context_store.update_document_fields(
                        document_id, 
                        {'ingestion_status': 'ingestion_failed'}
                    )
                    
                    # Add audit log entry for failed processing
                    self.context_store.add_audit_log_entry(
                        user_id=user_id,
                        event_type="AGENT_ACTIVITY",
                        event_name="COMPLETE_DOCUMENT_INGESTION",
                        status="FAILURE",
                        resource_type="document",
                        resource_id=document_id,
                        details=f"Failed to extract text from {filename}"
                    )
                    
                    self.logger.warning(
                        f"Failed to extract text from document: {filename} (ID: {document_id}). "
                        f"Moved to holding folder: {holding_path}"
                    )
            
            except Exception as e:
                self.logger.error(f"Error processing file {filename}: {str(e)}")
                
                # If we already created a document record, update it to failed
                if document_id:
                    try:
                        self.context_store.update_document_fields(
                            document_id, 
                            {'ingestion_status': 'ingestion_failed'}
                        )
                        
                        self.context_store.add_audit_log_entry(
                            user_id=user_id,
                            event_type="AGENT_ACTIVITY",
                            event_name="COMPLETE_DOCUMENT_INGESTION",
                            status="ERROR",
                            resource_type="document",
                            resource_id=document_id,
                            details=f"Error processing {filename}: {str(e)}"
                        )
                    except Exception as inner_e:
                        self.logger.error(f"Error updating document status: {str(inner_e)}")
                
                # Try to move the file to holding folder if it exists
                try:
                    if os.path.exists(file_path):
                        holding_path = os.path.join(self.holding_folder, filename)
                        # Handle duplicate filenames
                        if os.path.exists(holding_path):
                            import time
                            timestamp = int(time.time())
                            name, ext = os.path.splitext(filename)
                            holding_path = os.path.join(self.holding_folder, f"{name}_{timestamp}{ext}")
                        
                        shutil.move(file_path, holding_path)
                        self.logger.info(f"Moved problematic file to holding folder: {holding_path}")
                except Exception as move_e:
                    self.logger.error(f"Error moving file to holding folder: {str(move_e)}")
        
        self.logger.info(f"Specific file processing complete. Successfully processed: {len(successful_document_ids)}")
        return len(successful_document_ids)
    
    def _determine_file_type(self, filename: str) -> str:
        """
        Determine the file type category based on the filename extension.
        
        Args:
            filename: The name of the file
            
        Returns:
            String representing the file type category ('pdf', 'docx', 'txt', 'image', 'unsupported')
        """
        file_extension = os.path.splitext(filename)[1].lower()
        file_type_category = file_extension[1:] if file_extension.startswith('.') else file_extension

        if file_type_category in ['jpeg', 'jpg', 'png', 'bmp', 'tiff', 'tif']:
            return 'image'
        elif file_type_category == 'pdf':
            return 'pdf'
        elif file_type_category == 'docx':
            return 'docx'
        elif file_type_category == 'txt':
            return 'txt'
        else:
            self.logger.warning(f"Determined unsupported file type category: {file_type_category} for {filename}")
            return 'unsupported'
    
    def _extract_text_from_file(self, file_path: str, file_type: str) -> Tuple[Optional[str], Optional[float]]:
        """
        Extract text from a file based on its type.
        
        Args:
            file_path: Full path to the file
            file_type: Type of file ('pdf', 'docx', 'txt', 'image', or 'unsupported')
            
        Returns:
            Tuple containing:
                - Extracted text (or None if extraction failed)
                - Confidence percentage (0-100, or None if extraction failed)
        """
        try:
            if file_type == 'pdf':
                return self._extract_text_from_pdf(file_path)
            
            elif file_type == 'docx':
                # Import python-docx here to avoid requiring it for non-docx processing
                import docx
                text = ""
                doc = docx.Document(file_path)
                for para in doc.paragraphs:
                    text += para.text + '\n'
                return text, 100.0
            
            elif file_type == 'txt':
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                return text, 100.0
            
            elif file_type == 'image':
                # Import pytesseract here to avoid requiring it for non-image processing
                import pytesseract
                # Use pytesseract for OCR on image
                image = Image.open(file_path)
                ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT, lang='eng')
                
                # Calculate confidence
                confidences = [float(conf) for conf in ocr_data['conf'] if conf != '-1']
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
                
                # Get text
                text = pytesseract.image_to_string(image, lang='eng')
                
                if text.strip():
                    return text, avg_confidence
                return None, None
            
            else:  # unsupported file type
                self.logger.warning(f"Unsupported file type: {file_type}")
                return None, None
                
        except Exception as e:
            self.logger.error(f"Error extracting text from {file_path}: {str(e)}")
            return None, None
    
    def _extract_text_from_pdf(self, file_path: str) -> Tuple[Optional[str], Optional[float]]:
        """
        Extract text from a PDF using a competitive strategy: try both direct
        extraction and OCR, then return the result with the most text.
        """
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
            return None, None

        # Compare results and return the best one with a confidence score
        import os
        if len(direct_text.strip()) > len(ocr_text.strip()):
            self.logger.info(f"Using direct extraction result for {os.path.basename(file_path)}")
            return direct_text, 100.0
        elif len(ocr_text.strip()) > 0:
            self.logger.info(f"Using OCR extraction result for {os.path.basename(file_path)}")
            return ocr_text, 75.0  # Assign a lower confidence for OCR
        else:
            self.logger.error(f"Both direct and OCR text extraction failed for {file_path}")
            return None, None