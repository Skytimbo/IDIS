#!/usr/bin/env python3
"""
Check if the new document was added to the database
"""

from context_store import ContextStore
import json

def check_new_document():
    """Check the new document that was just added"""
    
    store = ContextStore("production_idis.db")
    
    # Query all documents to see what we have
    cursor = store.conn.execute("""
        SELECT ROWID, file_name, document_type, issuer_source, tags_extracted, 
               full_text, extracted_data, filed_path, processing_status
        FROM documents 
        ORDER BY ROWID DESC 
        LIMIT 5
    """)
    
    docs = cursor.fetchall()
    if docs:
        print(f"Found {len(docs)} documents in database:")
        for i, doc in enumerate(docs):
            print(f"\nDocument {i+1}:")
            print(f"  ROWID: {doc[0]}")
            print(f"  File: {doc[1]}")
            print(f"  Type: {doc[2]}")
            print(f"  Issuer: {doc[3]}")
            print(f"  Tags: {doc[4]}")
            print(f"  Full text: {doc[5][:50]}..." if doc[5] else "No full text")
            print(f"  Has extracted_data: {'Yes' if doc[6] else 'No'}")
            print(f"  Filed path: {doc[7]}")
            print(f"  Status: {doc[8]}")
            
            # Show extracted data structure for the first document
            if i == 0 and doc[6]:
                try:
                    extracted_data = json.loads(doc[6])
                    print(f"\nExtracted data structure:")
                    print(f"  Document type: {extracted_data.get('document_type', {}).get('predicted_class')}")
                    print(f"  Issuer name: {extracted_data.get('issuer', {}).get('name')}")
                    print(f"  Primary date: {extracted_data.get('key_dates', {}).get('primary_date')}")
                    print(f"  Total amount: {extracted_data.get('financials', {}).get('total_amount')}")
                    print(f"  Summary: {extracted_data.get('content', {}).get('summary')}")
                except json.JSONDecodeError as e:
                    print(f"  Could not parse extracted_data JSON: {e}")
                except Exception as e:
                    print(f"  Error parsing extracted_data: {e}")
    else:
        print("No documents found in database")
    
    store.conn.close()

if __name__ == "__main__":
    check_new_document()