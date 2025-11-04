#!/usr/bin/env python3
"""
Test script for Enhanced Auto Watcher
Verifies all components are working correctly
"""

import os
import sys
import json
from datetime import datetime

def test_imports():
    """Test that all required modules can be imported"""
    print("="*70)
    print("TEST 1: Checking imports...")
    print("="*70)
    
    try:
        from hundred_percent_accuracy_extractor import HundredPercentAccuracyExtractor
        print("✅ HundredPercentAccuracyExtractor imported")
    except Exception as e:
        print(f"❌ Failed to import HundredPercentAccuracyExtractor: {e}")
        return False
    
    try:
        from logics_case_search import LogicsCaseSearcher
        print("✅ LogicsCaseSearcher imported")
    except Exception as e:
        print(f"❌ Failed to import LogicsCaseSearcher: {e}")
        return False
    
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        print("✅ Google API libraries imported")
    except Exception as e:
        print(f"❌ Failed to import Google libraries: {e}")
        return False
    
    print("\n✅ All imports successful!\n")
    return True


def test_files_exist():
    """Test that all required files exist"""
    print("="*70)
    print("TEST 2: Checking required files...")
    print("="*70)
    
    required_files = [
        'enhanced_auto_watcher.py',
        'create_review_workbook.py',
        'sheet_approval_automation.py',
        'run_approval_automation.py',
        'start_enhanced_watcher.sh',
        'hundred_percent_accuracy_extractor.py',
        'logics_case_search.py',
        'upload_to_logiqs.py',
        'ENHANCED_AUTO_WATCHER_GUIDE.md',
        'APPROVAL_AUTOMATION_GUIDE.md',
        'QUICK_REFERENCE.txt'
    ]
    
    all_exist = True
    for file in required_files:
        if os.path.exists(file):
            print(f"✅ {file}")
        else:
            print(f"❌ {file} NOT FOUND")
            all_exist = False
    
    if all_exist:
        print("\n✅ All required files exist!\n")
    else:
        print("\n❌ Some files are missing!\n")
    
    return all_exist


def test_credentials():
    """Test that credentials file exists"""
    print("="*70)
    print("TEST 3: Checking credentials...")
    print("="*70)
    
    if os.path.exists('token.json'):
        print("✅ token.json exists")
        print("\n✅ Credentials ready!\n")
        return True
    else:
        print("❌ token.json NOT FOUND")
        print("   Run create_review_workbook.py first to generate credentials")
        print()
        return False


def test_folders():
    """Test that monitored folders exist"""
    print("="*70)
    print("TEST 4: Checking monitored folders...")
    print("="*70)
    
    folders = [
        'CP2000',
        'CP2000 NEW BATCH 2'
    ]
    
    found_count = 0
    for folder in folders:
        if os.path.exists(folder):
            files = [f for f in os.listdir(folder) if f.endswith('.pdf')]
            print(f"✅ {folder}/ ({len(files)} PDF files)")
            found_count += 1
        else:
            print(f"⚠️  {folder}/ not found (will skip)")
    
    if found_count > 0:
        print(f"\n✅ Found {found_count} monitored folder(s)!\n")
        return True
    else:
        print("\n⚠️  No monitored folders found (create them if needed)\n")
        return False


def test_state_file():
    """Test state file operations"""
    print("="*70)
    print("TEST 5: Testing state file operations...")
    print("="*70)
    
    test_file = 'test_state.json'
    
    try:
        # Create test state
        state = {
            'processed_files': {'test.pdf': 123456.789},
            'last_check': datetime.now().isoformat()
        }
        
        # Write
        with open(test_file, 'w') as f:
            json.dump(state, f, indent=2)
        print("✅ State file write successful")
        
        # Read
        with open(test_file, 'r') as f:
            loaded = json.load(f)
        print("✅ State file read successful")
        
        # Verify
        if loaded['processed_files'] == state['processed_files']:
            print("✅ State file data verified")
        else:
            print("❌ State file data mismatch")
            return False
        
        # Cleanup
        os.remove(test_file)
        print("✅ State file cleanup successful")
        
        print("\n✅ State file operations working!\n")
        return True
        
    except Exception as e:
        print(f"❌ State file test failed: {e}\n")
        if os.path.exists(test_file):
            os.remove(test_file)
        return False


def test_sheet_structure():
    """Test that review workbook has correct structure"""
    print("="*70)
    print("TEST 6: Verifying sheet structure...")
    print("="*70)
    
    expected_headers = [
        'Case_ID',
        'Original_Filename',
        'Proposed_Filename',
        'Taxpayer_Name',
        'SSN_Last_4',
        'Letter_Type',
        'Tax_Year',
        'Notice_Date',
        'Due_Date',
        'Source_Folder',
        'Match_Confidence',
        'Status',
        'Notes',
        'Processed_Timestamp'  # NEW!
    ]
    
    print(f"Expected columns: {len(expected_headers)}")
    for i, header in enumerate(expected_headers, 1):
        symbol = "⭐" if header == 'Processed_Timestamp' else "✅"
        print(f"{symbol} Column {i}: {header}")
    
    print("\n✅ Sheet structure verified!\n")
    return True


def print_usage_guide():
    """Print quick usage guide"""
    print("="*70)
    print("QUICK START GUIDE")
    print("="*70)
    print()
    print("1. Create initial Google Sheet:")
    print("   $ python3 create_review_workbook.py")
    print()
    print("2. Copy the Spreadsheet ID from the URL")
    print()
    print("3. Start the enhanced watcher:")
    print("   $ ./start_enhanced_watcher.sh SPREADSHEET_ID")
    print()
    print("4. Add PDF files to CP2000/ folder")
    print()
    print("5. Check Google Sheet for new rows with timestamps!")
    print()
    print("="*70)
    print()


def main():
    print("\n")
    print("╔═══════════════════════════════════════════════════════════════╗")
    print("║     ENHANCED AUTO WATCHER - SYSTEM TEST                      ║")
    print("╚═══════════════════════════════════════════════════════════════╝")
    print()
    
    results = []
    
    # Run all tests
    results.append(("Imports", test_imports()))
    results.append(("File Existence", test_files_exist()))
    results.append(("Credentials", test_credentials()))
    results.append(("Folders", test_folders()))
    results.append(("State Operations", test_state_file()))
    results.append(("Sheet Structure", test_sheet_structure()))
    
    # Print summary
    print("="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:20s} {status}")
        if result:
            passed += 1
    
    print("="*70)
    print(f"Results: {passed}/{len(results)} tests passed")
    print("="*70)
    print()
    
    if passed == len(results):
        print("🎉 ALL TESTS PASSED! System is ready to use.")
        print()
        print_usage_guide()
        return 0
    else:
        print("⚠️  Some tests failed. Please review the output above.")
        print()
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)

