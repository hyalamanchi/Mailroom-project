"""
DATE VALIDATION AND CORRECTION SCRIPT

Fixes OCR errors in notice dates and due dates:
- Future dates (2026-2028) → Corrected to 2024-2025
- Validates due dates are 30-60 days from notice date
- Ensures notice dates are in the past

LOGIC:
1. Notice date MUST be in the past (we already have the letter)
2. Due date = Notice date + 30 days (typical IRS timeline)
3. Common OCR errors: 2024→2028, 2024→2026, 2025→2028

USAGE:
    python3 fix_date_errors.py
"""

import json
import os
from datetime import datetime, timedelta
from dateutil import parser
import re

class DateValidator:
    """Validates and corrects date errors in extracted data"""
    
    def __init__(self):
        self.current_year = datetime.now().year  # 2025
        self.current_date = datetime.now()
        
        # Statistics
        self.total_cases = 0
        self.corrected_notice_dates = 0
        self.corrected_due_dates = 0
        self.invalid_cases = []
        self.corrections = []
    
    def parse_date(self, date_string: str) -> datetime:
        """Parse various date formats"""
        try:
            if not date_string:
                return None
            return parser.parse(date_string)
        except:
            return None
    
    def correct_year_ocr_error(self, date_str: str, original_date: datetime) -> tuple:
        """
        Correct common OCR year errors
        2028 → 2024 or 2025 (most common)
        2026 → 2024
        2027 → 2024
        """
        if not date_str or not original_date:
            return date_str, original_date, False
        
        year = original_date.year
        corrected = False
        
        # If year is in the future, try corrections
        if year > self.current_year:
            # Try 2024 first (most common for tax year 2021-2022)
            possible_years = [2024, 2023, self.current_year]
            
            for test_year in possible_years:
                test_date = original_date.replace(year=test_year)
                
                # Check if this makes sense (date is in the past)
                if test_date < self.current_date:
                    corrected_date = test_date
                    corrected_str = corrected_date.strftime("%B %d, %Y")
                    corrected = True
                    return corrected_str, corrected_date, corrected
        
        return date_str, original_date, corrected
    
    def validate_and_fix_dates(self, case: dict) -> dict:
        """Validate and fix dates for a single case"""
        corrections_made = []
        
        # Parse original dates
        notice_date_str = case.get('notice_date', '')
        due_date_str = case.get('response_due_date', '')
        
        notice_date = self.parse_date(notice_date_str)
        due_date = self.parse_date(due_date_str)
        
        # Fix notice date if in future
        if notice_date and notice_date > self.current_date:
            old_notice = notice_date_str
            corrected_str, corrected_date, was_corrected = self.correct_year_ocr_error(
                notice_date_str, notice_date
            )
            
            if was_corrected:
                case['notice_date'] = corrected_str
                case['notice_date_original'] = old_notice
                case['notice_date_corrected'] = True
                notice_date = corrected_date
                self.corrected_notice_dates += 1
                corrections_made.append(f"Notice date: {old_notice} → {corrected_str}")
        
        # Fix due date if in future or invalid
        if due_date and notice_date:
            # Calculate expected due date (30 days from notice)
            expected_due_date = notice_date + timedelta(days=30)
            
            # If due date is way off, recalculate
            if due_date > self.current_date or abs((due_date - expected_due_date).days) > 60:
                old_due = due_date_str
                corrected_due_str = expected_due_date.strftime("%B %d, %Y")
                
                case['response_due_date'] = corrected_due_str
                case['response_due_date_original'] = old_due
                case['response_due_date_corrected'] = True
                due_date = expected_due_date
                self.corrected_due_dates += 1
                corrections_made.append(f"Due date: {old_due} → {corrected_due_str}")
        
        # Recalculate days remaining
        if notice_date and due_date:
            days_remaining = (due_date - self.current_date).days
            case['days_remaining'] = days_remaining
            
            # Update urgency status
            if days_remaining < 0:
                case['urgency_status'] = 'OVERDUE'
                case['urgency_level'] = 'CRITICAL'
            elif days_remaining < 7:
                case['urgency_status'] = 'URGENT'
                case['urgency_level'] = 'HIGH'
            elif days_remaining < 15:
                case['urgency_status'] = 'PENDING'
                case['urgency_level'] = 'MEDIUM'
            else:
                case['urgency_status'] = 'PENDING'
                case['urgency_level'] = 'LOW'
        
        # Track corrections
        if corrections_made:
            self.corrections.append({
                'filename': case.get('filename', 'Unknown'),
                'taxpayer_name': case.get('taxpayer_name', 'Unknown'),
                'corrections': corrections_made
            })
        
        return case
    
    def process_file(self, input_file: str, output_file: str = None):
        """Process and fix dates in JSON file"""
        print("\n" + "=" * 80)
        print("🔧 DATE VALIDATION AND CORRECTION")
        print("=" * 80)
        print(f"\n📂 Input: {input_file}")
        
        # Load data
        with open(input_file, 'r') as f:
            data = json.load(f)
        
        # Get case data
        if isinstance(data, dict) and 'case_matching_data' in data:
            cases = data['case_matching_data']
            metadata = data.get('extraction_metadata', {})
        elif isinstance(data, list):
            cases = data
            metadata = {}
        else:
            print("❌ Unexpected data format")
            return
        
        self.total_cases = len(cases)
        print(f"📊 Total cases: {self.total_cases}")
        print(f"📅 Current date: {self.current_date.strftime('%B %d, %Y')}")
        print(f"📅 Current year: {self.current_year}")
        
        # Process each case
        print("\n🔍 Scanning for date errors...")
        
        for i, case in enumerate(cases, 1):
            cases[i-1] = self.validate_and_fix_dates(case)
            
            if i % 50 == 0:
                print(f"   Processed: {i}/{self.total_cases}")
        
        # Update metadata
        if metadata:
            metadata['date_correction_applied'] = True
            metadata['date_correction_timestamp'] = datetime.now().isoformat()
            metadata['corrections_count'] = len(self.corrections)
        
        # Save corrected data
        if output_file is None:
            # Create new filename
            base, ext = os.path.splitext(input_file)
            output_file = f"{base}_DATE_CORRECTED{ext}"
        
        corrected_data = {
            'extraction_metadata': metadata,
            'case_matching_data': cases,
            'date_corrections': {
                'total_corrections': len(self.corrections),
                'notice_dates_corrected': self.corrected_notice_dates,
                'due_dates_corrected': self.corrected_due_dates,
                'correction_details': self.corrections
            }
        }
        
        with open(output_file, 'w') as f:
            json.dump(corrected_data, f, indent=2)
        
        print(f"\n✅ Processing complete!")
        print(f"💾 Output: {output_file}")
        
        # Print summary
        self.print_summary()
        
        return output_file
    
    def print_summary(self):
        """Print correction summary"""
        print("\n" + "=" * 80)
        print("📊 CORRECTION SUMMARY")
        print("=" * 80)
        
        print(f"\nTotal Cases: {self.total_cases}")
        print(f"Notice Dates Corrected: {self.corrected_notice_dates}")
        print(f"Due Dates Corrected: {self.corrected_due_dates}")
        print(f"Total Corrections: {len(self.corrections)}")
        
        if self.corrections:
            print("\n🔧 Corrections Made:")
            for i, corr in enumerate(self.corrections[:10], 1):
                print(f"\n{i}. {corr['taxpayer_name']} - {corr['filename']}")
                for fix in corr['corrections']:
                    print(f"   • {fix}")
            
            if len(self.corrections) > 10:
                print(f"\n   ... and {len(self.corrections) - 10} more")
        else:
            print("\n✅ No corrections needed - all dates are valid!")
        
        print("\n" + "=" * 80)
        print("✅ Date validation complete!")
        print("=" * 80)

