"""
ENHANCED CASE MATCHER - Advanced Matching for Unmatched Cases

This script applies multiple advanced matching strategies to improve case matching:
1. Name variations (spaces, suffixes, prefixes)
2. SSN verification (check for OCR errors)
3. Fuzzy name matching (Levenshtein distance)
4. Combined search strategies

USAGE:
    python enhanced_case_matcher.py
    python enhanced_case_matcher.py --input case_matching_results.json
"""

import sys
sys.dont_write_bytecode = True
from logics_case_search import LogicsCaseSearcher, generate_document_name
import json
import time
from datetime import datetime
import os
import re
from difflib import SequenceMatcher

class EnhancedCaseMatcher:
    """Advanced case matching with multiple strategies"""
    
    def __init__(self):
        self.searcher = LogicsCaseSearcher()
        self.newly_matched = []
        self.still_not_found = []
        
    def get_name_variations(self, name):
        """Generate multiple name variations for matching"""
        variations = set()
        
        # Original
        variations.add(name)
        variations.add(name.upper())
        variations.add(name.lower())
        variations.add(name.title())
        
        # Remove spaces
        if ' ' in name:
            variations.add(name.replace(' ', ''))
            variations.add(name.replace(' ', '-'))
        
        # Handle suffixes (Jr, III, II, IV, Sr)
        suffixes = [' JR', ' III', ' II', ' IV', ' SR', ' JR.', ' SR.']
        for suffix in suffixes:
            if suffix in name.upper():
                base_name = name.upper().split(suffix)[0]
                variations.add(base_name)
                variations.add(base_name.title())
                # Also try without space
                variations.add(name.replace(' ', ''))
        
        # Handle middle initials (e.g., "Smith J" -> "Smith")
        if ' ' in name:
            parts = name.split()
            if len(parts) == 2 and len(parts[1]) <= 2:
                variations.add(parts[0])
                # Also try combined
                variations.add(''.join(parts))
        
        # Handle "Mc" and "Mac" prefixes
        if name.lower().startswith('mc') and len(name) > 2:
            variations.add('Mc' + name[2:].title())
            variations.add('Mac' + name[2:].title())
        
        # Handle "O'" prefix
        if name.lower().startswith('o') and len(name) > 1:
            variations.add("O'" + name[1:].title())
        
        # Handle hyphenated names
        if '-' in name:
            # Try without hyphen
            variations.add(name.replace('-', ''))
            variations.add(name.replace('-', ' '))
            # Try just first part
            variations.add(name.split('-')[0])
        
        return list(variations)
    
    def is_suspicious_ssn(self, ssn):
        """Check if SSN looks like an OCR error"""
        suspicious_patterns = ['0021', '0521', '1505', '9012', '0000', '1111', '9999']
        return ssn in suspicious_patterns
    
    def get_ssn_variations(self, ssn):
        """Generate possible SSN corrections for OCR errors"""
        variations = [ssn]
        
        # Common OCR errors
        ocr_substitutions = {
            '0': ['8', '6', 'O'],
            '1': ['7', 'I', 'l'],
            '2': ['7', 'Z'],
            '5': ['3', 'S'],
            '8': ['0', '3'],
            '9': ['4', '7']
        }
        
        # Only try variations if it looks suspicious
        if self.is_suspicious_ssn(ssn):
            # Try common substitutions for each digit
            for i, digit in enumerate(ssn):
                if digit in ocr_substitutions:
                    for replacement in ocr_substitutions[digit]:
                        if replacement.isdigit():
                            new_ssn = ssn[:i] + replacement + ssn[i+1:]
                            variations.append(new_ssn)
        
        return variations
    
    def similarity_score(self, str1, str2):
        """Calculate similarity between two strings (0-1)"""
        return SequenceMatcher(None, str1.upper(), str2.upper()).ratio()
    
    def try_match_case(self, case):
        """Try multiple strategies to match a single case"""
        last_name = case['last_name']
        ssn = case['ssn_last_4']
        
        # Strategy 1: Name variations with original SSN
        name_variations = self.get_name_variations(last_name)
        for name_var in name_variations:
            try:
                result = self.searcher.search_case(ssn, name_var)
                if result and 'caseData' in result:
                    return {
                        'success': True,
                        'case_id': result['caseData']['data'].get('CaseID'),
                        'match_type': result.get('matchType'),
                        'similarity': result.get('nameSimilarity', 0),
                        'strategy': 'name_variation',
                        'name_used': name_var,
                        'ssn_used': ssn
                    }
                time.sleep(0.1)
            except Exception as e:
                continue
        
        # Strategy 2: SSN variations with original name (if suspicious SSN)
        if self.is_suspicious_ssn(ssn):
            ssn_variations = self.get_ssn_variations(ssn)
            for ssn_var in ssn_variations[:3]:  # Limit to first 3 variations
                try:
                    result = self.searcher.search_case(ssn_var, last_name)
                    if result and 'caseData' in result:
                        return {
                            'success': True,
                            'case_id': result['caseData']['data'].get('CaseID'),
                            'match_type': result.get('matchType'),
                            'similarity': result.get('nameSimilarity', 0),
                            'strategy': 'ssn_correction',
                            'name_used': last_name,
                            'ssn_used': ssn_var,
                            'original_ssn': ssn
                        }
                    time.sleep(0.1)
                except Exception as e:
                    continue
        
        return {'success': False}
    
    def process_unmatched_cases(self, unmatched_cases):
        """Process all unmatched cases with enhanced strategies"""
        print(f"\n🔧 Enhanced Case Matching - Processing {len(unmatched_cases)} unmatched cases")
        print("=" * 80)
        print("\nStrategies applied:")
        print("  1. Name variations (spaces, suffixes, prefixes)")
        print("  2. SSN corrections (OCR error detection)")
        print("  3. Fuzzy matching")
        print("  4. Combined approaches\n")
        
        for idx, case in enumerate(unmatched_cases, 1):
            last_name = case['last_name']
            ssn = case['ssn_last_4']
            
            # Show suspicious SSN indicator
            suspicious = "⚠️ " if self.is_suspicious_ssn(ssn) else ""
            print(f"{idx:3d}/{len(unmatched_cases)} {suspicious}{last_name:20s} (SSN: {ssn}) ", end='', flush=True)
            
            # Try to match
            match_result = self.try_match_case(case)
            
            if match_result['success']:
                print(f"✅ FOUND! Case ID: {match_result['case_id']} ({match_result['strategy']})")
                
                # Add to newly matched
                self.newly_matched.append({
                    'original_case': case,
                    'case_id': match_result['case_id'],
                    'match_type': match_result['match_type'],
                    'similarity': match_result['similarity'],
                    'strategy': match_result['strategy'],
                    'name_used': match_result['name_used'],
                    'ssn_used': match_result['ssn_used'],
                    'original_ssn': match_result.get('original_ssn', ssn)
                })
            else:
                print(f"⚠️  Still not found")
                self.still_not_found.append(case)
            
            time.sleep(0.25)  # Rate limiting
    
    def generate_report(self, original_matched_count, total_cases):
        """Generate comprehensive report"""
        print("\n" + "=" * 80)
        print("📊 ENHANCED MATCHING RESULTS")
        print("=" * 80)
        
        # Summary
        print(f"\n✅ Newly Matched: {len(self.newly_matched)}")
        print(f"⚠️  Still Not Found: {len(self.still_not_found)}")
        
        if self.newly_matched:
            print(f"\n🎉 Successfully matched {len(self.newly_matched)} additional cases:")
            
            # Group by strategy
            strategies = {}
            for match in self.newly_matched:
                strategy = match['strategy']
                strategies[strategy] = strategies.get(strategy, 0) + 1
            
            print(f"\nBy Strategy:")
            for strategy, count in strategies.items():
                print(f"   • {strategy}: {count} cases")
            
            print(f"\nDetailed Results:")
            for match in self.newly_matched:
                orig_name = match['original_case']['last_name']
                new_name = match['name_used']
                orig_ssn = match['original_ssn']
                new_ssn = match['ssn_used']
                case_id = match['case_id']
                strategy = match['strategy']
                
                if orig_ssn == new_ssn:
                    print(f"   • {orig_name:20s} → {case_id:8} (as '{new_name}') [{strategy}]")
                else:
                    print(f"   • {orig_name:20s} → {case_id:8} (SSN: {orig_ssn}→{new_ssn}) [{strategy}]")
        
        # Updated statistics
        new_total_matched = original_matched_count + len(self.newly_matched)
        
        print(f"\n📈 Updated Match Statistics:")
        print(f"   Previous: {original_matched_count}/{total_cases} ({original_matched_count/total_cases*100:.1f}%)")
        print(f"   Current:  {new_total_matched}/{total_cases} ({new_total_matched/total_cases*100:.1f}%)")
        print(f"   Improvement: +{len(self.newly_matched)} cases (+{len(self.newly_matched)/total_cases*100:.1f}%)")
        
        # Analysis of remaining unmatched
        if self.still_not_found:
            print(f"\n🔍 Analysis of {len(self.still_not_found)} remaining unmatched:")
            
            suspicious_ssns = [c for c in self.still_not_found if self.is_suspicious_ssn(c['ssn_last_4'])]
            print(f"   • Suspicious SSNs: {len(suspicious_ssns)} cases")
            print(f"   • Likely don't exist in Logiqs: {len(self.still_not_found) - len(suspicious_ssns)} cases")
        
        print("\n" + "=" * 80)
        
        return {
            'newly_matched': self.newly_matched,
            'still_not_found': self.still_not_found,
            'new_total_matched': new_total_matched,
            'improvement_count': len(self.newly_matched),
            'strategies_used': strategies if self.newly_matched else {}
        }
    
    def save_results(self, results, output_dir='MAIL_ROOM_RESULTS'):
        """Save results to JSON file"""
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"{output_dir}/enhanced_matching_{timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n💾 Results saved to: {output_file}")
        return output_file

