#!/usr/bin/env python3
"""
Migration Script: Consolidate patients table into entities table
Purpose: Complete the Patient-to-Entity refactor by migrating all data
         from the legacy patients table to the new entities table
"""

import sqlite3
import sys
from datetime import datetime

def migrate_patients_to_entities(db_path: str = "production_idis.db"):
    """
    Migrate all data from patients table to entities table, then drop patients table.
    
    Args:
        db_path: Path to the SQLite database file
    """
    print(f"Starting migration from patients to entities table...")
    print(f"Database: {db_path}")
    
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        cursor = conn.cursor()
        
        # Step 1: Check if both tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('patients', 'entities')")
        existing_tables = [row['name'] for row in cursor.fetchall()]
        
        if 'patients' not in existing_tables:
            print("✓ No patients table found - migration not needed")
            return
            
        if 'entities' not in existing_tables:
            print("✗ Error: entities table does not exist")
            return
        
        # Step 2: Get data from patients table
        cursor.execute("SELECT * FROM patients")
        patient_records = cursor.fetchall()
        
        if not patient_records:
            print("✓ No patient records to migrate")
        else:
            print(f"Found {len(patient_records)} patient records to migrate")
            
            # Step 3: Check for duplicates in entities table
            for patient in patient_records:
                cursor.execute("SELECT id FROM entities WHERE entity_name = ?", (patient['patient_name'],))
                existing_entity = cursor.fetchone()
                
                if existing_entity:
                    print(f"  - Skipping duplicate: {patient['patient_name']} (already exists as entity ID {existing_entity['id']})")
                else:
                    # Insert into entities table
                    cursor.execute("""
                        INSERT INTO entities (entity_name, creation_timestamp, last_modified_timestamp)
                        VALUES (?, ?, ?)
                    """, (
                        patient['patient_name'],
                        patient.get('creation_timestamp', datetime.now().isoformat()),
                        patient.get('last_modified_timestamp', datetime.now().isoformat())
                    ))
                    new_entity_id = cursor.lastrowid
                    print(f"  ✓ Migrated: {patient['patient_name']} -> Entity ID {new_entity_id}")
        
        # Step 4: Check for foreign key constraints
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        all_tables = [row['name'] for row in cursor.fetchall()]
        
        # Check documents table - it should have entity_id, not patient_id
        if 'documents' in all_tables:
            cursor.execute("PRAGMA table_info(documents)")
            doc_columns = [col[1] for col in cursor.fetchall()]
            if 'entity_id' in doc_columns:
                cursor.execute("SELECT COUNT(*) as count FROM documents WHERE entity_id IS NOT NULL")
                doc_count = cursor.fetchone()['count']
                print(f"Found {doc_count} documents with entity_id references (this is correct)")
            elif 'patient_id' in doc_columns:
                cursor.execute("SELECT COUNT(*) as count FROM documents WHERE patient_id IS NOT NULL")
                doc_count = cursor.fetchone()['count']
                print(f"Warning: Found {doc_count} documents with patient_id references")
                print("These references will become invalid after dropping patients table")
            else:
                print("No patient_id or entity_id column found in documents table")
        
        # Step 5: Drop the patients table
        print("Dropping patients table...")
        cursor.execute("DROP TABLE IF EXISTS patients")
        
        # Commit all changes
        conn.commit()
        
        print("✓ Migration completed successfully!")
        print("✓ Patients table has been removed")
        
        # Step 6: Verify final state
        cursor.execute("SELECT COUNT(*) as count FROM entities")
        entity_count = cursor.fetchone()['count']
        print(f"✓ Final entity count: {entity_count}")
        
        # Verify patients table is gone
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='patients'")
        if cursor.fetchone():
            print("✗ Error: patients table still exists!")
        else:
            print("✓ Confirmed: patients table successfully removed")
            
    except sqlite3.Error as e:
        print(f"✗ Database error: {e}")
        conn.rollback()
        sys.exit(1)
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "production_idis.db"
    migrate_patients_to_entities(db_path)