#!/usr/bin/env python3
"""
Debug script to investigate the document_id issue
"""

import sqlite3

def debug_document_id():
    """Debug the document_id issue"""
    
    db_path = 'production_idis.db'
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check table structure
        print("=== DOCUMENTS TABLE STRUCTURE ===")
        cursor.execute("PRAGMA table_info(documents)")
        columns = cursor.fetchall()
        for col in columns:
            print(f"Column: {col[1]}, Type: {col[2]}, PK: {col[5]}")
        
        # Find test documents
        print("\n=== RECENT DOCUMENTS ===")
        cursor.execute("""
            SELECT document_id, file_name, document_type, upload_timestamp
            FROM documents 
            WHERE file_name LIKE '%test%' OR file_name LIKE '%payslip%'
            ORDER BY upload_timestamp DESC 
            LIMIT 5
        """)
        
        docs = cursor.fetchall()
        for doc in docs:
            print(f"ID: {doc[0]}, File: {doc[1]}, Type: {doc[2]}, Time: {doc[3]}")
        
        # Check if there are any documents with NULL document_id
        print("\n=== NULL DOCUMENT_ID CHECK ===")
        cursor.execute("SELECT COUNT(*) FROM documents WHERE document_id IS NULL")
        null_count = cursor.fetchone()[0]
        print(f"Documents with NULL document_id: {null_count}")
        
        # Show sample documents to understand structure
        print("\n=== SAMPLE DOCUMENTS ===")
        cursor.execute("""
            SELECT document_id, file_name, document_type 
            FROM documents 
            ORDER BY upload_timestamp DESC 
            LIMIT 3
        """)
        
        sample_docs = cursor.fetchall()
        for doc in sample_docs:
            print(f"ID: {doc[0]}, File: {doc[1]}, Type: {doc[2]}")
        
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    debug_document_id()