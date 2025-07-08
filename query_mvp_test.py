#!/usr/bin/env python3
"""Query the database for the MVP test payslip document."""

import sqlite3
import json

def query_mvp_payslip():
    """Query the database for the mvp_payslip.txt document and display results."""
    
    try:
        # Connect to the production database
        conn = sqlite3.connect('production_idis.db')
        conn.row_factory = sqlite3.Row  # This enables column access by name
        cursor = conn.cursor()
        
        # Query for the mvp_payslip.txt document
        query = """
        SELECT 
            id,
            file_name,
            processing_status,
            document_type,
            issuer_source,
            recipient,
            document_dates,
            tags_extracted,
            filed_path,
            full_text,
            extracted_data,
            upload_timestamp,
            last_modified_timestamp
        FROM documents 
        WHERE file_name = 'mvp_payslip.txt'
        ORDER BY id DESC 
        LIMIT 1
        """
        
        cursor.execute(query)
        row = cursor.fetchone()
        
        if row:
            print("=" * 80)
            print("MVP TEST RESULTS - mvp_payslip.txt")
            print("=" * 80)
            print(f"Document ID: {row['id']}")
            print(f"File Name: {row['file_name']}")
            print(f"Processing Status: {row['processing_status']}")
            print(f"Document Type: {row['document_type']}")
            print(f"Issuer Source: {row['issuer_source']}")
            print(f"Recipient: {row['recipient']}")
            print(f"Document Dates: {row['document_dates']}")
            print(f"Tags Extracted: {row['tags_extracted']}")
            print(f"Filed Path: {row['filed_path']}")
            print(f"Upload Timestamp: {row['upload_timestamp']}")
            print(f"Last Modified: {row['last_modified_timestamp']}")
            print()
            
            # Display extracted text (truncated)
            full_text = row['full_text'] or ''
            print("EXTRACTED TEXT:")
            print("-" * 40)
            if len(full_text) > 300:
                print(full_text[:300] + "... [truncated]")
            else:
                print(full_text)
            print()
            
            # Display extracted data JSON
            extracted_data = row['extracted_data']
            if extracted_data:
                print("EXTRACTED DATA (JSON):")
                print("-" * 40)
                try:
                    data = json.loads(extracted_data)
                    print(json.dumps(data, indent=2))
                except json.JSONDecodeError:
                    print(f"Raw data: {extracted_data}")
            else:
                print("EXTRACTED DATA: None")
            
        else:
            print("No document found with filename 'mvp_payslip.txt'")
        
        # Check database schema and get agent outputs
        if row:
            print("\n" + "=" * 80)
            print("DATABASE SCHEMA & AGENT OUTPUTS")
            print("=" * 80)
            
            # First, let's see what tables exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            print("Available tables:")
            for table in tables:
                print(f"  - {table['name']}")
            
            # Try to get agent outputs from the correct table
            try:
                # First check the schema of agent_outputs table
                cursor.execute("PRAGMA table_info(agent_outputs)")
                columns = cursor.fetchall()
                print("\nAgent_outputs table columns:")
                for col in columns:
                    print(f"  - {col[1]} ({col[2]})")
                
                # Query with correct column names (using creation_timestamp)
                output_query = """
                SELECT agent_id, output_type, output_data, confidence, creation_timestamp
                FROM agent_outputs 
                WHERE document_id = ?
                ORDER BY creation_timestamp ASC
                """
                
                cursor.execute(output_query, (row['id'],))
                outputs = cursor.fetchall()
                
                print(f"\nAgent outputs for document {row['id']}:")
                if outputs:
                    for output in outputs:
                        print(f"\nAgent: {output['agent_id']}")
                        print(f"Type: {output['output_type']}")
                        print(f"Confidence: {output['confidence']}")
                        print(f"Timestamp: {output['creation_timestamp']}")
                        print("Output:")
                        print("-" * 20)
                        output_data = output['output_data']
                        if len(output_data) > 200:
                            print(output_data[:200] + "... [truncated]")
                        else:
                            print(output_data)
                else:
                    print("No agent outputs found for this document.")
                    
            except Exception as e:
                print(f"Could not query agent_outputs table: {e}")
                # Try alternative table name
                try:
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%output%'")
                    output_tables = cursor.fetchall()
                    print(f"Tables containing 'output': {[t['name'] for t in output_tables]}")
                except:
                    pass
        
        conn.close()
        
    except Exception as e:
        print(f"Error querying database: {e}")

if __name__ == "__main__":
    query_mvp_payslip()