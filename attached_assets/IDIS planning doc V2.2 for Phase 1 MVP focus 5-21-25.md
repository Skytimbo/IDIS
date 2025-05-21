

---

## **Intelligent Document Insight System (IDIS) – MCP Architecture**

Version: 2.2 (Phase 1 MVP Focus)

Date: May 21, 2025

Project Lead: Dr. Tim Scheffel, D.O.

Development Strategy: AI-assisted modular build with MCP (Model Context Protocol) orchestration; Phase 1 MVP with focused local processing and targeted API use for advanced features.

1\. Updated Vision

To build a modular, privacy-first (with considerations for MVP demo needs), and context-aware system that transforms chaotic, real-world documents—medical, legal, operational—into structured, actionable insight. IDIS, powered by a lightweight Model Context Protocol (MCP) Host (conceptually for Phase 1, explicitly in later phases), will orchestrate intelligent micro-agents to perform document classification, summarization, tagging, discrepancy detection (future), and smart filing, all on user-controlled infrastructure.

2\. Why This Matters

Modern practices (medical, legal, care-based) are overwhelmed with fragmented records and ad hoc documents. Traditional systems (EHRs, DMS, cloud tools) fail to:

* Integrate unstructured documents meaningfully  
* Respect user data control and sovereignty (primary long-term goal)  
* Automate narrative and cross-record understanding IDIS aims to solve this through intelligent, edge-deployable middleware that augments—not replaces—existing systems.

3\. High-Level System Structure

Key Components:

* **MCP Host (Controller):**  
  * Orchestrates tasks across micro-agents.  
  * Manages shared context, memory, routing, and permissions.  
  * *Note for Phase 1 MVP:* The full MCP Host is not explicitly built as a separate, complex orchestrator. A script (run\_mvp.py) will sequentially call agents. Permissions logic will be designed (permissions.py) but will have limited enforcement points in the automated MVP pipeline, which will run with a default all-access user role.  
* **Context Store:**  
  * An SQLite database tracking patient/user, session metadata, document details (including extracted text and rich metadata), agent state, and prior outputs.  
* **Permissions Model:**  
  * Governs who/what can access/route data (by privacy level, role, agent type) via a JSON configuration file.  
* **Micro Agents:**  
  * Modular, callable Python services: ingestion\_agent.py, summarizer\_agent.py, classifier\_agent.py, tagger\_agent.py, etc.  
  * Each has a structured input/output API and interacts with the Context Store.  
* **Audit Log:**  
  * A dedicated SQLite table within the Context Store, recording all key task flows, agent actions, data access/modifications, and decisions, supporting chain of custody and access auditing.

4\. Core MVP Workflow (Phase 1\)

User Input: Document batches dropped into an input folder (hardcoded "watchfolder" path for MVP) or uploaded via UI (future).

* **Ingestion (**ingestion\_agent.py**):**  
  * Monitors the "watchfolder."  
  * Handles various file types:  
    * PDFs: Uses PyMuPDF (Fitz) for direct text extraction first; if image-based, uses Tesseract OCR (via pytesseract). Configurable for multiple languages (default 'eng').  
    * DOCX: Uses python-docx for text extraction.  
    * TXT: Uses standard Python I/O.  
    * Images (PNG, JPG, etc.): Uses Tesseract OCR.  
  * Stores extracted text and initial metadata (filename, original type, timestamp, OCR confidence where applicable (0-100%), 100% confidence for direct extraction) into the Context Store.  
  * Problematic files (corrupted, password-protected) are flagged, status updated in Context Store, and moved to a "holding folder."  
* **Context Initialization:** Metadata extracted during ingestion (including patient\_id if provided for the batch) is stored in the Context Store.  
* **Classification (**classifier\_agent.py**):**  
  * Reads extracted text from the Context Store.  
  * For MVP, uses a local, Python-based keyword-matching approach (not GPT-4o).  
  * Assigns a document\_type label from a defined list for MVP (e.g., "Invoice," "Insurance Document," "Letter," "Medical Record," "Receipt," "Legal Document," "Report," "Unclassified").  
  * Assigns a classification\_confidence ("Low," "Medium," "High") based on keyword matching rules.  
  * Stores results back to the Context Store.  
