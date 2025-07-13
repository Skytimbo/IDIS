"""
Entity Management UI Module for IDIS

This module provides a Streamlit interface for managing entities in the IDIS system.
Users can view all existing entities and create new ones through a simple interface.
"""

import streamlit as st
import pandas as pd
import os
from context_store import ContextStore


def get_database_path():
    """Get the database path from command line arguments or default."""
    import sys
    if len(sys.argv) > 1:
        # Check if --database-path is provided
        for i, arg in enumerate(sys.argv):
            if arg == '--database-path' and i + 1 < len(sys.argv):
                return sys.argv[i + 1]
    return 'production_idis.db'


def render_entity_management_ui():
    """
    Main function to render the Entity Management UI.
    
    This function creates the Streamlit interface for viewing and managing entities,
    including a data table for existing entities and a form for creating new ones.
    """
    
    # Page header
    st.title("🏢 Entity Management")
    st.markdown("---")
    
    # Get database path and initialize context store
    db_path = get_database_path()
    
    try:
        context_store = ContextStore(db_path)
        
        # Display existing entities
        st.subheader("📋 Existing Entities")
        
        # Load entities from database
        entities = context_store.get_all_entities()
        
        if entities:
            # Convert to DataFrame for display
            entities_df = pd.DataFrame(entities)
            
            # Format the DataFrame for better display
            if not entities_df.empty:
                # Rename columns for better display
                display_df = entities_df.rename(columns={
                    'id': 'Entity ID',
                    'entity_name': 'Entity Name',
                    'creation_timestamp': 'Created',
                    'last_modified_timestamp': 'Last Modified'
                })
                
                # Display the dataframe
                st.dataframe(
                    display_df,
                    use_container_width=True
                )
                
                st.info(f"Total entities: {len(entities)}")
        else:
            st.info("No entities found in the database.")
        
        # Add new entity section
        st.markdown("---")
        st.subheader("➕ Add New Entity")
        
        # Create form for adding new entity
        with st.form("add_entity_form"):
            entity_name = st.text_input(
                "Entity Name",
                placeholder="Enter the name of the new entity",
                help="Enter a unique name for the entity (e.g., 'John Doe', 'Acme Corporation')"
            )
            
            submitted = st.form_submit_button("Add New Entity")
            
            if submitted:
                if entity_name and entity_name.strip():
                    try:
                        # Add entity to database
                        entity_id = context_store.add_entity(entity_name.strip())
                        
                        # Show success message
                        st.success(f"✅ Successfully added entity: '{entity_name}' (ID: {entity_id})")
                        
                        # Refresh the page to show the new entity
                        st.experimental_rerun()
                        
                    except Exception as e:
                        st.error(f"❌ Error adding entity: {str(e)}")
                else:
                    st.warning("⚠️ Please enter a valid entity name.")
        
        # Usage instructions
        st.markdown("---")
        st.subheader("ℹ️ Usage Instructions")
        st.markdown("""
        - **View Entities**: All entities are displayed in the table above
        - **Add Entity**: Use the form to create a new entity
        - **Entity Names**: Should be unique and descriptive (e.g., person names, organization names)
        - **Auto-Refresh**: The page will automatically refresh after adding a new entity
        """)
        
    except Exception as e:
        st.error(f"❌ Database connection error: {str(e)}")
        st.info("Please ensure the database file exists and is accessible.")


if __name__ == "__main__":
    render_entity_management_ui()