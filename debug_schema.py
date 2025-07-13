#!/usr/bin/env python3
"""
Debug script to check the case_documents table schema in the production database.
"""

import sqlite3

def check_schema():
    """Check the schema of the case_documents table."""
    try:
        conn = sqlite3.connect('production_idis.db')
        cursor = conn.cursor()
        
        # Get table schema
        cursor.execute("PRAGMA table_info(case_documents)")
        columns = cursor.fetchall()
        
        print("=== case_documents table schema ===")
        for column in columns:
            print(f"Column: {column[1]} | Type: {column[2]} | Not Null: {column[3]} | Default: {column[4]} | PK: {column[5]}")
        
        # Check if the table has any data
        cursor.execute("SELECT COUNT(*) FROM case_documents")
        count = cursor.fetchone()[0]
        print(f"\nTotal records in case_documents: {count}")
        
        # Show sample data if any exists
        if count > 0:
            cursor.execute("SELECT * FROM case_documents LIMIT 3")
            rows = cursor.fetchall()
            print("\nSample data:")
            for i, row in enumerate(rows, 1):
                print(f"Row {i}: {row}")
        
        conn.close()
        
    except Exception as e:
        print(f"Error checking schema: {e}")

if __name__ == "__main__":
    check_schema()