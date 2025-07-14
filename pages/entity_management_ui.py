"""
Entity Management UI Module for IDIS

This module provides a Streamlit interface for managing entities in the IDIS system.
Users can view all existing entities and create new ones through a simple interface.
"""

import streamlit as st
import pandas as pd
from context_store import ContextStore

def render_entity_management_page():
    """
    Main function to render the Entity Management UI.
    """

    st.title("🏢 Entity & Case Management")
    st.markdown("---")

    try:
        context_store = ContextStore("production_idis.db")

        # Display existing entities
        st.subheader("📋 Existing Entities")

        entities = context_store.get_all_entities()

        if entities:
            entities_df = pd.DataFrame(entities)
            # Rename columns for a professional display
            display_df = entities_df.rename(columns={
                'id': 'Entity ID',
                'entity_name': 'Entity Name',
                'creation_timestamp': 'Created',
                'last_modified_timestamp': 'Last Modified'
            })
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True
            )
            st.info(f"Total entities: {len(entities)}")
        else:
            st.info("No entities found. Add one below to get started.")

        # Add new entity section
        st.markdown("---")
        st.subheader("➕ Add New Entity")

        with st.form("add_entity_form", clear_on_submit=True):
            entity_name = st.text_input(
                "Entity Name",
                placeholder="Enter the name of the new entity (e.g., John Doe)",
            )

            submitted = st.form_submit_button("Add New Entity")

            if submitted and entity_name.strip():
                try:
                    entity_id = context_store.add_entity({'entity_name': entity_name.strip()})
                    st.success(f"✅ Successfully added entity: '{entity_name}' (ID: {entity_id})")
                    # Rerun to refresh the entity list
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"❌ Error adding entity: {str(e)}")
            elif submitted:
                st.warning("⚠️ Please enter a valid entity name.")

    except Exception as e:
        st.error(f"❌ Database connection error: {str(e)}")
        st.info("Please ensure the database file exists and is accessible.")

if __name__ == "__main__":
    render_entity_management_page()