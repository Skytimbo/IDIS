# quanta_ui/app.py

import streamlit as st

# Note: set_page_config() is now handled by the main app.py router

st.title("Welcome to QuantaIQ / IDIS 🧠")
st.header("The Intelligent Document Insight System")

st.markdown("""
This is the central interface for the QuantaIQ system. Use the navigation sidebar on the left to access different modules.

### Current Status
- **Backend Services:** Operational
- **Document Ingestion:** Active
- **UI Development:** In Progress

### Next Steps
- Implement the 'Needs Review' screen for document categorization.
- Build out the main document search and viewer dashboard.
- Design and implement the V1 Chatbot interface.
""")

st.sidebar.success("Select a module above to begin.")