* **Summarization (**summarizer\_agent.py**):**  
  * Fetches extracted text and classification from the Context Store.  
  * For Phase 1 MVP demo, calls the OpenAI GPT-4o API.  
  * Generates brief (2-3 sentence) per-document narrative summaries and a brief batch-level overview summary.  
  * Style: Neutral, fact-based, no advice/diagnosis.  
  * Stores summaries and a confidence metric (indicating successful LLM execution) in the Context Store.  
* **Tagging \+ Filing (**tagger\_agent.py**):**  
  * Works from the full extracted\_text in the Context Store.  
  * Uses local Python libraries (e.g., regex, spaCy) with a hybrid-ready design for future LLM integration.  
  * Extracts key metadata: date\_detected (various relevant dates and their context), issuer/source, recipient, and predefined tags (e.g., "urgent," "confidential").  
  * Stores this rich metadata in the Context Store.  
  * Moves original files to a structured archive folder (e.g., /\<base\_folder\>/\<context\_segment\>/\<year\>/\<month\>/\<doc\_id\>\_\<filename\>) and updates filed\_path in Context Store.  
* **Output (**SmartCoverSheetRenderer.py**):**  
  * Aggregates batch summaries and key metadata from the Context Store.  
  * Generates a Markdown and then PDF cover sheet (stylized text IDIS branding, document count, batch summary, structured metadata index for batch contents). Agent selects a suitable Markdown-to-PDF library.  
* **Logging (**audit\_log.py**):** Audit entry created in the SQLite audit\_trail table for key data access/modifications, agent actions, and decisions, including timestamp, user\_id, event\_type, resource\_id, status, and details.

5\. Example Micro Agent Definition (JSON-style)

(This general structure remains a good example for defining agent capabilities, inputs, and outputs for future reference or more dynamic loading).

JSON

{  
  "agent\_id": "summarizer\_agent\_v1",  
  "input\_type": \["text\_content\_reference", "classification\_data"\],  
  "output\_type": \["document\_summary\_reference", "batch\_summary\_reference"\],  
  "can\_run\_locally": false, // For MVP, if using cloud LLM for summarization  
  "requires\_context": true,  
  "description": "Generates structured summaries for documents or batches using an external LLM service."  
}

**6\. Core Design Principles**

* **Local-First & Privacy-Centric:** Primary long-term goal. No PHI leaves the system by default in production.  
  * *Clarification for Phase 1 MVP Demo:* The summarizer\_agent.py will utilize the OpenAI GPT-4o API, requiring an internet connection. For this specific demo phase, data sent for summarization is handled with the understanding that this is for demonstration of capability, and future production versions would offer fully local/private LLM options or make external LLM use explicit and optional with user consent, potentially via a cloud\_delegate\_agent.  
* **Composable & Modular:** Agents are independently testable and replaceable.  
* **Contextual & Intelligent:** Each action is informed by prior steps and stored memory.  
* **Scalable by Design:** Works for individuals, clinics, or multi-user consulting platforms (future).  
* **Audit-Ready & Explainable:** Full trace of what was done and why, via the Audit Log.

7\. Sample Deployment Scenarios

(Likely still accurate for long-term vision).

| Scenario | Description |

|--------------------------|-------------------------------------------------|

| Solo Clinician (Offline) | Processes referrals and notes on a NUC workstation |

| Legal Consultant | Prepares document packets for review/court |

| Caregiver Agent Model | Uses IDIS to organize and track elder records |

| RPM Integration (Future) | Adds wearable & device data to records context |

8\. Updated Development Plan

Phase 1: MVP (You Are the First Client)

\* Implement Core Agents:

\* ingestion\_agent.py: Handles PDF (PyMuPDF/Tesseract), DOCX, TXT, Image (Tesseract) ingestion; stores extracted text and basic metadata.

\* classifier\_agent.py: Local Python keyword-based classification into defined types (Invoice, Letter, Medical Record, etc.) with Low/Medium/High confidence.

\* summarizer\_agent.py: Uses OpenAI GPT-4o API (for MVP demo) for per-document and batch summaries.

\* tagger\_agent.py: Local Python-based extraction of key metadata (date\_detected, issuer/source, recipient, predefined tags); handles file archiving.

\* Implement Core Modules:

