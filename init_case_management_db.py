#!/usr/bin/env python3
"""
Case Management Database Initialization Script

This script adds case management tables to the production IDIS database
to support tracking Medicaid application requirements and document submissions.

Author: IDIS Development Team
Date: July 2025
"""

import sqlite3
import sys
import os
from datetime import datetime

def connect_to_database(db_path):
    """Connect to the production database."""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}")
        sys.exit(1)

def create_case_management_tables(conn):
    """Create the case management tables."""
    cursor = conn.cursor()
    
    try:
        # Create application_checklists table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS application_checklists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                checklist_name TEXT NOT NULL,
                required_doc_name TEXT NOT NULL,
                description TEXT
            )
        """)
        
        # Create case_documents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS case_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT NOT NULL,
                patient_id INTEGER NOT NULL,
                checklist_item_id INTEGER NOT NULL,
                document_id INTEGER,
                status TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES patients (id),
                FOREIGN KEY (checklist_item_id) REFERENCES application_checklists (id),
                FOREIGN KEY (document_id) REFERENCES documents (id)
            )
        """)
        
        conn.commit()
        print("✅ Case management tables created successfully")
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Error creating tables: {e}")
        conn.rollback()
        return False

def populate_alaska_medicaid_checklist(conn):
    """Populate the application_checklists table with Alaska Medicaid requirements."""
    cursor = conn.cursor()
    
    # Alaska Medicaid Adult application requirements
    alaska_medicaid_requirements = [
        ("SOA Medicaid - Adult", "Proof of Identity", "e.g., Driver's License, State ID Card"),
        ("SOA Medicaid - Adult", "Proof of Citizenship", "e.g., U.S. Birth Certificate, Passport"),
        ("SOA Medicaid - Adult", "Proof of Alaska Residency", "e.g., Utility Bill, Lease Agreement"),
        ("SOA Medicaid - Adult", "Proof of Income", "e.g., Pay stubs (last 30 days), Tax Return"),
        ("SOA Medicaid - Adult", "Proof of Resources/Assets", "e.g., Bank Statements (last 60 days)")
    ]
    
    try:
        # Check if requirements already exist
        cursor.execute("""
            SELECT COUNT(*) FROM application_checklists 
            WHERE checklist_name = 'SOA Medicaid - Adult'
        """)
        existing_count = cursor.fetchone()[0]
        
        if existing_count > 0:
            print(f"ℹ️  Found {existing_count} existing SOA Medicaid requirements. Skipping population.")
            return True
        
        # Insert the requirements
        cursor.executemany("""
            INSERT INTO application_checklists (checklist_name, required_doc_name, description)
            VALUES (?, ?, ?)
        """, alaska_medicaid_requirements)
        
        conn.commit()
        print(f"✅ Successfully populated {len(alaska_medicaid_requirements)} Alaska Medicaid requirements")
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Error populating checklist: {e}")
        conn.rollback()
        return False

def verify_schema_changes(conn):
    """Verify that the new tables were created correctly."""
    cursor = conn.cursor()
    
    try:
        # Check application_checklists table
        cursor.execute("SELECT COUNT(*) FROM application_checklists")
        checklist_count = cursor.fetchone()[0]
        
        # Check case_documents table structure
        cursor.execute("PRAGMA table_info(case_documents)")
        case_docs_columns = [row[1] for row in cursor.fetchall()]
        
        print(f"✅ Verification complete:")
        print(f"   - application_checklists table: {checklist_count} requirements")
        print(f"   - case_documents table: {len(case_docs_columns)} columns")
        
        # Show the populated requirements
        if checklist_count > 0:
            cursor.execute("""
                SELECT checklist_name, required_doc_name, description 
                FROM application_checklists 
                ORDER BY id
            """)
            requirements = cursor.fetchall()
            
            print("\n📋 Alaska Medicaid Requirements:")
            for req in requirements:
                print(f"   • {req[1]}: {req[2]}")
        
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Error during verification: {e}")
        return False

def main():
    """Main execution function."""
    db_path = "production_idis.db"
    
    print("🚀 Starting Case Management Database Initialization")
    print(f"📁 Database: {db_path}")
    print(f"🕐 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 60)
    
    # Check if database exists
    if not os.path.exists(db_path):
        print(f"❌ Database file {db_path} not found!")
        sys.exit(1)
    
    # Connect to database
    conn = connect_to_database(db_path)
    
    try:
        # Create tables
        if not create_case_management_tables(conn):
            sys.exit(1)
        
        # Populate checklist
        if not populate_alaska_medicaid_checklist(conn):
            sys.exit(1)
        
        # Verify changes
        if not verify_schema_changes(conn):
            sys.exit(1)
        
        print("-" * 60)
        print("🎉 Case management database initialization completed successfully!")
        print("📊 The system now supports:")
        print("   • Medicaid application checklists")
        print("   • Case document tracking")
        print("   • Requirement status management")
        
    finally:
        conn.close()

if __name__ == "__main__":
    main()