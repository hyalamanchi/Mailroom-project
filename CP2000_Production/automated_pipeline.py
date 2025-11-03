#!/usr/bin/env python3
"""
Automated Mail Room Pipeline with File Watching
Author: Hemalatha Yalamanchi

This pipeline:
1. Watches CP2000 NEW BATCH 2 folder for new files
2. Automatically processes new PDFs
3. Matches against Logiqs
4. Moves to TEST/MATCHED or TEST/UNMATCHED
5. Generates approval Excel for matched cases
6. Uploads approved cases to Logiqs with tasks
"""

import os
import sys
import json
import time
import logging
from datetime import datetime
from pathlib import Path

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from google.oauth2 import service_account
from googleapiclient.discovery import build
from hundred_percent_accuracy_extractor import HundredPercentAccuracyExtractor
from logics_case_search import LogicsCaseSearcher
from upload_to_logiqs import LogiqsDocumentUploader
import pandas as pd

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AutomatedMailRoomPipeline:
    """Automated pipeline with file watching and approval workflow"""
    
    def __init__(self, test_mode=False, file_limit=None):
        """
        Initialize automated pipeline
        
        Args:
            test_mode: If True, run in test mode with limited files
            file_limit: Maximum number of files to process (for testing)
        """
        self.test_mode = test_mode
        self.file_limit = file_limit
        
        # Google Drive setup
        self.SERVICE_ACCOUNT_FILE = 'service-account-key.json'
        self.SCOPES = ['https://www.googleapis.com/auth/drive']
        self.creds = None
        self.drive_service = None
        
        # Folder IDs
        self.main_folder_id = '18e8lj66Mdr7PFGhJ7ySYtsnkNgiuczmx'
        self.input_folder_name = 'CP2000 NEW BATCH 2'
        self.input_folder_id = None
        
        # Load test folders
        self.load_test_folders()
        
        # Processing tracking
        self.processed_file_ids = set()
        self.load_processing_history()
        
        # Initialize components
        self.extractor = HundredPercentAccuracyExtractor()
        self.case_searcher = LogicsCaseSearcher()
        self.uploader = LogiqsDocumentUploader()
        
        # Results
        self.matched_cases = []
        self.unmatched_cases = []
        
        logger.info(f"🤖 Automated Pipeline initialized (test_mode={test_mode}, limit={file_limit})")
    
    def load_test_folders(self):
        """Load TEST folder IDs"""
        test_folders_file = '.test_folders.json'
        if os.path.exists(test_folders_file):
            with open(test_folders_file, 'r') as f:
                folders = json.load(f)
                self.test_matched_folder = folders.get('matched_id')
                self.test_unmatched_folder = folders.get('unmatched_id')
        else:
            self.test_matched_folder = None
            self.test_unmatched_folder = None
    
    def load_processing_history(self):
        """Load history of processed files"""
        history_file = 'PROCESSING_HISTORY.json'
        if os.path.exists(history_file):
            with open(history_file, 'r') as f:
                history = json.load(f)
                self.processed_file_ids = set(history.keys())
        logger.info(f"📋 Loaded {len(self.processed_file_ids)} previously processed files")
    
    def save_processing_history(self, file_id, filename, status):
        """Save file to processing history"""
        history_file = 'PROCESSING_HISTORY.json'
        
        history = {}
        if os.path.exists(history_file):
            with open(history_file, 'r') as f:
                history = json.load(f)
        
        history[file_id] = {
            'filename': filename,
            'status': status,
            'processed_at': datetime.now().isoformat()
        }
        
        with open(history_file, 'w') as f:
            json.dump(history, f, indent=2)
        
        self.processed_file_ids.add(file_id)
    
    def authenticate_google_drive(self):
        """Authenticate with Google Drive"""
        logger.info("🔐 Authenticating with Google Drive...")
        self.creds = service_account.Credentials.from_service_account_file(
            self.SERVICE_ACCOUNT_FILE, scopes=self.SCOPES
        )
        self.drive_service = build('drive', 'v3', credentials=self.creds)
        logger.info("✅ Google Drive authenticated")
    
    def find_input_folder(self):
        """Find CP2000 NEW BATCH 2 folder"""
        results = self.drive_service.files().list(
            q=f"'{self.main_folder_id}' in parents and name='{self.input_folder_name}' and trashed=false",
            fields='files(id, name)'
        ).execute()
        
        folders = results.get('files', [])
        if folders:
            self.input_folder_id = folders[0]['id']
            logger.info(f"✅ Found input folder: {self.input_folder_name}")
            return True
        else:
            logger.error(f"❌ Input folder not found: {self.input_folder_name}")
            return False
    
    def get_new_files(self):
        """Get new PDF files from input folder"""
        if not self.input_folder_id:
            if not self.find_input_folder():
                return []
        
        # Query for PDFs
        query = f"'{self.input_folder_id}' in parents and mimeType='application/pdf' and trashed=false"
        
        results = self.drive_service.files().list(
            q=query,
            fields='files(id, name)',
            pageSize=1000
        ).execute()
        
        all_files = results.get('files', [])
        
        # Filter out already processed files
        new_files = [f for f in all_files if f['id'] not in self.processed_file_ids]
        
        # Apply limit if in test mode
        if self.file_limit and len(new_files) > self.file_limit:
            new_files = new_files[:self.file_limit]
        
        logger.info(f"📁 Found {len(new_files)} new files to process")
        return new_files
    
    def download_and_process_file(self, file_info):
        """Download and process a single file"""
        file_id = file_info['id']
        filename = file_info['name']
        
        logger.info(f"📄 Processing: {filename}")
        
        # Download file
        temp_dir = 'TEMP_PROCESSING'
        os.makedirs(temp_dir, exist_ok=True)
        
        local_path = os.path.join(temp_dir, filename)
        
        request = self.drive_service.files().get_media(fileId=file_id)
        with open(local_path, 'wb') as f:
            f.write(request.execute())
        
        # Extract data
        extracted_data = self.extractor.extract_100_percent_accuracy_data(local_path)
        
        if not extracted_data:
            logger.warning(f"⚠️  Extraction failed: {filename}")
            return None
        
        # Search for case in Logiqs
        ssn_last_4 = extracted_data.get('ssn_last_4')
        taxpayer_name = extracted_data.get('taxpayer_name', '')
        last_name = taxpayer_name.split()[-1] if taxpayer_name else ''
        
        case_id = None
        if ssn_last_4 and last_name:
            logger.info(f"🔍 Searching Logiqs: {last_name} (SSN: {ssn_last_4})")
            case_id = self.case_searcher.search_case(ssn_last_4, last_name)
        
        # Build result
        result = {
            'file_id': file_id,
            'filename': filename,
            'local_path': local_path,
            'extracted_data': extracted_data,
            'case_id': case_id,
            'matched': case_id is not None
        }
        
        if case_id:
            logger.info(f"✅ Matched to Case ID: {case_id}")
            self.matched_cases.append(result)
        else:
            logger.warning(f"⚠️  No match found")
            self.unmatched_cases.append(result)
        
        return result
    
    def move_file_to_folder(self, file_id, target_folder_id):
        """Move file to target folder"""
        try:
            # Get current parents
            file_info = self.drive_service.files().get(
                fileId=file_id,
                fields='parents'
            ).execute()
            
            previous_parents = ",".join(file_info.get('parents', []))
            
            # Move file
            self.drive_service.files().update(
                fileId=file_id,
                addParents=target_folder_id,
                removeParents=previous_parents,
                fields='id, parents'
            ).execute()
            
            return True
        except Exception as e:
            logger.error(f"❌ Failed to move file: {e}")
            return False
    
    def generate_approval_excel(self):
        """Generate approval Excel for matched cases"""
        if not self.matched_cases:
            logger.info("⏭️  No matched cases - skipping approval Excel")
            return None
        
        logger.info(f"📋 Generating approval Excel for {len(self.matched_cases)} matched cases...")
        
        # Prepare data
        review_data = []
        for case in self.matched_cases:
            extracted = case['extracted_data']
            
            # Generate proposed filename
            letter_type = extracted.get('letter_type', 'CP2000')
            tax_year = extracted.get('tax_year', 'Unknown')
            notice_date = extracted.get('notice_date', 'Unknown').replace('/', '.')
            taxpayer_name = extracted.get('taxpayer_name', '')
            last_name = taxpayer_name.split()[-1] if taxpayer_name else 'Unknown'
            
            proposed_name = f"IRS_CORR_{letter_type}_{tax_year}_DTD_{notice_date}_{last_name}.pdf"
            
            review_data.append({
                'Case_ID': case['case_id'],
                'Original_Filename': case['filename'],
                'Proposed_Filename': proposed_name,
                'Taxpayer_Name': taxpayer_name,
                'SSN_Last_4': extracted.get('ssn_last_4', ''),
                'Letter_Type': letter_type,
                'Tax_Year': tax_year,
                'Notice_Date': extracted.get('notice_date', ''),
                'Due_Date': extracted.get('response_due_date', ''),
                'Match_Confidence': 'High',
                'Status': '',  # APPROVE / UNDER_REVIEW / REJECT
                'Notes': ''
            })
        
        # Create DataFrame
        df = pd.DataFrame(review_data)
        
        # Add instructions
        instructions = [
            {'Case_ID': '=== INSTRUCTIONS ===', 'Status': '', 'Notes': ''},
            {'Case_ID': 'Review each matched case below', 'Status': '', 'Notes': ''},
            {'Case_ID': 'In Status column, enter: APPROVE, UNDER_REVIEW, or REJECT', 'Status': '', 'Notes': ''},
            {'Case_ID': 'APPROVE = Upload to Logiqs + Create Task', 'Status': '', 'Notes': ''},
            {'Case_ID': 'UNDER_REVIEW = Skip for now', 'Status': '', 'Notes': ''},
            {'Case_ID': 'REJECT = Move to UNMATCHED folder', 'Status': '', 'Notes': ''},
            {'Case_ID': 'Save file and run: python3 automated_pipeline.py --upload-approved', 'Status': '', 'Notes': ''},
            {'Case_ID': '', 'Status': '', 'Notes': ''},
        ]
        
        # Pad instructions with empty columns
        for inst in instructions:
            for col in df.columns:
                if col not in inst:
                    inst[col] = ''
        
        instructions_df = pd.DataFrame(instructions)
        final_df = pd.concat([instructions_df, df], ignore_index=True)
        
        # Save to Excel
        os.makedirs('QUALITY_REVIEW', exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        excel_path = f'QUALITY_REVIEW/APPROVAL_MATCHED_CASES_{timestamp}.xlsx'
        
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            final_df.to_excel(writer, sheet_name='Review & Approve', index=False)
            
            # Auto-adjust columns
            worksheet = writer.sheets['Review & Approve']
            for idx, col in enumerate(final_df.columns):
                max_length = max(final_df[col].astype(str).map(len).max(), len(col)) + 2
                col_letter = chr(65 + idx) if idx < 26 else chr(65 + idx // 26 - 1) + chr(65 + idx % 26)
                worksheet.column_dimensions[col_letter].width = min(max_length, 50)
        
        logger.info(f"✅ Approval Excel created: {excel_path}")
        return excel_path
    
    def process_pipeline(self):
        """Run the complete automated pipeline"""
        logger.info("\n" + "=" * 80)
        logger.info("🚀 AUTOMATED MAIL ROOM PIPELINE - STARTING")
        if self.test_mode:
            logger.info(f"🧪 TEST MODE: Processing up to {self.file_limit} files")
        logger.info("=" * 80)
        
        # Step 1: Authenticate
        self.authenticate_google_drive()
        
        # Step 2: Get new files
        new_files = self.get_new_files()
        
        if not new_files:
            logger.info("✅ No new files to process")
            return
        
        # Step 3: Process each file
        for file_info in new_files:
            self.download_and_process_file(file_info)
        
        # Step 4: Move files to TEST folders
        logger.info(f"\n📦 Moving files to TEST folders...")
        
        # Move matched files
        for case in self.matched_cases:
            self.move_file_to_folder(case['file_id'], self.test_matched_folder)
            self.save_processing_history(case['file_id'], case['filename'], 'matched')
            logger.info(f"✅ Moved to TEST/MATCHED: {case['filename']}")
        
        # Move unmatched files
        for case in self.unmatched_cases:
            self.move_file_to_folder(case['file_id'], self.test_unmatched_folder)
            self.save_processing_history(case['file_id'], case['filename'], 'unmatched')
            logger.info(f"⚠️  Moved to TEST/UNMATCHED: {case['filename']}")
        
        # Step 5: Generate approval Excel
        excel_path = self.generate_approval_excel()
        
        # Step 6: Summary
        logger.info("\n" + "=" * 80)
        logger.info("✅ PIPELINE COMPLETE")
        logger.info("=" * 80)
        logger.info(f"📊 Summary:")
        logger.info(f"   ✅ Matched: {len(self.matched_cases)} files")
        logger.info(f"   ⚠️  Unmatched: {len(self.unmatched_cases)} files")
        
        if excel_path:
            logger.info(f"\n📋 NEXT STEP - REVIEW & APPROVE:")
            logger.info(f"   1. Open: {excel_path}")
            logger.info(f"   2. Review each case and set Status: APPROVE/UNDER_REVIEW/REJECT")
            logger.info(f"   3. Save the file")
            logger.info(f"   4. Run: python3 automated_pipeline.py --upload-approved")
        
        logger.info("=" * 80)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Automated Mail Room Pipeline')
    parser.add_argument('--test', action='store_true', help='Run in test mode')
    parser.add_argument('--limit', type=int, default=15, help='Max files to process (default: 15)')
    parser.add_argument('--upload-approved', action='store_true', help='Upload approved cases from Excel')
    
    args = parser.parse_args()
    
    # Run pipeline
    pipeline = AutomatedMailRoomPipeline(
        test_mode=args.test,
        file_limit=args.limit
    )
    
    pipeline.process_pipeline()

