#!/usr/bin/env python3
"""
View Text Utility for IDIS Debugging

This utility script allows viewing the OCR-extracted text stored in the database
for a specific document ID. Useful for debugging text extraction issues.
"""

import argparse
import os
import sys
from context_store import ContextStore


def main():
    """Main function to view extracted text from database."""
    parser = argparse.ArgumentParser(
        description="View OCR extracted text from IDIS database"
    )
    parser.add_argument(
        "--document-id",
        required=True,
        help="Document ID to retrieve text for"
    )
    parser.add_argument(
        "--db-path",
        required=True,
        help="Path to the SQLite database file"
    )
    
    args = parser.parse_args()
    
    # Use database path from command-line argument
    db_path = args.db_path
    
    # Check if database exists
    if not os.path.exists(db_path):
        print(f"ERROR: Database not found at {db_path}")
        print("Make sure the watcher service has been run at least once to create the database.")
        sys.exit(1)
    
    try:
        # Connect to the Context Store
        context_store = ContextStore(db_path)
        
        # Fetch the document record
        document = context_store.get_document(args.document_id)
        
        if document is None:
            print(f"ERROR: Document with ID '{args.document_id}' not found in database.")
            sys.exit(1)
        
        # Display document information
        print(f"Document ID: {document['document_id']}")
        print(f"File Name: {document['file_name']}")
        print(f"Document Type: {document.get('document_type', 'Not classified')}")
        print(f"Processing Status: {document['processing_status']}")
        print(f"Upload Timestamp: {document['upload_timestamp']}")
        print("-" * 80)
        
        # Display extracted text
        extracted_text = document.get('full_text')
        if extracted_text:
            print("EXTRACTED TEXT:")
            print("-" * 80)
            print(extracted_text)
        else:
            print("No extracted text found for this document.")
            print("This could indicate:")
            print("- The document hasn't been processed by the Ingestion Agent yet")
            print("- OCR extraction failed for this document")
            print("- The document is in the holding folder due to processing issues")
        
    except Exception as e:
        print(f"ERROR: Failed to retrieve document: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()