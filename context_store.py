"""
Context Store Module for Intelligent Document Insight System (IDIS)

This module manages the SQLite database containing all persistent data for IDIS,
including documents, patients, sessions, agent outputs, and audit trails.
"""

import sqlite3
import json
import uuid
import datetime
from typing import Dict, List, Optional, Tuple, Union, Any


class ContextStore:
    """
    Manages persistent storage and retrieval of IDIS data using SQLite.
    
    The ContextStore handles all database operations for the Intelligent Document
    Insight System, providing CRUD operations for patients, sessions, documents,
    agent outputs, and maintaining a comprehensive audit trail of all activities.
    """
    
    def __init__(self, db_path: str):
        """
        Initialize the Context Store with the specified database path.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        # Enable foreign key constraints
        self.conn.execute("PRAGMA foreign_keys = ON")
        # Configure SQLite to return rows as dictionaries
        self.conn.row_factory = sqlite3.Row
        # Initialize database schema if needed
        self._initialize_db()
    
    def __del__(self):
        """Close the database connection when the object is destroyed."""
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()
    
    def _initialize_db(self):
        """
        Create all required tables, indexes, and constraints if they don't exist.
        """
        cursor = self.conn.cursor()
        
        # Create patients table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS patients (
                patient_id TEXT PRIMARY KEY,
                patient_name TEXT,
                creation_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_modified_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create index on patient_name for faster searches
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_patient_name ON patients(patient_name)
        ''')
        
        # Create sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT,
                creation_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                status TEXT,
                session_metadata TEXT
            )
        ''')
        
        # Create indexes for sessions table
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status)
        ''')
        
        # Create documents table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                document_id TEXT PRIMARY KEY,
                patient_id TEXT,
                session_id TEXT,
                file_name TEXT,
                original_file_type TEXT,
                original_watchfolder_path TEXT,
                upload_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                ingestion_status TEXT,
                extracted_text TEXT,
                ocr_confidence_percent REAL,
                document_type TEXT,
                classification_confidence TEXT,
                processing_status TEXT,
                document_dates TEXT,
                issuer_source TEXT,
                recipient TEXT,
                tags_extracted TEXT,
                filed_path TEXT,
                last_modified_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        ''')
        
        # Create indexes for documents table
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_documents_patient_id 
            ON documents(patient_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_documents_session_id 
            ON documents(session_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_documents_document_type 
            ON documents(document_type)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_documents_upload_timestamp 
            ON documents(upload_timestamp)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_documents_processing_status 
            ON documents(processing_status)
        ''')
        
        # Create agent_outputs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agent_outputs (
                output_id TEXT PRIMARY KEY,
                document_id TEXT,
                agent_id TEXT,
                output_type TEXT,
                output_data TEXT,
                confidence REAL,
                creation_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (document_id) REFERENCES documents(document_id)
            )
        ''')
        
        # Create indexes for agent_outputs table
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_agent_outputs_document_id 
            ON agent_outputs(document_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_agent_outputs_agent_id 
            ON agent_outputs(agent_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_agent_outputs_output_type 
            ON agent_outputs(output_type)
        ''')
        
        # Create audit_trail table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_trail (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                user_id TEXT,
                event_type TEXT,
                event_name TEXT,
                resource_type TEXT,
                resource_id TEXT,
                status TEXT,
                details TEXT,
                source_ip_address TEXT DEFAULT 'localhost'
            )
        ''')
        
        # Create indexes for audit_trail table
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_audit_trail_timestamp 
            ON audit_trail(timestamp)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_audit_trail_user_id 
            ON audit_trail(user_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_audit_trail_event_type 
            ON audit_trail(event_type)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_audit_trail_resource_id 
            ON audit_trail(resource_id)
        ''')
        
        self.conn.commit()
    
    # Patient Methods
    
    def add_patient(self, patient_data: Dict[str, Any]) -> str:
        """
        Add a new patient to the database.
        
        Args:
            patient_data: Dictionary containing patient information
                          Required keys: 'patient_name'
        
        Returns:
            str: The newly created patient_id
            
        Raises:
            sqlite3.Error: If there's a database error
        """
        patient_id = str(uuid.uuid4())
        
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                '''
                INSERT INTO patients (patient_id, patient_name)
                VALUES (?, ?)
                ''',
                (patient_id, patient_data.get('patient_name'))
            )
            self.conn.commit()
            return patient_id
        except sqlite3.Error as e:
            self.conn.rollback()
            raise e
    
    def get_patient(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a patient by ID.
        
        Args:
            patient_id: The patient's unique identifier
        
        Returns:
            Optional[Dict]: Patient data as a dictionary, or None if not found
            
        Raises:
            sqlite3.Error: If there's a database error
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT * FROM patients WHERE patient_id = ?", 
                (patient_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return dict(row)
            return None
        except sqlite3.Error as e:
            raise e
    
    def update_patient(self, patient_id: str, update_data: Dict[str, Any]) -> bool:
        """
        Update a patient's information.
        
        Args:
            patient_id: The patient's unique identifier
            update_data: Dictionary with fields to update
        
        Returns:
            bool: True if successful, False if patient not found
            
        Raises:
            sqlite3.Error: If there's a database error
        """
        try:
            cursor = self.conn.cursor()
            
            # Start constructing the SQL query
            sql = "UPDATE patients SET "
            params = []
            
            # Add each field to be updated
            for key, value in update_data.items():
                if key != 'patient_id':  # Prevent updating the primary key
                    sql += f"{key} = ?, "
                    params.append(value)
            
            # Add last_modified_timestamp
            sql += "last_modified_timestamp = CURRENT_TIMESTAMP "
            
            # Add WHERE clause and execute
            sql += "WHERE patient_id = ?"
            params.append(patient_id)
            
            cursor.execute(sql, params)
            self.conn.commit()
            
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            self.conn.rollback()
            raise e
    
    # Session Methods
    
    def create_session(self, user_id: str, session_metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a new session.
        
        Args:
            user_id: ID of the user creating the session
            session_metadata: Optional dictionary of session metadata
        
        Returns:
            str: The newly created session_id
            
        Raises:
            sqlite3.Error: If there's a database error
        """
        session_id = str(uuid.uuid4())
        metadata_json = json.dumps(session_metadata) if session_metadata else None
        
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                '''
                INSERT INTO sessions 
                (session_id, user_id, status, session_metadata)
                VALUES (?, ?, ?, ?)
                ''',
                (session_id, user_id, 'active', metadata_json)
            )
            self.conn.commit()
            return session_id
        except sqlite3.Error as e:
            self.conn.rollback()
            raise e
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a session by ID.
        
        Args:
            session_id: The session's unique identifier
        
        Returns:
            Optional[Dict]: Session data as a dictionary or None if not found
            
        Raises:
            sqlite3.Error: If there's a database error
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT * FROM sessions WHERE session_id = ?",
                (session_id,)
            )
            row = cursor.fetchone()
            
            if row:
                result = dict(row)
                
                # Parse metadata JSON if it exists
                if result.get('session_metadata'):
                    result['session_metadata'] = json.loads(result['session_metadata'])
                
                return result
            return None
        except sqlite3.Error as e:
            raise e
    
    def update_session_status(self, session_id: str, status: str) -> bool:
        """
        Update a session's status.
        
        Args:
            session_id: The session's unique identifier
            status: New status (e.g., 'active', 'completed', 'archived')
        
        Returns:
            bool: True if successful, False if session not found
            
        Raises:
            sqlite3.Error: If there's a database error
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                '''
                UPDATE sessions
                SET status = ?
                WHERE session_id = ?
                ''',
                (status, session_id)
            )
            self.conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            self.conn.rollback()
            raise e
    
    # Document Methods
    
    def add_document(self, document_data: Dict[str, Any]) -> str:
        """
        Add a new document to the database.
        
        Args:
            document_data: Dictionary containing document information
                Required keys: 'file_name', 'original_file_type', 'ingestion_status'
                Optional keys: 'patient_id', 'session_id', 'extracted_text',
                               'document_type', 'classification_confidence',
                               'processing_status', 'document_dates', 'issuer_source',
                               'recipient', 'tags_extracted', 'filed_path'
        
        Returns:
            str: The newly created document_id
            
        Raises:
            sqlite3.Error: If there's a database error
        """
        document_id = str(uuid.uuid4())
        
        # Handle JSON fields
        if 'document_dates' in document_data and document_data['document_dates']:
            document_data['document_dates'] = json.dumps(document_data['document_dates'])
        
        if 'tags_extracted' in document_data and document_data['tags_extracted']:
            document_data['tags_extracted'] = json.dumps(document_data['tags_extracted'])
        
        try:
            cursor = self.conn.cursor()
            
            # Build dynamic query based on provided fields
            fields = ['document_id']
            values = [document_id]
            placeholders = ['?']
            
            for key, value in document_data.items():
                if key not in ['document_id']:  # Skip document_id as we generated it
                    fields.append(key)
                    values.append(value)
                    placeholders.append('?')
            
            query = f'''
                INSERT INTO documents ({', '.join(fields)})
                VALUES ({', '.join(placeholders)})
            '''
            
            cursor.execute(query, values)
            self.conn.commit()
            return document_id
        except sqlite3.Error as e:
            self.conn.rollback()
            raise e
    
    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a document by ID.
        
        Args:
            document_id: The document's unique identifier
        
        Returns:
            Optional[Dict]: Document data as a dictionary or None if not found
            
        Raises:
            sqlite3.Error: If there's a database error
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT * FROM documents WHERE document_id = ?",
                (document_id,)
            )
            row = cursor.fetchone()
            
            if row:
                result = dict(row)
                
                # Parse JSON fields
                if result.get('document_dates'):
                    result['document_dates'] = json.loads(result['document_dates'])
                
                if result.get('tags_extracted'):
                    result['tags_extracted'] = json.loads(result['tags_extracted'])
                
                return result
            return None
        except sqlite3.Error as e:
            raise e
    
    def update_document_fields(self, document_id: str, fields_to_update: Dict[str, Any]) -> bool:
        """
        Update specific fields of a document.
        
        Args:
            document_id: The document's unique identifier
            fields_to_update: Dictionary with fields to update
        
        Returns:
            bool: True if successful, False if document not found
            
        Raises:
            sqlite3.Error: If there's a database error
        """
        # Handle JSON fields
        if 'document_dates' in fields_to_update and fields_to_update['document_dates']:
            fields_to_update['document_dates'] = json.dumps(fields_to_update['document_dates'])
        
        if 'tags_extracted' in fields_to_update and fields_to_update['tags_extracted']:
            fields_to_update['tags_extracted'] = json.dumps(fields_to_update['tags_extracted'])
        
        try:
            cursor = self.conn.cursor()
            
            # Start constructing the SQL query
            sql = "UPDATE documents SET "
            params = []
            
            # Add each field to be updated
            for key, value in fields_to_update.items():
                if key != 'document_id':  # Prevent updating the primary key
                    sql += f"{key} = ?, "
                    params.append(value)
            
            # Add last_modified_timestamp
            sql += "last_modified_timestamp = CURRENT_TIMESTAMP "
            
            # Add WHERE clause and execute
            sql += "WHERE document_id = ?"
            params.append(document_id)
            
            cursor.execute(sql, params)
            self.conn.commit()
            
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            self.conn.rollback()
            raise e
    
    def link_document_to_session(self, document_id: str, session_id: str) -> bool:
        """
        Link an existing document to a session.
        
        Args:
            document_id: The document's unique identifier
            session_id: The session's unique identifier
        
        Returns:
            bool: True if successful, False if document or session not found
            
        Raises:
            sqlite3.Error: If there's a database error
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                '''
                UPDATE documents
                SET session_id = ?, last_modified_timestamp = CURRENT_TIMESTAMP
                WHERE document_id = ?
                ''',
                (session_id, document_id)
            )
            self.conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            self.conn.rollback()
            raise e
    
    def get_documents_for_session(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve all documents associated with a session.
        
        Args:
            session_id: The session's unique identifier
        
        Returns:
            List[Dict]: List of document dictionaries
            
        Raises:
            sqlite3.Error: If there's a database error
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT * FROM documents WHERE session_id = ?",
                (session_id,)
            )
            rows = cursor.fetchall()
            
            result = []
            for row in rows:
                doc = dict(row)
                
                # Parse JSON fields
                if doc.get('document_dates'):
                    doc['document_dates'] = json.loads(doc['document_dates'])
                
                if doc.get('tags_extracted'):
                    doc['tags_extracted'] = json.loads(doc['tags_extracted'])
                
                result.append(doc)
            
            return result
        except sqlite3.Error as e:
            raise e
    
    # Agent Output Methods
    
    def save_agent_output(
        self, 
        document_id: str, 
        agent_id: str, 
        output_type: str, 
        output_data: str, 
        confidence: Optional[float] = None
    ) -> str:
        """
        Save output from an agent processing a document.
        
        Args:
            document_id: The document's unique identifier
            agent_id: Identifier for the agent (e.g., "summarizer_agent_v1.0")
            output_type: Type of output (e.g., "per_document_summary")
            output_data: The output content (text or JSON string)
            confidence: Optional confidence score (0.0 to 1.0)
        
        Returns:
            str: The newly created output_id
            
        Raises:
            sqlite3.Error: If there's a database error
        """
        output_id = str(uuid.uuid4())
        
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                '''
                INSERT INTO agent_outputs
                (output_id, document_id, agent_id, output_type, output_data, confidence)
                VALUES (?, ?, ?, ?, ?, ?)
                ''',
                (output_id, document_id, agent_id, output_type, output_data, confidence)
            )
            self.conn.commit()
            return output_id
        except sqlite3.Error as e:
            self.conn.rollback()
            raise e
    
    def get_agent_outputs_for_document(
        self, 
        document_id: str, 
        agent_id: Optional[str] = None, 
        output_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve agent outputs for a document with optional filtering.
        
        Args:
            document_id: The document's unique identifier
            agent_id: Optional filter for specific agent
            output_type: Optional filter for specific output type
        
        Returns:
            List[Dict]: List of agent output dictionaries
            
        Raises:
            sqlite3.Error: If there's a database error
        """
        try:
            cursor = self.conn.cursor()
            
            # Build the query based on provided filters
            query = "SELECT * FROM agent_outputs WHERE document_id = ?"
            params = [document_id]
            
            if agent_id:
                query += " AND agent_id = ?"
                params.append(agent_id)
            
            if output_type:
                query += " AND output_type = ?"
                params.append(output_type)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            raise e
    
    # Audit Log Methods
    
    def add_audit_log_entry(
        self,
        user_id: str,
        event_type: str,
        event_name: str,
        status: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[str] = None,
        source_ip: str = "localhost"
    ) -> Optional[int]:
        """
        Add an entry to the audit log.
        
        Args:
            user_id: ID of the user performing the action
            event_type: Type of event (e.g., "DATA_ACCESS", "AGENT_ACTIVITY")
            event_name: Specific action (e.g., "VIEW_DOCUMENT_TEXT")
            status: Outcome status (e.g., "SUCCESS", "FAILURE")
            resource_type: Optional type of resource affected (e.g., "document")
            resource_id: Optional ID of the resource affected
            details: Optional human-readable description
            source_ip: Source IP address, defaults to "localhost"
        
        Returns:
            int: The newly created log_id
            
        Raises:
            sqlite3.Error: If there's a database error
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                '''
                INSERT INTO audit_trail
                (user_id, event_type, event_name, status, resource_type, 
                resource_id, details, source_ip_address)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (user_id, event_type, event_name, status, resource_type, 
                resource_id, details, source_ip)
            )
            self.conn.commit()
            if cursor.lastrowid:
                return cursor.lastrowid
            return None
        except sqlite3.Error as e:
            self.conn.rollback()
            raise e
    
    # Query Methods
    
    def get_documents_by_processing_status(self, processing_status: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Retrieve documents that match a specific processing_status.

        Args:
            processing_status: The processing status to filter by (e.g., "new", "ingested", "classified").
            limit: Maximum number of documents to return.

        Returns:
            List[Dict[str, Any]]: A list of document dictionaries.
                                 Each dictionary should contain at least 'document_id' and 'extracted_text'.
                                 Include other relevant fields like 'file_name' for context if easy.
        """
        try:
            cursor = self.conn.cursor()
            # Select essential fields needed by agents for processing
            cursor.execute(
                """
                SELECT document_id, extracted_text, file_name, patient_id, session_id,
                       original_file_type, document_type, classification_confidence
                FROM documents
                WHERE processing_status = ?
                ORDER BY upload_timestamp ASC
                LIMIT ?
                """,
                (processing_status, limit)
            )
            rows = cursor.fetchall()
            
            # Convert rows to dictionaries and handle JSON fields
            results = []
            for row in rows:
                result = dict(row)
                results.append(result)
                
            return results
        except sqlite3.Error as e:
            # Log the error here
            raise e
    
    def query_patient_history(self, patient_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve document history for a patient.
        
        Args:
            patient_id: The patient's unique identifier
        
        Returns:
            List[Dict]: List of document summary dictionaries with fields:
                - document_id
                - file_name
                - document_type
                - processing_status
                - upload_timestamp
            
        Raises:
            sqlite3.Error: If there's a database error
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                '''
                SELECT document_id, file_name, document_type, 
                       processing_status, upload_timestamp
                FROM documents
                WHERE patient_id = ?
                ORDER BY upload_timestamp DESC
                ''',
                (patient_id,)
            )
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            raise e
