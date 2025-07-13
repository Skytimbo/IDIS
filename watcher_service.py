#!/usr/bin/env python3
"""
Watcher Service Module for Intelligent Document Insight System (IDIS) - Triage Architecture

This module provides continuous monitoring of a specified watch folder for new files.
It implements a "triage" architecture that separates file watching from processing:
- A simple watcher moves files to an inbox folder
- A timer-based processor handles the complete IDIS pipeline
"""

import os
import sys
import time
import logging
import argparse
import shutil
from typing import Dict, List, Optional, Any
from watchdog.observers.polling import PollingObserver as Observer
from watchdog.events import FileSystemEventHandler

# Import IDIS components
from context_store import ContextStore
from unified_ingestion_agent import UnifiedIngestionAgent
from cover_sheet import SmartCoverSheetRenderer
from permissions import PermissionsManager
from run_mvp import execute_pipeline_for_files, CLASSIFICATION_RULES, TAG_DEFINITIONS, PERMISSIONS_RULES_FILE

# Note: Logging is now configured in the main() function using environment variables


def process_inbox_file(
    file_path: str,
    config_paths: Dict[str, str],
    classification_rules: Dict[str, List[str]],
    tag_definitions: Dict[str, List[str]],
    openai_api_key: Optional[str],
    patient_id_for_new_docs: Optional[str] = None,
    user_id_for_new_docs: str = "watcher_service_user"
) -> Dict[str, Any]:
    """
    Process a single file from the inbox folder through the complete IDIS pipeline.
    
    Args:
        file_path: Full path to the file in the inbox folder
        config_paths: Dictionary containing folder paths configuration
        classification_rules: Document classification rules
        tag_definitions: Tag extraction definitions
        openai_api_key: Optional OpenAI API key for summarization
        patient_id_for_new_docs: Optional default patient ID for new documents
        user_id_for_new_docs: User ID for audit trail purposes
        
    Returns:
        Dictionary containing processing results and statistics
    """
    logger = logging.getLogger("InboxProcessor")
    original_filename = os.path.basename(file_path)
    
    try:
        logger.info(f"Processing inbox file: {original_filename}")
        
        # Create a local ContextStore instance for this processing session
        local_context_store = ContextStore(db_path=config_paths['db_path'])
        
        # Create a new session for this file
        session_id = local_context_store.create_session(
            user_id=user_id_for_new_docs,
            session_metadata={
                "source_file": original_filename,
                "trigger": "inbox_processor",
                "processing_mode": "single_file"
            }
        )
        
        # Initialize the modern UnifiedIngestionAgent which handles the complete pipeline
        unified_agent = UnifiedIngestionAgent(
            context_store=local_context_store,
            watch_folder=os.path.dirname(file_path),  # Use inbox folder as source
            holding_folder=config_paths['holding_folder']
        )
        
        # Process the specific file through the unified cognitive pipeline
        processing_success = unified_agent._process_single_file(
            file_path=file_path,
            filename=original_filename,
            entity_id=int(patient_id_for_new_docs) if patient_id_for_new_docs else 1,
            session_id=session_id
        )
        
        # Set results based on processing success
        ingestion_results = 1 if processing_success else 0
        
        if processing_success:
            logger.info(f"Successfully processed {original_filename} through unified cognitive pipeline")
            
            # The UnifiedIngestionAgent handles the complete pipeline including:
            # 1. Text extraction
            # 2. CognitiveAgent AI analysis for document classification and data extraction
            # 3. Database storage with both legacy fields and rich JSON data
            # 4. Automatic processing status management
            
            # No need for separate classifier, summarizer, or tagger agents
            # as the CognitiveAgent provides superior intelligence in a single step
            
            classification_results = (1, 0)  # Success tuple format
            summarization_results = (1, 0)   # Success tuple format  
            tagging_results = (1, 0)         # Success tuple format
            
            # Generate cover sheet
            documents = local_context_store.get_documents_for_session(session_id)
            document_ids = [doc["document_id"] for doc in documents]
            
            cover_sheet_pdf_path = None
            if document_ids:
                cover_sheet_pdf_path = os.path.join(
                    config_paths['pdf_output_dir'],
                    f"Inbox_Cover_Sheet_{session_id}.pdf"
                )
                
                cover_sheet_renderer = SmartCoverSheetRenderer(context_store=local_context_store)
                cover_sheet_renderer.generate_cover_sheet(
                    document_ids=document_ids,
                    output_pdf_filename=cover_sheet_pdf_path,
                    session_id=str(session_id),
                    user_id=user_id_for_new_docs
                )
            
            # File cleanup for unified processing
            # The UnifiedIngestionAgent handles complete processing in the database but doesn't archive files
            # We need to clean up the inbox file after successful processing
            try:
                os.remove(file_path)
                logger.info(f"Successfully processed and cleaned up inbox file: {original_filename}")
            except Exception as e:
                logger.warning(f"Failed to clean up inbox file {original_filename}: {e}")
                # Non-critical error - file processed successfully but cleanup failed
            
            return {
                'session_id': session_id,
                'documents': documents,
                'cover_sheet_path': cover_sheet_pdf_path,
                'stats': {
                    'ingested': ingestion_results,
                    'classified': classification_results,
                    'summarized': summarization_results,
                    'tagged': tagging_results
                }
            }
        else:
            # Ingestion failed: Move file to holding folder for manual inspection
            logger.warning(f"Failed to ingest file: {original_filename}")
            try:
                holding_path = os.path.join(config_paths['holding_folder'], original_filename)
                shutil.move(file_path, holding_path)
                logger.error(f"INGESTION FAILED: Moved {original_filename} to holding folder for manual inspection")
            except Exception as e:
                logger.error(f"CRITICAL: Failed to move {original_filename} to holding folder: {e}")
                logger.error(f"File remains in inbox: {file_path}")
            return {'session_id': session_id, 'stats': {'ingested': 0}}
            
    except Exception as e:
        logger.exception(f"Error processing inbox file {file_path}: {e}")
        
        # Move file to holding folder due to processing error
        try:
            holding_path = os.path.join(config_paths['holding_folder'], original_filename)
            shutil.move(file_path, holding_path)
            logger.error(f"PROCESSING ERROR: Moved {original_filename} to holding folder due to exception")
        except Exception as move_error:
            logger.error(f"CRITICAL: Failed to move {original_filename} to holding folder after processing error: {move_error}")
            logger.error(f"File remains in inbox: {file_path}")
        
        return {'error': str(e), 'file': original_filename}


