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
    context_store: ContextStore = Field(default_factory=lambda: ContextStore(db_path=DB_PATH))
    ingestion_agent: IngestionAgent = Field(default_factory=lambda: IngestionAgent(context_store=ContextStore(db_path=DB_PATH)))

    def _run(self, file_path: str) -> str:
        """Use the tool."""
        if not os.path.exists(file_path):
            return f"Error: File not found at {file_path}"

        try:
            # 1. Extract text using logic from the old agent
            text, confidence = self.ingestion_agent._extract_text_from_file(file_path)
            if not text:
                return f"Error: Failed to extract text from {file_path}"

            # 2. Create a record in the database
            document_data = {
                'file_name': os.path.basename(file_path),
                'full_text': text,
                'ingestion_status': 'ingestion_successful',
                'processing_status': 'ingested', 
                # Add other initial fields as necessary
            }

            new_doc_id = self.context_store.add_document_with_text(document_data)

            if new_doc_id:
                logging.info(f"Successfully ingested '{file_path}' with document ID {new_doc_id}.")
                return f"Successfully ingested document. New document ID is {new_doc_id}."
            else:
                return "Error: Failed to create a document record in the database."

        except Exception as e:
            logging.error(f"An error occurred during ingestion tool run: {e}")
            return f"An error occurred: {e}"

    def _arun(self, file_path: str):
        # This tool does not support async run yet.
        raise NotImplementedError("IngestionTool does not support async")