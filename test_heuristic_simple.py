#!/usr/bin/env python3
"""
Simple test to verify the Heuristic Rules Engine logic without OpenAI API
"""

import sys
from unified_ingestion_agent import UnifiedIngestionAgent
from context_store import ContextStore

def test_heuristic_logic():
    """Test the heuristic rules logic directly"""
    
    print("Testing Heuristic Rules Engine Logic...")
    
    # Create minimal agent instance
    context_store = ContextStore(":memory:")  # In-memory database for testing
    agent = UnifiedIngestionAgent(context_store, ".", ".")
    
    # Test Case 1: Payslip document with "Correspondence" classification
    print("\n1. Testing Payslip Override:")
    
    mock_ai_data = {
        "document_type": {
            "predicted_class": "Correspondence",
            "confidence_score": 0.5
        }
    }
    
    payslip_text = """
    EMPLOYEE PAYSLIP
    Employee Name: John Doe
    Pay Period: 12/01/2024 - 12/15/2024
    Gross Pay: $2,187.50
    Net Pay: $1,435.77
    """
    
    result = agent.apply_heuristic_rules(mock_ai_data, payslip_text)
    
    final_type = result.get('document_type', {}).get('predicted_class', '')
    print(f"   AI Classification: Correspondence")
    print(f"   Heuristic Result: {final_type}")
    print(f"   Success: {'✅' if final_type == 'Payslip' else '❌'}")
    
    # Test Case 2: Utility bill with "Unknown" classification  
    print("\n2. Testing Utility Bill Override:")
    
    mock_ai_data2 = {
        "document_type": {
            "predicted_class": "Unknown",
            "confidence_score": 0.3
        }
    }
    
    utility_text = """
    GCI ALASKA ELECTRIC UTILITY
    Account Number: 123456789
    Usage: 200 kWh
    Electric Charges: $89.50
    Total Amount Due: $107.25
    """
    
    result2 = agent.apply_heuristic_rules(mock_ai_data2, utility_text)
    
    final_type2 = result2.get('document_type', {}).get('predicted_class', '')
    print(f"   AI Classification: Unknown")
    print(f"   Heuristic Result: {final_type2}")
    print(f"   Success: {'✅' if final_type2 == 'Utility Bill' else '❌'}")
    
    # Test Case 3: High-confidence AI result should NOT be overridden
    print("\n3. Testing High-Confidence AI (No Override):")
    
    mock_ai_data3 = {
        "document_type": {
            "predicted_class": "Medical Report",
            "confidence_score": 0.9
        }
    }
    
    result3 = agent.apply_heuristic_rules(mock_ai_data3, "This is a medical report about payslip")
    
    final_type3 = result3.get('document_type', {}).get('predicted_class', '')
    print(f"   AI Classification: Medical Report (high confidence)")
    print(f"   Heuristic Result: {final_type3}")
    print(f"   Success: {'✅' if final_type3 == 'Medical Report' else '❌'}")
    
    # Summary
    test_results = [
        final_type == 'Payslip',
        final_type2 == 'Utility Bill', 
        final_type3 == 'Medical Report'
    ]
    
    passed = sum(test_results)
    total = len(test_results)
    
    print(f"\n📊 Test Summary: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
    
    if passed == total:
        print("🎉 All heuristic rules tests passed!")
        return True
    else:
        print("❌ Some tests failed. Check the implementation.")
        return False

if __name__ == "__main__":
    success = test_heuristic_logic()
    sys.exit(0 if success else 1)