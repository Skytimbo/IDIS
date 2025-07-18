"""
Admin Panel Module for IDIS Demo Management
Provides password-protected admin functionality for demo management.
"""

import streamlit as st
import sqlite3
import shutil
import os
from datetime import datetime
import logging
from context_store import ContextStore

# Simple password (in production, use proper authentication)
ADMIN_PASSWORD = "admin123"

def check_admin_password():
    """Check if admin password is correct"""
    if 'admin_authenticated' not in st.session_state:
        st.session_state.admin_authenticated = False
    
    if not st.session_state.admin_authenticated:
        st.title("🔧 Admin Panel")
        st.markdown("---")
        st.warning("Admin authentication required")
        
        password = st.text_input("Enter admin password:", type="password")
        
        if st.button("Login"):
            if password == ADMIN_PASSWORD:
                st.session_state.admin_authenticated = True
                st.success("Authentication successful!")
                st.rerun()
            else:
                st.error("Incorrect password")
                return False
        return False
    
    return True

def get_database_stats(db_path):
    """Get basic statistics about a database"""
    try:
        if not os.path.exists(db_path):
            return {"exists": False}
        
        context_store = ContextStore(db_path)
        cursor = context_store.conn.cursor()
        
        # Get table counts
        stats = {"exists": True}
        
        # Count entities
        cursor.execute("SELECT COUNT(*) FROM entities")
        stats["entities"] = cursor.fetchone()[0]
        
        # Count cases
        cursor.execute("SELECT COUNT(*) FROM cases")
        stats["cases"] = cursor.fetchone()[0]
        
        # Count documents
        cursor.execute("SELECT COUNT(*) FROM documents")
        stats["documents"] = cursor.fetchone()[0]
        
        # Get file size
        stats["file_size"] = round(os.path.getsize(db_path) / (1024 * 1024), 2)  # MB
        
        context_store.conn.close()
        return stats
        
    except Exception as e:
        return {"exists": True, "error": str(e)}

def reset_demo_database():
    """Reset the demo database to pristine state"""
    try:
        # Remove existing demo database
        if os.path.exists("demo_idis.db"):
            os.remove("demo_idis.db")
            st.success("Existing demo database removed")
        
        # Run the demo database creation script
        import subprocess
        result = subprocess.run(["python", "create_demo_database.py"], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            st.success("Demo database reset successfully!")
            st.info("Demo database now contains fresh sample data")
        else:
            st.error(f"Error resetting demo database: {result.stderr}")
            
    except Exception as e:
        st.error(f"Error during demo reset: {str(e)}")

def switch_database_mode(new_mode):
    """Switch between demo and production database modes"""
    try:
        if new_mode == "demo":
            st.session_state.database_path = "demo_idis.db"
            st.session_state.archive_path = "data/demo_archive"
        else:
            st.session_state.database_path = "production_idis.db"
            st.session_state.archive_path = "data/archive"
        
        st.success(f"Switched to {new_mode} mode")
        st.info("Please refresh the page to apply changes")
        
    except Exception as e:
        st.error(f"Error switching database mode: {str(e)}")

def render_admin_panel():
    """Render the admin panel interface"""
    if not check_admin_password():
        return
    
    st.title("🔧 Admin Panel")
    st.markdown("---")
    
    # Current Status Section
    st.subheader("📊 Current Status")
    
    current_db = st.session_state.get('database_path', 'production_idis.db')
    current_mode = "Demo" if "demo" in current_db else "Production"
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Current Mode", current_mode)
        st.metric("Database Path", current_db)
    
    with col2:
        st.metric("Session Active", "Yes" if st.session_state.admin_authenticated else "No")
        st.metric("Last Updated", datetime.now().strftime("%H:%M:%S"))
    
    st.markdown("---")
    
    # Database Statistics
    st.subheader("📈 Database Statistics")
    
    demo_stats = get_database_stats("demo_idis.db")
    prod_stats = get_database_stats("production_idis.db")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Demo Database**")
        if demo_stats["exists"]:
            if "error" in demo_stats:
                st.error(f"Error: {demo_stats['error']}")
            else:
                st.write(f"• Entities: {demo_stats['entities']}")
                st.write(f"• Cases: {demo_stats['cases']}")
                st.write(f"• Documents: {demo_stats['documents']}")
                st.write(f"• File Size: {demo_stats['file_size']} MB")
        else:
            st.warning("Demo database not found")
    
    with col2:
        st.markdown("**Production Database**")
        if prod_stats["exists"]:
            if "error" in prod_stats:
                st.error(f"Error: {prod_stats['error']}")
            else:
                st.write(f"• Entities: {prod_stats['entities']}")
                st.write(f"• Cases: {prod_stats['cases']}")
                st.write(f"• Documents: {prod_stats['documents']}")
                st.write(f"• File Size: {prod_stats['file_size']} MB")
        else:
            st.warning("Production database not found")
    
    st.markdown("---")
    
    # Database Management Section
    st.subheader("🗄️ Database Management")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Switch Database Mode**")
        new_mode = st.radio(
            "Select database mode:",
            ["demo", "production"],
            index=0 if current_mode == "Demo" else 1
        )
        
        if st.button("Switch Mode", type="primary"):
            if new_mode != current_mode.lower():
                switch_database_mode(new_mode)
            else:
                st.info("Already in selected mode")
    
    with col2:
        st.markdown("**Demo Management**")
        st.warning("This will completely reset the demo database!")
        
        if st.button("Reset Demo Database", type="secondary"):
            with st.spinner("Resetting demo database..."):
                reset_demo_database()
    
    st.markdown("---")
    
    # System Actions
    st.subheader("⚙️ System Actions")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Clear Session State"):
            # Clear all session state except admin authentication
            keys_to_keep = ['admin_authenticated']
            keys_to_remove = [key for key in st.session_state.keys() if key not in keys_to_keep]
            for key in keys_to_remove:
                del st.session_state[key]
            st.success("Session state cleared")
    
    with col2:
        if st.button("Logout"):
            st.session_state.admin_authenticated = False
            st.success("Logged out successfully")
            st.rerun()
    
    st.markdown("---")
    
    # System Information
    st.subheader("ℹ️ System Information")
    
    info_col1, info_col2 = st.columns(2)
    
    with info_col1:
        st.write("**File System**")
        st.write(f"• Current working directory: {os.getcwd()}")
        st.write(f"• Demo archive exists: {os.path.exists('data/demo_archive')}")
        st.write(f"• Production archive exists: {os.path.exists('data/archive')}")
    
    with info_col2:
        st.write("**Session Info**")
        st.write(f"• Session items: {len(st.session_state)}")
        st.write(f"• Admin authenticated: {st.session_state.admin_authenticated}")
        st.write(f"• Current database: {st.session_state.get('database_path', 'Not set')}")