"""
DOCUMENT UPLOAD PREPARATION TOOL

This script generates the final upload list with proper naming convention:
{CaseID}_CP2000_{Date}.pdf

USAGE:
    python generate_upload_list.py

OUTPUT:
    - Upload list with old and new filenames
    - CSV for bulk operations
    - Excel report for review
"""

import json
import pandas as pd
import os
import re
from datetime import datetime

class UploadListGenerator:
    """Generate upload list with proper naming convention"""
    
    def __init__(self):
        self.matched_cases = []
        self.upload_list = []
        
    def extract_date_from_filename(self, filename):
        """Extract date from filename in various formats"""
        # Pattern 1: DTD MM.DD.YYYY
        pattern1 = r'DTD[_ ](\d{2})[._](\d{2})[._](\d{4})'
        match = re.search(pattern1, filename)
        if match:
            month, day, year = match.groups()
            return f"{month}.{day}.{year}"
        
        # Pattern 2: DTD MM DD YYYY (with spaces)
        pattern2 = r'DTD[_ ](\d{2})[_ ](\d{2})[_ ](\d{4})'
        match = re.search(pattern2, filename)
        if match:
            month, day, year = match.groups()
            return f"{month}.{day}.{year}"
        
        # Pattern 3: YYYY_MM_DD or YYYY-MM-DD
        pattern3 = r'(\d{4})[_-](\d{2})[_-](\d{2})'
        match = re.search(pattern3, filename)
        if match:
            year, month, day = match.groups()
            return f"{month}.{day}.{year}"
        
        # Default: use today's date
        return datetime.now().strftime("%m.%d.%Y")
    
    def generate_new_filename(self, case_id, original_filename, case_info):
        """Generate new filename: IRS_CORR_{Letter Type}_{Tax Year}_DTD {Date}_{Last Name}.pdf"""
        # Extract date
        date = self.extract_date_from_filename(original_filename)
        
        # Get letter type (default to CP2000)
        letter_type = case_info.get('letter_type', 'CP2000')
        if not letter_type:
            letter_type = 'CP2000'
        
        # Get tax year
        tax_year = case_info.get('tax_year', '')
        if not tax_year:
            tax_year = '2021'  # Default
        
        # Get last name (uppercase)
        last_name = case_info.get('last_name', '').upper()
        
        # Generate new filename: IRS_CORR_{Letter Type}_{Tax Year}_DTD {Date}_{Last Name}.pdf
        new_filename = f"IRS_CORR_{letter_type}_{tax_year}_DTD {date}_{last_name}.pdf"
        
        return new_filename
    
    def load_matched_cases(self):
        """Load all matched cases from both files"""
        print("📂 Loading matched cases...")
        
        # Load initial matches (163)
        initial_file = 'MAIL_ROOM_RESULTS/case_matching_results_269_20251029_174324.json'
        if os.path.exists(initial_file):
            with open(initial_file, 'r') as f:
                initial_data = json.load(f)
            
            # Extract matched cases
            for result in initial_data.get('results', []):
                if result['status'] == 'MATCHED' and result.get('case_id'):
                    self.matched_cases.append({
                        'case_id': result['case_id'],
                        'filename': result['filename'],
                        'last_name': result['last_name'],
                        'ssn_last_4': result['ssn_last_4'],
                        'tax_year': result.get('tax_year'),
                        'response_due_date': result.get('response_due_date'),
                        'match_type': result.get('match_type', 'initial'),
                        'source': 'initial_match'
                    })
            
            print(f"   ✅ Loaded {len(self.matched_cases)} from initial matching")
        
        # Load enhanced matches (+6)
        enhanced_file = 'MAIL_ROOM_RESULTS/enhanced_matching_20251029_191126.json'
        if os.path.exists(enhanced_file):
            with open(enhanced_file, 'r') as f:
                enhanced_data = json.load(f)
            
            # Extract newly matched cases
            for match in enhanced_data.get('newly_matched', []):
                orig_case = match['original_case']
                self.matched_cases.append({
                    'case_id': match['case_id'],
                    'filename': orig_case['filename'],
                    'last_name': orig_case['last_name'],
                    'ssn_last_4': orig_case['ssn_last_4'],
                    'tax_year': orig_case.get('tax_year'),
                    'response_due_date': orig_case.get('response_due_date'),
                    'match_type': match['strategy'],
                    'source': 'enhanced_match'
                })
            
            print(f"   ✅ Loaded {len(enhanced_data.get('newly_matched', []))} from enhanced matching")
        
        print(f"\n📊 Total matched cases: {len(self.matched_cases)}")
        return len(self.matched_cases)
    
    def generate_upload_list(self):
        """Generate upload list with naming convention"""
        print("\n🎯 Generating upload list with naming convention...")
        
        for idx, case in enumerate(self.matched_cases, 1):
            old_filename = case['filename']
            new_filename = self.generate_new_filename(case['case_id'], old_filename, case)
            
            self.upload_list.append({
                'Index': idx,
                'Case_ID': case['case_id'],
                'Old_Filename': old_filename,
                'New_Filename': new_filename,
                'Last_Name': case['last_name'],
                'SSN_Last_4': case['ssn_last_4'],
                'Tax_Year': case.get('tax_year', ''),
                'Response_Due_Date': case.get('response_due_date', ''),
                'Match_Type': case['match_type'],
                'Source': case['source'],
                'Status': 'Ready_for_Upload'
            })
        
        print(f"   ✅ Generated {len(self.upload_list)} upload entries")
        
        # Show sample
        print(f"\n📝 Sample entries:")
        for i in range(min(5, len(self.upload_list))):
            entry = self.upload_list[i]
            print(f"   {i+1}. {entry['Old_Filename'][:50]:50s}")
            print(f"      → {entry['New_Filename']}")
            print()
    
    def save_outputs(self):
        """Save upload list in multiple formats"""
        print("💾 Saving output files...")
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        os.makedirs('UPLOAD_READY', exist_ok=True)
        
        # Convert to DataFrame
        df = pd.DataFrame(self.upload_list)
        
        # 1. Save as CSV (for bulk operations)
        csv_file = f'UPLOAD_READY/upload_list_{timestamp}.csv'
        df.to_csv(csv_file, index=False)
        print(f"   ✅ CSV: {csv_file}")
        
        # 2. Save as Excel (with formatting)
        excel_file = f'UPLOAD_READY/upload_list_{timestamp}.xlsx'
        with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Upload List', index=False)
            
            # Auto-adjust column widths
            worksheet = writer.sheets['Upload List']
            for idx, col in enumerate(df.columns):
                max_length = max(
                    df[col].astype(str).map(len).max(),
                    len(col)
                ) + 2
                worksheet.column_dimensions[chr(65 + idx)].width = min(max_length, 60)
        
        print(f"   ✅ Excel: {excel_file}")
        
        # 3. Save as JSON (for automation)
        json_file = f'UPLOAD_READY/upload_list_{timestamp}.json'
        with open(json_file, 'w') as f:
            json.dump({
                'generated_at': datetime.now().isoformat(),
                'total_files': len(self.upload_list),
                'upload_list': self.upload_list
            }, f, indent=2)
        print(f"   ✅ JSON: {json_file}")
        
        # 4. Save naming convention reference
        ref_file = 'UPLOAD_READY/NAMING_CONVENTION_REFERENCE.txt'
        with open(ref_file, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("DOCUMENT NAMING CONVENTION REFERENCE\n")
            f.write("=" * 80 + "\n\n")
            f.write("Format: IRS_CORR_{Letter Type}_{Tax Year}_DTD {Date}_{Last Name}.pdf\n\n")
            f.write("Example: IRS_CORR_CP2000_2021_DTD 05.06.2024_NEALE.pdf\n\n")
            f.write("Components:\n")
            f.write("  • IRS_CORR: Prefix (constant)\n")
            f.write("  • Letter Type: CP2000, CP2501, LTR3172, CP566, etc.\n")
            f.write("  • Tax Year: 2021, 2022, etc.\n")
            f.write("  • DTD Date: Notice date (MM.DD.YYYY)\n")
            f.write("  • Last Name: Taxpayer last name (UPPERCASE)\n\n")
            f.write("Examples:\n")
            for i in range(min(10, len(self.upload_list))):
                entry = self.upload_list[i]
                f.write(f"\n{i+1}. Case ID: {entry['Case_ID']}\n")
                f.write(f"   Old: {entry['Old_Filename']}\n")
                f.write(f"   New: {entry['New_Filename']}\n")
            f.write("\n" + "=" * 80 + "\n")
            f.write(f"Total files ready for upload: {len(self.upload_list)}\n")
        
        print(f"   ✅ Reference: {ref_file}")
        
        return {
            'csv_file': csv_file,
            'excel_file': excel_file,
            'json_file': json_file,
            'ref_file': ref_file
        }
    
    def generate_statistics(self):
        """Generate upload statistics"""
        print("\n" + "=" * 80)
        print("📊 UPLOAD PREPARATION STATISTICS")
        print("=" * 80)
        
        df = pd.DataFrame(self.upload_list)
        
        print(f"\nTotal Files Ready: {len(self.upload_list)}")
        
        # By source
        print(f"\nBy Source:")
        for source, count in df['Source'].value_counts().items():
            print(f"   • {source}: {count} files")
        
        # By match type
        print(f"\nBy Match Type:")
        for match_type, count in df['Match_Type'].value_counts().items():
            print(f"   • {match_type}: {count} files")
        
        # By tax year
        if 'Tax_Year' in df.columns:
            print(f"\nBy Tax Year:")
            tax_years = df['Tax_Year'].value_counts().head(5)
            for year, count in tax_years.items():
                if year:
                    print(f"   • {year}: {count} files")
        
        print("\n" + "=" * 80)
    
    def run(self):
        """Main execution"""
        print("\n" + "=" * 80)
        print("🚀 DOCUMENT UPLOAD PREPARATION TOOL")
        print("=" * 80)
        
        # Load matched cases
        total = self.load_matched_cases()
        
        if total == 0:
            print("\n❌ No matched cases found!")
            return
        
        # Generate upload list
        self.generate_upload_list()
        
        # Save outputs
        files = self.save_outputs()
        
        # Statistics
        self.generate_statistics()
        
        # Summary
        print("\n✨ PREPARATION COMPLETE!")
        print(f"\n📂 Output Location: UPLOAD_READY/")
        print(f"\n📄 Files Generated:")
        print(f"   • CSV (bulk operations): {os.path.basename(files['csv_file'])}")
        print(f"   • Excel (review): {os.path.basename(files['excel_file'])}")
        print(f"   • JSON (automation): {os.path.basename(files['json_file'])}")
        print(f"   • Reference guide: {os.path.basename(files['ref_file'])}")
        
        print(f"\n🎯 Ready for upload: {len(self.upload_list)} files")
        print(f"\n💡 Next Step: Download PDFs from Google Drive and rename using upload list")
        print("\n" + "=" * 80)

if __name__ == "__main__":
    generator = UploadListGenerator()
    generator.run()

