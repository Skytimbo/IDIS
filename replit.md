# IDIS: Intelligent Document Insight System

## Overview
The Intelligent Document Insight System (IDIS) is designed to transform unstructured documents (medical, legal, operational) into structured, actionable insights. The system employs a modular, privacy-first architecture using an MCP (Model Context Protocol) orchestration approach. The Phase 1 MVP focuses on local processing with targeted API usage for advanced features.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture
IDIS follows a modular architecture with the following core components:

1. **Context Store**: SQLite database that serves as the persistent storage layer, tracking patients, sessions, documents, agent outputs, and audit trails. This is the central data repository.

2. **MCP Host Controller**: For Phase 1 MVP, this will be implemented as a simple script (run_mvp.py) that sequentially calls micro-agents rather than a complex orchestrator.

3. **Micro Agents**: Modular Python services (ingestion_agent.py, summarizer_agent.py, classifier_agent.py, tagger_agent.py) that perform specific tasks in the document processing pipeline.

4. **Permissions Model**: JSON configuration file that governs data access based on privacy level, role, and agent type.

5. **Audit Log**: Integrated into the Context Store as a dedicated table to record all system activities for tracking and compliance.

## Key Components

### Context Store
- **Purpose**: Manages all persistent data storage using SQLite
- **Implementation**: context_store.py with the ContextStore class
- **Key Functions**:
  - Database initialization and schema management
  - CRUD operations for patients, sessions, documents, and agent outputs
  - Audit trail management
  - JSON handling for metadata storage

### Database Schema
The SQLite database includes the following key tables:
1. **patients**: Stores patient information with fields like patient_id, patient_name, and timestamps
2. **sessions**: Tracks user sessions with metadata
3. **documents**: Stores document information, linked to patients and sessions
4. **outputs**: Records agent processing outputs
5. **audit_log**: Tracks all system activities for compliance and debugging

### Testing Framework
Unit tests for the Context Store are implemented in tests/test_context_store.py, using Python's unittest framework.

## Data Flow
1. Documents are added to a designated "watchfolder" (for MVP) or uploaded via UI (future)
2. The Ingestion Agent processes documents, extracting text and metadata
3. Data is persisted in the Context Store
4. Various micro-agents process the documents and generate insights
5. All operations are logged in the audit trail
6. Authorized users can retrieve processed information through defined interfaces

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