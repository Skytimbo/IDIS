#!/usr/bin/env python3
"""
Check the filed_path column in the production database to see if documents have file paths.
"""
import sqlite3
import os

# Database path
DB_PATH = "production_idis.db"

def check_filed_paths():
    """Check filed_path column in documents table."""
    if not os.path.exists(DB_PATH):
        print(f"Database not found: {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check filed_path column
    cursor.execute("""
        SELECT document_id, file_name, filed_path, processing_status 
        FROM documents 
        ORDER BY document_id DESC 
        LIMIT 10
    """)
    
    rows = cursor.fetchall()
    
    print("Recent Documents:")
    print("-" * 80)
    print(f"{'ID':<5} {'File Name':<30} {'Filed Path':<25} {'Status':<15}")
    print("-" * 80)
    
    for row in rows:
        doc_id, file_name, filed_path, status = row
        filed_path_display = str(filed_path) if filed_path else "None"
        file_name_display = str(file_name) if file_name else "None"
        status_display = str(status) if status else "None"
        print(f"{doc_id} | {file_name_display} | {filed_path_display} | {status_display}")
    
    # Check if any documents have filed_path
    cursor.execute("SELECT COUNT(*) FROM documents WHERE filed_path IS NOT NULL AND filed_path != ''")
    count_with_path = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM documents")
    total_count = cursor.fetchone()[0]
    
    print(f"\nSummary:")
    print(f"Total documents: {total_count}")
    print(f"Documents with filed_path: {count_with_path}")
    print(f"Documents without filed_path: {total_count - count_with_path}")
    
    conn.close()

if __name__ == "__main__":
    check_filed_paths()