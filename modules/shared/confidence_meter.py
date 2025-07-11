"""
Color-Coded Confidence Meter for Document Processing

This module provides visual confidence indicators for AI document classification,
helping users understand the reliability of automated processing results.
"""

import streamlit as st
import json
from typing import Dict, Any, Optional, Tuple


def get_confidence_color(confidence: float) -> str:
    """
    Returns color code based on confidence level.
    
    Args:
        confidence: Confidence score from 0.0 to 1.0
        
    Returns:
        CSS color code for the confidence level
    """
    if confidence >= 0.9:
        return "#22c55e"  # Green - High confidence
    elif confidence >= 0.7:
        return "#f59e0b"  # Yellow - Medium confidence
    elif confidence >= 0.5:
        return "#ef4444"  # Red - Low confidence
    else:
        return "#6b7280"  # Gray - Very low confidence


def get_confidence_label(confidence: float) -> str:
    """
    Returns human-readable label for confidence level.
    
    Args:
        confidence: Confidence score from 0.0 to 1.0
        
    Returns:
        Text label describing the confidence level
    """
    if confidence >= 0.9:
        return "High Confidence"
    elif confidence >= 0.7:
        return "Medium Confidence"
    elif confidence >= 0.5:
        return "Low Confidence"
    else:
        return "Very Low Confidence"


