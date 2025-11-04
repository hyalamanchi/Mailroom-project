"""
CP2000 Case ID Extractor
This script processes the extracted CP2000 data and matches it with Logics cases.
"""

from logics_case_search import LogicsCaseSearcher
import json
from datetime import datetime
import os

def load_extracted_data(json_file):
    """Load previously extracted CP2000 data"""
    with open(json_file, 'r') as f:
        return json.load(f)

def process_cases():
    """Process cases and find matching Logics case IDs"""
    # Initialize the case searcher
    searcher = LogicsCaseSearcher()
    
    # Test connection
    if not searcher.test_connection():
        print("❌ Could not connect to Logics API")
        return
    
    # Find the most recent extraction file
    data_files = [f for f in os.listdir('.') if f.startswith('LOGICS_DATA_') and f.endswith('.json')]
    if not data_files:
        print("❌ No extracted data files found")
        return
    
    latest_file = max(data_files)
    print(f"📄 Loading data from: {latest_file}")
    
    # Load extracted data
    data = load_extracted_data(latest_file)
    if 'extracted_data' in data:
        cases = data['extracted_data']
    else:
        print("❌ No case data found in file")
        return
    
    # Process each case
    matched_cases = []
    unmatched_cases = []
    
    print(f"\n🔍 Processing {len(cases)} cases...")
    for case in cases:
        ssn_last_4 = case.get('ssn_last_4')
        taxpayer_name = case.get('taxpayer_name', '')
        
        if not ssn_last_4 or not taxpayer_name:
            print(f"⚠️ Missing data - SSN: {bool(ssn_last_4)}, Name: {bool(taxpayer_name)}")
            unmatched_cases.append(case)
            continue
        
        # Split name into parts
        name_parts = taxpayer_name.split(' ', 1)
        last_name = name_parts[-1]
        first_name = name_parts[0] if len(name_parts) > 1 else None
        
        print(f"\n🔍 Searching for: {last_name}, SSN: ***-**-{ssn_last_4}")
        case_result = searcher.search_case(
            ssn_last_4=ssn_last_4,
            last_name=last_name,
            first_name=first_name
        )
        
        if case_result:
            case['logics_case_id'] = case_result.get('case_data', {}).get('caseId')
            case['logics_case_data'] = case_result.get('case_data', {})
            matched_cases.append(case)
            print(f"✅ Found case ID: {case['logics_case_id']}")
        else:
            unmatched_cases.append(case)
            print("❌ No matching case found")
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_data = {
        "extraction_metadata": {
            "timestamp": datetime.now().isoformat(),
            "total_cases": len(cases),
            "matched_cases": len(matched_cases),
            "unmatched_cases": len(unmatched_cases)
        },
        "matched_cases": matched_cases,
        "unmatched_cases": unmatched_cases
    }
    
    output_file = f"CASE_MATCHES_{timestamp}.json"
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\n✅ Processing complete!")
    print(f"📊 Total cases: {len(cases)}")
    print(f"✅ Matched cases: {len(matched_cases)}")
    print(f"❌ Unmatched cases: {len(unmatched_cases)}")
    print(f"💾 Results saved to: {output_file}")

if __name__ == "__main__":
    process_cases()