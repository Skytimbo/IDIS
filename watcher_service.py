#!/usr/bin/env python3
"""
Watcher Service Module for Intelligent Document Insight System (IDIS)

This module provides continuous monitoring of a specified watch folder for new files.
When a new file is detected and deemed stable, it triggers the IDIS pipeline
to process that single file through the complete agent workflow.
"""

import os
import time
import logging
import argparse
from typing import Dict, List, Optional, Any
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Import IDIS components
from context_store import ContextStore
from ingestion_agent import IngestionAgent
from classifier_agent import ClassifierAgent
from summarizer_agent import SummarizerAgent
from tagger_agent import TaggerAgent
from cover_sheet import SmartCoverSheetRenderer
from permissions import PermissionsManager
from run_mvp import execute_pipeline_for_files, CLASSIFICATION_RULES, TAG_DEFINITIONS, PERMISSIONS_RULES_FILE

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class NewFileHandler(FileSystemEventHandler):
    """
    File system event handler for processing new files detected by the watcher service.
    
    This handler monitors file creation events, performs stability checks to ensure
    files are fully written, and then triggers the IDIS pipeline for processing.
    """
    
    def __init__(
        self,
        context_store_instance: ContextStore,
        config_paths: Dict[str, str],
        classification_rules: Dict[str, List[str]],
        tag_definitions: Dict[str, List[str]],
        openai_api_key: Optional[str],
        patient_id_for_new_docs: Optional[str] = None,
        user_id_for_new_docs: str = "watcher_service_user"
    ):
        """
        Initialize the file handler with pipeline configuration.
        
        Args:
            context_store_instance: Initialized ContextStore instance
            config_paths: Dictionary containing folder paths configuration
            classification_rules: Document classification rules
            tag_definitions: Tag extraction definitions
            openai_api_key: Optional OpenAI API key for summarization
            patient_id_for_new_docs: Optional default patient ID for new documents
            user_id_for_new_docs: User ID for audit trail purposes
        """
        super().__init__()
        self.context_store_instance = context_store_instance
        self.config_paths = config_paths
        self.classification_rules = classification_rules
        self.tag_definitions = tag_definitions
        self.openai_api_key = openai_api_key
        self.patient_id_for_new_docs = patient_id_for_new_docs
        self.user_id_for_new_docs = user_id_for_new_docs
        
        # File stability configuration
        self.file_stability_delay = 10  # seconds - initial cooldown
        self.file_stability_checks = 3  # number of size checks
        self.file_stability_check_interval = 2  # seconds between checks
        
        self.logger = logging.getLogger("NewFileHandler")
    
    def on_created(self, event):
        """
        Handle file creation events.
        
        Args:
            event: File system event object
        """
        if event.is_directory:
            return
        
        file_path = event.src_path
        self.logger.info(f"Detected new file: {file_path}. Starting stability check...")
        
        # Initial cooldown period
        time.sleep(self.file_stability_delay)
        
        # Perform file stability check
        try:
            if not os.path.exists(file_path):
                self.logger.info(f"File {file_path} disappeared during cooldown.")
                return
            
            last_size = os.path.getsize(file_path)
            stable_count = 0
            
            for _ in range(self.file_stability_checks):
                time.sleep(self.file_stability_check_interval)
                
                if not os.path.exists(file_path):
                    self.logger.info(f"File {file_path} disappeared during stability checks.")
                    return
                
                current_size = os.path.getsize(file_path)
                
                if current_size == last_size and current_size > 0:
                    stable_count += 1
                else:
                    last_size = current_size
                    stable_count = 0  # Reset if size changes
                
                if stable_count >= 2:  # Consider stable if size hasn't changed
                    break
            
            if stable_count >= 2:
                self.logger.info(f"File {file_path} confirmed stable. Triggering pipeline.")
                
                # Create a new session for this file
                session_id = self.context_store_instance.create_session(
                    user_id=self.user_id_for_new_docs,
                    session_metadata={
                        "source_file": os.path.basename(file_path),
                        "trigger": "watcher_service",
                        "processing_mode": "single_file"
                    }
                )
                
                # Call the pipeline executor for this single file
                try:
                    results = execute_pipeline_for_files(
                        context_store=self.context_store_instance,
                        config_paths=self.config_paths,
                        classification_rules=self.classification_rules,
                        tag_definitions=self.tag_definitions,
                        openai_api_key=self.openai_api_key,
                        files_to_process_paths=[file_path],
                        session_id=session_id,
                        patient_id=self.patient_id_for_new_docs,
                        user_id=self.user_id_for_new_docs
                    )
                    
                    self.logger.info(
                        f"Pipeline processing completed for {file_path} under session {session_id}. "
                        f"Results: {results['stats']}"
                    )
                    
                    # Log cover sheet generation if successful
                    if results.get('cover_sheet_path'):
                        self.logger.info(f"Cover sheet generated: {results['cover_sheet_path']}")
                
                except Exception as pipeline_error:
                    self.logger.error(f"Pipeline processing failed for {file_path}: {pipeline_error}")
                    
                    # Update session with error status
                    try:
                        self.context_store_instance.update_session_metadata(
                            session_id, 
                            {"processing_error": str(pipeline_error)}
                        )
                    except Exception as update_error:
                        self.logger.error(f"Failed to update session with error: {update_error}")
            
            else:
                self.logger.info(f"File {file_path} did not stabilize or is empty. Skipping.")
        
        except Exception as e:
            self.logger.error(f"Error during stability check or pipeline trigger for {file_path}: {e}")


