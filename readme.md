# QuantaIQ / IDIS: The Intelligent Document Insight System

**Status:** V2.0 Backend Complete - UI Development Phase (As of June 22, 2025)

---

## 1. Vision & Mission

* **Vision:** To create a "Swiss Army knife" for document intelligence. To transform the "digital black hole" of personal and small business documents into a structured, searchable, and intelligent knowledge base. The long-term vision is a turnkey, plug-and-play **Intelligent Document Appliance**.
* **Mission:** To turn unstructured noise into structured knowledge. The system must be private (local-first), user-friendly, and highly automated.

## 2. Core Architecture (Current)

The IDIS project has successfully pivoted to a modern, AI-first architecture that replaces brittle, rule-based agents with a single, powerful cognitive engine.

* **Unified Cognitive Agent:** A central agent (`CognitiveAgent`) leverages a Large Language Model (LLM, e.g., GPT-4o) via a master prompt to extract a rich, structured JSON object from any document text.
* **Hybrid Database Schema:** The `ContextStore` (SQLite) is designed with a hybrid model. It stores the full JSON in a dedicated `extracted_data` column for rich, forward-looking analysis, while also populating a few key "legacy" columns to maintain compatibility with the existing UI.
* **Human-in-the-Loop (HITL) Workflow:** The system has a complete backend workflow to handle ambiguous documents (e.g., receipts, invoices). It automatically flags these documents with a `pending_categorization` status, queuing them for simple, one-click user review to assign them to the correct context (e.g., a specific property or business).
* **Modular, Agent-Based Design:** The system is composed of distinct agents (`UnifiedIngestionAgent`, `CognitiveAgent`) and a central `ContextStore`, allowing for maintainable and scalable development.
* **Local-First Privacy Focus:** The core design principle is that all user documents and the primary database are stored locally on the user's hardware, ensuring privacy and control.

## 3. Current Phase: V1 UI Development

With the backend foundation and core data pipeline now complete, stable, and tested, the project is officially entering the UI development phase. The immediate next steps are to build the user-facing features that leverage the new intelligent backend.

* **Implement the HITL "Needs Review" Screen:** Build the UI that allows the user to easily categorize documents flagged as `pending_categorization`.
* **Upgrade the Main Document View:** Enhance the UI to display the rich, structured data contained within the `extracted_data` JSON field.
* **Design and Build the V1 Chatbot:** Create the first version of the conversational interface that can query the structured data in the `ContextStore`.

## 4. Future Vision (Phase 2 & Beyond)

* **Full RAG Implementation:** Add an **`EmbeddingAgent`** and a local **Vector DB** (e.g., ChromaDB) to enable true semantic search across all document text.
* **Learning HITL System:** Evolve the Human-in-the-Loop system to learn from user choices, making intelligent suggestions and eventually automating categorization for recurring document types.
* **Advanced Cognitive Interface:** Evolve the UI into a comprehensive dashboard with proactive insights, data visualizations, and advanced analytics.
* **Hardware Appliance:** Package the entire software stack (via Docker) onto a dedicated Mini PC with a scanner and touchscreen to create the final turnkey QuantaIQ product.
