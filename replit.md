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

The application is containerized and designed for a one-step launch.

1.  Ensure Docker is installed and running.
2.  Set the `OPENAI_API_KEY` in your environment.
3.  Run the deployment script: `./deploy.sh`

## 7. Product Roadmap

### Phase 1: UI Polish & Core Workflow Hardening (Current Focus)
- [x] Implement the "Active Case Dashboard".
- [x] Build FastAPI Layer for backend decoupling and scalability.
- [ ] Refine the UI with a "Two-Panel" layout and contextual guidance.
- [ ] Build the "Generate Application Packet" feature.
- [ ] Address medium/low priority issues from CodeRabbit review (e.g., harden `deploy.sh`, improve exception handling).

### Phase 2: RAG & Conversational Intelligence
- [ ] Implement the `RetrievalEmbedder` model and a vector database.
- [ ] Build a conversational chat interface for asking natural language questions about the document archive.

### Phase 3: The Private AI Appliance
- [ ] Fine-tune a 7B-parameter local LLM to replace the cloud API dependency, making the appliance fully self-contained.
- [ ] Design and prototype the physical hardware shell.








