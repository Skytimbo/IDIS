import os
import logging
from typing import Type
from pydantic import BaseModel, Field

from langchain.tools import BaseTool

from context_store import ContextStore
from ingestion_agent import IngestionAgent

# Assume a default database path for now
DB_PATH = "production_idis.db"

class IngestionInput(BaseModel):
    """Input schema for the IngestionTool."""
    file_path: str = Field(description="The absolute path to the file to be ingested.")

class IngestionTool(BaseTool):
    """A tool to ingest a single document, extract its text, and create a database record."""
    name = "ingest_document"
    description = "Useful for when you need to process a new document. Takes a file_path as input, extracts its text, and saves it to the database, returning the new document's ID."
    args_schema: Type[BaseModel] = IngestionInput

    def _run(self, file_path: str) -> str:
        """Use the tool."""
        if not os.path.exists(file_path):
            return f"Error: File not found at {file_path}"

        try:
            # Initialize agents locally
            context_store = ContextStore(db_path=DB_PATH)
            # Create temporary directories for the ingestion agent
            import tempfile
            temp_watch = tempfile.mkdtemp()
            temp_holding = tempfile.mkdtemp()
            ingestion_agent = IngestionAgent(context_store=context_store, 
                                           watch_folder=temp_watch, 
                                           holding_folder=temp_holding)
            
            # 1. Extract text based on file extension
            text = None
            confidence = 0.0
            file_ext = os.path.splitext(file_path)[1].lower()

            if file_ext == '.pdf':
                text, confidence = ingestion_agent._extract_text_from_pdf(file_path)
            elif file_ext in ['.jpg', '.jpeg', '.png', '.tiff', '.bmp']:
                text, confidence = ingestion_agent._extract_text_from_image(file_path)
            elif file_ext in ['.docx', '.doc']:
                text, confidence = ingestion_agent._extract_text_from_docx(file_path)
            elif file_ext == '.txt':
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                    confidence = 100.0
            
            if not text:
                return f"Error: Failed to extract text from {file_path}"

            # 2. Correctly create a record in the database in two steps
            initial_doc_data = {
                'file_name': os.path.basename(file_path),
                'original_file_type': os.path.splitext(file_path)[1],
                'ingestion_status': 'pending_ingestion', # Start as pending
            }
            new_doc_id = context_store.add_document(initial_doc_data)

            if not new_doc_id:
                return "Error: Failed to create initial document record."

            # Now, update the record with the extracted text
            update_data = {
                'full_text': text,
                'ingestion_status': 'ingestion_successful',
                'processing_status': 'ingested'
            }
            update_success = context_store.update_document_fields(new_doc_id, update_data)

            if update_success:
                logging.info(f"Successfully ingested '{file_path}' with document ID {new_doc_id}.")
                return f"Successfully ingested document. New document ID is {new_doc_id}."
            else:
                return f"Error: Failed to update document {new_doc_id} with extracted text."

        except Exception as e:
            logging.error(f"An error occurred during ingestion tool run: {e}")
            return f"An error occurred: {e}"

    def _arun(self, file_path: str):
        # This tool does not support async run yet.
        raise NotImplementedError("IngestionTool does not support async")