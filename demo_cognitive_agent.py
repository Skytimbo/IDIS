#!/usr/bin/env python3
"""
Demo script for testing the CognitiveAgent with OpenAI API integration.
"""

import os
import json
from agents.cognitive_agent import CognitiveAgent

def test_cognitive_agent():
    """Test the CognitiveAgent with sample document text."""
    
    print("=== CognitiveAgent OpenAI API Demo ===\n")
    
    # Initialize the agent
    agent = CognitiveAgent()
    
    # Sample document text (similar to what OCR would extract)
    sample_text = """
    FIDELITY REWARDS VISA SIGNATURE CARD
    
    Statement Date: June 15, 2025
    Account Number: XXXX-XXXX-XXXX-1234
    
    Previous Balance: $1,109.56
    Payments/Credits: -$500.00
    New Purchases: $625.00
    Interest Charges: $0.00
    Fees: $0.00
    
    New Balance: $1,234.56
    Minimum Payment Due: $25.00
    Payment Due Date: July 10, 2025
    
    RECENT TRANSACTIONS:
    06/12/25  AMAZON.COM           $89.99
    06/10/25  STARBUCKS #1234      $12.45
    06/08/25  SHELL GAS STATION    $65.32
    06/05/25  GROCERY MART         $125.88
    06/03/25  NETFLIX SUBSCRIPTION $15.99
    """
    
    print("Sample document text:")
    print("-" * 50)
    print(sample_text)
    print("-" * 50)
    print()
    
    # Extract structured data using OpenAI API
    print("Calling OpenAI API to extract structured data...")
    result = agent.extract_structured_data(sample_text)
    
    if result:
        print("\n=== EXTRACTED STRUCTURED DATA ===")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        # Validate the schema structure
        print("\n=== SCHEMA VALIDATION ===")
        expected_keys = [
            "schema_version", "document_type", "issuer", "recipient", 
            "key_dates", "financials", "content", "filing"
        ]
        
        for key in expected_keys:
            if key in result:
                print(f"✓ {key}: Present")
            else:
                print(f"✗ {key}: Missing")
    else:
        print("❌ Failed to extract structured data")
        
    print("\n=== Demo Complete ===")

if __name__ == "__main__":
    test_cognitive_agent()