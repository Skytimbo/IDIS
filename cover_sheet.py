#!/usr/bin/env python3
"""
Smart Cover Sheet Renderer Module for Intelligent Document Insight System (IDIS)

This module provides the SmartCoverSheetRenderer class which generates professional
PDF cover sheets summarizing document batches processed by the IDIS system.
"""

import os
import logging
import datetime
import json
from typing import List, Dict, Any, Optional, Tuple

import markdown2
from weasyprint import HTML

from context_store import ContextStore

# Part 2 Fix: Custom filter class to explicitly block messages from noisy loggers
class NoisyLibraryFilter(logging.Filter):
    def filter(self, record):
        noisy_loggers = ['fontTools', 'fpdf2', 'reportlab', 'PIL']
        return not any(record.name.startswith(logger) for logger in noisy_loggers)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Apply the custom filter to the root logger
logging.getLogger().addFilter(NoisyLibraryFilter())

# Comprehensive suppression of noisy third-party PDF and font libraries
noisy_loggers = ['fontTools', 'fpdf2', 'reportlab']
for logger_name in noisy_loggers:
    logging.getLogger(logger_name).setLevel(logging.WARNING)

class SmartCoverSheetRenderer:
    """
    Agent responsible for generating professional PDF cover sheets from document metadata.
    
    The SmartCoverSheetRenderer aggregates document summaries and key metadata from the 
    Context Store and generates a well-formatted PDF cover sheet that provides an overview
    of processed documents, enabling easy review of document insights.
    """
    
    def __init__(self, context_store: ContextStore):
        """
        Initialize the Smart Cover Sheet Renderer with required parameters.
        
        Args:
            context_store: An initialized instance of the ContextStore
        """
        self.context_store = context_store
        self.agent_id = "cover_sheet_renderer_v1.0"
        self.logger = logging.getLogger("SmartCoverSheetRenderer")
    
    def generate_cover_sheet(
        self, 
        document_ids: List[str], 
        output_pdf_filename: str, 
        session_id: Optional[str] = None, 
        user_id: str = "cover_sheet_agent_mvp_user"
    ) -> bool:
        """
        Generate a PDF cover sheet for a set of documents.
        
        Args:
            document_ids: List of document IDs to include in the cover sheet
            output_pdf_filename: Path where the output PDF should be saved
            session_id: Optional session ID to retrieve batch-level summary
            user_id: User ID for audit trail purposes
            
        Returns:
            True if PDF generation was successful, False otherwise.
            Note: Even if PDF generation fails, the Markdown content will be saved
            to a .md file with the same base name as the requested PDF.
        """
        self.logger.info(f"Starting cover sheet generation for {len(document_ids)} documents")
        
        # Collect document data
        documents_data = []
        for doc_id in document_ids:
            # Get document details
            document = self.context_store.get_document(doc_id)
            if not document:
                self.logger.warning(f"Document {doc_id} not found in Context Store")
                continue
            
            # Parse JSON fields if they're stored as strings
            doc_data = document.copy()
            
            # Handle document_dates as either JSON string or dict
            if isinstance(document.get('document_dates'), str):
                try:
                    doc_data['document_dates'] = json.loads(document['document_dates'])
                except (json.JSONDecodeError, TypeError):
                    doc_data['document_dates'] = {}
            
            # Handle tags_extracted as either JSON string or list
            if isinstance(document.get('tags_extracted'), str):
                try:
                    doc_data['tags_extracted'] = json.loads(document['tags_extracted'])
                except (json.JSONDecodeError, TypeError):
                    doc_data['tags_extracted'] = []
            
            # Get document summary
            summary_outputs = self.context_store.get_agent_outputs_for_document(
                document_id=doc_id,
                agent_id="summarizer_agent_v1.0",
                output_type="per_document_summary"
            )
            
            per_doc_summary = None
            if summary_outputs and len(summary_outputs) > 0:
                # Get the most recent summary
                per_doc_summary = summary_outputs[0]["output_data"]
            
            # Add summary to document data
            doc_data["per_doc_summary"] = per_doc_summary
            documents_data.append(doc_data)
        
        # Get batch summary if session ID is provided
        batch_summary_text = None
        if session_id:
            session_data = self.context_store.get_session(session_id)
            if session_data and "session_metadata" in session_data:
                session_metadata = session_data.get("session_metadata", {})
                # Handle both string and dictionary metadata formats
                if isinstance(session_metadata, dict):
                    batch_summary_text = session_metadata.get("batch_summary")
                elif isinstance(session_metadata, str):
                    # Try to extract batch summary from string
                    try:
                        # Try to parse as JSON
                        metadata_dict = json.loads(session_metadata)
                        batch_summary_text = metadata_dict.get("batch_summary")
                    except (json.JSONDecodeError, TypeError):
                        # If it's a plain string, check if it might be a batch summary
                        if "batch_summary" in session_metadata.lower():
                            batch_summary_text = session_metadata
        
        # Generate markdown content
        markdown_content = self._build_markdown_content(documents_data, batch_summary_text)
        
        # Save the markdown content to a file
        markdown_filename = output_pdf_filename.replace('.pdf', '.md')
        markdown_saved = False
        
        try:
            # Create output directory if it doesn't exist
            output_dir = os.path.dirname(markdown_filename)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
                
            # Write markdown content to file
            with open(markdown_filename, 'w') as md_file:
                md_file.write(markdown_content)
            markdown_saved = True
            self.logger.info(f"Successfully saved Markdown content to: {markdown_filename}")
        except Exception as e:
            self.logger.error(f"Failed to save Markdown content to {markdown_filename}: {e}")
            # If Markdown saving fails, we should log but continue to attempt PDF generation
        
        # Attempt PDF conversion only if Markdown was successfully saved
        pdf_success = False
        if markdown_saved:
            pdf_success = self._convert_markdown_to_pdf(markdown_content, output_pdf_filename)
        
        # Log result and create audit entry
        if pdf_success:
            self.logger.info(f"Successfully generated cover sheet PDF: {output_pdf_filename}")
            self.context_store.add_audit_log_entry(
                user_id=user_id,
                event_type="DOCUMENT_PROCESSING",
                event_name="COVER_SHEET_GENERATED",
                status="SUCCESS",
                resource_type="cover_sheet",
                resource_id=output_pdf_filename,
                details=json.dumps({
                    "document_count": len(documents_data),
                    "session_id": session_id,
                    "markdown_saved": True
                })
            )
            return True
        else:
            # Different logging based on whether Markdown was saved
            if markdown_saved:
                self.logger.warning(
                    f"Failed to convert to PDF: {output_pdf_filename}, but Markdown was saved to: {markdown_filename}"
                )
                # Audit trail with note about Markdown being saved
                self.context_store.add_audit_log_entry(
                    user_id=user_id,
                    event_type="DOCUMENT_PROCESSING",
                    event_name="COVER_SHEET_GENERATED",
                    status="FAILURE",
                    resource_type="cover_sheet",
                    resource_id=output_pdf_filename,
                    details=json.dumps({
                        "document_count": len(documents_data),
                        "session_id": session_id,
                        "error": "PDF generation failed",
                        "markdown_saved": True,
                        "markdown_path": markdown_filename
                    })
                )
            else:
                # Both Markdown and PDF failed
                self.logger.error(f"Failed to generate cover sheet: both Markdown and PDF generation failed")
                self.context_store.add_audit_log_entry(
                    user_id=user_id,
                    event_type="DOCUMENT_PROCESSING",
                    event_name="COVER_SHEET_GENERATED",
                    status="FAILURE",
                    resource_type="cover_sheet",
                    resource_id=output_pdf_filename,
                    details=json.dumps({
                        "document_count": len(documents_data),
                        "session_id": session_id,
                        "error": "Both Markdown and PDF generation failed",
                        "markdown_saved": False
                    })
                )
            return False
    
    def _build_markdown_content(
        self, 
        documents_data: List[Dict[str, Any]], 
        batch_summary_text: Optional[str]
    ) -> str:
        """
        Build the markdown content for the cover sheet.
        
        Args:
            documents_data: List of dictionaries containing document details
            batch_summary_text: Optional batch-level summary text
            
        Returns:
            Formatted markdown string
        """
        # Current date and time for the header
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Start building the markdown content
        markdown = []
        
        # Header Section
        markdown.append("# IDIS Smart Cover Sheet")
        markdown.append(f"**Generated on:** {now}")
        markdown.append(f"**Documents in Batch:** {len(documents_data)}")
        markdown.append("")
        
        # Batch Summary (if available and more than one document)
        if batch_summary_text and len(documents_data) > 1:
            markdown.append("## Batch Overview")
            markdown.append(batch_summary_text)
            markdown.append("")
        
        # Document Details Section
        if len(documents_data) == 1 and documents_data:
            # Single document detailed view
            doc = documents_data[0]
            markdown.append(f"## Document Details: {doc.get('file_name', 'Unnamed Document')}")
            
            # Summary
            if doc.get('per_doc_summary'):
                markdown.append(f"**Summary:** {doc['per_doc_summary']}")
            else:
                markdown.append("**Summary:** No summary available")
            markdown.append("")
            
            # Key metadata
            markdown.append(f"**File Name:** {doc.get('file_name', 'N/A')}")
            
            doc_type = doc.get('document_type', 'Unclassified')
            confidence = doc.get('classification_confidence', 'N/A')
            markdown.append(f"**Document Type:** {doc_type} (Confidence: {confidence})")
            
            patient_id = doc.get('patient_id', 'N/A')
            markdown.append(f"**Patient ID:** {patient_id}")
            
            # Dates
            markdown.append("**Key Dates:**")
            doc_dates = doc.get('document_dates', {})
            if doc_dates and isinstance(doc_dates, dict):
                for date_label, date_value in doc_dates.items():
                    markdown.append(f"  - {date_label}: {date_value}")
            else:
                markdown.append("  - No date information available")
            
            # Source and recipient
            markdown.append(f"**Issuer/Source:** {doc.get('issuer_source', 'N/A')}")
            markdown.append(f"**Recipient:** {doc.get('recipient', 'N/A')}")
            
            # Tags
            tags = doc.get('tags_extracted', [])
            if tags:
                markdown.append(f"**Tags:** {', '.join(tags)}")
            else:
                markdown.append("**Tags:** None")
                
        elif len(documents_data) > 1:
            # Batch of documents - create a table
            markdown.append("## Document Index")
            markdown.append("")
            markdown.append("| No. | File Name | Type | Patient ID | Key Date | Summary Snippet | Tags |")
            markdown.append("| --- | --------- | ---- | ---------- | -------- | --------------- | ---- |")
            
            for idx, doc in enumerate(documents_data, 1):
                # Get key date (use the first one found or 'N/A')
                key_date = "N/A"
                doc_dates = doc.get('document_dates', {})
                if doc_dates and isinstance(doc_dates, dict) and len(doc_dates) > 0:
                    # Just take the first date we find
                    key_date = list(doc_dates.values())[0]
                
                # Get summary snippet (first ~100 chars)
                summary = doc.get('per_doc_summary', '')
                summary_snippet = summary[:100] + '...' if summary and len(summary) > 100 else summary or 'N/A'
                
                # Get tags as comma-separated string
                tags = doc.get('tags_extracted', [])
                tags_str = ', '.join(tags) if tags else 'N/A'
                
                # Add table row
                markdown.append(f"| {idx} | {doc.get('file_name', 'N/A')} | {doc.get('document_type', 'Unclassified')} | {doc.get('patient_id', 'None')} | {key_date} | {summary_snippet} | {tags_str} |")
        
        # Join all markdown lines with newlines
        return "\n".join(markdown)
    
    def _convert_markdown_to_pdf(self, markdown_content: str, output_pdf_filename: str) -> bool:
        """
        Convert markdown content to PDF file.
        
        Args:
            markdown_content: The markdown string to convert
            output_pdf_filename: Path where the output PDF should be saved
            
        Returns:
            True if conversion successful, False otherwise
        """
        try:
            # Create output directory if it doesn't exist
            output_dir = os.path.dirname(output_pdf_filename)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            
            # Convert markdown to HTML
            html_content = markdown2.markdown(
                markdown_content,
                extras=["tables", "fenced-code-blocks"]
            )
            
            # Add CSS styling for a professional look
            styled_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>IDIS Smart Cover Sheet</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        line-height: 1.6;
                        margin: 2em;
                        color: #333;
                    }}
                    h1 {{
                        color: #2c3e50;
                        border-bottom: 2px solid #3498db;
                        padding-bottom: 10px;
                    }}
                    h2 {{
                        color: #2980b9;
                        margin-top: 1.5em;
                    }}
                    table {{
                        border-collapse: collapse;
                        width: 100%;
                        margin: 1em 0;
                    }}
                    th, td {{
                        border: 1px solid #ddd;
                        padding: 8px;
                        text-align: left;
                    }}
                    th {{
                        background-color: #f2f2f2;
                        font-weight: bold;
                    }}
                    tr:nth-child(even) {{
                        background-color: #f9f9f9;
                    }}
                    strong {{
                        color: #2c3e50;
                    }}
                </style>
            </head>
            <body>
                {html_content}
            </body>
            </html>
            """
            
            # Convert HTML to PDF using WeasyPrint
            HTML(string=styled_html).write_pdf(output_pdf_filename)
            return True
            
        except Exception as e:
            self.logger.error(f"Error converting markdown to PDF: {e}")
            return False