class NewFileHandler(FileSystemEventHandler):
    """
    Simplified file system event handler for triage architecture.
    
    This handler has one job: move files from the watch folder to the inbox folder.
    All complex processing logic has been moved to the process_inbox_file function.
    """
    
    def __init__(self, inbox_folder: str):
        """
        Initialize the simplified file handler for triage architecture.
        
        Args:
            inbox_folder: Path to the inbox folder where files should be moved
        """
        super().__init__()
        self.inbox_folder = inbox_folder
        self.logger = logging.getLogger("NewFileHandler")
    
    def on_created(self, event):
        """
        Simple file triage - move PDF files to inbox folder immediately.
        
        This method has one job: grab PDF files and move them to the inbox.
        No processing logic, no stability checks, just fast file claiming.
        
        Args:
            event: File system event object
        """
        if event.is_directory:
            return
        
        file_path = event.src_path
        original_filename = os.path.basename(file_path)
        
        # Ignore temporary files created by scanner
        if original_filename.endswith('.tmp'):
            self.logger.debug(f"Ignoring temporary file: {original_filename}")
            return
        
        # Simple move to inbox - no retries, no complex logic
        inbox_path = os.path.join(self.inbox_folder, original_filename)
        try:
            shutil.move(file_path, inbox_path)
            self.logger.info(f"File moved to inbox: {inbox_path}")
        except Exception as e:
            self.logger.debug(f"Failed to move {file_path} to inbox: {e}")
            pass
    
    def on_modified(self, event):
        """
        Simple file triage - move PDF files to inbox folder immediately.
        
        This method has one job: grab PDF files and move them to the inbox.
        No processing logic, no stability checks, just fast file claiming.
        
        Args:
            event: File system event object
        """
        if event.is_directory:
            return
        
        file_path = event.src_path
        original_filename = os.path.basename(file_path)
        
        # Ignore temporary files created by scanner
        if original_filename.endswith('.tmp'):
            self.logger.debug(f"Ignoring temporary file: {original_filename}")
            return
        
        # Simple move to inbox - no retries, no complex logic
        inbox_path = os.path.join(self.inbox_folder, original_filename)
        try:
            shutil.move(file_path, inbox_path)
            self.logger.info(f"File moved to inbox: {inbox_path}")
        except Exception as e:
            self.logger.debug(f"Failed to move {file_path} to inbox: {e}")
            pass


