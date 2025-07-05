"""
Tagger Agent Module for Intelligent Document Insight System (IDIS)

This module provides the TaggerAgent class which extracts key metadata from documents,
tags them appropriately, and files them in an organized directory structure.
"""

import os
import re
import json
import shutil
import logging
import hashlib
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional
from dateutil import parser as date_parser

from context_store import ContextStore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Comprehensive suppression of noisy third-party PDF and font libraries
noisy_loggers = ['fontTools', 'fpdf2', 'reportlab']
for logger_name in noisy_loggers:
    logging.getLogger(logger_name).setLevel(logging.WARNING)


class TaggerAgent:
    """
    Agent responsible for extracting metadata from documents and filing them.
    
    The TaggerAgent retrieves documents that have been summarized from the Context Store,
    extracts key entities (dates, issuer, recipient, status tags), and files the
    documents in an organized directory structure.
    """
    
    def __init__(self, context_store: ContextStore, base_filed_folder: str, 
                 tag_definitions: Optional[Dict[str, List[str]]] = None):
        """
        Initialize the Tagger Agent with required parameters.
        
        Args:
            context_store: An initialized instance of the ContextStore
            base_filed_folder: The root directory where processed files will be archived
            tag_definitions: A dictionary for predefined status-like tags
                Keys are tag names (e.g., "urgent")
                Values are lists of case-insensitive keywords/phrases that trigger the tag
        """
        self.context_store = context_store
        self.base_filed_folder = base_filed_folder
        self.tag_definitions = tag_definitions or {}
        self.logger = logging.getLogger('TaggerAgent')
        self.agent_id = "tagger_agent_v1.0"
        
        # Pre-compile regex patterns for tag matching
        self.compiled_rules = {}
        for tag_name, keywords in self.tag_definitions.items():
            self.compiled_rules[tag_name] = [
                re.compile(r'\b' + re.escape(keyword) + r'\b', re.IGNORECASE) 
                for keyword in keywords
            ]
        
        # Create the base filing directory if it doesn't exist
        os.makedirs(self.base_filed_folder, exist_ok=True)
        
        # Known issuers for high-confidence identification
        self.KNOWN_ISSUERS = {
            "Fidelity": ["Fidelity", "Fidelity Rewards"],
            "Spenard Builders Supply": ["Spenard Builders Supply"],
            "GCI": ["GCI", "General Communication, Inc."],
            "Waste Management": ["Waste Management", "WM"],
            "State of Alaska": ["state of alaska", "department of commerce"],
            "Homer Electric Association": ["homer electric association", "hea"],
            "Bank of America": ["bank of america"],
            "Global Credit Union": ["global credit union"],
            "State Farm": ["state farm"],
            "Safeway": ["safeway"]
        }
        
        # Document type abbreviations for filename generation
        self.doc_type_abbreviations = {
            "Invoice": "INV",
            "Medical Record": "MEDREC",
            "Letter": "LTR",
            "Report": "RPT",
            "Insurance Document": "INS",
            "Legal Document": "LEGAL",
            "Receipt": "RCPT",
            "Credit Card Statement": "CCSTMT",
            "Business License": "BIZLIC",
            "Bank Statement": "BNKSTMT",
            "Utility Bill": "UTIL",
            "Unclassified": "UNC"
        }
        
        self.logger.info(f"TaggerAgent initialized with base filing directory: {base_filed_folder}")
        if tag_definitions:
            self.logger.info(f"Configured with {len(tag_definitions)} tag definitions")
    
    def _sanitize_for_filename(self, text: str) -> str:
        """
        Sanitize text to make it safe for file and folder names.
        
        Args:
            text: The text to sanitize
            
        Returns:
            Sanitized text safe for filesystem use
        """
        if not text:
            return "Unknown"
        
        # Replace spaces with underscores
        sanitized = text.replace(" ", "_")
        
        # Remove or replace special characters, keep only alphanumeric, underscore, and hyphen
        sanitized = re.sub(r'[^a-zA-Z0-9_\-]', '', sanitized)
        
        # Limit length to avoid filesystem issues
        sanitized = sanitized[:50]
        
        # Ensure it's not empty after sanitization
        return sanitized if sanitized else "Unknown"
    
    def _get_primary_date(self, document_dates: Dict[str, Any], upload_timestamp: str) -> datetime:
        """
        Determine the primary date for filing from document dates with priority order.
        
        Args:
            document_dates: Dictionary of extracted dates from document
            upload_timestamp: Document upload timestamp as fallback
            
        Returns:
            Primary date to use for filing
        """
        # Priority order for date keys
        priority_keys = ["invoice_date", "letter_date", "visit_date", "report_date"]
        
        # Try priority keys first
        for key in priority_keys:
            if key in document_dates:
                try:
                    date_str = document_dates[key]
                    if isinstance(date_str, str) and len(date_str) >= 10:
                        return datetime.strptime(date_str[:10], '%Y-%m-%d')
                except (ValueError, TypeError):
                    continue
        
        # Find earliest valid date from any key
        valid_dates = []
        for date_value in document_dates.values():
            if isinstance(date_value, str) and len(date_value) >= 10:
                try:
                    valid_dates.append(datetime.strptime(date_value[:10], '%Y-%m-%d'))
                except (ValueError, TypeError):
                    continue
        
        if valid_dates:
            return min(valid_dates)
        
        # Fallback to upload timestamp
        try:
            if upload_timestamp:
                return datetime.fromisoformat(upload_timestamp.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            pass
        
        # Final fallback to current time
        return datetime.now()
    
    def _get_patient_folder_name(self, patient_id: str) -> str:
        """
        Get sanitized patient folder name with patient name and ID prefix.
        
        Args:
            patient_id: The patient ID to look up
            
        Returns:
            Sanitized folder name in format: PatientName_first6chars or patient_id if name not found
        """
        # Convert patient_id to string right away to prevent TypeErrors
        patient_id = str(patient_id)
        
        try:
            # Convert patient_id to int if it's a string (database expects integer)
            if isinstance(patient_id, str):
                try:
                    patient_id_int = int(patient_id)
                except ValueError:
                    # If patient_id is not a valid integer string, return fallback
                    return patient_id
            else:
                patient_id_int = patient_id
            patient_data = self.context_store.get_patient(patient_id_int)
            if patient_data and patient_data.get('patient_name'):
                sanitized_name = self._sanitize_for_filename(patient_data['patient_name'])
                id_prefix = patient_id[:6] if len(patient_id) >= 6 else patient_id
                return f"{sanitized_name}_{id_prefix}"
        except Exception as e:
            self.logger.warning(f"Could not fetch patient name for {patient_id}: {e}")
        
        # Fallback to full patient_id
        return self._sanitize_for_filename(patient_id)
    
    def _generate_new_filename(self, document_id: str, file_name: str, document_type: str, 
                               primary_date: datetime, patient_id: Optional[str], 
                               issuer_source: Optional[str]) -> str:
        """
        Generate new descriptive filename using the enhanced naming convention.
        
        Args:
            document_id: The document UUID
            file_name: Original filename
            document_type: The classified document type
            primary_date: The primary date for the document
            patient_id: Patient ID if associated with a patient
            issuer_source: The document issuer/source
            
        Returns:
            New filename in format: YYYY-MM-DD_[SanitizedInfo]_[DocTypeAbbrev]-[doc_id_first_8].[ext]
        """
        # Get date prefix
        date_prefix = primary_date.strftime('%Y-%m-%d')
        
        # Get document type abbreviation
        doc_abbrev = self.doc_type_abbreviations.get(document_type, "UNC")
        
        # Get document ID prefix (first 8 characters)
        doc_id_prefix = document_id[:8] if len(document_id) >= 8 else document_id
        
        # Get original file extension
        _, ext = os.path.splitext(file_name)
        ext = ext if ext else '.txt'
        
        # Determine sanitized info part
        if patient_id:
            # For patient documents, use sanitized original filename
            base_name = os.path.splitext(file_name)[0]
            sanitized_info = self._sanitize_for_filename(base_name)
        else:
            # For general documents, use sanitized issuer or fallback
            if issuer_source:
                sanitized_info = self._sanitize_for_filename(issuer_source)
            else:
                sanitized_info = "UnknownSource"
        
        # Construct the new filename
        new_filename = f"{date_prefix}_{sanitized_info}_{doc_abbrev}-{doc_id_prefix}{ext}"
        
        return new_filename
    
    def _is_valid_entity_name(self, name: str) -> bool:
        """
        Check if extracted entity name is valid and not garbage data.
        
        Args:
            name: The entity name to validate
            
        Returns:
            True if name appears to be a valid entity name
        """
        if not name or len(name.strip()) < 3:
            return False
        
        name = name.strip()
        
        # Filter out common garbage patterns
        garbage_patterns = [
            r'^[\d\s\-_.,]+$',  # Only numbers, spaces, and punctuation
            r'^[A-Z]{1,2}\s*\d+$',  # State codes with numbers (e.g., "CA 123")
            r'^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$',  # Date patterns
            r'^[A-Z]{2,3}\s*\d{5,}$',  # ZIP codes or similar
            r'^(page|p\.)\s*\d+',  # Page numbers
            r'^(invoice|bill|receipt|statement)#?\s*\d+',  # Document numbers
            r'^(fax|phone|tel|email)[:.]',  # Contact info labels
        ]
        
        for pattern in garbage_patterns:
            if re.match(pattern, name, re.IGNORECASE):
                return False
        
        # Must contain at least one letter
        if not re.search(r'[a-zA-Z]', name):
            return False
        
        # Reject if too many consecutive special characters
        if re.search(r'[^\w\s]{3,}', name):
            return False
        
        return True
    
    def _validate_extracted_data(self, extracted_dates: Dict[str, str], 
                                 issuer: Optional[str], recipient: Optional[str], 
                                 tags: List[str]) -> Dict[str, Any]:
        """
        Validate and clean extracted metadata using quality checks.
        
        Args:
            extracted_dates: Dictionary of extracted dates
            issuer: Extracted issuer name
            recipient: Extracted recipient name  
            tags: List of extracted tags
            
        Returns:
            Dictionary of validated metadata
        """
        validated_data = {}
        
        # Validate dates - remove invalid ones
        validated_dates = {}
        for context, date_str in extracted_dates.items():
            if date_str and re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
                try:
                    # Parse to verify it's a valid date
                    date_parser.parse(date_str)
                    validated_dates[context] = date_str
                except:
                    self.logger.warning(f"Invalid date format ignored: {date_str}")
        
        validated_data['dates'] = validated_dates
        
        # Validate issuer
        if issuer and self._is_valid_entity_name(issuer):
            validated_data['issuer'] = issuer.strip()
        else:
            validated_data['issuer'] = None
            if issuer:
                self.logger.debug(f"Invalid issuer name filtered out: {issuer}")
        
        # Validate recipient  
        if recipient and self._is_valid_entity_name(recipient):
            validated_data['recipient'] = recipient.strip()
        else:
            validated_data['recipient'] = None
            if recipient:
                self.logger.debug(f"Invalid recipient name filtered out: {recipient}")
        
        # Validate tags - ensure they're non-empty strings
        validated_tags = [tag.strip() for tag in tags if tag and tag.strip()]
        validated_data['tags'] = validated_tags
        
        return validated_data
    
    def _extract_semantic_tags(self, text: str, document_type: str) -> List[str]:
        """
        Extract context-aware semantic tags based on document type and content.
        
        Args:
            text: The document text to process
            document_type: The classified document type
            
        Returns:
            List of semantic tags
        """
        semantic_tags = []
        text_lower = text.lower()
        
        # Document type specific tagging
        if document_type == "Medical Record":
            medical_patterns = {
                'lab_results': [r'\b(lab\s+results?|laboratory|blood\s+work|test\s+results?)\b'],
                'prescription': [r'\b(prescription|medication|rx|drug|dosage)\b'],
                'diagnosis': [r'\b(diagnosis|diagnosed|condition|disorder|disease)\b'],
                'treatment': [r'\b(treatment|therapy|procedure|surgery|operation)\b'],
                'followup': [r'\b(follow\s*up|next\s+visit|appointment|schedule)\b']
            }
            
            for tag, patterns in medical_patterns.items():
                if any(re.search(pattern, text_lower) for pattern in patterns):
                    semantic_tags.append(tag)
        
        elif document_type == "Invoice":
            invoice_patterns = {
                'overdue': [r'\b(overdue|past\s+due|late|delinquent)\b'],
                'payment_due': [r'\b(payment\s+due|due\s+date|remit|pay\s+by)\b'],
                'services': [r'\b(services?|consulting|professional)\b'],
                'products': [r'\b(products?|goods|items|materials)\b'],
                'discount': [r'\b(discount|rebate|credit|reduction)\b']
            }
            
            for tag, patterns in invoice_patterns.items():
                if any(re.search(pattern, text_lower) for pattern in patterns):
                    semantic_tags.append(tag)
        
        elif document_type == "Legal Document":
            legal_patterns = {
                'contract': [r'\b(contract|agreement|terms|conditions)\b'],
                'notice': [r'\b(notice|notification|serve|legal\s+notice)\b'],
                'court': [r'\b(court|judge|hearing|trial|lawsuit)\b'],
                'settlement': [r'\b(settlement|resolve|mediation|arbitration)\b']
            }
            
            for tag, patterns in legal_patterns.items():
                if any(re.search(pattern, text_lower) for pattern in patterns):
                    semantic_tags.append(tag)
        
        # Extract predefined tags as well
        predefined_tags = self._extract_predefined_tags(text)
        semantic_tags.extend(predefined_tags)
        
        # Remove duplicates while preserving order
        return list(dict.fromkeys(semantic_tags))
    
    def _verify_file_integrity(self, src: str, dst: str) -> bool:
        """
        Verify file integrity by comparing SHA256 hashes.
        
        Args:
            src: Source file path
            dst: Destination file path
            
        Returns:
            True if files have matching hashes, False otherwise
        """
        try:
            def get_file_hash(filepath: str) -> str:
                hash_sha256 = hashlib.sha256()
                with open(filepath, "rb") as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        hash_sha256.update(chunk)
                return hash_sha256.hexdigest()
            
            return get_file_hash(src) == get_file_hash(dst)
        except Exception as e:
            self.logger.error(f"Failed to verify file integrity: {e}")
            return False
    
    def _safe_file_move(self, src: str, dst: str) -> bool:
        """
        Safely move a file using copy-verify-delete mechanism.
        
        Args:
            src: Source file path
            dst: Destination file path
            
        Returns:
            True if file was successfully moved, False otherwise
        """
        try:
            # Pre-flight checks
            if not os.path.exists(src):
                self.logger.error(f"Source file does not exist: {src}")
                return False
            
            if os.path.exists(dst):
                self.logger.error(f"Destination file already exists: {dst}")
                return False
            
            # Ensure destination directory exists
            dst_dir = os.path.dirname(dst)
            os.makedirs(dst_dir, exist_ok=True)
            
            # Get source file size
            src_size = os.path.getsize(src)
            
            # Copy file with metadata
            shutil.copy2(src, dst)
            
            # Verify copy was successful
            if not os.path.exists(dst):
                self.logger.error(f"Destination file was not created: {dst}")
                return False
            
            # Verify file size matches
            dst_size = os.path.getsize(dst)
            if src_size != dst_size:
                self.logger.error(f"File size mismatch: src={src_size}, dst={dst_size}")
                # Clean up partial copy
                try:
                    os.remove(dst)
                except:
                    pass
                return False
            
            # For larger files, verify integrity with hash comparison
            if src_size > 1024 * 1024:  # 1MB threshold
                if not self._verify_file_integrity(src, dst):
                    self.logger.error(f"File integrity verification failed for {src}")
                    # Clean up partial copy
                    try:
                        os.remove(dst)
                    except:
                        pass
                    return False
            
            # All verifications passed, remove original
            os.remove(src)
            self.logger.info(f"Successfully moved file: {src} -> {dst}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error during safe file move: {e}")
            # Clean up any partial copy
            try:
                if os.path.exists(dst):
                    os.remove(dst)
            except:
                pass
            return False
    
    def process_documents_for_tagging_and_filing(
        self,
        user_id: str = "tagger_agent_mvp_user",
        status_to_process: str = "summarized",
        new_status_after_filing: str = "filed"
    ) -> Tuple[int, int]:
        """
        Process documents for metadata extraction, tagging, and filing.
        
        Fetches documents with the specified processing status, extracts metadata,
        and files them in an organized directory structure.
        
        Args:
            user_id: User ID for audit trail purposes
            status_to_process: Processing status of documents to retrieve for tagging
            new_status_after_filing: New processing status to set after successful filing
            
        Returns:
            Tuple containing (successfully_processed_count, failed_count)
        """
        self.logger.info(f"Starting tagging and filing batch run for documents with status: {status_to_process}")
        
        # Fetch documents that need tagging and filing
        documents = self.context_store.get_documents_by_processing_status(
            processing_status=status_to_process
        )
        
        self.logger.info(f"Found {len(documents)} documents to process")
        
        successfully_processed_count = 0
        failed_count = 0
        
        # Process each document
        for document in documents:
            document_id = document["document_id"]
            extracted_text = document.get("full_text")
            original_watchfolder_path = document.get("original_watchfolder_path")
            patient_id = document.get("patient_id")
            file_name = document.get("file_name", "unknown_file")
            document_type = document.get("document_type", "Unclassified")
            
            # Extract metadata from document text using enhanced methods
            # Handle cases where extracted_text might be None or empty
            text_to_process: str = extracted_text or ""
            extracted_dates_dict = self._extract_dates(text_to_process)
            issuer = self._extract_issuer(text_to_process)
            recipient = self._extract_recipient(text_to_process)
            
            # Use enhanced semantic tagging based on document type
            semantic_tags = self._extract_semantic_tags(text_to_process, document_type)
            
            # Validate all extracted data for quality
            validated_data = self._validate_extracted_data(
                extracted_dates_dict, issuer, recipient, semantic_tags
            )
            
            # Use validated data
            extracted_dates_dict = validated_data['dates']
            issuer = validated_data['issuer']
            recipient = validated_data['recipient']
            active_tags = validated_data['tags']
            
            # Determine the filed path for document using enhanced schema
            filing_successful = False
            new_filed_path = None
            
            try:
                # Get primary date using enhanced logic
                upload_timestamp = document.get("upload_timestamp", "")
                primary_date = self._get_primary_date(extracted_dates_dict, upload_timestamp)
                
                # Construct filing path based on enhanced schema
                year_month_folder = os.path.join(
                    str(primary_date.year),
                    f"{primary_date.month:02d}"
                )
                
                # Create patient-specific or general folder using new schema
                if patient_id:
                    patient_folder_name = self._get_patient_folder_name(patient_id)
                    relative_folder = os.path.join("patients", patient_folder_name, year_month_folder)
                else:
                    # For general documents, create fallback structure for unclassified items
                    if document_type == "Unclassified" or not issuer:
                        relative_folder = os.path.join("general_archive", "Uncategorized", year_month_folder)
                    else:
                        relative_folder = os.path.join("general_archive", year_month_folder)
                
                # Create full path
                filing_dir = os.path.join(self.base_filed_folder, relative_folder)
                os.makedirs(filing_dir, exist_ok=True)
                
                # Generate new descriptive filename using enhanced naming convention
                filed_filename = self._generate_new_filename(
                    str(document_id), file_name, document_type, primary_date, patient_id, issuer
                )
                new_filed_path = os.path.join(filing_dir, filed_filename)
                
                # Get the confirmed current path from the database
                current_file_path = document.get("original_watchfolder_path")
                self.logger.info(f"TAGGER: Processing document_id: {document_id}, filename: {file_name}")
                self.logger.info(f"TAGGER: Attempting to find file for doc {document_id} at path: {current_file_path}")
                
                # Attempt file movement if the path exists and is a file
                if current_file_path and os.path.isfile(current_file_path):
                    self.logger.info(f"TAGGER: Found file at: {current_file_path}")
                    filing_successful = self._safe_file_move(current_file_path, new_filed_path)
                    if filing_successful:
                        self.logger.info(f"Successfully moved document {document_id} from {current_file_path} to {new_filed_path}")
                    else:
                        self.logger.error(f"Failed to safely move document {document_id} from {current_file_path}")
                        new_filed_path = None
                        filing_successful = False
                else:
                    # This block now means the file is truly lost or the DB path is wrong
                    self.logger.error(f"CRITICAL: File not found at the path specified in database: {current_file_path}")
                    filing_successful = False
            
            except Exception as e:
                self.logger.error(f"Error filing document {document_id}: {str(e)}")
                filing_successful = False
                new_filed_path = None
            
            # Prepare update data
            update_data = {}
            
            # Add extracted metadata
            if extracted_dates_dict:
                update_data["document_dates"] = json.dumps(extracted_dates_dict)
            
            if issuer:
                update_data["issuer_source"] = issuer
            
            if recipient:
                update_data["recipient"] = recipient
            
            if active_tags:
                update_data["tags_extracted"] = json.dumps(active_tags)
            
            # Update filing status and path
            if filing_successful:
                if new_filed_path:
                    update_data["filed_path"] = new_filed_path
                update_data["processing_status"] = new_status_after_filing
                status = "SUCCESS"
                successfully_processed_count += 1
            else:
                update_data["processing_status"] = "filing_error"
                status = "FAILURE"
                failed_count += 1
            
            # Update document in Context Store
            self.context_store.update_document_fields(document_id, update_data)
            
            # Add comprehensive audit log entry with enhanced details
            metadata_summary = []
            if extracted_dates_dict:
                metadata_summary.append(f"{len(extracted_dates_dict)} dates extracted")
            if issuer:
                metadata_summary.append(f"issuer: {issuer[:30]}...")
            if recipient:
                metadata_summary.append(f"recipient: {recipient[:30]}...")
            if active_tags:
                metadata_summary.append(f"{len(active_tags)} semantic tags: {', '.join(active_tags[:3])}")
            
            details = f"Enhanced processing: {'; '.join(metadata_summary)}"
            if filing_successful:
                details += f"; filed at {new_filed_path}"
            else:
                details += "; metadata-only processing (no file movement)"
                
            self.context_store.add_audit_log_entry(
                user_id=user_id,
                event_type="AGENT_ACTIVITY",
                event_name="DOCUMENT_TAGGED_AND_FILED",
                status=status,
                resource_type="document",
                resource_id=document_id,
                details=details
            )
        
        # Enhanced summary logging with quality metrics
        total_processed = successfully_processed_count + failed_count
        success_rate = (successfully_processed_count / total_processed * 100) if total_processed > 0 else 0
        
        self.logger.info(f"Enhanced tagging and filing batch run complete.")
        self.logger.info(f"Processing summary: {successfully_processed_count}/{total_processed} successful ({success_rate:.1f}%)")
        self.logger.info(f"Enhanced features: semantic tagging, data validation, safe file movement")
        
        return (successfully_processed_count, failed_count)
    
    def _extract_dates(self, text: str) -> Dict[str, str]:
        """
        Extract dates from document text and identify their context.
        
        Args:
            text: The document text to process
            
        Returns:
            Dict mapping date contexts to ISO format dates (YYYY-MM-DD)
        """
        # Dictionary to store extracted dates with their context
        dates_dict = {}
        
        # Common date formats - ordered by specificity
        # Format: Month YYYY (e.g., "February 2025", "Feb 2025", "Feb. 2025") - must come first
        pattern1 = r'(\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?,?\s+\d{4})\b'
        # Format: Month DD, YYYY (e.g., "January 15, 2023") - requires day AND year
        pattern2 = r'(\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)[,.\s]+\d{1,2}[,.\s]+\d{4})\b'
        # Format: MM/DD/YYYY or MM-DD-YYYY
        pattern3 = r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
        # Format: YYYY-MM-DD
        pattern4 = r'(\d{4}[/-]\d{1,2}[/-]\d{1,2})'
        
        # Common date labels
        date_labels = {
            "invoice_date": [r'invoice\s+(?:is\s+)?dated', r'date\s+of\s+invoice', r'invoice\s+date'],
            "due_date": [r'due\s+date', r'payment\s+(?:is\s+)?due', r'due\s+by', r'pay\s+by'],
            "service_date": [r'service\s+(?:was\s+)?provided', r'service\s+date', r'date\s+of\s+service'],
            "letter_date": [r'letter\s+(?:was\s+)?(?:dated|written)', r'this\s+letter\s+(?:is\s+)?dated'],
            "exam_date": [r'exam\s+(?:scheduled\s+for|date)', r'examination\s+date', r'date\s+of\s+exam'],
            "report_date": [r'report\s+(?:from|date)', r'reported\s+on', r'date\s+of\s+report']
        }
        
        # Find dates with context
        for context, label_patterns in date_labels.items():
            for label_pattern in label_patterns:
                # Look for the label pattern
                label_matches = list(re.finditer(label_pattern, text, re.IGNORECASE))
                for label_match in label_matches:
                    # Search for date patterns near the label (within ~100 chars)
                    label_pos = label_match.end()
                    search_text = text[label_pos:label_pos + 100]
                    
                    # Try each date pattern
                    for pattern in [pattern1, pattern2, pattern3, pattern4]:
                        date_match = re.search(pattern, search_text, re.IGNORECASE)
                        if date_match:
                            date_str = date_match.group(1)
                            try:
                                # Try to parse and normalize the date to YYYY-MM-DD
                                parsed_date = self._normalize_date(date_str)
                                if parsed_date:
                                    dates_dict[context] = parsed_date
                                    break  # Found a date for this context
                            except ValueError:
                                continue
        
        # Look for any additional dates without context
        all_dates = []
        for pattern in [pattern1, pattern2, pattern3, pattern4]:
            all_dates.extend(re.findall(pattern, text, re.IGNORECASE))
        
        # Add dates without identified context
        date_counter = 1
        for date_str in all_dates:
            try:
                parsed_date = self._normalize_date(date_str)
                if parsed_date and not any(parsed_date == d for d in dates_dict.values()):
                    context_key = f"doc_date_{date_counter}"
                    dates_dict[context_key] = parsed_date
                    date_counter += 1
            except ValueError:
                continue
        
        return dates_dict
    
    def _normalize_date(self, date_str: str) -> Optional[str]:
        """
        Normalize a date string to YYYY-MM-DD format using robust dateutil parsing.
        
        Args:
            date_str: The date string to normalize
            
        Returns:
            Normalized date in YYYY-MM-DD format or None if parsing fails
        """
        try:
            # Clean the input string
            cleaned_str = date_str.strip(',. ')
            
            # Handle "Month YYYY" format specially (defaults to first day of month)
            month_year_pattern = r'\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?\s+(\d{4})\b'
            month_year_match = re.search(month_year_pattern, cleaned_str, re.IGNORECASE)
            
            if month_year_match:
                month_name = month_year_match.group(1).rstrip('.')
                year = month_year_match.group(2)
                # Use explicit month mapping to ensure first day of month
                month_map = {
                    'jan': 1, 'january': 1, 'feb': 2, 'february': 2,
                    'mar': 3, 'march': 3, 'apr': 4, 'april': 4,
                    'may': 5, 'jun': 6, 'june': 6, 'jul': 7, 'july': 7,
                    'aug': 8, 'august': 8, 'sep': 9, 'september': 9,
                    'oct': 10, 'october': 10, 'nov': 11, 'november': 11,
                    'dec': 12, 'december': 12
                }
                month_num = month_map.get(month_name.lower())
                if month_num:
                    return f"{year}-{month_num:02d}-01"
            
            # Use dateutil parser for comprehensive date parsing
            parsed_date = date_parser.parse(cleaned_str, fuzzy=True)
            
            # Validate date is reasonable (not before 1900 or more than 1 year in future)
            current_year = datetime.now().year
            if parsed_date.year < 1900 or parsed_date.year > current_year + 1:
                self.logger.warning(f"Date {parsed_date.year} outside reasonable range, skipping")
                return None
            
            return parsed_date.strftime("%Y-%m-%d")
            
        except Exception as e:
            self.logger.debug(f"Error normalizing date '{date_str}': {str(e)}")
            return None
    
    def _clean_issuer_name(self, raw_name: str) -> str:
        """
        Clean extracted issuer name by removing noise.
        
        Args:
            raw_name: Raw extracted issuer name
            
        Returns:
            Cleaned issuer name
        """
        # Remove everything after | symbol (common in headers)
        if '|' in raw_name:
            raw_name = raw_name.split('|')[0]
        
        # Remove address/phone patterns
        cleaned = re.sub(r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b', '', raw_name)  # Phone numbers
        cleaned = re.sub(r'\b\d{1,5}\s+\w+\s+(St|Street|Ave|Avenue|Rd|Road|Blvd|Boulevard)\b', '', cleaned, flags=re.IGNORECASE)  # Addresses
        cleaned = re.sub(r'\b[A-Z]{2}\s+\d{5}(-\d{4})?\b', '', cleaned)  # ZIP codes
        
        return cleaned.strip()
    
    def _is_metadata_line(self, line: str) -> bool:
        """
        Check if a line contains metadata rather than issuer information.
        
        Args:
            line: Line of text to check
            
        Returns:
            True if line appears to be metadata
        """
        metadata_patterns = [
            r'^\s*(?:to|from|date|subject|re):\s*',
            r'^\s*(?:invoice|bill|statement|receipt)#?\s*:?\s*\d',
            r'^\s*(?:page|p\.)\s*\d+\s*(?:of|/)\s*\d+',
            r'^\s*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\s*$'
        ]
        
        return any(re.match(pattern, line, re.IGNORECASE) for pattern in metadata_patterns)
    
    def _extract_issuer(self, text: str) -> Optional[str]:
        """
        Extract the issuer/source of the document using intelligent multi-pass strategy.
        
        Args:
            text: The document text to process
            
        Returns:
            Extracted issuer name or None if not found
        """
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        if not lines:
            return None
        
        # Pass 0: Check for known issuers (high-confidence identification)
        text_lower = text.lower()
        for issuer_name, keywords in self.KNOWN_ISSUERS.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    return issuer_name
        
        # Pass 1: Search header (first ~7 lines) for high-confidence signals
        header_lines = lines[:7]
        
        # Look for explicit "From:" patterns
        for line in header_lines:
            from_match = re.search(r'(?:from|sender|issued\s+by):\s*(.+)', line, re.IGNORECASE)
            if from_match:
                issuer = self._clean_issuer_name(from_match.group(1))
                if len(issuer) > 3:
                    return issuer
        
        # Pass 2: Look for company suffixes in header
        company_suffixes = r'\b(Inc\.?|LLC|Ltd\.?|Corp\.?|Corporation|Company|Hospital|Clinic|Associates|Foundation|Center|Medical\s+Center|Health\s+System)\b'
        
        for line in header_lines:
            if re.search(company_suffixes, line, re.IGNORECASE) and not self._is_metadata_line(line):
                # Extract the organization name
                # Look for text before the suffix plus the suffix
                match = re.search(r'([A-Z][A-Za-z0-9\s&.,\'-]+' + company_suffixes + r')', line, re.IGNORECASE)
                if match:
                    issuer = self._clean_issuer_name(match.group(0))
                    if len(issuer) > 3:
                        return issuer
        
        # Pass 3: First line fallback (if not metadata)
        if not self._is_metadata_line(lines[0]) and len(lines[0]) > 3:
            # Check if it looks like an organization name
            if any(char.isupper() for char in lines[0]) and not lines[0].isdigit():
                return self._clean_issuer_name(lines[0])
        
        return None
    
    def _extract_recipient(self, text: str) -> Optional[str]:
        """
        Extract the recipient of the document.
        
        Args:
            text: The document text to process
            
        Returns:
            Extracted recipient name or None if not found
        """
        # Common patterns for recipients
        recipient_patterns = [
            r'(?:to|attention|attn|deliver\s+to|bill\s+to):\s*([A-Z][A-Za-z0-9\s&.,]+)',
            r'dear\s+([^,\n:]+)[,:]',
            r'(?:patient(?:\s+name)?|name\s+of\s+patient):\s*([A-Z][A-Za-z0-9\s&.,]+)'
        ]
        
        # Try each pattern
        for pattern in recipient_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                recipient = match.group(1).strip()
                if len(recipient) > 3:  # Avoid very short matches
                    return recipient
        
        return None
    
    def _extract_predefined_tags(self, text: str) -> List[str]:
        """
        Extract predefined tags based on keyword matches.
        
        Args:
            text: The document text to process
            
        Returns:
            List of matched tag names
        """
        active_tags = []
        
        # Skip if no tag definitions were provided
        if not self.compiled_rules:
            return active_tags
        
        # Check each tag's patterns
        for tag_name, patterns in self.compiled_rules.items():
            for pattern in patterns:
                if pattern.search(text):
                    active_tags.append(tag_name)
                    break  # One match is enough for this tag
        
        return active_tags