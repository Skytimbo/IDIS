#!/usr/bin/env python3
"""
Debug the database structure to understand the document_id issue
"""
import sqlite3
import os

DB_PATH = "production_idis.db"

def debug_database():
    """Debug the database structure and content."""
    if not os.path.exists(DB_PATH):
        print(f"Database not found: {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get table schema
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='documents'")
    schema = cursor.fetchone()
    if schema:
        print("Documents table schema:")
        print(schema[0])
        print("\n" + "="*50 + "\n")
    
    # Get column info
    cursor.execute("PRAGMA table_info(documents)")
    columns = cursor.fetchall()
    print("Column information:")
    for col in columns:
        print(f"  {col[1]} ({col[2]}) - Primary Key: {col[5]}")
    print("\n" + "="*50 + "\n")
    
    # Get all document records with proper column names
    cursor.execute("SELECT * FROM documents LIMIT 5")
    rows = cursor.fetchall()
    
    # Get column names
    cursor.execute("PRAGMA table_info(documents)")
    columns = [col[1] for col in cursor.fetchall()]
    print(f"Column names: {columns}")
    print("\n" + "="*50 + "\n")
    
    print("Sample document records:")
    for i, row in enumerate(rows):
        print(f"Record {i+1}:")
        for j, col_name in enumerate(columns):
            if j < len(row):
                print(f"  {col_name}: {row[j]}")
        print()
    
    conn.close()

if __name__ == "__main__":
    debug_database()