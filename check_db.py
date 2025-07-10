#!/usr/bin/env python3
from context_store import ContextStore
import os

# Check database for documents with filed_path
db_path = "production_idis.db"
store = ContextStore(db_path)

# Query documents with filed_path
cursor = store.conn.execute("""
    SELECT document_id, file_name, filed_path 
    FROM documents 
    WHERE filed_path IS NOT NULL AND filed_path != ''
    LIMIT 10
""")

docs = cursor.fetchall()
print(f"Found {len(docs)} documents with filed_path:")
for doc in docs:
    print(f"  ID: {doc[0]}, File: {doc[1]}, Path: {doc[2]}")
    if doc[2] and os.path.exists(doc[2]):
        print(f"    ✓ File exists")
    else:
        print(f"    ✗ File missing")

# Check all documents to understand the structure
cursor = store.conn.execute("SELECT document_id, file_name, filed_path FROM documents LIMIT 5")
all_docs = cursor.fetchall()
print(f"\nFirst 5 documents in database:")
for doc in all_docs:
    print(f"  ID: {doc[0]}, File: {doc[1]}, Path: {doc[2]}")
    
store.conn.close()