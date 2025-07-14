#!/usr/bin/env python3
"""
Script to examine the current database schema and add user_id columns
"""

import sqlite3
import sys

def examine_schema():
    """Examine the current database schema"""
    conn = sqlite3.connect('production_idis.db')
    cursor = conn.cursor()
    
    print("=== ENTITIES TABLE SCHEMA ===")
    cursor.execute("PRAGMA table_info(entities)")
    entities_schema = cursor.fetchall()
    for row in entities_schema:
        print(f"  {row}")
    
    print("\n=== CASE_DOCUMENTS TABLE SCHEMA ===")
    cursor.execute("PRAGMA table_info(case_documents)")
    case_docs_schema = cursor.fetchall()
    for row in case_docs_schema:
        print(f"  {row}")
    
    print("\n=== ENTITIES SAMPLE DATA ===")
    cursor.execute("SELECT * FROM entities LIMIT 5")
    entities_data = cursor.fetchall()
    for row in entities_data:
        print(f"  {row}")
    
    print("\n=== CASE_DOCUMENTS SAMPLE DATA ===")
    cursor.execute("SELECT * FROM case_documents LIMIT 5")
    case_docs_data = cursor.fetchall()
    for row in case_docs_data:
        print(f"  {row}")
    
    conn.close()

def add_user_id_columns():
    """Add user_id columns to entities and case_documents tables"""
    conn = sqlite3.connect('production_idis.db')
    cursor = conn.cursor()
    
    try:
        # Add user_id to entities table
        print("Adding user_id column to entities table...")
        cursor.execute("ALTER TABLE entities ADD COLUMN user_id TEXT DEFAULT 'user_a'")
        print("  ✓ Added user_id to entities table")
        
        # Add user_id to case_documents table
        print("Adding user_id column to case_documents table...")
        cursor.execute("ALTER TABLE case_documents ADD COLUMN user_id TEXT DEFAULT 'user_a'")
        print("  ✓ Added user_id to case_documents table")
        
        # Update existing records with default values
        print("Updating existing records with default user_id values...")
        cursor.execute("UPDATE entities SET user_id = 'user_a' WHERE user_id IS NULL")
        cursor.execute("UPDATE case_documents SET user_id = 'user_a' WHERE user_id IS NULL")
        print("  ✓ Updated existing records")
        
        conn.commit()
        print("✓ Database schema updated successfully")
        
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print(f"Column already exists: {e}")
        else:
            print(f"Error: {e}")
    
    conn.close()

if __name__ == "__main__":
    print("Examining current database schema...")
    examine_schema()
    
    print("\n" + "="*50)
    print("Adding user_id columns...")
    add_user_id_columns()
    
    print("\n" + "="*50)
    print("Updated database schema:")
    examine_schema()