\* context\_store.py: SQLite database module with defined schema (tables for patients, sessions, documents with rich metadata fields, agent\_outputs) and CRUD methods.

\* permissions.py: Defines generic roles for MVP (admin, editor, viewer) and privacy levels (Highly Confidential, Confidential, General) with rules in a JSON config file. MVP assumes a default "all access" role for pipeline runs; full enforcement deferred but logic will be testable.

\* audit\_log.py: Logs to a dedicated SQLite table (audit\_trail) key data access/modifications, agent actions, with fields supporting chain of custody and access auditing.

\* Implement Output Generation:

\* SmartCoverSheetRenderer.py: Generates Markdown and PDF cover sheets with agreed content (branding, counts, summaries, metadata index).

\* Testing:

\* Unit tests for each module.

\* Automated end-to-end test (tests/test\_end\_to\_end.py) using dynamically generated mock/dummy files for consistent pipeline validation. User acceptance testing on real documents is a separate, valuable step.

Phase 2: Expand to Consulting Model  
\* Build web UI \+ dashboard  
\* Multi-user routing  
\* Add controlled cloud processing via \`cloud\_delegate\_agent\`

Phase 3: Domain Generalization  
\* Add legal, financial, and operational schemas  
\* Build custom pipelines with same MCP core

**9\. Codex/LLM Usage**

* For Phase 1 MVP:  
  * Use **GPT-4o (via API call)** for:  
    * **Summarization** (summarizer\_agent.py).  
  * **Classification** (classifier\_agent.py) will be handled by a **local, keyword-based Python agent** for MVP. GPT-4o for classification is a potential future enhancement.  
  * **Tagging/Entity Extraction** (tagger\_agent.py) will use **local Python libraries (regex, spaCy, etc.)** for MVP. A hybrid approach with LLM assistance is a potential future enhancement.  
  * Discrepancy detection (future).  
* Use Codex-style instructions (our detailed task breakdowns) to generate modular Python agents and config readers.  
* Avoid AI handling of permission logic—enforce that at the MCP Host level (conceptually) or via permissions.py logic.

10\. Deliverables for Replit Agent (for building Phase 1 MVP)

(This section describes what the Replit agent will create based on our detailed instructions, or what config files it might need to generate/use).

* Python source files for all agents and modules (e.g., context\_store.py, ingestion\_agent.py, permissions.py, run\_mvp.py, etc.).  
* Associated unit test files (e.g., test\_context\_store.py).  
* Configuration files to be created or used:  
  * permissions\_rules.json (defines roles and access rules).  
  * Potentially a main app\_config.yaml (for paths like watchfolder, base filed folder, SQLite DB path).  
* The SQLite database file itself will be created and populated during runtime.  
* Sample dynamically generated documents for end-to-end testing.  
* Generated Markdown and PDF cover sheets as output examples.

11\. HIM Extensions & Governance

(This section outlines future capabilities. The Phase 1 Context Store schema for metadata – document\_type, classification\_confidence, document\_dates, issuer\_source, recipient, tags\_extracted – is designed to support and align with these future Search & Retrieval APIs and Reporting & Audit Endpoints.)

11.1 Document Retention & Archiving  
\* Configurable retention policies (e.g., 7-year medical, 10-year legal hold)  
\* Automated archival of expired records to cold storage  
\* Retention rule engine with audit trail of purged or archived items

11.2 Search & Retrieval APIs  
\* Full-text search over extracted OCR text and summaries (SQLite FTS capability to be leveraged).  
\* Faceted search by patient, document type, date range, tags.  
\* REST/gRPC endpoints for integration in web or desktop clients.

11.3 Integration Connectors  
\* EHR Connectors: FHIR® DocumentReference and Bundle exports/imports  
\* DMS Connectors: RESTful ingestion and export for non-clinical clients  
\* Upstream Watchers: Folder or inbox monitors for automated ingestion

11.4 Reporting & Audit Endpoints  
\* Batch processing metrics (volumes, error rates, throughput)  
\* Discrepancy and quality assurance reports  
\* Audit logs accessible via API for compliance and discovery

11.5 Event Hooks & Webhooks  
\* Webhooks for key events (batch completed, discrepancy flagged, retention triggered)  
\* Customizable event subscribers for external systems (care coordination portals, notification services)

