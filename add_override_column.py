#!/usr/bin/env python3
"""
Script to add the is_override column to the case_documents table
"""

import sqlite3
import sys

def add_override_column():
    """Add the is_override column to case_documents table"""
    try:
        conn = sqlite3.connect('production_idis.db')
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(case_documents)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'is_override' not in columns:
            # Add the column
            cursor.execute("ALTER TABLE case_documents ADD COLUMN is_override INTEGER DEFAULT 0")
            conn.commit()
            print("✅ Added is_override column to case_documents table")
        else:
            print("✅ is_override column already exists")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error adding column: {e}")
        return False

if __name__ == "__main__":
    success = add_override_column()
    sys.exit(0 if success else 1)