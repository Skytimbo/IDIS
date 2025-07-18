#!/usr/bin/env python3
"""
Fix Archive Backlog - Process documents stuck in processing_complete status
This script runs the TaggerAgent to archive documents that were processed but not filed.
"""

import os
import logging
from context_store import ContextStore
from tagger_agent import TaggerAgent

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_archive_backlog():
    """Process documents that are stuck in processing_complete status."""
    
    # Initialize components
    context_store = ContextStore("production_idis.db")
    tagger_agent = TaggerAgent(
        context_store=context_store,
        base_filed_folder=os.path.join("data", "archive")
    )
    
    logger.info("Starting archive backlog fix...")
    
    # Check how many documents need processing
    cursor = context_store.conn.cursor()
    cursor.execute("SELECT * FROM documents WHERE processing_status = ?", ("processing_complete",))
    documents = cursor.fetchall()
    logger.info(f"Found {len(documents)} documents in processing_complete status")
    
    if len(documents) == 0:
        logger.info("No documents to process. Exiting.")
        return
    
    # Process documents for tagging and filing
    try:
        filed_count, failed_count = tagger_agent.process_documents_for_tagging_and_filing(
            status_to_process="processing_complete",
            new_status_after_filing="filed_and_tagged"
        )
        
        logger.info(f"Archive backlog fix completed:")
        logger.info(f"  Successfully filed: {filed_count}")
        logger.info(f"  Failed to file: {failed_count}")
        
        if filed_count > 0:
            logger.info("✅ Documents have been successfully archived!")
        if failed_count > 0:
            logger.warning(f"⚠️  {failed_count} documents failed to archive - check logs for details")
            
    except Exception as e:
        logger.error(f"Error during archive backlog fix: {e}")
        raise

if __name__ == "__main__":
    fix_archive_backlog()