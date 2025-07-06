import os
import logging
from typing import Type, List
from pydantic import BaseModel, Field

from langchain.tools import BaseTool
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.chains.openai_functions import create_structured_output_chain

from context_store import ContextStore
from ingestion_agent import IngestionAgent

# Assume a default database path for now
DB_PATH = "production_idis.db"

# --- Data Schemas for Cognitive Extraction ---

class KeyDates(BaseModel):
    primary_date: str | None = Field(None, description="The single most important date, in YYYY-MM-DD format.")
    due_date: str | None = Field(None, description="The payment due date, if present.")
    invoice_date: str | None = Field(None, description="The date the invoice was issued.")

class Issuer(BaseModel):
    name: str | None = Field(None, description="The name of the company or person issuing the document.")
    contact_info: str | None = Field(None, description="Any contact information like a phone number or email for the issuer.")

class Filing(BaseModel):
    suggested_tags: List[str] = Field(default_factory=list, description="A list of 1-3 relevant keywords for filing.")

class DocumentIntelligence(BaseModel):
    """The main schema for structured data extracted from a document."""
    document_type: str = Field("Unclassified", description="The classified type of the document (e.g., 'Invoice', 'Medical Record').")
    issuer: Issuer
    key_dates: KeyDates
    filing: Filing
    summary: str = Field(description="A 2-3 sentence summary of the document's content.")

class IngestionInput(BaseModel):
    """Input schema for the IngestionTool."""
    file_path: str = Field(description="The absolute path to the file to be ingested.")

class IngestionTool(BaseTool):
    """A tool to ingest a single document, extract its text, and create a database record."""
    name: str = "ingest_document"
    description: str = "Useful for when you need to process a new document. Takes a file_path as input, extracts its text, and saves it to the database, returning the new document's ID."
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


class CognitiveTaggerInput(BaseModel):
    """Input schema for the CognitiveTaggerTool."""
    document_text: str = Field(description="The full text of the document to be analyzed.")

class CognitiveTaggerTool(BaseTool):
    """A tool to analyze document text and extract structured intelligence using an LLM."""
    name: str = "extract_document_intelligence"
    description: str = "Useful for when you need to understand and categorize a document. Takes the full text of a document and returns a structured JSON object with its type, issuer, key dates, and a summary."
    args_schema: Type[BaseModel] = CognitiveTaggerInput

    def _run(self, document_text: str) -> dict:
        """Use the tool."""
        try:
            # For now, we'll use OpenAI. This can be swapped for a local LLM later.
            llm = ChatOpenAI(model="gpt-4o", temperature=0)

            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are an expert at analyzing documents. Your task is to extract key information from the provided text and format it according to the specified JSON schema. Only return information found in the text."),
                ("human", "Extract the required information from the following document text: \n\n```{text}```")
            ])

            # Create a chain that forces the LLM to output in our desired Pydantic schema
            chain = create_structured_output_chain(output_schema=DocumentIntelligence, llm=llm, prompt=prompt)

            result = chain.invoke({"text": document_text})

            # Convert the result to a dictionary if it's a Pydantic model
            if hasattr(result, 'model_dump'):
                return result.model_dump()
            elif hasattr(result, 'dict'):
                return result.dict()
            else:
                return result

        except Exception as e:
            logging.error(f"An error occurred in CognitiveTaggerTool: {e}")
            return {"error": str(e)}

    def _arun(self, document_text: str):
        raise NotImplementedError("CognitiveTaggerTool does not support async")