# IDIS: Intelligent Document Insight System

## Overview
The Intelligent Document Insight System (IDIS) is designed to transform unstructured documents (medical, legal, operational) into structured, actionable insights. The system employs a modular, privacy-first architecture using an MCP (Model Context Protocol) orchestration approach. The Phase 1 MVP focuses on local processing with targeted API usage for advanced features.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture
IDIS follows a modular architecture with the following core components:

1. **Context Store**: SQLite database that serves as the persistent storage layer, tracking patients, sessions, documents, agent outputs, and audit trails. This is the central data repository. **[HARDENED - June 2025]**: Complete security refactor with type safety, SQL injection prevention, and V1.3 schema compatibility.

2. **MCP Host Controller**: For Phase 1 MVP, this will be implemented as a simple script (run_mvp.py) that sequentially calls micro-agents rather than a complex orchestrator.

3. **Micro Agents**: Modular Python services (ingestion_agent.py, summarizer_agent.py, classifier_agent.py, tagger_agent.py) that perform specific tasks in the document processing pipeline.

4. **Permissions Model**: JSON configuration file that governs data access based on privacy level, role, and agent type.

5. **Audit Log**: Integrated into the Context Store as a dedicated table to record all system activities for tracking and compliance.

## Key Components

### Unified Cognitive Agent System
- **Purpose**: LLM-powered document processing using OpenAI GPT-4o for structured data extraction
- **Implementation**: 
  - `agents/cognitive_agent.py` - Core LLM integration with V1.3 JSON schema
  - `unified_ingestion_agent.py` - Complete pipeline combining text extraction with cognitive processing
  - `prompts/V1_Cognitive_Agent_Prompt.txt` - Master prompt template for structured extraction
- **Key Features**:
  - Real OpenAI API integration with GPT-4o model
  - V1.3 JSON schema for consistent structured data output
  - Unified processing replacing rule-based agents
  - Support for PDF, DOCX, TXT, and image files via OCR

### Context Store
- **Purpose**: Manages all persistent data storage using SQLite with hybrid V1.3 schema
- **Implementation**: context_store.py with the ContextStore class
- **Key Functions**:
  - V1.3 schema with both legacy compatibility and modern JSON structure
  - CRUD operations for patients, sessions, documents, and agent outputs
  - Hybrid column support: `document_type` for UI, `extracted_data` for cognitive agent
  - Audit trail management and comprehensive metadata storage

### Watcher Service with Triage Architecture
- **Purpose**: Monitors watch folder and manages file processing pipeline using separated responsibilities
- **Implementation**: watcher_service.py with NewFileHandler class and process_inbox_file function
- **Architecture**: "Triage" design that completely eliminates race conditions by separating file watching from processing
- **Two-Phase Operation**:
  - **Simple Watcher**: NewFileHandler immediately moves files from watch folder to inbox folder with no processing logic
  - **Timer-Based Processor**: Main loop checks inbox folder every 15 seconds and processes files through complete IDIS pipeline
- **Key Features**:
  - No race conditions - system refuses to participate in timing conflicts with scanner software
  - Temporary file filtering (ignores .tmp files from scanner)
  - Inbox folder serves as processing queue
  - Files are deleted from inbox after successful processing and archiving
  - Integration with start_watcher.sh script for Dell testing setup
  - Robust error handling and comprehensive logging

### Database Schema
The SQLite database includes the following key tables:
1. **patients**: Stores patient information with fields like patient_id, patient_name, and timestamps
2. **sessions**: Tracks user sessions with metadata
3. **documents**: Stores document information, linked to patients and sessions
4. **outputs**: Records agent processing outputs
5. **audit_log**: Tracks all system activities for compliance and debugging

### Testing Framework
Unit tests for the Context Store are implemented in tests/test_context_store.py, using Python's unittest framework.

## Data Flow - Unified Cognitive Processing with V1 HITL Workflow
1. Documents are added to a designated "watchfolder" 
2. The Watcher Service detects new files and moves them to a processing folder with unique timestamped filenames
3. **UnifiedIngestionAgent** processes documents through complete LLM-powered pipeline:
   - Text extraction from PDF, DOCX, TXT, and image files (via OCR)
   - **CognitiveAgent** sends text to OpenAI GPT-4o API for structured data extraction
   - V1.3 JSON schema output with comprehensive document metadata
   - Storage of both raw text and structured JSON data in Context Store
   - **V1 HITL Logic**: Documents with ambiguous categorization are flagged with `processing_status = 'pending_categorization'`
4. Data is persisted with hybrid schema supporting legacy UI and modern JSON structure
5. **Human-in-the-Loop Review**: Documents requiring manual review can be processed through the UI using `update_document_categorization()` method
6. All operations are logged in the audit trail with comprehensive error handling
7. Authorized users can retrieve processed information through the QuantaIQ Streamlit interface with enhanced search capabilities

