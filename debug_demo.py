#!/usr/bin/env python3
"""
Debug script to examine demo database contents and identify user ID mismatches
"""

import sqlite3
import os

def debug_demo_database():
    """Debug the demo database to find user ID mismatches"""
    
    # Check which database files exist
    print("=== DATABASE FILES ===")
    for db_file in ['demo_idis.db', 'production_idis.db']:
        if os.path.exists(db_file):
            print(f"✓ {db_file} exists")
        else:
            print(f"✗ {db_file} missing")
    
    # Check demo database first
    if os.path.exists('demo_idis.db'):
        print("\n=== DEMO DATABASE (demo_idis.db) ===")
        debug_database('demo_idis.db')
    
    # Check production database
    if os.path.exists('production_idis.db'):
        print("\n=== PRODUCTION DATABASE (production_idis.db) ===")
        debug_database('production_idis.db')

def debug_database(db_file):
    """Debug a specific database file"""
    
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    print(f"\n--- ENTITIES in {db_file} ---")
    cursor.execute("SELECT id, entity_name, user_id FROM entities")
    entities = cursor.fetchall()
    for e in entities:
        print(f"ID: {e[0]}, Name: {e[1]}, User: {e[2]}")
    
    print(f"\n--- CASE DOCUMENTS in {db_file} ---")
    cursor.execute("SELECT case_id, entity_id, user_id FROM case_documents LIMIT 5")
    cases = cursor.fetchall()
    for c in cases:
        print(f"Case: {c[0]}, Entity: {c[1]}, User: {c[2]}")
    
    print(f"\n--- DOCUMENTS in {db_file} ---")
    cursor.execute("SELECT id, file_name, user_id, entity_id FROM documents LIMIT 5")
    docs = cursor.fetchall()
    for d in docs:
        print(f"Doc ID: {d[0]}, File: {d[1]}, User: {d[2]}, Entity: {d[3]}")
    
    print(f"\n--- UNIQUE USER IDs in {db_file} ---")
    cursor.execute("SELECT DISTINCT user_id FROM entities UNION SELECT DISTINCT user_id FROM case_documents UNION SELECT DISTINCT user_id FROM documents")
    users = cursor.fetchall()
    for u in users:
        print(f"User ID: {repr(u[0])}")
    
    conn.close()

def check_app_expectations():
    """Check what user IDs the app expects"""
    print("\n=== APP EXPECTATIONS ===")
    print("App probably looking for user_id:", repr('user_a'))
    print("Common user IDs in app:", ['user_a', 'caseworker_demo', 'demo_user'])

if __name__ == "__main__":
    debug_demo_database()
    check_app_expectations()