def main():
    """
    Main function to set up and run the watcher service.
    """
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(description="IDIS Watcher Service - Continuous Document Monitoring")
    parser.add_argument('--watch-folder', type=str, required=True,
                        help='Path to the folder to monitor for new documents')
    parser.add_argument('--holding-folder', type=str, required=True,
                        help='Path to the folder for processed/problematic documents')
    parser.add_argument('--archive-folder', type=str, required=True,
                        help='Path to the folder for archived documents')
    parser.add_argument('--cover-sheets-folder', type=str, required=True,
                        help='Path to the folder for generated cover sheets')
    parser.add_argument('--db-path', type=str, required=True,
                        help='Path to the SQLite database file')
    parser.add_argument('--openai', action='store_true',
                        help='Enable OpenAI for summarization')
    parser.add_argument('--default-patient-id', type=str,
                        help='Optional default patient ID for new documents')
    
    args = parser.parse_args()
    
    # Set up logging
    logger = logging.getLogger("WatcherService")
    logger.info("Starting IDIS Watcher Service")
    
    # Build config paths dictionary
    config_paths = {
        'watch_folder': args.watch_folder,
        'holding_folder': args.holding_folder,
        'archive_folder': args.archive_folder,
        'pdf_output_dir': args.cover_sheets_folder,
        'db_path': args.db_path
    }
    
    # Ensure all directories exist
    for folder_name, folder_path in config_paths.items():
        if folder_name != 'db_path':  # Skip database path
            os.makedirs(folder_path, exist_ok=True)
            logger.info(f"Ensured directory exists: {folder_path}")
    
    # Ensure database directory exists
    db_dir = os.path.dirname(config_paths['db_path'])
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    
    # Initialize Context Store
    try:
        context_store = ContextStore(db_path=config_paths['db_path'])
        logger.info(f"Initialized Context Store with database: {config_paths['db_path']}")
    except Exception as e:
        logger.error(f"Failed to initialize Context Store: {e}")
        return 1
    
    # Initialize Permissions Manager
    try:
        permissions_manager = PermissionsManager(rules_file_path=PERMISSIONS_RULES_FILE)
        logger.info("Initialized Permissions Manager")
    except Exception as e:
        logger.warning(f"Failed to initialize Permissions Manager: {e}")
    
    # Get OpenAI API key if requested
    openai_api_key = None
    if args.openai:
        openai_api_key = os.environ.get('OPENAI_API_KEY')
        if openai_api_key:
            logger.info("OpenAI integration enabled")
        else:
            logger.warning("--openai flag used but no OPENAI_API_KEY environment variable found")
    
    # Create file event handler
    event_handler = NewFileHandler(
        context_store_instance=context_store,
        config_paths=config_paths,
        classification_rules=CLASSIFICATION_RULES,
        tag_definitions=TAG_DEFINITIONS,
        openai_api_key=openai_api_key,
        patient_id_for_new_docs=args.default_patient_id,
        user_id_for_new_docs="watcher_service_user"
    )
    
    # Initialize and start the watchdog observer
    observer = Observer()
    observer.schedule(event_handler, args.watch_folder, recursive=False)
    observer.start()
    
    logger.info(f"Watcher service started. Monitoring folder: {args.watch_folder}")
    logger.info("Press Ctrl+C to stop the service.")
    
    try:
        while True:
            time.sleep(5)  # Keep main thread alive
    except KeyboardInterrupt:
        logger.info("Watcher service shutting down...")
        observer.stop()
    finally:
        observer.join()
        logger.info("Watcher service stopped.")
    
    return 0


if __name__ == "__main__":
    exit(main())