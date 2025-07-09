"""
User Journey Progress Visualizer Module for IDIS

This module provides visual tracking of user progress through document processing
workflows, showing completed steps, current position, and remaining tasks.
"""

import streamlit as st
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import json

class UserJourneyVisualizer:
    """
    Visualizes user progress through document processing workflows.
    
    Tracks user actions, document processing stages, and provides
    visual feedback on progress through various IDIS workflows.
    """
    
    def __init__(self, db_path: str):
        """
        Initialize the User Journey Visualizer.
        
        Args:
            db_path: Path to the SQLite database
        """
        self.db_path = db_path
        
        # Define workflow stages for different document types
        self.workflow_stages = {
            "document_upload": [
                {"id": "upload", "name": "Upload Document", "description": "Document uploaded to system"},
                {"id": "ingestion", "name": "Text Extraction", "description": "Extract text content from document"},
                {"id": "classification", "name": "AI Classification", "description": "Classify document type and content"},
                {"id": "review", "name": "Human Review", "description": "Manual review if needed"},
                {"id": "filing", "name": "Archive & File", "description": "Store document in organized structure"},
                {"id": "complete", "name": "Complete", "description": "Document processing finished"}
            ],
            "search_workflow": [
                {"id": "search_start", "name": "Search Query", "description": "Enter search terms"},
                {"id": "results_display", "name": "View Results", "description": "Browse search results"},
                {"id": "document_view", "name": "Document Access", "description": "Open and view document"},
                {"id": "search_complete", "name": "Search Complete", "description": "Found desired information"}
            ],
            "medicaid_navigation": [
                {"id": "upload_docs", "name": "Upload Documents", "description": "Upload Medicaid-related documents"},
                {"id": "ai_analysis", "name": "AI Analysis", "description": "Analyze documents for Medicaid relevance"},
                {"id": "categorization", "name": "Categorize", "description": "Organize by Medicaid program type"},
                {"id": "insights", "name": "Generate Insights", "description": "Provide actionable recommendations"},
                {"id": "export", "name": "Export Results", "description": "Download organized results"}
            ]
        }
    
    def get_user_progress(self, user_id: str = "default_user", workflow_type: str = "document_upload") -> Dict[str, Any]:
        """
        Get current user progress for a specific workflow.
        
        Args:
            user_id: User identifier
            workflow_type: Type of workflow to track
            
        Returns:
            Dictionary containing progress information
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get recent user activity
            cursor.execute("""
                SELECT event_type, event_name, timestamp, details, status
                FROM audit_log 
                WHERE user_id = ? 
                ORDER BY timestamp DESC 
                LIMIT 50
            """, (user_id,))
            
            recent_activity = cursor.fetchall()
            
            # Get document processing statistics
            cursor.execute("""
                SELECT processing_status, COUNT(*) as count
                FROM documents 
                GROUP BY processing_status
            """)
            
            processing_stats = dict(cursor.fetchall())
            
            # Get session activity
            cursor.execute("""
                SELECT COUNT(*) as session_count,
                       MAX(created_at) as last_activity
                FROM sessions
            """)
            
            session_info = cursor.fetchone()
            
            conn.close()
            
            # Determine current stage based on recent activity
            current_stage = self._determine_current_stage(recent_activity, workflow_type)
            
            return {
                "user_id": user_id,
                "workflow_type": workflow_type,
                "current_stage": current_stage,
                "recent_activity": recent_activity,
                "processing_stats": processing_stats,
                "session_count": session_info[0] if session_info else 0,
                "last_activity": session_info[1] if session_info else None,
                "workflow_stages": self.workflow_stages.get(workflow_type, [])
            }
            
        except Exception as e:
            st.error(f"Error getting user progress: {str(e)}")
            return {
                "user_id": user_id,
                "workflow_type": workflow_type,
                "current_stage": "upload",
                "recent_activity": [],
                "processing_stats": {},
                "session_count": 0,
                "last_activity": None,
                "workflow_stages": self.workflow_stages.get(workflow_type, [])
            }
    
    def _determine_current_stage(self, recent_activity: List[tuple], workflow_type: str) -> str:
        """
        Determine the current stage based on recent user activity.
        
        Args:
            recent_activity: List of recent activity tuples
            workflow_type: Type of workflow
            
        Returns:
            Current stage identifier
        """
        if not recent_activity:
            return "upload"
        
        # Map activity to workflow stages
        stage_mapping = {
            "document_upload": {
                "DATA_ACCESS": "ingestion",
                "AGENT_ACTIVITY": "classification", 
                "DOCUMENT_PROCESSING": "review",
                "FILE_OPERATION": "filing",
                "UPLOAD_DOCUMENT": "upload"
            },
            "search_workflow": {
                "SEARCH_QUERY": "search_start",
                "SEARCH_RESULTS": "results_display",
                "DOCUMENT_ACCESS": "document_view",
                "DATA_ACCESS": "document_view"
            },
            "medicaid_navigation": {
                "UPLOAD": "upload_docs",
                "AI_ANALYSIS": "ai_analysis",
                "CATEGORIZATION": "categorization",
                "DOCUMENT_PROCESSING": "insights"
            }
        }
        
        # Find the most recent relevant activity
        for activity in recent_activity:
            event_type = activity[0]
            if event_type in stage_mapping.get(workflow_type, {}):
                return stage_mapping[workflow_type][event_type]
        
        return "upload"
    
    def render_progress_visualization(self, user_id: str = "default_user", workflow_type: str = "document_upload"):
        """
        Render the progress visualization in Streamlit.
        
        Args:
            user_id: User identifier
            workflow_type: Type of workflow to visualize
        """
        st.subheader("📊 Your Progress Journey")
        
        # Get user progress data
        progress_data = self.get_user_progress(user_id, workflow_type)
        
        # Workflow type selector
        col1, col2 = st.columns([2, 1])
        with col1:
            selected_workflow = st.selectbox(
                "Select Workflow to Track",
                options=list(self.workflow_stages.keys()),
                format_func=lambda x: x.replace('_', ' ').title(),
                index=list(self.workflow_stages.keys()).index(workflow_type)
            )
        
        with col2:
            if st.button("🔄 Refresh Progress"):
                st.rerun()
        
        # Update progress data if workflow changed
        if selected_workflow != workflow_type:
            progress_data = self.get_user_progress(user_id, selected_workflow)
        
        # Render progress steps
        self._render_progress_steps(progress_data)
        
        # Render activity summary
        self._render_activity_summary(progress_data)
        
        # Render statistics
        self._render_statistics(progress_data)
    
    def _render_progress_steps(self, progress_data: Dict[str, Any]):
        """
        Render the visual progress steps.
        
        Args:
            progress_data: Progress data dictionary
        """
        st.markdown("### 🎯 Current Progress")
        
        stages = progress_data["workflow_stages"]
        current_stage = progress_data["current_stage"]
        
        if not stages:
            st.warning("No workflow stages defined for this workflow type.")
            return
        
        # Calculate progress percentage
        current_index = next((i for i, stage in enumerate(stages) if stage["id"] == current_stage), 0)
        progress_percentage = (current_index + 1) / len(stages)
        
        # Show overall progress bar
        st.progress(progress_percentage, text=f"Overall Progress: {progress_percentage:.0%}")
        
        # Create progress visualization
        progress_cols = st.columns(len(stages))
        
        for i, stage in enumerate(stages):
            with progress_cols[i]:
                stage_id = stage["id"]
                stage_name = stage["name"]
                stage_desc = stage["description"]
                
                # Determine stage status
                if stage_id == current_stage:
                    status = "🔵 Current"
                    status_color = "#5c85ad"
                elif self._is_stage_completed(stage_id, current_stage, stages):
                    status = "✅ Complete"
                    status_color = "#28a745"
                else:
                    status = "⏳ Pending"
                    status_color = "#6c757d"
                
                # Render stage card
                st.markdown(f"""
                <div style="
                    padding: 12px;
                    border-radius: 8px;
                    border: 2px solid {status_color};
                    background-color: {'#e8f4f8' if stage_id == current_stage else '#f8f9fa'};
                    margin-bottom: 10px;
                    text-align: center;
                    min-height: 120px;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                ">
                    <strong style="color: #1f2041;">{stage_name}</strong><br>
                    <small style="color: #6c757d;">{stage_desc}</small><br>
                    <span style="color: {status_color}; font-weight: bold;">{status}</span>
                </div>
                """, unsafe_allow_html=True)
    
    def _render_activity_summary(self, progress_data: Dict[str, Any]):
        """
        Render recent activity summary.
        
        Args:
            progress_data: Progress data dictionary
        """
        st.markdown("### 📋 Recent Activity")
        
        recent_activity = progress_data["recent_activity"]
        
        if not recent_activity:
            st.info("No recent activity recorded.")
            return
        
        # Display recent activities
        activity_container = st.container()
        with activity_container:
            for i, activity in enumerate(recent_activity[:10]):  # Show last 10 activities
                event_type, event_name, timestamp, details, status = activity
                
                # Format timestamp
                try:
                    formatted_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M')
                except:
                    formatted_time = timestamp
                
                # Status indicator
                status_emoji = "✅" if status == "SUCCESS" else "❌" if status == "FAILURE" else "⚠️"
                
                with st.expander(f"{status_emoji} {event_name} - {formatted_time}"):
                    st.write(f"**Type:** {event_type}")
                    st.write(f"**Status:** {status}")
                    if details:
                        st.write(f"**Details:** {details}")
    
    def _render_statistics(self, progress_data: Dict[str, Any]):
        """
        Render progress statistics.
        
        Args:
            progress_data: Progress data dictionary
        """
        st.markdown("### 📊 Progress Statistics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total Sessions",
                progress_data["session_count"]
            )
        
        with col2:
            processing_stats = progress_data["processing_stats"]
            total_docs = sum(processing_stats.values())
            st.metric(
                "Documents Processed",
                total_docs
            )
        
        with col3:
            completed_docs = processing_stats.get("filed", 0) + processing_stats.get("complete", 0)
            st.metric(
                "Completed Documents",
                completed_docs
            )
        
        with col4:
            pending_docs = processing_stats.get("pending_categorization", 0) + processing_stats.get("ingested", 0)
            st.metric(
                "Pending Review",
                pending_docs
            )
        
        # Document status breakdown
        if processing_stats:
            st.markdown("#### Document Status Breakdown")
            status_cols = st.columns(len(processing_stats))
            
            for i, (status, count) in enumerate(processing_stats.items()):
                with status_cols[i]:
                    st.metric(
                        status.replace('_', ' ').title(),
                        count
                    )
    
    def _is_stage_completed(self, stage_id: str, current_stage: str, stages: List[Dict[str, Any]]) -> bool:
        """
        Check if a stage has been completed.
        
        Args:
            stage_id: Stage to check
            current_stage: Current active stage
            stages: List of all stages
            
        Returns:
            True if stage is completed
        """
        try:
            current_index = next(i for i, stage in enumerate(stages) if stage["id"] == current_stage)
            stage_index = next(i for i, stage in enumerate(stages) if stage["id"] == stage_id)
            return stage_index < current_index
        except StopIteration:
            return False

def render_user_journey_visualizer():
    """
    Render the User Journey Visualizer page.
    """
    st.title("🗺️ User Journey Progress Visualizer")
    
    # Initialize visualizer
    visualizer = UserJourneyVisualizer("production_idis.db")
    
    # Render the visualization
    visualizer.render_progress_visualization()
    
    # Additional features
    st.markdown("---")
    
    with st.expander("📈 Advanced Progress Insights"):
        st.markdown("""
        **Understanding Your Progress:**
        - **Blue circles** indicate your current step
        - **Green checkmarks** show completed steps
        - **Gray clocks** represent upcoming steps
        
        **Workflow Types:**
        - **Document Upload**: Track document processing from upload to filing
        - **Search Workflow**: Monitor your search and discovery activities
        - **Medicaid Navigation**: Follow your Medicaid document processing journey
        
        **Tips for Progress:**
        - Complete each step before moving to the next
        - Review pending documents regularly
        - Use the search function to find processed documents
        """)