"""
QuantaIQ/IDIS - Main Application Router
This Streamlit application serves as the main entry point and shell for various
document intelligence modules. It uses a sidebar to switch between different tools.
"""

import streamlit as st

# --- Page Configuration (Must be first Streamlit command) ---
st.set_page_config(
    page_title="QuantaIQ Intelligence Platform",
    page_icon="🧠",
    layout="centered",
    initial_sidebar_state="expanded"
)

import os
import sys

# --- Local Module Imports ---
# Import the UI functions from the different modules
from modules.search_ui import render_search_ui
from modules.medicaid_navigator.ui import render_navigator_ui
from quanta_ui.pages.needs_review_ui import render_needs_review_page
from modules.user_journey_visualizer import render_user_journey_visualizer

# --- Main Application Router ---
def main():
    """
    Main function to render the application shell and route to the selected module.
    """
    st.sidebar.title("QuantaIQ / IDIS")
    st.sidebar.markdown("---")

    # Module selection in the sidebar
    module_selection = st.sidebar.selectbox(
        "Select a Tool",
        ("General Document Search", "Medicaid Navigator", "Needs Review (HITL)", "User Journey Progress")
    )

    st.sidebar.markdown("---")

    # --- Routing Logic ---
    # Based on the user's selection, call the appropriate render function
    if module_selection == "General Document Search":
        render_search_ui()
    elif module_selection == "Medicaid Navigator":
        render_navigator_ui()
    elif module_selection == "Needs Review (HITL)":
        render_needs_review_page()
    elif module_selection == "User Journey Progress":
        render_user_journey_visualizer()
    else:
        st.error("An unexpected error occurred. Please select a valid module.")

if __name__ == "__main__":
    main()