def setup_folder_paths(args):
    """Set up and validate folder paths from command line arguments."""
    config_paths = {
        'watch_folder': args.watch_folder,
        'inbox_folder': args.inbox_folder,
        'holding_folder': args.holding_folder,
        'archive_folder': args.archive_folder,
        'cover_sheets_folder': args.cover_sheets_folder,
        'pdf_output_dir': args.cover_sheets_folder,  # Use cover sheets folder for PDF output
        'db_path': args.db_path,
    }
    
    # Create directories if they don't exist
    for path_name, path_value in config_paths.items():
        if path_name != 'db_path' and not os.path.exists(path_value):
            os.makedirs(path_value, exist_ok=True)
            logging.info(f"Created directory: {path_value}")
    
    return config_paths


def main():
    """Main function to run the triage-based watcher service."""
    parser = argparse.ArgumentParser(description='IDIS Watcher Service - Triage Architecture')
    parser.add_argument('--watch-folder', required=True, help='Folder to monitor for new files')
    parser.add_argument('--inbox-folder', required=True, help='Folder where files are moved for processing')
    parser.add_argument('--holding-folder', required=True, help='Folder for files that failed processing')
    parser.add_argument('--archive-folder', required=True, help='Folder for successfully processed files')
    parser.add_argument('--cover-sheets-folder', required=True, help='Folder for generated cover sheet PDFs')
    parser.add_argument('--db-path', required=True, help='Path to the SQLite database file')
    parser.add_argument('--openai', action='store_true', help='Enable OpenAI API for summarization')
    parser.add_argument('--patient-id', help='Default patient ID for new documents')
    parser.add_argument('--user-id', default='watcher_service_user', help='User ID for audit trail')
    
    args = parser.parse_args()
    
    # Get logging level from environment variable, default to INFO
    log_level_name = os.getenv("LOGGING_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)

    # Basic logging config
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout,
    )

    # Suppress noisy third-party loggers
    noisy_loggers = ['fontTools', 'fpdf2', 'reportlab', 'httpx', 'openai']
    for logger_name in noisy_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)
    
    # Set up logging
    logger = logging.getLogger("WatcherService")
    logger.info("Starting IDIS Watcher Service with Triage Architecture")
    
    # Set up folder paths
    config_paths = setup_folder_paths(args)
    logger.info(f"Watching folder: {config_paths['watch_folder']}")
    logger.info(f"Inbox folder: {config_paths['inbox_folder']}")
    
    # Get OpenAI API key if requested
    openai_api_key = None
    if args.openai:
        openai_api_key = os.environ.get('OPENAI_API_KEY')
        if not openai_api_key:
            logger.warning("OpenAI API requested but OPENAI_API_KEY environment variable not set")
    
    # Set up file watcher
    event_handler = NewFileHandler(inbox_folder=config_paths['inbox_folder'])
    observer = Observer()
    observer.schedule(event_handler, config_paths['watch_folder'], recursive=False)
    observer.start()
    logger.info("File watcher started")
    
    try:
        # Main processor loop - runs every 15 seconds
        while True:
            time.sleep(15)  # Wait 15 seconds between processing runs
            
            # Check inbox folder for files to process
            try:
                if os.path.exists(config_paths['inbox_folder']):
                    inbox_files = os.listdir(config_paths['inbox_folder'])
                    if inbox_files:
                        logger.info(f"Found {len(inbox_files)} files in inbox for processing")
                        
                        for filename in inbox_files:
                            file_path = os.path.join(config_paths['inbox_folder'], filename)
                            if os.path.isfile(file_path):
                                # Process the file
                                result = process_inbox_file(
                                    file_path=file_path,
                                    config_paths=config_paths,
                                    classification_rules=CLASSIFICATION_RULES,
                                    tag_definitions=TAG_DEFINITIONS,
                                    openai_api_key=openai_api_key,
                                    patient_id_for_new_docs=args.patient_id,
                                    user_id_for_new_docs=args.user_id
                                )
                                
                                if 'error' in result:
                                    logger.error(f"Failed to process file {filename}: {result['error']}")
                                    # File should already be moved to holding folder by process_inbox_file
                                else:
                                    logger.info(f"Successfully processed file {filename}")
                                    # File should already be removed from inbox by process_inbox_file
                    
            except Exception as e:
                logger.exception(f"Error in main processor loop: {e}")
                
    except KeyboardInterrupt:
        logger.info("Shutting down watcher service...")
    finally:
        observer.stop()
        observer.join()
        logger.info("Watcher service stopped")


if __name__ == "__main__":
    main()