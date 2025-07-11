"""
Entity Management UI for IDIS
Allows users to create and manage entity records for case management.
"""

import streamlit as st
import sqlite3
from datetime import datetime
import logging
from context_store import ContextStore

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def render_entity_management_page():
    """Main function to render the entity management interface."""
    st.title("Entity & Case Management")
    st.markdown("---")
    
    # Initialize context store
    try:
        cs = ContextStore("production_idis.db")
    except Exception as e:
        st.error(f"Database connection failed: {str(e)}")
        return
    
    # Display existing entities
    st.subheader("Existing Entities")
    
    try:
        # Get all entities from the database
        entities = get_all_entities(cs)
        
        if entities:
            # Display entities in a table format
            st.dataframe(entities, use_container_width=True)
        else:
            st.info("No entities found in the system.")
    
    except Exception as e:
        st.error(f"Error loading entities: {str(e)}")
        logger.error(f"Error loading entities: {str(e)}")
    
    st.markdown("---")
    
    # Add new entity section
    st.subheader("Add New Entity")
    
    with st.form("add_entity_form"):
        entity_name = st.text_input(
            "Entity Name",
            placeholder="Enter entity name (person, organization, etc.)",
            help="Enter the name of the entity"
        )
        
        submitted = st.form_submit_button("Add New Entity")
        
        if submitted:
            if entity_name.strip():
                try:
                    # Create new entity record
                    entity_data = {
                        "entity_name": entity_name.strip()
                    }
                    
                    entity_id = cs.add_entity(entity_data)
                    
                    st.success(f"Entity '{entity_name}' added successfully with ID: {entity_id}")
                    logger.info(f"Created new entity: {entity_name} (ID: {entity_id})")
                    
                    # Rerun to refresh the entity list
                    st.experimental_rerun()
                    
                except Exception as e:
                    st.error(f"Error adding entity: {str(e)}")
                    logger.error(f"Error adding entity {entity_name}: {str(e)}")
            else:
                st.warning("Please enter a valid entity name.")

def get_all_entities(context_store):
    """
    Retrieve all entities from the database.
    
    Args:
        context_store: ContextStore instance
        
    Returns:
        List of entity dictionaries
    """
    try:
        cursor = context_store.conn.cursor()
        cursor.execute("""
            SELECT id, entity_name, creation_timestamp 
            FROM entities 
            ORDER BY creation_timestamp DESC
        """)
        
        entities = []
        for row in cursor.fetchall():
            entities.append({
                "ID": row[0],
                "Entity Name": row[1],
                "Created": row[2]
            })
        
        return entities
        
    except Exception as e:
        logger.error(f"Error retrieving entities: {str(e)}")
        raise

if __name__ == "__main__":
    render_entity_management_page()