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
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional

from context_store import ContextStore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


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
        
        # Document type abbreviations for filename generation
        self.doc_type_abbreviations = {
            "Invoice": "INV",
            "Medical Record": "MEDREC", 
            "Letter": "LTR",
            "Report": "RPT",
            "Insurance Document": "INS",
            "Legal Document": "LEGAL",
            "Receipt": "RCPT",
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
        try:
            patient_data = self.context_store.get_patient(patient_id)
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
            extracted_text = document.get("extracted_text")
            original_watchfolder_path = document.get("original_watchfolder_path")
            patient_id = document.get("patient_id")
            file_name = document.get("file_name", "unknown_file")
            document_type = document.get("document_type", "Unclassified")
            
            # Skip documents with no extracted text
            if not extracted_text:
                self.logger.warning(f"Document {document_id} ({file_name}) has no extracted text")
                
                # Update document status to indicate it was skipped
                self.context_store.update_document_fields(
                    document_id, 
                    {"processing_status": "tagging_skipped_no_text"}
                )
                
                # Add audit log entry
                self.context_store.add_audit_log_entry(
                    user_id=user_id,
                    event_type="AGENT_ACTIVITY",
                    event_name="DOCUMENT_TAGGING_SKIPPED",
                    status="SKIPPED",
                    resource_type="document",
                    resource_id=document_id,
                    details="Document skipped due to no extracted text"
                )
                
                failed_count += 1
                continue
            
            # Extract metadata from document text
            extracted_dates_dict = self._extract_dates(extracted_text)
            issuer = self._extract_issuer(extracted_text)
            recipient = self._extract_recipient(extracted_text)
            active_tags = self._extract_predefined_tags(extracted_text)
            
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
                    relative_folder = os.path.join("general_archive", year_month_folder)
                
                # Create full path
                filing_dir = os.path.join(self.base_filed_folder, relative_folder)
                os.makedirs(filing_dir, exist_ok=True)
                
                # Generate new descriptive filename using enhanced naming convention
                filed_filename = self._generate_new_filename(
                    document_id, file_name, document_type, primary_date, patient_id, issuer
                )
                new_filed_path = os.path.join(filing_dir, filed_filename)
                
                # Add detailed logging for debugging file path issues
                self.logger.info(f"TAGGER: Attempting to process document_id: {document_id}")
                self.logger.info(f"TAGGER: Original watchfolder path from DB: '{original_watchfolder_path}'")
                if original_watchfolder_path:  # Add a check to ensure path is not None
                    self.logger.info(f"TAGGER: Does original file exist at that path? {os.path.exists(original_watchfolder_path)}")
                else:
                    self.logger.warning("TAGGER: original_watchfolder_path is None or empty.")
                
                # Move file if original path exists
                if original_watchfolder_path and os.path.isfile(original_watchfolder_path):
                    shutil.move(original_watchfolder_path, new_filed_path)
                    filing_successful = True
                    self.logger.info(f"Successfully moved document {document_id} to {new_filed_path}")
                else:
                    # If no original file exists, just update metadata
                    self.logger.warning(f"Original file not found for document {document_id}, updating metadata only")
                    filing_successful = False
                    new_filed_path = None
            
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
            
            # Add audit log entry
            details = f"Document tagged with {len(active_tags)} tags, {len(extracted_dates_dict)} dates"
            if filing_successful:
                details += f", and filed at {new_filed_path}"
            else:
                details += ", but filing failed"
                
            self.context_store.add_audit_log_entry(
                user_id=user_id,
                event_type="AGENT_ACTIVITY",
                event_name="DOCUMENT_TAGGED_AND_FILED",
                status=status,
                resource_type="document",
                resource_id=document_id,
                details=details
            )
        
        self.logger.info(f"Tagging and filing batch run complete. "
                        f"Successfully processed: {successfully_processed_count}, "
                        f"Failed: {failed_count}")
        
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
        
        # Common date formats
        # Format: MM/DD/YYYY or MM-DD-YYYY
        pattern1 = r'(\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)[,.\s]+\d{1,2}(?:[,.\s]+\d{2,4})?)'
        pattern2 = r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
        pattern3 = r'(\d{4}[/-]\d{1,2}[/-]\d{1,2})'
        
        # Common date labels
        date_labels = {
            "invoice_date": [r'invoice\s+date', r'date\s+of\s+invoice', r'dated'],
            "due_date": [r'due\s+date', r'payment\s+due', r'due\s+by', r'pay\s+by'],
            "service_date": [r'service\s+date', r'date\s+of\s+service'],
            "letter_date": [r'letter\s+date', r'dated'],
            "exam_date": [r'exam\s+date', r'examination\s+date', r'date\s+of\s+exam'],
            "report_date": [r'report\s+date', r'reported\s+on', r'date\s+of\s+report']
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
                    for pattern in [pattern1, pattern2, pattern3]:
                        date_match = re.search(pattern, search_text)
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
        for pattern in [pattern1, pattern2, pattern3]:
            all_dates.extend(re.findall(pattern, text))
        
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
        Normalize a date string to YYYY-MM-DD format.
        
        Args:
            date_str: The date string to normalize
            
        Returns:
            Normalized date in YYYY-MM-DD format or None if parsing fails
        """
        # Handle various date formats
        try:
            # Try parsing Month DD, YYYY
            month_names = ['january', 'february', 'march', 'april', 'may', 'june', 
                           'july', 'august', 'september', 'october', 'november', 'december',
                           'jan', 'feb', 'mar', 'apr', 'may', 'jun', 
                           'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
            
            date_str = date_str.lower().strip(',. ')
            for i, month in enumerate(month_names):
                if month in date_str:
                    # This is a textual month format
                    # Extract day and year
                    parts = re.split(r'[,\s]+', date_str.replace(month, ''))
                    parts = [p for p in parts if p.strip()]
                    
                    if len(parts) >= 2:  # Need at least day and year
                        day = next((p for p in parts if p.isdigit() and 1 <= int(p) <= 31), None)
                        year = next((p for p in parts if p.isdigit() and len(p) >= 4), None)
                        
                        if not year:  # Try two-digit year
                            year = next((p for p in parts if p.isdigit() and len(p) == 2), None)
                            if year:
                                year = f"20{year}" if int(year) < 50 else f"19{year}"
                        
                        if day and year:
                            month_num = (i % 12) + 1  # Convert to 1-12
                            return f"{year}-{month_num:02d}-{int(day):02d}"
            
            # Try MM/DD/YYYY or MM-DD-YYYY
            if '/' in date_str or '-' in date_str:
                separator = '/' if '/' in date_str else '-'
                parts = date_str.split(separator)
                
                if len(parts) == 3:
                    # Determine format: MM/DD/YYYY or YYYY/MM/DD
                    if len(parts[0]) == 4:  # YYYY-MM-DD
                        year, month, day = parts
                    else:  # MM-DD-YYYY (assume American format)
                        month, day, year = parts
                    
                    # Fix two-digit years
                    if len(year) == 2:
                        year = f"20{year}" if int(year) < 50 else f"19{year}"
                    
                    return f"{year}-{int(month):02d}-{int(day):02d}"
            
            # If we couldn't parse it, return None
            return None
            
        except (ValueError, IndexError) as e:
            self.logger.debug(f"Error normalizing date '{date_str}': {str(e)}")
            return None
    
    def _extract_issuer(self, text: str) -> Optional[str]:
        """
        Extract the issuer/source of the document.
        
        Args:
            text: The document text to process
            
        Returns:
            Extracted issuer name or None if not found
        """
        # Common patterns for issuers
        issuer_patterns = [
            r'(?:from|issued\s+by|sender):\s*([A-Z][A-Za-z0-9\s&.,]+(?:Inc\.|LLC|Ltd\.|Corp\.|Corporation|Company))',
            r'(?:letterhead|header):\s*([A-Z][A-Za-z0-9\s&.,]+(?:Inc\.|LLC|Ltd\.|Corp\.|Corporation|Company))',
            r'([A-Z][A-Za-z0-9\s&.,]+(?:Inc\.|LLC|Ltd\.|Corp\.|Corporation|Company|Hospital|Medical Center))[^\n.]*?presents',
            r'^([A-Z][A-Za-z0-9\s&.,]+(?:Inc\.|LLC|Ltd\.|Corp\.|Corporation|Company|Hospital|Medical Center))[\n\r]'
        ]
        
        # Try each pattern
        for pattern in issuer_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                issuer = match.group(1).strip()
                if len(issuer) > 3:  # Avoid very short matches
                    return issuer
        
        # Fallback: Look at the first non-empty line (often contains letterhead info)
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        if lines and len(lines[0]) > 3 and not lines[0].lower().startswith(('re:', 'subject:', 'to:', 'date:')):
            return lines[0]
            
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