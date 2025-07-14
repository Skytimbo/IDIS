"""
Context Store Module for Intelligent Document Insight System (IDIS)

This module serves as the central data persistence layer for the IDIS platform,
managing all SQLite database operations for document intelligence workflows.
"""

import sqlite3
import json
from typing import Dict, List, Optional, Any

class ContextStore:
    """
    Manages persistent storage and retrieval of IDIS data using SQLite.
    """

    def __init__(self, db_path: str):
        """
        Initialize the Context Store.
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._initialize_db()

    def __del__(self):
        """Close the database connection."""
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()

    def _initialize_db(self):
        """
        Create all required tables if they don't exist.
        """
        cursor = self.conn.cursor()

        # This was the legacy table, ensure it's gone.
        cursor.execute("DROP TABLE IF EXISTS patients")

        # Create entities table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY,
                entity_name TEXT NOT NULL,
                creation_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_modified_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create other tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT UNIQUE NOT NULL,
                entity_id INTEGER NOT NULL,
                case_type TEXT DEFAULT 'SOA Medicaid - Adult',
                status TEXT DEFAULT 'Active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (entity_id) REFERENCES entities(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY,
                document_id TEXT, -- For legacy UUIDs
                file_name TEXT NOT NULL,
                original_file_type TEXT,
                original_watchfolder_path TEXT,
                filed_path TEXT,
                ingestion_status TEXT,
                processing_status TEXT,
                entity_id INTEGER,
                session_id INTEGER,
                extracted_data TEXT,
                full_text TEXT,
                document_type TEXT,
                classification_confidence REAL,
                issuer_source TEXT,
                recipient TEXT,
                document_dates TEXT,
                tags_extracted TEXT,
                upload_timestamp TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_modified_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (entity_id) REFERENCES entities (id)
            )
        ''')

        cursor.execute('''
             CREATE TABLE IF NOT EXISTS application_checklists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                checklist_name TEXT NOT NULL,
                required_doc_name TEXT NOT NULL,
                description TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS case_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT NOT NULL,
                entity_id INTEGER NOT NULL,
                checklist_item_id INTEGER NOT NULL,
                document_id INTEGER,
                status TEXT NOT NULL,
                is_override INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (entity_id) REFERENCES entities (id),
                FOREIGN KEY (checklist_item_id) REFERENCES application_checklists (id),
                FOREIGN KEY (document_id) REFERENCES documents (id)
            )
        ''')

        self.conn.commit()

    # --- Entity Methods ---

    def add_entity(self, entity_data: Dict[str, Any]) -> int:
        """Adds a new entity to the database."""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO entities (entity_name) VALUES (?)",
            (entity_data.get('entity_name'),)
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_all_entities(self) -> List[Dict[str, Any]]:
        """Retrieve all entities from the database."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM entities ORDER BY entity_name")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    # --- Document Methods ---

    def add_document(self, doc_data: dict) -> int:
        """Adds a new document to the database."""
        sql = ''' INSERT INTO documents(file_name, original_file_type, ingestion_status, document_type, classification_confidence, processing_status, entity_id, session_id, extracted_data, full_text, document_dates, upload_timestamp)
                  VALUES(?,?,?,?,?,?,?,?,?,?,?,?) '''

        # Ensure extracted_data and document_dates are JSON strings
        extracted_data = doc_data.get('extracted_data')
        if extracted_data and not isinstance(extracted_data, str):
            extracted_data = json.dumps(extracted_data)

        document_dates = doc_data.get('document_dates')
        if document_dates and not isinstance(document_dates, str):
            document_dates = json.dumps(document_dates)

        cur = self.conn.cursor()
        cur.execute(sql, (
            doc_data.get('file_name'),
            doc_data.get('original_file_type'),
            doc_data.get('ingestion_status'),
            doc_data.get('document_type'),
            doc_data.get('classification_confidence'),
            doc_data.get('processing_status'),
            doc_data.get('entity_id'), # Use the correct entity_id key
            doc_data.get('session_id'),
            extracted_data,
            doc_data.get('full_text'),
            document_dates,
            doc_data.get('upload_timestamp')
        ))
        self.conn.commit()
        return cur.lastrowid

    # ... [Other existing methods like get_document, update_document_fields, etc.]
    # (Leaving them out for brevity, but they would be here in the final file)