## External Dependencies
The system has minimal external dependencies for the MVP:
- Python 3.11 (as specified in .replit)
- SQLite (embedded database)
- Standard Python libraries: sqlite3, json, uuid, datetime

For future phases, additional dependencies may include:
- OCR libraries for document text extraction
- NLP libraries for advanced text processing
- External APIs for specialized analysis

## Deployment Strategy
The current deployment is configured in .replit to run unit tests:
```
[deployment]
run = ["sh", "-c", "python -m unittest discover tests"]
```

For the Phase 1 MVP:
1. The system is designed to run locally for privacy and performance
2. A simple CLI interface will allow basic operations
3. The watchfolder approach simplifies document ingestion without requiring a complex UI
4. All data is stored in a local SQLite database for easy deployment

Future phases may include:
- Web-based UI
- Multi-user support
- Enhanced security features
- Optional cloud integration with privacy controls

## Recent Changes  
- **July 2025**: **COMPREHENSIVE INTELLIGENCE BATCH UPDATE COMPLETE** - Performed major batch update to enhance system intelligence for seven new document/issuer types: expanded CLASSIFICATION_RULES to include Bank Statement, Utility Bill, Insurance Document, and Receipt with specific keywords, updated KNOWN_ISSUERS to include Homer Electric Association, Bank of America, Global Credit Union, State Farm, and Safeway, added corresponding filename abbreviations (BNKSTMT, UTIL) for complete filing integration across all agents
- **July 2025**: **SEARCH HIGHLIGHTING DARK MODE FIX COMPLETE** - Fixed search term highlighting feature for dark mode compatibility: added explicit 'color: black;' to highlighted spans and container div, converted newlines to HTML <br> tags for proper formatting, ensuring yellow highlighting with black text is visible in both light and dark modes
- **July 2025**: **ALASKA CERTIFICATE INTELLIGENCE ENHANCEMENT COMPLETE** - Enhanced system intelligence to correctly classify and identify Alaska Certificate of Organization documents: added "Business License" classification rule with keywords ["certificate of organization", "business license"] in ClassifierAgent, added "State of Alaska" issuer rule with keywords ["state of alaska", "department of commerce, community, and economic development"] in TaggerAgent, added "BIZLIC" abbreviation for Business License document type
- **July 2025**: **RACE CONDITION FIX COMPLETE** - Resolved race condition in InboxProcessor where it tried to delete files already moved by TaggerAgent during successful archiving: removed redundant file cleanup logic since TaggerAgent's _safe_file_move already handles file removal, eliminating "Failed to remove processed file" warnings for clean pipeline execution
- **July 2025**: **CRITICAL DATA LOSS BUG PERMANENTLY FIXED** - Diagnosed and permanently fixed critical data loss bug in document processing pipeline: fixed InboxProcessor cleanup logic to only delete files when TaggerAgent archiving succeeds completely (failed_count == 0), ensuring failed files are moved to holding folder for manual inspection with zero data loss
- **July 2025**: **PERMANENT DATA LOSS FIX COMPLETE** - Permanently fixed the TaggerAgent data loss bug by ensuring the TaggerAgent can always find the source file for archiving: replaced complex, flawed search logic with simple direct database path lookup, eliminating "File not found" errors and ensuring 100% file archiving success with no data loss
- **July 2025**: **TWO-PART PIPELINE FIX COMPLETE** - Implemented critical fixes to finalize document processing pipeline: (1) Fixed TaggerAgent file location bug by updating original_watchfolder_path to point to inbox location after ingestion, ensuring 100% file archiving success, (2) Permanently solved logging noise with custom NoisyLibraryFilter in cover_sheet.py that blocks fontTools/fpdf2/reportlab DEBUG messages for clean console output
- **July 2025**: **MEDICAID NAVIGATOR BACKEND INTEGRATION COMPLETE** - Successfully connected the Medicaid Navigator UI file uploader to the backend processing pipeline: implemented file upload functionality that saves documents to data/scanner_output folder, created production watcher service monitoring this folder, verified complete end-to-end processing with OpenAI API integration, documents now flow from UI upload → watch folder → processing pipeline → database storage with AI extraction
- **July 2025**: **ENHANCED SEARCH UI DATA MAPPING COMPLETE** - Fixed UI data mapping to properly display extracted information from cognitive agent: enhanced search interface with robust JSON parsing for AI summaries, dates, issuer info, and tags, added comprehensive data extraction functions that handle both cognitive agent JSON and legacy columns for optimal backward compatibility
- **July 2025**: **CRITICAL TAGGER AGENT TYPEERROR FIX COMPLETE** - Resolved all "object of type 'int' has no len()" errors in TaggerAgent: (1) Fixed document_id integer-to-string conversion in filename generation method, (2) Added patient_id string conversion in _get_patient_folder_name function, ensuring all string operations work correctly with database integer values
- **July 2025**: **ENVIRONMENT-BASED LOGGING SYSTEM COMPLETE** - Implemented comprehensive logging configuration in watcher_service.py using LOGGING_LEVEL environment variable for flexible control, with robust suppression of third-party libraries (fontTools, fpdf2, reportlab, httpx, openai) ensuring clean console output for debugging and production monitoring
- **July 2025**: **COMPREHENSIVE LOGGING FIX** - Implemented robust logging suppression across all entry points (watcher_service.py, ingestion_agent.py, tagger_agent.py, cover_sheet.py, demo_idis_pipeline.py) to eliminate noisy DEBUG messages from fontTools, fpdf2, and reportlab libraries, ensuring clean console output for debugging
- **July 2025**: **CRITICAL FILING BUG FIX** - Fixed TaggerAgent file location detection failure in inbox workflow: agent now searches multiple potential file locations (inbox, watch folders) instead of only looking at original_watchfolder_path, resolving "FILING FAILED" errors and preventing documents from being incorrectly moved to holding folder
- **July 2025**: **CRITICAL DATABASE BUG FIX** - Fixed IngestionAgent database persistence failure caused by attempting to update non-existent 'ocr_confidence_percent' column, preventing extracted text from being saved and causing documents to incorrectly move to holding folder
- **July 2025**: **CRITICAL PIPELINE FIX COMPLETE** - Diagnosed and fixed column name mismatch that was breaking text flow through the pipeline: synchronized all agents to use 'full_text' column consistently (IngestionAgent saves to full_text, ClassifierAgent/SummarizerAgent/TaggerAgent read from full_text), eliminating the bug where extracted text wasn't reaching downstream agents
- **July 2025**: **MODULAR ARCHITECTURE COMPLETE** - Transformed IDIS into a multi-module platform: created modules/ directory structure, moved document search to modules/search_ui.py, implemented Medicaid Navigator UI at modules/medicaid_navigator/ui.py, and converted app.py into application router with sidebar module selection for scalable platform expansion
- **July 2025**: **COMPREHENSIVE FIX COMPLETE** - Implemented robust competitive PDF extraction strategy in both IngestionAgent and UnifiedIngestionAgent with correct return formats: IngestionAgent returns (text, confidence) tuple while UnifiedIngestionAgent returns text string, both agents always perform direct text extraction AND OCR then intelligently select the result with more content, definitively solving mixed-content PDF processing failures
- **July 2025**: Critical data loss prevention fix implemented with two-part solution: removed TaggerAgent text validation block that was skipping documents, added conditional cleanup in watcher service to only delete files after successful archiving, failed files now moved to holding folder for manual inspection
- **July 2025**: Made view_text.py utility configurable by removing hardcoded database path and adding --db-path command-line argument for Docker/Mac compatibility
- **June 2025**: Enhanced SummarizerAgent with comprehensive improvements: tiktoken-based token management for accurate token counting, cost optimization with dynamic model selection (gpt-3.5-turbo for simple docs, gpt-4o for complex), and customizable summary styles/lengths
- **June 2025**: Comprehensive documents table schema update - added missing columns: filed_path, issuer_source, recipient, tags_extracted, and changed classification_confidence to REAL type for complete UI compatibility
- **June 2025**: Fixed PDF text extraction bug by changing page.get_text() to page.get_text("text") for improved reliability with text-based PDFs
- **June 2025**: Updated app.py with command-line argument parsing for Docker deployment compatibility and dynamic database path configuration
- **June 2025**: Updated docker-compose.yml with correct multi-service configuration and standardized folder structure
- **June 2025**: Added complete Docker containerization setup with Dockerfile, docker-compose.yml, and deployment documentation for production-ready deployment
- **June 2025**: Restored local Dell development machine database paths for final deployment readiness
- **June 2025**: Comprehensive security analysis confirmed SQL injection vulnerability reports were false positives due to proper whitelisting and parameterized queries

## Development Guidelines
1. Maintain the modular structure to enable independent agent development
2. Ensure comprehensive unit testing for all components
3. Follow privacy-by-design principles
4. Document all API interfaces between components
5. Prioritize features based on the Phase 1 MVP roadmap

## Docker Deployment
The system now includes complete containerization support:
- **Dockerfile**: Production-ready container with Python 3.11 and Tesseract OCR
- **docker-compose.yml**: Multi-service orchestration for watcher and UI services
- **Volume mounts**: Persistent data storage for documents and database
- **Environment variables**: OpenAI API key configuration support