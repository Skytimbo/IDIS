#!/usr/bin/env python3
"""
Database Migration Script: Patient to Entity Refactor
This script migrates the database schema from patient-specific terms to generic entity terms.
"""

import sqlite3
import os
import sys
from typing import Optional

def backup_database(db_path: str) -> str:
    """Create a backup of the database before migration."""
    backup_path = f"{db_path}.backup"
    
    # Create backup by copying the database file
    import shutil
    shutil.copy2(db_path, backup_path)
    print(f"✓ Database backed up to: {backup_path}")
    return backup_path

def migrate_database(db_path: str) -> bool:
    """
    Perform the complete patient-to-entity migration.
    
    Returns:
        bool: True if migration successful, False otherwise
    """
    print(f"Starting migration of database: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Enable foreign key constraints
        cursor.execute("PRAGMA foreign_keys = OFF")
        
        print("Step 1: Renaming 'patients' table to 'entities'...")
        cursor.execute("ALTER TABLE patients RENAME TO entities")
        
        print("Step 2: Renaming 'patient_name' column to 'entity_name'...")
        cursor.execute("ALTER TABLE entities RENAME COLUMN patient_name TO entity_name")
        
        print("Step 3: Updating 'documents' table - renaming 'patient_id' to 'entity_id'...")
        cursor.execute("ALTER TABLE documents RENAME COLUMN patient_id TO entity_id")
        
        print("Step 4: Updating 'case_documents' table - renaming 'patient_id' to 'entity_id'...")
        cursor.execute("ALTER TABLE case_documents RENAME COLUMN patient_id TO entity_id")
        
        print("Step 5: Updating foreign key constraints...")
        # Note: SQLite doesn't allow direct modification of foreign key constraints,
        # but since we're renaming the referenced table and columns consistently,
        # the relationships should remain intact.
        
        print("Step 6: Recreating indexes with new names...")
        
        # Drop old indexes
        cursor.execute("DROP INDEX IF EXISTS idx_patient_name")
        cursor.execute("DROP INDEX IF EXISTS idx_documents_patient_id")
        
        # Create new indexes with entity naming
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entity_name ON entities(entity_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_entity_id ON documents(entity_id)")
        
        # Re-enable foreign key constraints
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # Verify the migration
        print("Step 7: Verifying migration...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='entities'")
        if not cursor.fetchone():
            raise Exception("Migration failed: 'entities' table not found")
            
        cursor.execute("PRAGMA table_info(entities)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'entity_name' not in columns:
            raise Exception("Migration failed: 'entity_name' column not found")
            
        cursor.execute("PRAGMA table_info(documents)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'entity_id' not in columns:
            raise Exception("Migration failed: 'entity_id' column not found in documents")
            
        cursor.execute("PRAGMA table_info(case_documents)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'entity_id' not in columns:
            raise Exception("Migration failed: 'entity_id' column not found in case_documents")
        
        conn.commit()
        conn.close()
        
        print("✓ Database migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        conn.rollback()
        conn.close()
        return False

def main():
    """Main migration function."""
    db_path = "production_idis.db"
    
    if not os.path.exists(db_path):
        print(f"✗ Database file not found: {db_path}")
        sys.exit(1)
    
    print("=" * 60)
    print("IDIS DATABASE MIGRATION: PATIENT → ENTITY")
    print("=" * 60)
    
    # Create backup
    backup_path = backup_database(db_path)
    
    # Perform migration
    if migrate_database(db_path):
        print("\n✓ Migration completed successfully!")
        print(f"✓ Backup available at: {backup_path}")
        print("\nThe following changes were made:")
        print("  • 'patients' table → 'entities' table")
        print("  • 'patient_name' column → 'entity_name' column")
        print("  • 'patient_id' foreign keys → 'entity_id' foreign keys")
        print("  • Updated indexes to use entity naming")
    else:
        print("\n✗ Migration failed!")
        print(f"Database backup is available at: {backup_path}")
        sys.exit(1)

if __name__ == "__main__":
    main()