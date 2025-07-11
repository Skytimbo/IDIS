#!/usr/bin/env python3
"""
Test script to verify the Heuristic Rules Engine functionality
"""

import os
import sys
import json
from context_store import ContextStore
from unified_ingestion_agent import UnifiedIngestionAgent

def test_heuristic_rules_engine():
    """Test the Heuristic Rules Engine with known test cases"""
    
    print("🔧 Testing Heuristic Rules Engine...")
    
    # Test case 1: Payslip document
    print("\n📋 Test Case 1: Payslip Classification")
    payslip_content = """
    EMPLOYEE PAYSLIP
    
    Employee Name: John Doe
    Employee ID: 12345
    Pay Period: 12/01/2024 - 12/15/2024
    Pay Date: 12/20/2024
    
    EARNINGS:
    Regular Hours: 80.0 hrs @ $25.00/hr = $2,000.00
    Overtime Hours: 5.0 hrs @ $37.50/hr = $187.50
    Gross Pay: $2,187.50
    
    DEDUCTIONS:
    Federal Tax: $328.13
    State Tax: $131.25
    Social Security: $135.63
    Medicare: $31.72
    Health Insurance: $125.00
    Total Deductions: $751.73
    
    NET PAY: $1,435.77
    """
    
    # Test case 2: Utility bill document
    print("\n⚡ Test Case 2: Utility Bill Classification")
    utility_content = """
    GCI GENERAL COMMUNICATION INC.
    ALASKA ELECTRIC UTILITY BILL
    
    Account Number: 123456789
    Service Address: 123 Main St, Anchorage, AK
    Bill Date: June 15, 2024
    
    ELECTRIC SERVICE CHARGES:
    Previous Reading: 1,250 kWh
    Current Reading: 1,450 kWh
    Usage: 200 kWh
    
    Electric Charges: $89.50
    Distribution Charge: $15.25
    Regulatory Fee: $2.50
    
    Total Amount Due: $107.25
    Due Date: July 15, 2024
    """
    
    # Initialize components
    context_store = ContextStore("test_heuristic_rules.db")
    temp_folder = "data/temp_heuristic_test"
    holding_folder = "data/holding_heuristic_test"
    
    # Create directories
    os.makedirs(temp_folder, exist_ok=True)
    os.makedirs(holding_folder, exist_ok=True)
    
    # Initialize agent
    agent = UnifiedIngestionAgent(
        context_store=context_store,
        watch_folder=temp_folder,
        holding_folder=holding_folder
    )
    
    print("✅ Initialized UnifiedIngestionAgent with Heuristic Rules Engine")
    
    # Test each document type
    test_cases = [
        ("test_payslip_heuristic.txt", payslip_content, "Payslip"),
        ("test_utility_heuristic.txt", utility_content, "Utility Bill")
    ]
    
    results = []
    
    for filename, content, expected_type in test_cases:
        print(f"\n🧪 Testing {filename}...")
        
        # Create test file
        test_file_path = os.path.join(temp_folder, filename)
        with open(test_file_path, 'w') as f:
            f.write(content)
        
        # Process through the pipeline
        success = agent._process_single_file(test_file_path, filename, entity_id=1, session_id=1)
        
        if success:
            # Query the database to verify classification
            docs = context_store.get_documents_by_processing_status('processing_complete', limit=10)
            
            # Find our document
            our_doc = None
            for doc in docs:
                if doc.get('file_name') == filename:
                    our_doc = doc
                    break
            
            if our_doc:
                actual_type = our_doc.get('document_type', 'Unknown')
                extracted_data = json.loads(our_doc.get('extracted_data', '{}'))
                
                print(f"  📄 Document Type: {actual_type}")
                print(f"  🎯 Expected: {expected_type}")
                print(f"  ✅ Match: {actual_type == expected_type}")
                
                # Check if heuristic rules were applied
                if 'heuristic_metadata' in extracted_data:
                    heuristic_info = extracted_data['heuristic_metadata']
                    print(f"  🔍 Heuristic Rule Applied: {heuristic_info.get('rule_applied', False)}")
                    print(f"  🏷️  Matched Keywords: {heuristic_info.get('matched_keywords', [])}")
                    print(f"  🔄 Original Classification: {heuristic_info.get('original_classification', 'N/A')}")
                
                results.append({
                    'filename': filename,
                    'expected': expected_type,
                    'actual': actual_type,
                    'success': actual_type == expected_type,
                    'heuristic_applied': 'heuristic_metadata' in extracted_data
                })
            else:
                print(f"  ❌ Document not found in database")
                results.append({
                    'filename': filename,
                    'expected': expected_type,
                    'actual': 'NOT_FOUND',
                    'success': False,
                    'heuristic_applied': False
                })
        else:
            print(f"  ❌ Processing failed for {filename}")
            results.append({
                'filename': filename,
                'expected': expected_type,
                'actual': 'PROCESSING_FAILED',
                'success': False,
                'heuristic_applied': False
            })
        
        # Clean up test file
        if os.path.exists(test_file_path):
            os.remove(test_file_path)
    
    # Summary
    print("\n📊 HEURISTIC RULES ENGINE TEST RESULTS")
    print("=" * 50)
    
    successful_tests = sum(1 for r in results if r['success'])
    total_tests = len(results)
    
    for result in results:
        status = "✅ PASS" if result['success'] else "❌ FAIL"
        heuristic_status = "🔍 RULES APPLIED" if result['heuristic_applied'] else "🤖 AI ONLY"
        print(f"{status} {result['filename']}: {result['expected']} -> {result['actual']} ({heuristic_status})")
    
    print(f"\n🎯 Overall Success Rate: {successful_tests}/{total_tests} ({successful_tests/total_tests*100:.1f}%)")
    
    # Clean up
    try:
        os.rmdir(temp_folder)
        os.rmdir(holding_folder)
        if os.path.exists("test_heuristic_rules.db"):
            os.remove("test_heuristic_rules.db")
    except:
        pass  # Ignore cleanup errors
    
    if successful_tests == total_tests:
        print("\n🎉 All tests passed! Heuristic Rules Engine is working correctly.")
        return True
    else:
        print(f"\n⚠️  {total_tests - successful_tests} test(s) failed. Please review the implementation.")
        return False

if __name__ == "__main__":
    success = test_heuristic_rules_engine()
    sys.exit(0 if success else 1)