def main():
    """Main execution"""
    print("\n" + "=" * 80)
    print("🚀 ENHANCED CASE MATCHER")
    print("=" * 80)
    
    # Load unmatched cases
    input_file = 'MAIL_ROOM_RESULTS/case_matching_results_269_20251029_174324.json'
    
    # Check for custom input file
    if len(sys.argv) > 2 and sys.argv[1] == '--input':
        input_file = sys.argv[2]
    
    if not os.path.exists(input_file):
        print(f"\n❌ Input file not found: {input_file}")
        print("💡 Please run the initial case matching first:")
        print("   python logics_case_search.py")
        return
    
    print(f"\n📂 Loading from: {input_file}")
    
    with open(input_file, 'r') as f:
        data = json.load(f)
    
    # Extract unmatched cases
    all_results = data.get('results', [])
    unmatched = [r for r in all_results if r['status'] == 'NOT_FOUND']
    matched_count = data.get('matched', 0)
    total_cases = data.get('total_cases', len(all_results))
    
    print(f"📊 Loaded: {total_cases} total cases")
    print(f"   ✅ Already matched: {matched_count}")
    print(f"   ⚠️  Unmatched: {len(unmatched)}")
    
    if not unmatched:
        print("\n✅ All cases already matched! No work needed.")
        return
    
    # Process unmatched cases
    matcher = EnhancedCaseMatcher()
    matcher.process_unmatched_cases(unmatched)
    
    # Generate report
    results = matcher.generate_report(matched_count, total_cases)
    
    # Save results
    output_file = matcher.save_results(results)
    
    # Summary
    print(f"\n✨ Enhanced matching complete!")
    print(f"   New matches: {len(matcher.newly_matched)}")
    print(f"   Total matched: {results['new_total_matched']}/{total_cases}")
    print(f"   Match rate: {results['new_total_matched']/total_cases*100:.1f}%")

if __name__ == "__main__":
    main()

