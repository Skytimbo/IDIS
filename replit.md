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

## Development Guidelines
1. Maintain the modular structure to enable independent agent development
2. Ensure comprehensive unit testing for all components
3. Follow privacy-by-design principles
4. Document all API interfaces between components
5. Prioritize features based on the Phase 1 MVP roadmap