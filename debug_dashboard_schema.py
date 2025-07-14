#!/usr/bin/env python3
"""
Debug script to understand the database schema for the Case Management Dashboard.
"""

from context_store import ContextStore

def debug_case_management_schema():
    """Debug the database schema for case management."""
    store = ContextStore('production_idis.db')
    cursor = store.conn.cursor()
    
    print("=== APPLICATION_CHECKLISTS SCHEMA ===")
    cursor.execute("PRAGMA table_info(application_checklists)")
    schema = cursor.fetchall()
    for col in schema:
        print(f"Column: {col[1]}, Type: {col[2]}, NotNull: {col[3]}, Default: {col[4]}")
    
    print("\n=== CASE_DOCUMENTS SCHEMA ===")
    cursor.execute("PRAGMA table_info(case_documents)")
    schema = cursor.fetchall()
    for col in schema:
        print(f"Column: {col[1]}, Type: {col[2]}, NotNull: {col[3]}, Default: {col[4]}")
    
    print("\n=== ENTITIES SCHEMA ===")
    cursor.execute("PRAGMA table_info(entities)")
    schema = cursor.fetchall()
    for col in schema:
        print(f"Column: {col[1]}, Type: {col[2]}, NotNull: {col[3]}, Default: {col[4]}")
    
    print("\n=== SAMPLE CASE_DOCUMENTS DATA ===")
    cursor.execute("SELECT * FROM case_documents LIMIT 5")
    rows = cursor.fetchall()
    for row in rows:
        print(f"ID: {row[0]}, Case ID: {row[1]}, Patient ID: {row[2]}, Checklist Item: {row[3]}, Doc ID: {row[4]}, Status: {row[5]}")
    
    print("\n=== DISTINCT CASE_IDS ===")
    cursor.execute("SELECT DISTINCT case_id FROM case_documents")
    case_ids = cursor.fetchall()
    for case_id in case_ids:
        print(f"Case ID: {case_id[0]}")
    
    print("\n=== ENTITIES DATA ===")
    cursor.execute("SELECT * FROM entities LIMIT 5")
    entities = cursor.fetchall()
    for entity in entities:
        print(f"ID: {entity[0]}, Name: {entity[1]}, Created: {entity[2]}")
    
    print("\n=== APPLICATION CHECKLIST ITEMS ===")
    cursor.execute("SELECT id, required_doc_name FROM application_checklists WHERE checklist_name = 'SOA Medicaid - Adult'")
    items = cursor.fetchall()
    for item in items:
        print(f"ID: {item[0]}, Name: {item[1]}")
    
    store.conn.close()

if __name__ == "__main__":
    debug_case_management_schema()