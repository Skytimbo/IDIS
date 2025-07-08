"""
Context Store Module for Intelligent Document Insight System (IDIS)

This module serves as the central data persistence layer for the IDIS platform,
managing all SQLite database operations for document intelligence workflows.

Key Responsibilities:
- Document lifecycle management (ingestion, processing, archiving)
- Patient and session data management with privacy controls
- Agent output storage for AI-powered document analysis results
- Comprehensive audit logging for compliance and debugging
- Hybrid V1.3 schema supporting both legacy UI and modern JSON structures

The ContextStore class provides thread-safe CRUD operations and maintains
data integrity across the entire document processing pipeline, from initial
file upload through AI analysis to final archiving and retrieval.

CodeRabbit Integration Test: This comment was added to verify automated 
code review functionality is working correctly with GitHub integration.
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
                id INTEGER PRIMARY KEY,
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
                id INTEGER PRIMARY KEY,
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
        
        # Create documents table with comprehensive schema
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY,
                document_id TEXT, -- For UUIDs
                file_name TEXT NOT NULL,
                original_file_type TEXT,
                original_watchfolder_path TEXT,
                filed_path TEXT, -- The final path in the archive
                ingestion_status TEXT,
                processing_status TEXT,
                patient_id INTEGER,
                session_id INTEGER,
                extracted_data TEXT, -- Full JSON object from cognitive agent
                full_text TEXT, -- Primary text storage
                document_type TEXT,
                classification_confidence REAL,
                issuer_source TEXT, -- The document issuer
                recipient TEXT,
                document_dates TEXT, -- JSON of extracted dates
                tags_extracted TEXT, -- JSON of extracted tags
                upload_timestamp TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_modified_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES patients (id),
                FOREIGN KEY (session_id) REFERENCES sessions (id)
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
            CREATE INDEX IF NOT EXISTS idx_documents_processing_status 
            ON documents(processing_status)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_documents_created_at 
            ON documents(created_at)
        ''')
        
        # Create agent_outputs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agent_outputs (
                output_id INTEGER PRIMARY KEY,
                document_id INTEGER,
                agent_id TEXT,
                output_type TEXT,
                output_data TEXT,
                confidence REAL,
                creation_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (document_id) REFERENCES documents(id)
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
    
    def add_patient(self, patient_data: Dict[str, Any]) -> int:
        """
        Add a new patient to the database.
        
        Args:
            patient_data: Dictionary containing patient information
                          Required keys: 'patient_name'
        
        Returns:
            int: The newly created patient ID
            
        Raises:
            sqlite3.Error: If there's a database error
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                '''
                INSERT INTO patients (patient_name)
                VALUES (?)
                ''',
                (patient_data.get('patient_name'),)
            )
            self.conn.commit()
            if cursor.lastrowid is None:
                raise sqlite3.Error("Failed to get patient ID after insert")
            return cursor.lastrowid
        except sqlite3.Error as e:
            self.conn.rollback()
            raise e
    
    def get_patient(self, patient_id: int) -> Optional[Dict[str, Any]]:
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
                "SELECT * FROM patients WHERE id = ?", 
                (patient_id,)
            )
            row = cursor.fetchone()
            
            if row:
                result = dict(row)
                # Add patient_id field for backward compatibility
                result['patient_id'] = result['id']
                return result
            return None
        except sqlite3.Error as e:
            raise e
    
    def update_patient(self, patient_id: int, update_data: Dict[str, Any]) -> bool:
        """
        Update a patient's information safely.
        """
        allowed_keys = {'patient_name'} # Whitelist of columns that can be updated
        
        # Filter out any keys that are not allowed
        valid_update_data = {k: v for k, v in update_data.items() if k in allowed_keys}

        if not valid_update_data:
            # No valid fields to update
            return False

        # Build the SET part of the query
        set_clause = ", ".join([f"{key} = ?" for key in valid_update_data.keys()])
        params = list(valid_update_data.values())
        
        sql = f"UPDATE patients SET {set_clause}, last_modified_timestamp = CURRENT_TIMESTAMP WHERE id = ?"
        params.append(patient_id)
        
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, tuple(params))
            self.conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            self.conn.rollback()
            raise e
    
    # Session Methods
    
    def create_session(self, user_id: str, session_metadata: Optional[Dict[str, Any]] = None) -> int:
        """
        Create a new session.
        
        Args:
            user_id: ID of the user creating the session
            session_metadata: Optional dictionary of session metadata
        
        Returns:
            int: The newly created session ID
            
        Raises:
            sqlite3.Error: If there's a database error
        """
        metadata_json = json.dumps(session_metadata) if session_metadata else None
        
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                '''
                INSERT INTO sessions 
                (user_id, status, session_metadata)
                VALUES (?, ?, ?)
                ''',
                (user_id, 'active', metadata_json)
            )
            self.conn.commit()
            if cursor.lastrowid is None:
                raise sqlite3.Error("Failed to get session ID after insert")
            return cursor.lastrowid
        except sqlite3.Error as e:
            self.conn.rollback()
            raise e
    
    def get_session(self, session_id: int) -> Optional[Dict[str, Any]]:
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
                "SELECT * FROM sessions WHERE id = ?",
                (session_id,)
            )
            row = cursor.fetchone()
            
            if row:
                result = dict(row)
                # Add session_id field for backward compatibility
                result['session_id'] = result['id']
                
                # Parse metadata JSON if it exists
                if result.get('session_metadata'):
                    try:
                        result['session_metadata'] = json.loads(result['session_metadata'])
                    except (json.JSONDecodeError, TypeError):
                        result['session_metadata'] = None
                
                return result
            return None
        except sqlite3.Error as e:
            raise e
    
    def update_session_status(self, session_id: int, status: str) -> bool:
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
                WHERE id = ?
                ''',
                (status, session_id)
            )
            self.conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            self.conn.rollback()
            raise e
            
    def update_session_metadata(self, session_id: int, metadata_update: Dict[str, Any]) -> bool:
        """
        Updates the JSON metadata for a given session.
        Fetches existing metadata, updates it with new key-value pairs, and saves it back.

        Args:
            session_id: The ID of the session to update.
            metadata_update: A dictionary containing the key-value pairs to add or update.

        Returns:
            bool: True if successful, False otherwise.
            
        Raises:
            sqlite3.Error: If there's a database error
            json.JSONDecodeError: If there's an error parsing JSON
        """
        try:
            session_data = self.get_session(session_id)
            if not session_data:
                return False  # Session not found

            current_metadata = session_data.get('session_metadata')
            if current_metadata is None:  # It might be None if not parsed by get_session, or if initially null
                current_metadata = {}
            elif isinstance(current_metadata, str):  # If get_session returned raw JSON string
                current_metadata = json.loads(current_metadata)
            
            current_metadata.update(metadata_update)
            
            cursor = self.conn.cursor()
            cursor.execute(
                '''
                UPDATE sessions
                SET session_metadata = ?
                WHERE id = ?
                ''',
                (json.dumps(current_metadata), session_id)
            )
            self.conn.commit()
            return cursor.rowcount > 0
        except (sqlite3.Error, json.JSONDecodeError) as e:
            self.conn.rollback()
            raise e
    
    # Document Methods
    
    def add_document(self, doc_data: dict) -> int:
        """
        Adds a new document to the database. Expects a dictionary containing
        the file_name and the full extracted_data JSON object.
        """
        sql = ''' INSERT INTO documents(file_name, original_file_type, ingestion_status, document_type, classification_confidence, processing_status, patient_id, session_id, extracted_data, full_text, document_dates)
                  VALUES(?,?,?,?,?,?,?,?,?,?,?) '''
        
        # Handle extracted_data field - create JSON structure if needed
        extracted_data = doc_data.get('extracted_data')
        if not extracted_data and (doc_data.get('tags_extracted') or doc_data.get('document_dates')):
            # Create extracted_data from legacy fields
            extracted_data_obj = {}
            if doc_data.get('tags_extracted'):
                extracted_data_obj['tags'] = doc_data['tags_extracted']
            if doc_data.get('document_dates'):
                extracted_data_obj.update(doc_data['document_dates'])
            extracted_data = json.dumps(extracted_data_obj) if extracted_data_obj else None
        elif extracted_data and not isinstance(extracted_data, str):
            # Convert dict to JSON string
            extracted_data = json.dumps(extracted_data)
        
        # Handle document_dates field
        document_dates = doc_data.get('document_dates')
        if document_dates and not isinstance(document_dates, str):
            document_dates = json.dumps(document_dates)
        
        try:
            cur = self.conn.cursor()
            cur.execute(sql, (
                doc_data.get('file_name'),
                doc_data.get('original_file_type'),
                doc_data.get('ingestion_status'),
                doc_data.get('document_type'),
                doc_data.get('classification_confidence'),
                doc_data.get('processing_status'),
                doc_data.get('patient_id'),
                doc_data.get('session_id'),
                extracted_data,
                doc_data.get('extracted_text') or doc_data.get('full_text'),  # Support both field names
                document_dates
            ))
            self.conn.commit()
            if cur.lastrowid is None:
                raise sqlite3.Error("Failed to get document ID after insert")
            return cur.lastrowid
        except Exception as e:
            print(f"Database error in add_document: {e}")
            raise e
    
    def get_document(self, document_id: int) -> Optional[Dict[str, Any]]:
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
                "SELECT * FROM documents WHERE id = ?",
                (document_id,)
            )
            row = cursor.fetchone()
            
            if row:
                result = dict(row)
                # Add document_id field for backward compatibility
                result['document_id'] = result['id']
                
                # Parse JSON fields
                if result.get('document_dates'):
                    try:
                        result['document_dates'] = json.loads(result['document_dates'])
                    except (json.JSONDecodeError, TypeError):
                        result['document_dates'] = None
                
                # Add extracted_text field for backward compatibility (maps to full_text)
                result['extracted_text'] = result.get('full_text')
                
                # Add tags_extracted field for backward compatibility
                if result.get('extracted_data'):
                    try:
                        extracted_data = json.loads(result['extracted_data'])
                        result['tags_extracted'] = extracted_data.get('tags', [])
                    except (json.JSONDecodeError, TypeError):
                        result['tags_extracted'] = []
                else:
                    result['tags_extracted'] = []
                
                return result
            return None
        except sqlite3.Error as e:
            raise e
    
    def update_document_fields(self, document_id: int, fields_to_update: Dict[str, Any]) -> bool:
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
        # Security whitelist: Only allow updates to these specific columns
        allowed_keys = {
            'file_name', 'original_file_type', 'original_watchfolder_path',
            'ingestion_status', 'processing_status', 'patient_id', 'session_id',
            'extracted_data', 'full_text', 'document_type', 'classification_confidence',
            'document_dates', 'associated_entity', 'upload_timestamp'
        }
        
        # Filter out any keys that are not allowed
        valid_update_data = {k: v for k, v in fields_to_update.items() if k in allowed_keys}

        if not valid_update_data:
            # No valid fields to update
            return False

        # Handle JSON fields
        if 'document_dates' in valid_update_data and valid_update_data['document_dates']:
            valid_update_data['document_dates'] = json.dumps(valid_update_data['document_dates'])
        
        # Handle tags_extracted field - store in extracted_data JSON for V1.3 schema compatibility
        if 'tags_extracted' in fields_to_update:
            tags = fields_to_update['tags_extracted']
            
            # Get existing extracted_data or create new
            existing_data = {}
            if 'extracted_data' in valid_update_data:
                try:
                    existing_data = json.loads(valid_update_data['extracted_data'])
                except (json.JSONDecodeError, TypeError):
                    existing_data = {}
            else:
                # Get from database if not in update
                try:
                    cursor = self.conn.cursor()
                    cursor.execute("SELECT extracted_data FROM documents WHERE id = ?", (document_id,))
                    row = cursor.fetchone()
                    if row and row['extracted_data']:
                        existing_data = json.loads(row['extracted_data'])
                except (sqlite3.Error, json.JSONDecodeError, TypeError):
                    existing_data = {}
            
            # Update tags in extracted_data (completely replace, not merge)
            existing_data['tags'] = tags if isinstance(tags, list) else []
            valid_update_data['extracted_data'] = json.dumps(existing_data)

        # Build the SET part of the query
        set_clause = ", ".join([f"{key} = ?" for key in valid_update_data.keys()])
        params = list(valid_update_data.values())
        
        sql = f"UPDATE documents SET {set_clause}, last_modified_timestamp = CURRENT_TIMESTAMP WHERE id = ?"
        params.append(document_id)
        
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, tuple(params))
            self.conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            self.conn.rollback()
            raise e
    
    def link_document_to_session(self, document_id: int, session_id: int) -> bool:
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
                WHERE id = ?
                ''',
                (session_id, document_id)
            )
            self.conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            self.conn.rollback()
            raise e
    
    def get_documents_for_session(self, session_id: int) -> List[Dict[str, Any]]:
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
                # Add document_id field for backward compatibility
                doc['document_id'] = doc['id']
                
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
        document_id: int, 
        agent_id: str, 
        output_type: str, 
        output_data: str, 
        confidence: Optional[float] = None
    ) -> int:
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
                (document_id, agent_id, output_type, output_data, confidence)
                VALUES (?, ?, ?, ?, ?)
                ''',
                (document_id, agent_id, output_type, output_data, confidence)
            )
            self.conn.commit()
            if cursor.lastrowid is None:
                raise sqlite3.Error("Failed to get agent output ID after insert")
            return cursor.lastrowid
        except sqlite3.Error as e:
            self.conn.rollback()
            raise e
    
    def get_agent_outputs_for_document(
        self, 
        document_id: int, 
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
            params: List[Union[int, str]] = [document_id]
            
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
                SELECT id as document_id, file_name, patient_id, session_id,
                       original_file_type, document_type, classification_confidence, original_watchfolder_path,
                       full_text
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
                # Add extracted_text field for backward compatibility (maps to full_text)
                result['extracted_text'] = result.get('full_text')
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
                SELECT id as document_id, file_name, document_type, 
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
    def update_document_categorization(self, document_id: int, entity_json: str) -> bool:
        """
        Updates a document's associated entity and sets its status to complete.
        This is called by the UI after the user review (HITL) step.

        Args:
            document_id: The ID of the document to update.
            entity_json: A JSON string representing the associated_entity object.

        Returns:
            True if the update was successful, False otherwise.
        """
        sql = ''' UPDATE documents
                  SET associated_entity = ?,
                      processing_status = ?
                  WHERE id = ? '''
        
        try:
            cur = self.conn.cursor()
            cur.execute(sql, (entity_json, 'processing_complete', document_id))
            self.conn.commit()
            
            # Check if the update was successful
            if cur.rowcount == 0:
                print(f"Warning: No document found with ID {document_id} to update.")
                return False
                
            print(f"Successfully categorized document ID: {document_id}")
            return True
        except Exception as e:
            print(f"Database error in update_document_categorization: {e}")
            return False