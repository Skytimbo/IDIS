#!/usr/bin/env python3
"""
Fix the filed_path column in the database by matching documents with their archived files.
This will enable the document image display feature in the search interface.
"""
import sqlite3
import os
import re
from pathlib import Path

# Database path
DB_PATH = "production_idis.db"
ARCHIVE_PATH = "data/archive"

def clean_filename_for_matching(filename):
    """Clean filename for matching purposes by removing extension and special characters."""
    # Remove extension
    base_name = os.path.splitext(filename)[0]
    # Remove common prefixes/suffixes and normalize
    cleaned = re.sub(r'[^a-zA-Z0-9\s]', '', base_name.lower())
    return cleaned.strip()

def find_matching_archive_file(file_name):
    """Find the archived file that matches the database file_name."""
    if not file_name:
        return None
    
    # Clean the target filename for matching
    target_clean = clean_filename_for_matching(file_name)
    
    # Search through all archive files
    for root, dirs, files in os.walk(ARCHIVE_PATH):
        for archive_file in files:
            # Skip cover sheets and other non-document files
            if 'cover_sheet' in archive_file.lower() or archive_file.startswith('.'):
                continue
                
            # Clean the archive filename for matching
            archive_clean = clean_filename_for_matching(archive_file)
            
            # Check if there's a match
            if target_clean in archive_clean or archive_clean in target_clean:
                return os.path.join(root, archive_file)
    
    return None

def update_filed_paths():
    """Update the filed_path column for all documents in the database."""
    if not os.path.exists(DB_PATH):
        print(f"Database not found: {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get all documents that don't have filed_path set
    cursor.execute("""
        SELECT id, file_name 
        FROM documents 
        WHERE filed_path IS NULL OR filed_path = ''
    """)
    
    documents = cursor.fetchall()
    
    print(f"Found {len(documents)} documents without filed_path")
    print("-" * 60)
    
    updated_count = 0
    not_found_count = 0
    
    for doc_id, file_name in documents:
        print(f"Processing document {doc_id}: {file_name}")
        
        # Find matching archive file
        archive_path = find_matching_archive_file(file_name)
        
        if archive_path and os.path.exists(archive_path):
            # Update the database with the file path
            cursor.execute("""
                UPDATE documents 
                SET filed_path = ? 
                WHERE id = ?
            """, (archive_path, doc_id))
            
            print(f"  ✓ Updated with path: {archive_path}")
            updated_count += 1
        else:
            # For test documents without archive files, create a placeholder path
            # This prevents the search UI from trying to display non-existent files
            placeholder_path = f"TEST_DOCUMENT_NO_ARCHIVE/{file_name}"
            cursor.execute("""
                UPDATE documents 
                SET filed_path = ? 
                WHERE id = ?
            """, (placeholder_path, doc_id))
            
            print(f"  ⚠ Set placeholder path: {placeholder_path}")
            not_found_count += 1
    
    # Commit the changes
    conn.commit()
    conn.close()
    
    print("-" * 60)
    print(f"Summary:")
    print(f"  Documents updated: {updated_count}")
    print(f"  Documents not found: {not_found_count}")
    print(f"  Total processed: {len(documents)}")

if __name__ == "__main__":
    update_filed_paths()