def render_confidence_meter(confidence: float, document_type: str, compact: bool = False) -> None:
    """
    Renders a visual confidence meter for document classification.
    
    Args:
        confidence: Confidence score from 0.0 to 1.0
        document_type: Classified document type
        compact: Whether to render in compact mode
    """
    if confidence is None:
        confidence = 0.0
    
    # Ensure confidence is within valid range
    confidence = max(0.0, min(1.0, confidence))
    
    color = get_confidence_color(confidence)
    label = get_confidence_label(confidence)
    percentage = int(confidence * 100)
    
    if compact:
        # Compact mode - single line display
        st.markdown(f"""
        <div style="
            display: flex; 
            align-items: center; 
            gap: 8px; 
            margin: 4px 0;
            font-size: 0.9em;
        ">
            <div style="
                background-color: {color}; 
                height: 12px; 
                width: {percentage}%; 
                max-width: 60px;
                border-radius: 6px;
                min-width: 8px;
            "></div>
            <span style="color: {color}; font-weight: bold;">{percentage}%</span>
            <span style="color: #6b7280; font-size: 0.8em;">{label}</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Full mode - detailed display
        st.markdown(f"""
        <div style="
            background-color: #f8fafc; 
            border: 1px solid #e2e8f0; 
            border-radius: 8px; 
            padding: 12px; 
            margin: 8px 0;
        ">
            <div style="
                display: flex; 
                justify-content: space-between; 
                align-items: center; 
                margin-bottom: 8px;
            ">
                <span style="font-weight: bold; color: #374151;">AI Classification Confidence</span>
                <span style="color: {color}; font-weight: bold; font-size: 1.1em;">{percentage}%</span>
            </div>
            <div style="
                background-color: #e5e7eb; 
                height: 8px; 
                border-radius: 4px; 
                overflow: hidden;
            ">
                <div style="
                    background-color: {color}; 
                    height: 100%; 
                    width: {percentage}%; 
                    transition: width 0.3s ease;
                "></div>
            </div>
            <div style="
                display: flex; 
                justify-content: space-between; 
                align-items: center; 
                margin-top: 6px;
                font-size: 0.9em;
            ">
                <span style="color: {color}; font-weight: 500;">{label}</span>
                <span style="color: #6b7280;">Document Type: <strong>{document_type}</strong></span>
            </div>
        </div>
        """, unsafe_allow_html=True)


def extract_confidence_from_document(document: Dict[str, Any]) -> Tuple[float, str, bool]:
    """
    Extracts confidence score and metadata from a document record.
    
    Args:
        document: Document record from database
        
    Returns:
        Tuple of (confidence_score, document_type, has_heuristic_override)
    """
    confidence = 0.0
    document_type = "Unknown"
    has_heuristic_override = False
    
    # First, try to get from extracted_data JSON
    extracted_data = document.get('extracted_data', '{}')
    if extracted_data:
        try:
            data = json.loads(extracted_data)
            
            # Check for heuristic override
            if 'heuristic_metadata' in data:
                has_heuristic_override = True
                # Use heuristic confidence if available
                heuristic_meta = data['heuristic_metadata']
                if 'confidence_override' in heuristic_meta:
                    confidence = heuristic_meta['confidence_override']
                document_type = heuristic_meta.get('rule_type', document_type)
            
            # Get AI confidence from document_type field
            if 'document_type' in data and not has_heuristic_override:
                doc_type_info = data['document_type']
                confidence = doc_type_info.get('confidence_score', 0.0)
                document_type = doc_type_info.get('predicted_class', document_type)
                
        except json.JSONDecodeError:
            pass
    
    # Fallback to legacy columns if no JSON data
    if confidence == 0.0 and document_type == "Unknown":
        document_type = document.get('document_type', 'Unknown')
        # Estimate confidence based on legacy data availability
        if document_type and document_type != 'Unknown':
            confidence = 0.7  # Medium confidence for legacy data
    
    return confidence, document_type, has_heuristic_override


def render_confidence_badge(confidence: float, has_heuristic_override: bool = False) -> str:
    """
    Renders a small confidence badge for use in tables and lists.
    
    Args:
        confidence: Confidence score from 0.0 to 1.0
        has_heuristic_override: Whether the classification was enhanced by heuristic rules
        
    Returns:
        HTML string for the confidence badge
    """
    if confidence is None:
        confidence = 0.0
    
    confidence = max(0.0, min(1.0, confidence))
    color = get_confidence_color(confidence)
    percentage = int(confidence * 100)
    
    # Add special indicator for heuristic overrides
    override_indicator = "🔧" if has_heuristic_override else ""
    
    return f"""
    <span style="
        background-color: {color}; 
        color: white; 
        padding: 2px 6px; 
        border-radius: 12px; 
        font-size: 0.8em; 
        font-weight: bold;
        white-space: nowrap;
    ">
        {override_indicator}{percentage}%
    </span>
    """


def render_processing_confidence_summary(documents: list) -> None:
    """
    Renders a summary of confidence levels for multiple documents.
    
    Args:
        documents: List of document records
    """
    if not documents:
        return
    
    # Analyze confidence distribution
    confidence_counts = {"High": 0, "Medium": 0, "Low": 0, "Very Low": 0}
    heuristic_count = 0
    
    for doc in documents:
        confidence, _, has_heuristic = extract_confidence_from_document(doc)
        
        if has_heuristic:
            heuristic_count += 1
        
        if confidence >= 0.9:
            confidence_counts["High"] += 1
        elif confidence >= 0.7:
            confidence_counts["Medium"] += 1
        elif confidence >= 0.5:
            confidence_counts["Low"] += 1
        else:
            confidence_counts["Very Low"] += 1
    
    total_docs = len(documents)
    
    st.markdown("### Processing Confidence Summary")
    
    # Create confidence distribution chart
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Horizontal bar chart
        st.markdown(f"""
        <div style="background-color: #f8fafc; padding: 12px; border-radius: 8px; margin: 8px 0;">
            <div style="margin-bottom: 8px; font-weight: bold; color: #374151;">
                Document Classification Confidence Distribution
            </div>
            <div style="display: flex; flex-direction: column; gap: 4px;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <div style="width: 80px; font-size: 0.9em; color: #6b7280;">High:</div>
                    <div style="background-color: #22c55e; height: 16px; width: {confidence_counts['High']/total_docs*200}px; border-radius: 8px; min-width: 4px;"></div>
                    <span style="font-size: 0.9em; color: #374151;">{confidence_counts['High']} docs</span>
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <div style="width: 80px; font-size: 0.9em; color: #6b7280;">Medium:</div>
                    <div style="background-color: #f59e0b; height: 16px; width: {confidence_counts['Medium']/total_docs*200}px; border-radius: 8px; min-width: 4px;"></div>
                    <span style="font-size: 0.9em; color: #374151;">{confidence_counts['Medium']} docs</span>
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <div style="width: 80px; font-size: 0.9em; color: #6b7280;">Low:</div>
                    <div style="background-color: #ef4444; height: 16px; width: {confidence_counts['Low']/total_docs*200}px; border-radius: 8px; min-width: 4px;"></div>
                    <span style="font-size: 0.9em; color: #374151;">{confidence_counts['Low']} docs</span>
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <div style="width: 80px; font-size: 0.9em; color: #6b7280;">Very Low:</div>
                    <div style="background-color: #6b7280; height: 16px; width: {confidence_counts['Very Low']/total_docs*200}px; border-radius: 8px; min-width: 4px;"></div>
                    <span style="font-size: 0.9em; color: #374151;">{confidence_counts['Very Low']} docs</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        # Summary statistics
        st.markdown(f"""
        <div style="background-color: #f8fafc; padding: 12px; border-radius: 8px; margin: 8px 0;">
            <div style="font-weight: bold; color: #374151; margin-bottom: 8px;">Summary</div>
            <div style="font-size: 0.9em; color: #6b7280;">
                <div>Total Documents: <strong>{total_docs}</strong></div>
                <div>Enhanced by Rules: <strong>{heuristic_count}</strong></div>
                <div>High Confidence: <strong>{confidence_counts['High']}</strong></div>
            </div>
        </div>
        """, unsafe_allow_html=True)