def main():
    """Main execution"""
    validator = DateValidator()
    
    # Find the latest extraction file
    data_files = [f for f in os.listdir('.') if f.startswith('LOGICS_DATA_') and f.endswith('.json')]
    
    if not data_files:
        print("❌ No LOGICS_DATA file found!")
        return
    
    latest_file = sorted(data_files)[-1]
    
    print("\n" + "=" * 80)
    print("🔧 DATE VALIDATION AND CORRECTION TOOL")
    print("=" * 80)
    print(f"\n📂 Found: {latest_file}")
    print("\n📋 This script will:")
    print("   1. Scan all notice dates and due dates")
    print("   2. Fix future dates (2026-2028 → 2024-2025)")
    print("   3. Recalculate due dates (notice date + 30 days)")
    print("   4. Update urgency status based on corrected dates")
    print("   5. Save corrected data to new file")
    
    response = input("\nProceed with date correction? (yes/no): ")
    
    if response.lower() != 'yes':
        print("Cancelled.")
        return
    
    # Process file
    output_file = validator.process_file(latest_file)
    
    print(f"\n💡 Next Steps:")
    print(f"   1. Review: {output_file}")
    print(f"   2. Re-run matching if needed")
    print(f"   3. Regenerate upload list: python3 generate_upload_list.py")
    print(f"   4. Upload to Logiqs: python3 upload_to_logiqs.py")

if __name__ == "__main__":
    main()

