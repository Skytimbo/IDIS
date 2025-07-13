#!/usr/bin/env python3
"""
Script to set up test users and entities for multi-user testing
"""

import sqlite3
import datetime

def setup_test_users():
    """Set up test users and entities"""
    conn = sqlite3.connect('production_idis.db')
    cursor = conn.cursor()
    
    # Create different entities for different users
    test_entities = [
        # User A entities
        ("Alice Johnson", "user_a"),
        ("Bob Wilson", "user_a"),
        ("Charlie Brown", "user_a"),
        
        # User B entities
        ("Diana Prince", "user_b"),
        ("Edward Smith", "user_b"),
        ("Fiona Davis", "user_b"),
    ]
    
    print("Setting up test entities for multi-user testing...")
    
    for entity_name, user_id in test_entities:
        # Check if entity already exists
        cursor.execute("SELECT id FROM entities WHERE entity_name = ? AND user_id = ?", (entity_name, user_id))
        if cursor.fetchone():
            print(f"  - Entity '{entity_name}' for {user_id} already exists")
            continue
        
        # Insert new entity
        cursor.execute("""
            INSERT INTO entities (entity_name, user_id, creation_timestamp, last_modified_timestamp)
            VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (entity_name, user_id))
        
        print(f"  + Created entity '{entity_name}' for {user_id}")
    
    # Update existing entities to have better user distribution
    print("\nUpdating existing entities for better test distribution...")
    
    # Assign some existing entities to user_b
    cursor.execute("UPDATE entities SET user_id = 'user_b' WHERE id IN (4, 5)")
    cursor.execute("UPDATE case_documents SET user_id = 'user_b' WHERE entity_id IN (4, 5)")
    
    conn.commit()
    
    # Show final user distribution
    print("\nFinal entity distribution:")
    cursor.execute("SELECT user_id, COUNT(*) FROM entities GROUP BY user_id")
    for user_id, count in cursor.fetchall():
        print(f"  {user_id}: {count} entities")
    
    print("\nEntities per user:")
    cursor.execute("SELECT user_id, entity_name FROM entities ORDER BY user_id, entity_name")
    current_user = None
    for user_id, entity_name in cursor.fetchall():
        if user_id != current_user:
            print(f"\n{user_id}:")
            current_user = user_id
        print(f"  - {entity_name}")
    
    conn.close()

if __name__ == "__main__":
    setup_test_users()