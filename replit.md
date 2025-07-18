# QuantaIQ / IDIS: The Intelligent Document Insight System

| Current Version | Development Stage | Key Focus |
| :--- | :--- | :--- |
| **MVP 1.0** | Post-MVP Refinement | UI/UX Polish & Core Workflow Hardening |

---

## 1. Vision & Mission

* **Vision:** To transform the chaos of unstructured documents ("Noise") into clear, actionable **Wisdom** through a private, secure, and intelligent software appliance.
* **Mission:** To empower professionals and small businesses by providing a turnkey solution that automates document processing, mitigates administrative burdens and liability, and provides intuitive access to a structured knowledge base—all while ensuring absolute data privacy through a local-first, "non-inference" design.

## 2. Core Philosophy

* **🧠 Augmented Intelligence:** The AI's role is to assist, not decide. It surfaces, summarizes, and organizes critical information under a strict "non-inference" policy, ensuring the human expert is always in control.
* **🔒 Private by Design:** The system is designed to operate as a self-contained appliance. All documents and data are processed and stored locally on the user's hardware.
* **✨ From Noise to Wisdom:** The system moves beyond simple data extraction to provide users with the context and insight needed to make better, faster decisions.

## 3. Architecture Overview

The system is a **Modular Monolith** designed for simplicity and rapid development, running as a set of coordinated services via Docker Compose.

**High-Level Flow:**
[ User ] --> [ QuantaIQ UI (Streamlit) ] <--> [ FastAPI Layer ] <--> [ IDIS Engine (Python) ] <--> [ Database (SQLite) ]
|
V
[ Document Archive (Local Files) ]


* **QuantaIQ UI:** The web-based front-end, built with Streamlit, for all user interaction. It includes modules for Entity/Case Management, Document Search, and more.
* **FastAPI Layer:** A professional API layer (`/api/`) that provides secure, structured endpoints for the Streamlit UI to interact with the backend services.
* **IDIS Engine:** The core backend, including the `watcher_service` for file system monitoring and the `UnifiedIngestionAgent` for document processing.
* **Database:** A local SQLite database (`production_idis.db`) acts as the central "source of truth".
* **Document Archive:** A local directory (`data/archive`) for storing the original, unaltered files.

## 4. Key Components & Data Model

* **CognitiveAgent & Heuristic Engine:** An LLM-powered agent (using GPT-4o via API in the MVP) combined with a deterministic, rule-based engine to accurately classify documents and extract structured JSON data.
* **Unified Uploader:** A single, context-aware component that handles all file uploads, ensuring consistent processing regardless of which module the user is in.
* **Database Schema:** The data model is built around three core concepts:
    * **`entities`**: The subjects of the documents (e.g., clients, patients, companies).
    * **`cases`**: A specific application or project related to an entity (e.g., "Jane Doe - Medicaid App 2025"). Stores metadata like status and deadlines.
    * **`documents`**: The individual files, each linked to an entity and optionally to a case requirement.

## 5. Current Workflow: Medicaid Navigator

The primary workflow implemented in the MVP is the Case Management system for the Medicaid Navigator:

1.  A caseworker navigates to the **Active Case Dashboard**.
2.  They can view all active cases with at-a-glance progress metrics.
3.  They can start a **New Application**, which takes them to the **Entity Management** page to select or create a new client (Entity).
4.  A new **Case** is created for that Entity.
5.  The user enters the detailed **Case View**, which displays a dynamic **Checklist** of required documents.
6.  The user uploads documents, which are processed by the AI.
7.  The user **Assigns** each processed document to a checklist requirement, with a "Trust, but Verify" system providing non-blocking warnings for potential mismatches.
8.  The checklist status updates in real-time.

## 6. Getting Started / Deployment

The application supports both Docker and native deployment options:

### Native Replit Deployment (Recommended)
1. Set the `OPENAI_API_KEY` in your environment
2. Run the native deployment script: `./deploy-native.sh`
3. Access the application at the URL provided by Replit

### Docker Deployment (Alternative)
1. Ensure Docker is installed and running
2. Set the `OPENAI_API_KEY` in your environment  
3. Run the Docker deployment script: `./deploy.sh`

The native deployment script (`deploy-native.sh`) is optimized for Replit's environment and includes:
- Automatic directory structure creation
- Database initialization with proper schema
- Smart dependency management
- Conflict detection for running services
- Integrated watcher service management

## 7. Recent Technical Fixes

### Critical Document Archiving Pipeline Fix (2025-07-17)
- **Issue**: Documents uploaded through the UI were failing to archive due to premature temp file deletion.
- **Root Cause**: The `unified_uploader.py` was deleting temporary files before the TaggerAgent could process them for archiving.
- **Fix**: Modified the upload pipeline to preserve temp files until after successful archiving.
- **Impact**: UI uploads now complete the full processing pipeline including automatic archiving to organized folders.

### ContextStore Method Completeness (2025-07-17)
- **Issue**: Missing methods in ContextStore class causing compatibility issues.
- **Fix**: Added missing methods: `get_documents_by_processing_status`, `update_document_fields`, `get_entity`, `add_audit_log_entry`.
- **Impact**: All components now have access to required database operations.

### Complete Case-Document Association Fix (2025-07-17)
- **Issue**: Documents uploaded in Medicaid cases were not appearing in the Case Documents section due to multiple pipeline issues.
- **Root Causes**: 
  - Database column name mismatch (`filename` vs `file_name`)
  - Hardcoded entity IDs in uploader instead of using session state
  - Missing case-document association creation during upload
- **Fixes**:
  - Fixed `get_documents_for_case()` to use correct column name `file_name`
  - Modified `_get_context_parameters()` to use actual entity ID from session state
  - Added `_create_case_document_association()` function to automatically link uploads to current case
  - Added missing `get_document_details_by_id()` method for "View Document" functionality
- **Impact**: Complete case-document workflow now functional - uploads appear in Case Documents section with working "View Document" buttons.

### Enhanced Document Viewer UX (2025-07-17)
- **Issue**: Document viewer showed confusing raw OCR text instead of showcasing excellent AI analysis results.
- **Root Cause**: UI emphasized problematic raw text extraction over valuable structured AI insights.
- **Fixes**:
  - Enhanced `get_document_details_by_id()` method to return comprehensive document metadata
  - Completely rebuilt document viewer in `modules/medicaid_navigator/ui.py`
  - Added prominent "AI Analysis" section with document classification, confidence scores, and structured data
  - Added original file download functionality
  - Moved raw OCR text to collapsed "Advanced Options" section with warnings
  - Added visual indicators for document type, confidence, and processing status
- **Impact**: Document viewer now showcases AI intelligence with clean, professional interface that builds user confidence in the system.

### Human-Readable Document Display & Duplicate Key Fix (2025-07-17)
- **Issues**: 
  - Document display showed raw JSON data instead of clean, human-friendly information
  - Duplicate key errors from multiple documents with same ID causing button conflicts
- **Root Causes**:
  - Technical JSON structures displayed directly to business users
  - Button keys only using document ID without case context
- **Fixes**:
  - Transformed technical JSON into conversational format (e.g., "Document Type: Payslip (95% confidence)")
  - Implemented human-readable financial display (e.g., "Total Amount: $150.00 USD")
  - Added conversational date formatting and payment method display
  - Fixed duplicate keys using format: `f"view_doc_{case_id}_{doc['id']}_{index}"`
  - Enhanced tags display with bullet-point format for better readability
- **Impact**: Professional, business-friendly interface with no technical jargon and zero duplicate key errors.

### Professional UX Improvements (2025-07-17)
- **Issues**:
  - Document viewer only had download functionality
  - Quick Actions buried at bottom of dashboard
  - Upload interface hidden behind expandable section
- **Root Causes**:
  - Users needed both in-app viewing and download options
  - Most-used functions not prominently positioned
  - Upload workflow required extra clicks to access
- **Fixes**:
  - Added in-app document viewing with PDF inline display, image preview, and text viewing
  - Moved Quick Actions section to top of dashboard (above KPI metrics)
  - Made upload interface expanded by default, removing clickable expansion box
  - Enhanced Case Documents section with both "View in App" and "Download" buttons
  - Added comprehensive file type support for in-app viewing (PDF, images, text)
- **Impact**: Professional UX that separates good software from great software - immediate access to key functions, dual viewing options, and intuitive upload workflow.

### Critical Session State & Document Viewer Bug Fixes (2025-07-17)
- **Issues**:
  - Document viewer had no close button, causing permanent interface clutter
  - Session state bleeding between cases - documents from one case appearing in different applications
  - Data integrity risk from cross-case document contamination
- **Root Causes**:
  - Missing close button functionality in document viewer
  - Session state (`document_to_view`) not cleared during case navigation
  - No validation to ensure viewed documents belong to current case
- **Fixes**:
  - Added prominent "✕ Close Document Viewer" button with proper state clearing
  - Implemented comprehensive session state cleanup across all navigation paths
  - Added data integrity check to verify document belongs to current case
  - Session state cleared when: navigating to home, switching cases, creating new applications, viewing active cases
  - Added database validation to prevent cross-case document viewing
- **Impact**: Resolved critical data integrity issues that could cause serious confusion in real case management scenarios. Clean separation between cases ensures professional reliability.

### Enhanced Document Viewer & Intelligent Metadata Extraction (2025-07-17)
- **Issues**:
  - Close button not prominently visible in document viewer
  - Issuer metadata showing "RETURN SERVICE REQUESTED" instead of actual issuer "FNB Alaska"
  - Raw OCR data prioritized over intelligent AI-extracted metadata
- **Root Causes**:
  - Close button buried at bottom of document viewer interface
  - No filtering of postal/shipping instructions from issuer field
  - Metadata extraction logic prioritized raw OCR over AI analysis
- **Fixes**:
  - Moved close button to top of document viewer as prominent primary button
  - Implemented intelligent issuer detection that prioritizes AI-extracted data
  - Added postal instruction filtering to ignore common shipping labels
  - Enhanced metadata extraction to check multiple AI-extracted data sources
  - Fallback logic filters out postal instructions from raw OCR data
- **Impact**: Professional document viewer with clear navigation controls and accurate metadata that showcases AI intelligence over raw text extraction.

## 8. Product Roadmap

### Phase 1: UI Polish & Core Workflow Hardening (Current Focus)
- [x] Implement the "Active Case Dashboard".
- [x] Build FastAPI Layer for backend decoupling and scalability.
- [x] Fix critical document archiving pipeline regression (TaggerAgent integration).
- [ ] Refine the UI with a "Two-Panel" layout and contextual guidance.
- [ ] Build the "Generate Application Packet" feature.
- [ ] Address medium/low priority issues from CodeRabbit review (e.g., harden `deploy.sh`, improve exception handling).

### Phase 2: RAG & Conversational Intelligence
- [ ] Implement the `RetrievalEmbedder` model and a vector database.
- [ ] Build a conversational chat interface for asking natural language questions about the document archive.

### Phase 3: The Private AI Appliance
- [ ] Fine-tune a 7B-parameter local LLM to replace the cloud API dependency, making the appliance fully self-contained.
- [ ] Design and prototype the physical hardware shell.








